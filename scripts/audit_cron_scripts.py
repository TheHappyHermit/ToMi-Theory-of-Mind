#!/usr/bin/env python3
"""Audit Hermes cron jobs: does every referenced script actually exist?

Reads the live cron job table and extracts every filesystem path that jobs
reference, both the `script` field and any path mentioned inside the prompt
text. Reports each as EXISTS or MISSING.
"""

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CRON_JSON_CANDIDATES = [
    Path(os.environ.get("HERMES_HOME", "")) / "cron" / "jobs.json" if os.environ.get("HERMES_HOME") else None,
    Path.home() / ".hermes" / "cron" / "jobs.json",
    (Path(os.environ["LOCALAPPDATA"]) / "hermes" / "cron" / "jobs.json") if sys.platform == "win32" and os.environ.get("LOCALAPPDATA") else None,
    Path.home() / ".hermes" / "cron" / "jobs.json",
    REPO_ROOT / "cron" / "jobs.template.json",
]
CRON_JSON_CANDIDATES = [str(p) for p in CRON_JSON_CANDIDATES if p]

SCRIPT_DIRS = [
    str(REPO_ROOT / "scripts"),
    str(REPO_ROOT),
    str(Path(os.environ["HERMES_HOME"]) / "scripts") if os.environ.get("HERMES_HOME") else None,
    str(Path.home() / ".hermes" / "scripts"),
    str(Path(os.environ["LOCALAPPDATA"]) / "hermes" / "scripts") if sys.platform == "win32" and os.environ.get("LOCALAPPDATA") else None,
    str(Path.home() / ".hermes" / "scripts"),
]
SCRIPT_DIRS = [d for d in SCRIPT_DIRS if d]

PATH_RE = re.compile(r"((?:[A-Za-z]:[\\/]|/home/|scripts/)[^\s\"'|;)>]+\.(?:py|sh|bash))")

# A prompt can name a repository or directory in prose with no filename in it,
# e.g. "execute the rebuild_oracle_index.py script from the autognosia
# repository". PATH_RE requires a match to END in .py/.sh/.bash, so the bare
# "autognosia repository" is invisible to it -- and the audit reported OK
# while four live cron jobs still pointed at a retired repository that does
# not exist on disk.
#
# This catches the named-entity form. It is deliberately narrow: it only
# fires on "<word> repository", which is a phrasing specific enough that a
# false positive is unlikely, and it only reports a problem when the
# directory is genuinely absent.
REPO_RE = re.compile(r"\b([A-Za-z][\w-]{2,})\s+repository\b", re.IGNORECASE)

# Names that are legitimate prose rather than a filesystem location.
REPO_ALLOWLIST = {"this", "the", "a", "an", "same", "other", "upstream", "git"}


def repo_references(prompt):
    """
    Return (name, is_checkable) for every "<word> repository" phrase.

    is_checkable is False for names that cannot be a path under $HOME, and
    for a small allowlist of ordinary English words.
    """
    out = []
    for match in REPO_RE.finditer(prompt or ""):
        name = match.group(1)
        if name.lower() in REPO_ALLOWLIST:
            continue
        # Only treat it as a location if something like it could exist as a
        # directory under home. "~/.hermes/<name>" or "<name>" both qualify.
        candidate_home = Path.home() / f".{name}"
        candidate_plain = Path.home() / name
        out.append((name, candidate_home.exists() or candidate_plain.exists()))
    return out


def load_jobs():
    for path in CRON_JSON_CANDIDATES:
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError) as exc:
                print(f"  ! {path} unreadable: {exc}")
                continue
            if isinstance(data, dict):
                for key in ("jobs", "items", "data"):
                    if isinstance(data.get(key), list):
                        return path, data[key]
                return path, list(data.values())
            if isinstance(data, list):
                return path, data
    return None, []


def resolve_script(name):
    """A bare or relative `script` name resolves against repo root and known script dirs."""
    if os.path.isabs(name) and os.path.isfile(name):
        return name
    base_name = os.path.basename(name)
    # Check direct relative to repo root
    repo_rel = REPO_ROOT / name
    if repo_rel.is_file():
        return str(repo_rel)
    for directory in SCRIPT_DIRS:
        for candidate in (os.path.join(directory, name), os.path.join(directory, base_name)):
            if os.path.isfile(candidate):
                return candidate
    return None


def main():
    src, jobs = load_jobs()
    if not jobs:
        print("Could not load any cron job definitions.")
        return 1

    print(f"Cron job audit  (source: {src})")
    print(f"jobs found: {len(jobs)}")

    missing = []
    checked = 0

    for job in jobs:
        if not isinstance(job, dict):
            continue
        name = job.get("name") or job.get("id") or job.get("job_id") or "<unnamed>"
        problems = []

        script = job.get("script")
        if script:
            # Handle script commands with arguments like "brain_sync_cron.py --sources ..."
            bare_script = script.split()[0]
            resolved = resolve_script(bare_script)
            checked += 1
            if not resolved:
                problems.append(f"script not found: {script}")

        prompt = job.get("prompt") or ""
        for path in sorted(set(PATH_RE.findall(prompt))):
            bare_path = path.split()[0]
            resolved = resolve_script(bare_path)
            checked += 1
            if not resolved:
                problems.append(f"prompt path missing: {path}")

        # Named repositories: "the <name> repository". No filename, so
        # PATH_RE never sees these, but the directory can still be gone.
        for name_, exists in repo_references(prompt):
            if not exists:
                problems.append(
                    f"prompt names '{name_} repository' but no such directory "
                    f"exists (~/{name_} or ~/.{name_})"
                )

        if problems:
            missing.append((name, job.get("id") or job.get("job_id"), problems))

    print(f"path references checked: {checked}")

    if not missing:
        print("\nRESULT: OK - every referenced script exists.")
        return 0

    print(f"\nRESULT: {len(missing)} job(s) reference missing files:\n")
    for name, job_id, problems in missing:
        print(f"  [{job_id}] {name}")
        for problem in problems:
            print(f"      - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
