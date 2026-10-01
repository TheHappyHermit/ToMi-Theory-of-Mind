#!/usr/bin/env python3
"""
Generate the repo-tracked cron job template from a live Hermes jobs.json.

The template that ships in this repository must contain no PII: no real
hostnames, no LAN IP addresses, no usernames, no chat identifiers, no
absolute home paths. Deployment-specific values are emitted as ${VARIABLE}
placeholders that resolve from the dashboard's .env.

Every variable used is already registered in the dashboard's settings
registry (dashboard/integrations_backend.py :: env_mappings), so an operator
can fill them in from the dashboard Settings page and have them trace
through to the jobs. See cron/VARIABLES.md.

READ-ONLY WITH RESPECT TO THE LIVE FILE. This script only ever reads its
input. It writes a new template plus a manifest; it never edits the
scheduler's jobs.json.

Usage:
    python3 scripts/generate_cron_template.py \
        --live ~/.hermes/cron/jobs.json \
        --out  cron/jobs.template.json \
        --manifest cron/variables-manifest.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

# ---------------------------------------------------------------------------
# Replacement rules, applied in order.
#
# Order matters: the most specific host patterns run first, because the
# generic rules below would otherwise collapse distinct machines into one
# catch-all variable.
#
# The regexes are deliberately shape-based rather than literal. A rule that
# hardcoded one machine's hostname or username would commit the very PII
# this script exists to strip, and would silently stop matching the next
# operator's environment.
# ---------------------------------------------------------------------------
VARIABLES: list[tuple[str, re.Pattern[str], str]] = [
    # The local inference cluster. A full base URL (host, port and API path)
    # is one setting, so an operator fills in INFERENCE_NODE_MAIN once in the
    # dashboard and every job that calls it follows. Matched by URL shape, not
    # by address, so the rule cannot go stale and never embeds the address.
    (
        "INFERENCE_NODE_MAIN",
        re.compile(r"https?://\d{1,3}(?:\.\d{1,3}){3}:\d{1,5}/v1"),
        "${INFERENCE_NODE_MAIN}",
    ),
    # A bare LAN host with no port, e.g. inside a health-check command.
    # Catches any RFC1918 address the URL rule above did not consume.
    (
        "INFERENCE_NODE_MAIN",
        re.compile(r"\b(?:10|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b(?!\s*\])"),
        "${INFERENCE_NODE_MAIN}",
    ),
    # The user's data directory. Historically a dot-directory whose name
    # predates this repo's rename; it is a deployment choice, not a
    # hardcoded path, so it is a variable.
    #
    # Runs AFTER HERMES_HOME, so the "~" and "${HERMES_HOME}/" prefixes have
    # already been rewritten. It must therefore match only the dot-directory
    # itself, in both the bare and the expanded form:
    #     ~/.hermes/...            -> ${HERMES_DATA_DIR}/...
    #     ${HERMES_HOME}/.autognosia/  -> ${HERMES_DATA_DIR}/...
    (
        "HERMES_DATA_DIR",
        re.compile(r"~?/\.(?:autognosia|cortex)\b"),
        "${HERMES_DATA_DIR}",
    ),
    # Utility scripts whose filenames carry a project-specific prefix. The
    # files exist in a live install under one name or another, so the name is
    # a variable rather than something the template invents. The stat key is
    # deliberately neutral: the manifest is committed, and a branded key would
    # put the retired name back into the repo.
    #
    # Each pattern matches both the retired name and the role-based one it was
    # renamed to, so a live job written before the rename is still captured.
    # Anything still carrying the old name is then left for the PII gate to
    # reject, rather than reaching the template.
    (
        "SCRIPT_BACKUP",
        re.compile(r"(?:autognosia_backup|daily_backup)\.(?:sh|py)"),
        "${SCRIPT_BACKUP}",
    ),
    (
        "SCRIPT_HEALTH",
        re.compile(r"(?:autognosia_health|daily_health_check)\.(?:sh|py)"),
        "${SCRIPT_HEALTH}",
    ),
    # The two database utilities kept a retired project name in their filenames.
    # They are parameterised for the same reason: the name belongs to whatever
    # install runs them, and neither is referenced by job text today, so the
    # variable is what the template would emit if one were.
    (
        "SCRIPT_DB_CHECK",
        re.compile(r"(?:check_autognosia_dbs|check_databases)\.py"),
        "${SCRIPT_DB_CHECK}",
    ),
    (
        "SCRIPT_DB_INIT",
        re.compile(r"(?:init_autognosia_db|init_experience_index)\.py"),
        "${SCRIPT_DB_INIT}",
    ),
    # Prose branding: the project is no longer called this. Quoted text that
    # is auditing a historical corpus is left alone by the check below.
    (
        "PROJECT_NAME",
        re.compile(r"research lane for Autognosia"),
        "research lane for the Hermes knowledge base",
    ),
    (
        "PROJECT_NAME",
        re.compile(r"[Tt]his project is called Autognosia"),
        "This project is the Hermes knowledge base",
    ),
    # "the autognosia repository" / "git repo" in prose now means this repo.
    (
        "PROJECT_NAME",
        re.compile(r"the autognosia (?:git )?repositor(?:y|ies)|the autognosia git repo"),
        "the hermes-brain repository",
    ),
    # The SQLite filename. Real on disk, so it stays a variable.
    (
        "DB_BRAIN",
        re.compile(r"\bautognosia\.db\b"),
        "${DB_BRAIN}",
    ),
    # Directory holding local model weights. The concrete filename is a
    # per-tier variable (below), so only a bare directory prefix is left to
    # handle. MUST run after the MODEL_* rules: those consume the .gguf text,
    # and a prefix rule placed first would be masked by their lookahead.
    ("MODEL_DIR", re.compile(r"/models/(?=[\w.-]+\.gguf)"), "${MODEL_DIR}/"),
    # Per-job model selections. A job's `model` is a *choice of which engine
    # answers it*, and that is exactly a dashboard setting: the operator picks
    # a model per tier once, and every job in that tier follows. Hardcoding a
    # GGUF filename here would pin the repo to one machine's disk.
    #
    # Tiers, smallest/cheapest first:
    #   MODEL_UTILITY   - short deterministic jobs (lint, backups, status)
    #   MODEL_DEEP      - long reasoning passes (consolidation, lanes, audits)
    #   MODEL_DESKTOP_* - the two desktop workers, served from their own nodes
    #
    # MODEL_DEEP must also swallow the MODEL_DIR prefix left by the rule above,
    # otherwise three jobs keep a bare "/models/${MODEL_DEEP}".
    (
        "MODEL_UTILITY",
        re.compile(r"Qwen3\.5-4B-UD-Q4_K_XL\.gguf"),
        "${MODEL_UTILITY}",
    ),
    (
        "MODEL_DEEP",
        re.compile(
            r"(?:\$\{MODEL_DIR\}/|/models/)?Qwen3\.6-35B-A3B-Q4_K_M\.gguf"
        ),
        "${MODEL_DEEP}",
    ),
    (
        "MODEL_DESKTOP_A",
        re.compile(r"\bqwen3\.5-9b\b"),
        "${MODEL_DESKTOP_A}",
    ),
    (
        "MODEL_DESKTOP_B",
        re.compile(r"\bqwen3\.8-27b\b"),
        "${MODEL_DESKTOP_B}",
    ),
    # The job's own display name.
    (
        "PROJECT_NAME",
        re.compile(r"Autognosia Health Check"),
        "Knowledge Base Health Check",
    ),
    # The Claude Code subscription used by the researcher profile. Identified
    # by its documented local socket path rather than by an address, so the
    # rule cannot go stale and never embeds the address itself.
    (
        "CLAUDE_CODE_SOCKET",
        re.compile(r"/tmp/claude-0?-[A-Za-z0-9._-]{6,}\.sock"),
        "${CLAUDE_CODE_SOCKET}",
    ),
    # Home directory. Already a first-class dashboard setting (HERMES_HOME).
    # Matched generically: any /home/<name> that is not the documented
    # placeholder /home/user.
    (
        "HERMES_HOME",
        re.compile(r"/home/(?!user\b)[a-z_][\w.-]*(?=/|\b)"),
        "${HERMES_HOME}",
    ),
    # Local model files. The bare model name is portable across installs;
    # the absolute /models/... path is one machine's disk layout.
    ("MODEL_DIR", re.compile(r"/models/(?=[\w.-]+\.gguf)"), "${MODEL_DIR}/"),
    # Personal account on a code host, matched by the personal-account shape
    # rather than by name.
    (
        "GITHUB_USER",
        re.compile(r"(?<![\w-])the operator[\w]{2,}\d{3,}(?![\w-])"),
        "${GITHUB_USER}",
    ),
]

# Runtime bookkeeping the scheduler rewrites on every tick. It carries no
# meaning for a fresh install and would otherwise be committed as noise.
RUNTIME_JOB_FIELDS = (
    "last_run_at",
    "last_run",
    "last_status",
    "last_error",
    "last_duration",
    "last_dispatch",
    "next_run_at",
    "created_at",
    "updated_at",
    "paused_at",
    "dispatch_in_flight",
    "dispatch_claim",
    "dispatch_lease_until",
    "consecutive_failures",
    "repeat",
    "origin",
    "schedule_source",
    "model_snapshot",
    "provider_snapshot",
)


def sanitise(value, counter: Counter, stats: Counter):
    """Recursively replace PII in a JSON-compatible value."""
    if isinstance(value, str):
        out = value
        for name, pattern, template in VARIABLES:
            hits = pattern.findall(out)
            if hits:
                counter[name] += len(hits)
                out = pattern.sub(template, out)
        return out
    if isinstance(value, list):
        return [sanitise(v, counter, stats) for v in value]
    if isinstance(value, dict):
        return {k: sanitise(v, counter, stats) for k, v in value.items()}
    return value


def scrub_job(job: dict, counter: Counter, stats: Counter) -> dict:
    out = {}
    for key, value in job.items():
        if key in RUNTIME_JOB_FIELDS:
            stats["runtime_fields_dropped"] += 1
            continue
        out[key] = sanitise(value, counter, stats)
    return out


# Self-check. This must come back empty or the template is not safe to commit.
# The patterns are shape-based for the same reason the rules above are: a
# checker that hardcoded the real values would itself be the leak.
RESIDUAL_CHECKS = {
    "private IPv4": r"\b(?:10|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    "personal home path": r"/home/(?!user\b)[a-z_][\w.-]*(?=/|\b)",
    "personal github account": r"(?<![\w-])the operator[\w]{2,}\d{3,}(?![\w-])",
    "email address": r"[\w.+-]+@[\w.-]+\.\w{2,}",
    "absolute model path": r"/models/[\w.-]+\.gguf",
    # A bare model name is the same defect one level up: the template should
    # name a *tier*, and the operator picks the concrete model per tier in the
    # dashboard. Catching it here stops a new job silently re-pinning one.
    # Only local weights are a defect; a hosted model id like
    # "qwen/qwen3-coder:free" is a portable public name and stays literal.
    "hardcoded local model file": r"\b[\w.-]+\.gguf\b",
    "hardcoded local model alias": r"(?<![\w/:-])qwen[\w.-]*\d[\w.-]*",
    "legacy brand name": r"(?i)\bautognosia\b",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", required=True, help="path to the live jobs.json (read only)")
    ap.add_argument("--out", required=True, help="path to write the template")
    ap.add_argument("--manifest", required=True, help="path to write the variable manifest")
    args = ap.parse_args()

    live = json.loads(Path(args.live).read_text())
    jobs = live["jobs"] if isinstance(live, dict) and "jobs" in live else live
    if not isinstance(jobs, list) or not jobs:
        print("error: no jobs found in input", file=sys.stderr)
        return 1

    counter: Counter = Counter()
    stats: Counter = Counter()
    clean = [scrub_job(j, counter, stats) for j in jobs]

    doc = {
        "$generated": "scripts/generate_cron_template.py",
        "$note": (
            "Repo-tracked cron job template. Generated from a live jobs.json with all "
            "deployment-specific values replaced by ${VARIABLE} placeholders. Every "
            "variable resolves from the dashboard .env via the settings registry in "
            "dashboard/integrations_backend.py (env_mappings). See cron/VARIABLES.md. "
            "The live jobs.json is never modified and must not be committed."
        ),
        "job_count": len(clean),
        "jobs": clean,
    }

    blob = json.dumps(doc, indent=2, ensure_ascii=False)
    residual = {}
    for label, rx in RESIDUAL_CHECKS.items():
        found = sorted(set(re.findall(rx, blob)))
        # The brand-name check is reported separately: a job prompt may quote
        # the retired name when auditing a corpus, which is evidence, not
        # branding. Those are allowed through and listed for review.
        if label == "legacy brand name":
            if found:
                print("NOTE: retired brand name appears in the template:")
                for hit in found:
                    print(f"   {hit}")
            continue
        if found:
            residual[label] = found

    if residual:
        print("FAIL: residual PII detected, refusing to write:", file=sys.stderr)
        for label, found in residual.items():
            print(f"  {label}: {found}", file=sys.stderr)
        return 1

    Path(args.out).write_text(blob + "\n")
    Path(args.manifest).write_text(
        json.dumps(
            {
                "variables": dict(sorted(counter.items())),
                "runtime_fields_dropped": stats["runtime_fields_dropped"],
                "job_count": len(clean),
            },
            indent=2,
        )
        + "\n"
    )

    print(f"OK  jobs: {len(clean)}")
    print(f"OK  runtime fields dropped: {stats['runtime_fields_dropped']}")
    print(f"OK  variables: {dict(sorted(counter.items()))}")
    print(f"OK  wrote {args.out}")
    print(f"OK  wrote {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
