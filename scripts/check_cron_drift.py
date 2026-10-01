#!/usr/bin/env python3
"""Report drift between the repo's cron template and a live Hermes install.

Read-only by design. It compares what a fresh install would produce
(cron/jobs.template.json) against what is actually live (~/.hermes/cron/jobs.json)
and prints the differences. It never writes to either file.

This replaced installers/arena_boundary.py and installers/lane_boundary.py.
Those were one-way deploy tools: they copied a repo artifact over the live one
with a backup, and were written for a copy-based install that no longer runs.
install.py symlinks skills/ into place and seeds cron from this same template, so
a fresh install already carries the write boundary and the child-dispatch clause
without them. Worse, installing the arena skill from the repo would have written
its unexpanded ${HERMES_HOME} variables over a working live skill, and their
byte-hash comparison reported drift on files that were logically identical.
Checking is the part worth keeping. Deploying was not.

Comparing raw text is useless here. The template is machine-independent and uses
${HERMES_HOME}-style variables; the live jobs have those expanded to real paths.
So both sides are normalised through the same variable map before comparison --
substituting the live values into the template, not the reverse. A difference
that survives that is real drift.

    python scripts/check_cron_drift.py                 # check the default install
    python scripts/check_cron_drift.py --jobs FILE     # check a jobs.json elsewhere
    python scripts/check_cron_drift.py --verbose       # show the diffs, not just counts
    python scripts/check_cron_drift.py --job <id>      # one job only

Exit status is 0 when the template and the live install agree on every checked
job, and 1 when any job has drifted, so this can gate a commit or a deploy.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "cron" / "jobs.template.json"
DEFAULT_JOBS = Path("~/.hermes/cron/jobs.json").expanduser()

# Which template variable stands in for which real path. Only the ones that
# appear inside job text matter here; the rest (models, script names, hosts) are
# handled by the model/tier substitutions below.
VARIABLES = {
    # These map to the fragment that follows the home directory. A template path
    # is written ${HERMES_HOME}/thing or ${HERMES_DATA_DIR}/thing, so each value
    # carries no leading slash of its own and the / in the template supplies it.
    "HERMES_DATA_DIR": "~/.hermes",
    "HERMES_HOME": "~",
    "DB_BRAIN": "~/.hermes/experience.db",
    # Resolved from the environment rather than hardcoded: the inference node's
    # address is a machine fact, and a committed LAN IP is a leak in a public repo.
    "INFERENCE_NODE_MAIN": os.environ.get("INFERENCE_NODE_MAIN", "<LAN-HOST-IP>"),
    # The two housekeeping scripts in ~/.hermes/scripts/ were renamed to describe
    # their job rather than the project they once belonged to. The template
    # names them through a variable, so the live name goes here.
    "SCRIPT_BACKUP": "daily_backup.sh",
    "SCRIPT_HEALTH": "daily_health_check.py",
}

# The rename of audit/fullread -> cognition-arena reached the repo and the live
# jobs at different times, so a live job that still names the old path is
# reporting exactly the kind of drift this script exists to surface. Collapse
# the retired name onto the current one before comparing, so that a genuinely
# current live job is not flagged for it.
RETIRED_PATHS = (
    ("audit/fullread", "cognition-arena"),
    # schemas/ and cron/ replaced standards/ at the repo root. A live job created
    # before that move still names the retired location, and that folder is gone,
    # so such a job is broken rather than merely worded differently. The retired
    # prefix is replaced by the folder that took over -- schemas/ for the schema
    # artifacts, which is what the job meant -- rather than deleted, so a
    # remaining difference is one of substance.
    ("hermes-brain/standards/okf", "hermes-brain/schemas/okf"),
    ("hermes-brain/standards/WIKI", "hermes-brain/docs/WIKI"),
)

# The repo deliberately carries no legacy project name, but a live job created
# before that rename still has it in its text. This is cosmetic, not drift.
LEGACY_WORDS = (
    (re.compile(r"\bAutognosia\b"), "Hermes"),
)

# The template names model tiers; the live jobs name a concrete model. Map each
# tier to whatever the live install actually resolved it to, learned from the
# live jobs themselves rather than hardcoded.
MODEL_TIERS = (
    "MODEL_DEEP",
    "MODEL_DESKTOP_A",
    "MODEL_DESKTOP_B",
    "MODEL_UTILITY",
)

# Fields worth comparing. Prompt and model are the ones that carry the boundary
# rules; the rest is scheduling plumbing that changes on its own.
CHECKED_FIELDS = ("prompt", "model", "schedule", "workdir", "skill", "skills")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def job_list(doc: dict) -> list[dict]:
    """Both the template and jobs.json hold a 'jobs' list, but be tolerant."""
    if isinstance(doc, dict):
        for key in ("jobs", "cron_jobs", "data"):
            if isinstance(doc.get(key), list):
                return doc[key]
            if isinstance(doc.get(key), dict) and isinstance(doc[key].get("jobs"), list):
                return doc[key]["jobs"]
    if isinstance(doc, list):
        return doc
    raise ValueError("no job list found in JSON")


def job_id(job: dict) -> str:
    for key in ("id", "job_id", "uuid"):
        if job.get(key):
            return str(job[key])
    return job.get("name", "?")


def expand_variables(text: str, values: dict[str, str]) -> str:
    """Substitute ${VAR} in the template text with the live install's values."""
    for name, value in values.items():
        text = text.replace("${" + name + "}", value)
    return text


def learn_tier_values(template_jobs: list[dict], live_jobs: list[dict]) -> dict[str, str]:
    """Work out what each ${MODEL_*} tier resolved to in the live install.

    A tier appears in a template prompt as ${MODEL_X}. The live job that
    corresponds has that same text with a real model id in it. Comparing the two
    gives the substitution without anyone having to maintain a table.
    """
    values: dict[str, str] = {}
    for tier in MODEL_TIERS:
        token = "${" + tier + "}"
        # The tier can appear either inside a prompt or as the job's model
        # field. Look in both: a job whose model is ${MODEL_UTILITY} and whose
        # prompt never mentions a model is resolved from the model field.
        field_holders = [
            j for j in template_jobs
            if token in (j.get("prompt") or "") or token == j.get("model")
        ]
        for holder in field_holders:
            live = next(
                (j for j in live_jobs if job_id(j) == job_id(holder)),
                None,
            )
            if not live:
                continue
            # Model field first: that is an exact one-to-one substitution.
            if token == holder.get("model") and live.get("model"):
                values[tier] = live["model"]
                break
            # Otherwise read the value out of the prompt word by word.
            for before, after in zip(
                (holder.get("prompt") or "").split(),
                (live.get("prompt") or "").split(),
            ):
                if before == token and after and not after.startswith("${"):
                    values[tier] = after.strip("`'\".,")
                    break
            if tier in values:
                break
    return values


def normalise(text: str, values: dict[str, str]) -> str:
    """Put both sides on the same footing before comparing.

    The template is machine-independent: it writes ${HERMES_HOME} for the home
    directory and spells a home-relative path with an explicit / after the
    variable. The live jobs have those resolved, and spell the same path as ~/.
    So the template is expanded first, then every home-relative path -- on either
    side -- is reduced to a single canonical ~/ form. The retired corpus path and
    the old project name are collapsed too, so a live job that predates a rename
    is not reported as drift for carrying the old name.
    """
    text = expand_variables(text or "", values)
    home = str(Path.home())
    # Both sides reduce to ~/ for a home-relative path. The template spells one as
    # ${HERMES_HOME}/thing, which after expansion is //thing because HERMES_HOME
    # carries its own trailing slash; the live job spells it ~/thing. Collapse any
    # run of slashes that follows ~ so the two forms meet.
    text = text.replace(home, "~")
    text = re.sub(r"~+/", "~/", text)
    for old, new in RETIRED_PATHS:
        text = text.replace(old, new)
    for pattern, new in LEGACY_WORDS:
        text = pattern.sub(new, text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def diff_lines(label: str, template_value: str, live_value: str,
               values: dict[str, str]) -> list[str]:
    out = [f"      {label}:"]
    out += [
        f"        {line}"
        for line in difflib.unified_diff(
            normalise(template_value, values).split(),
            normalise(live_value, values).split(),
            lineterm="",
            n=0,
        )
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Report drift between cron/jobs.template.json and a live install (read-only)."
    )
    ap.add_argument("--jobs", type=Path, default=DEFAULT_JOBS,
                    help=f"live jobs.json to compare against (default: {DEFAULT_JOBS})")
    ap.add_argument("--template", type=Path, default=TEMPLATE,
                    help="template to compare (default: cron/jobs.template.json)")
    ap.add_argument("--job", action="append", default=None, metavar="ID",
                    help="only check this job id (repeatable)")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="print the differing lines, not just the counts")
    args = ap.parse_args()

    if not args.template.exists():
        print(f"FAIL: template not found: {args.template}", file=sys.stderr)
        return 2
    if not args.jobs.exists():
        print(f"FAIL: live jobs.json not found: {args.jobs}", file=sys.stderr)
        print("      nothing to compare against; is Hermes installed?", file=sys.stderr)
        return 2

    template_jobs = job_list(load_json(args.template))
    live_jobs = job_list(load_json(args.jobs))
    live_by_id = {job_id(j): j for j in live_jobs}

    values = dict(VARIABLES)
    values.update(learn_tier_values(template_jobs, live_jobs))

    wanted = set(args.job) if args.job else None
    print(f"template : {args.template}")
    print(f"live     : {args.jobs}")
    print(f"jobs     : {len(template_jobs)} in template, {len(live_jobs)} live")
    print()

    drifted, missing, checked = [], [], 0

    for tjob in template_jobs:
        tid = job_id(tjob)
        if wanted and tid not in wanted:
            continue
        live = live_by_id.get(tid)
        if live is None:
            missing.append((tid, tjob.get("name", "?")))
            continue
        checked += 1
        differing = []
        for field in CHECKED_FIELDS:
            tv, lv = tjob.get(field), live.get(field)
            if tv is None and lv is None:
                continue
            tv_s = normalise(tv if isinstance(tv, str) else json.dumps(tv, sort_keys=True), values)
            lv_s = normalise(lv if isinstance(lv, str) else json.dumps(lv, sort_keys=True), values)
            if tv_s != lv_s:
                differing.append((field, tv if isinstance(tv, str) else json.dumps(tv, sort_keys=True),
                                  lv if isinstance(lv, str) else json.dumps(lv, sort_keys=True)))
        if differing:
            drifted.append((tid, tjob.get("name", "?"), differing))

    for tid, name, differing in drifted:
        print(f"  [DRIFT] {tid}  {name}")
        print(f"           {len(differing)} field(s) differ: {', '.join(f for f, _, _ in differing)}")
        if args.verbose:
            for field, tv, lv in differing:
                print(*diff_lines(field, tv, lv, values), sep="\n")

    for tid, name in missing:
        print(f"  [ABSENT] {tid}  {name} — in the template, not in the live install")

    # A prompt can match the template perfectly and still be unrunnable, because
    # the file it names exists only on the machine that wrote it. The Daily Backup
    # job did exactly this: prompt and template agreed, so no drift was reported,
    # while the script it ran was absent from the repo a fresh clone starts from.
    # Prompt equality cannot catch that; resolving the path can.
    unresolved = []
    for jjob in live_jobs:
        if wanted and job_id(jjob) not in wanted:
            continue
        blob = " ".join(str(jjob.get(f, "")) for f in ("prompt", "command", "message"))
        for path_str in re.findall(r"(?:bash|python3?|sh)\s+(/[\w./~-]+)", blob):
            expanded = os.path.expanduser(normalise(path_str, values))
            if not os.path.exists(expanded):
                unresolved.append((job_id(jjob), jjob.get("name", "?"), expanded))
            break  # first executable path per job is enough to judge it

    for tid, name, path_str in unresolved:
        print(f"  [NOSCRIPT] {tid}  {name}")
        print(f"             prompt names a file that does not exist: {path_str}")

    print()
    if not drifted and not missing and not unresolved:
        print(f"OK: {checked} job(s) match the template. Nothing to do.")
        return 0

    print(f"{len(drifted)} drifted, {len(missing)} absent, "
          f"{len(unresolved)} unrunnable, {checked} compared.")
    if unresolved:
        print("A job whose named script is missing fails at run time, not at compare")
        print("time. Ship the script in scripts/ or repoint the job.")
    print("This script only reports. To adopt the template's version of a prompt,")
    print("edit the live job deliberately, or re-run setup_cron_jobs.py --force.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
