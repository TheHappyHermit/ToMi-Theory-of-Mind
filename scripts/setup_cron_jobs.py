#!/usr/bin/env python3
"""
scripts/setup_cron_jobs.py — Provision and synchronize Hermes Brain cron jobs.

Reads cron/jobs.template.json and safely merges the standard cognitive jobs
into the target Hermes Agent environment (~/.hermes/cron/jobs.json) without
overwriting existing user jobs or leaking machine-specific PII.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List


def get_hermes_cron_file() -> Path:
    """Resolve the active Hermes jobs.json location."""
    if os.environ.get("HERMES_HOME"):
        return Path(os.environ["HERMES_HOME"]) / "cron" / "jobs.json"

    # Windows LocalAppData
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data and (Path(local_app_data) / "hermes").exists():
        return Path(local_app_data) / "hermes" / "cron" / "jobs.json"

    # Standard user home
    return Path.home() / ".hermes" / "cron" / "jobs.json"


def setup_cron_jobs(template_path: Path, target_path: Path, dry_run: bool = False) -> Dict[str, Any]:
    """Merge template jobs into target jobs.json."""
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found at: {template_path}")

    template_data = json.loads(template_path.read_text(encoding="utf-8"))
    template_jobs = template_data.get("jobs", [])

    existing_data = {"jobs": []}
    if target_path.exists():
        try:
            existing_data = json.loads(target_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[setup_cron_jobs] Warning reading existing jobs: {e}")

    existing_jobs = existing_data.get("jobs", [])
    existing_ids = {j.get("id"): j for j in existing_jobs if j.get("id")}
    existing_names = {j.get("name"): j for j in existing_jobs if j.get("name")}

    added = 0
    updated = 0

    for job in template_jobs:
        job_id = job.get("id")
        job_name = job.get("name")

        # Match by ID or Name
        target_job = existing_ids.get(job_id) or existing_names.get(job_name)
        if target_job:
            # Update schedule or prompt if changed
            target_job["prompt"] = job.get("prompt", target_job.get("prompt"))
            target_job["script"] = job.get("script", target_job.get("script"))
            target_job["schedule"] = job.get("schedule", target_job.get("schedule"))
            target_job["schedule_display"] = job.get("schedule_display", target_job.get("schedule_display"))
            updated += 1
        else:
            existing_jobs.append(job)
            added += 1

    existing_data["jobs"] = existing_jobs

    if not dry_run:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        tmp_target = target_path.with_suffix(".tmp")
        tmp_target.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")
        tmp_target.replace(target_path)
        print(f"[setup_cron_jobs] Successfully synced {len(existing_jobs)} jobs to {target_path} (Added: {added}, Updated: {updated})")
    else:
        print(f"[setup_cron_jobs] [DRY RUN] Would write {len(existing_jobs)} jobs to {target_path} (Added: {added}, Updated: {updated})")

    return {"total": len(existing_jobs), "added": added, "updated": updated}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed and setup Hermes Brain cron jobs.")
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parent.parent / "cron" / "jobs.template.json")
    parser.add_argument("--target", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    target = args.target or get_hermes_cron_file()
    setup_cron_jobs(args.template, target, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
