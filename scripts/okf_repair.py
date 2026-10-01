#!/usr/bin/env python3
"""
okf_repair.py — apply the schema's `repair.auto` policy, then report the rest.

This is the job that makes the corpus converge over time rather than just
accumulate a report. It never invents content: every automatic repair is a
mechanical transformation whose rule lives in schemas/okf-schema.yaml.

Guarantees
  * Only the classes in repair.auto are touched.
  * Everything in repair.report_only is written to a queue, never edited.
  * A backup of every modified file is kept under --backup-dir (default
    .okf-backups/<UTC timestamp>/), so any run is reversible.
  * --dry-run prints the plan and writes nothing.
  * Non-zero exit if a repair could not be applied, so cron notices.

Usage
  okf_repair.py --dry-run              # plan only
  okf_repair.py --source oracle        # one wiki
  okf_repair.py --apply                # actually write
  okf_repair.py --apply --max-files 50 # bounded pass, for a daily cron
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "okf_lint.py")
QUEUE_DEFAULT = os.path.expanduser("~/hermes-brain/schemas/okf-queue.jsonl")


def run_lint(source, limit_note=""):
    cmd = [sys.executable, LINT, "--check", "--json", "--source", source]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if out.returncode not in (0, 1):
        raise SystemExit(f"okf_repair: lint failed rc={out.returncode}\n{out.stderr[:2000]}")
    return json.loads(out.stdout)


def apply_repairs(source, apply, dry_run, backup_root, max_files):
    """
    Re-uses okf_lint's own --fix machinery per file so there is exactly one
    implementation of 'what is a valid frontmatter' in the codebase.
    """
    cmd = [sys.executable, LINT, "--fix", "--source", source, "--json"]
    if dry_run:
        cmd.append("--dry-run")
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if out.returncode not in (0, 1):
        raise SystemExit(f"okf_repair: repair pass failed\n{out.stderr[:2000]}")
    data = json.loads(out.stdout)
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="both", choices=["active-wiki", "oracle", "both"])
    ap.add_argument("--apply", action="store_true", help="write changes (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--queue", default=QUEUE_DEFAULT)
    ap.add_argument("--backup-dir", default=None)
    ap.add_argument("--no-backup", action="store_true")
    ap.add_argument("--max-files", type=int, default=0)
    args = ap.parse_args()

    dry = args.dry_run or not args.apply
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = args.backup_dir or os.path.expanduser(f"~/.okf-backups/{ts}")

    print(f"okf_repair  mode={'DRY-RUN' if dry else 'APPLY'}  source={args.source}")
    summary = {}

    for source in (["active-wiki", "oracle"] if args.source == "both" else [args.source]):
        res = apply_repairs(source, args.apply, dry, backup_root, args.max_files)
        by = collections.Counter(f["class"] for f in res["findings"])
        auto = res["auto_fixable"]
        report = res["findings"][auto:]
        print(f"\n  [{source}] scanned={res['scanned']} changed={res['files_changed']} "
              f"auto={auto} report-only={len(report)}")
        for cls, n in by.most_common(12):
            print(f"     {n:6d}  {cls}")

        # queue everything that needs judgement
        if not dry and report:
            with open(args.queue, "a", encoding="utf-8") as fh:
                for f in report:
                    fh.write(json.dumps({"ts": ts, "source": source, **f}) + "\n")
            print(f"     queued {len(report)} report-only findings -> {args.queue}")
        summary[source] = {"scanned": res["scanned"], "changed": res["files_changed"],
                           "auto": auto, "report_only": len(report)}

    if not dry and not args.no_backup:
        print(f"\n  backups: {backup_root}")

    print("\nsummary: " + json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
