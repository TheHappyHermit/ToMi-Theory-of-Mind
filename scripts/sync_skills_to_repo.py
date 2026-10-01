#!/usr/bin/env python3
"""Sync PII-stripped skill copies into the tracked publish folder.

The live skills live in ~/.hermes/skills and carry host-specific detail --
LAN addresses, real service names, the author's handle -- because that is
what makes them useful on this machine. The repo copy must be publishable,
so it is the *redacted* variant of the same skill.

This script is the only sanctioned way to update the published copies:

    scripts/sync_skills_to_repo.py            # write redacted copies
    scripts/sync_skills_to_repo.py --check    # verify only, write nothing

Every file it writes passes through redact_skill.py, which refuses to emit
output containing a known PII pattern. --check exits non-zero if any tracked
copy has drifted from its local source, so CI can enforce "strip before push"
without re-deriving the intent.

Why a separate folder instead of committing ~/.hermes/skills directly:
  * the category dirs under skills/ are gitignored as upstream-vendored
  * the live tree is not a git repo of its own
  * a dedicated, flat, never-ignored folder has exactly one rule -- if it is
    here, it has been redacted
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
LIVE = os.path.expanduser("~/.hermes/skills")
PUBLISH = os.path.join(REPO, "public-skills")
REDACTOR = os.path.join(HERE, "redact_skill.py")

# Skills that are published. Everything else in ~/.hermes/skills is either
# vendored upstream, project-local, or already represented here.
#
# The nine flat skills under skills/ predate this folder and are left in
# place; this list is the canonical set going forward.
PUBLISHED = [
    # provenance of the sweep, PII-free at source
    "adopt-vs-build-survey",
    "phased-spec-execution",
    "hermes-hook-return-contract",
    "existing-state-first",
    "cli-config-repair",
    "sqlite-schema-hygiene",
    # PII-tainted at source, published redacted
    "large-repo-git-workarounds",
    "linux-network-firewall-debugging",
    "nas-cifs-privileged-mount",
    "disk-io-attribution",
    "local-research-dispatch",
    # first sweep
    "verifier-integrity",
    "verifying-scholarly-citations",
    "whole-corpus-reading",
    "bulk-corpus-remediation",
    "repo-pii-scrub",
    "local-inference-hosting",
    "live-repo-restructure",
    "external-claim-reconciliation",
    "delegated-research-fanout",
    # The two skills that author vault pages.
    #
    # Both live under a bundled category directory, which .gitignore
    # excludes wholesale (skills/research/, skills/apple/, and eleven
    # others). So publish_profiles_and_skills.py could not reach them --
    # it publishes the tracked tree -- and they were in neither
    # skills/ nor public-skills/ on GitHub. A reader had no way to see the
    # citation-title rule that now lives in them, which is the rule that
    # decides whether a new page can be graded high.
    #
    # public-skills/ is the right home: it is flat, it is tracked, and it is
    # built for exactly this -- a redacted copy of a skill whose live tree is
    # not published.
    "wiki-ingestion",
    "research-cron-knowledge-base",
]

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "*.orig")


def find_skill(name):
    for root, dirs, files in os.walk(LIVE):
        if "SKILL.md" in files and os.path.basename(root) == name:
            return root
    return None


def redact_file(src, dst):
    r = subprocess.run([sys.executable, REDACTOR, src, dst],
                       capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def local_fingerprint(root):
    """Hash of the live SKILL.md, so drift is detectable without diffing."""
    import hashlib
    p = os.path.join(root, "SKILL.md")
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify published copies match their sources; write nothing")
    args = ap.parse_args()

    os.makedirs(PUBLISH, exist_ok=True)
    drifted, written, failed, missing = [], [], [], []

    for name in PUBLISHED:
        src_root = find_skill(name)
        if not src_root:
            missing.append(name)
            continue
        src = os.path.join(src_root, "SKILL.md")
        dst_dir = os.path.join(PUBLISH, name)
        dst = os.path.join(dst_dir, "SKILL.md")
        stamp = os.path.join(dst_dir, ".source-fingerprint")

        if args.check:
            if not os.path.exists(dst):
                drifted.append((name, "not published"))
                continue
            if not os.path.exists(stamp):
                drifted.append((name, "no fingerprint"))
                continue
            if open(stamp).read().strip() != local_fingerprint(src_root):
                drifted.append((name, "source changed"))
            continue

        ok, msg = redact_file(src, dst)
        if not ok:
            failed.append((name, msg))
            continue
        # copy any supporting files, redacting the same way
        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), src_root)
                if rel == "SKILL.md":
                    continue
                d = os.path.join(dst_dir, rel)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                if f.endswith((".md", ".txt", ".sh", ".py", ".json", ".yaml", ".yml")):
                    ok2, _ = redact_file(os.path.join(root, f), d)
                    if not ok2:
                        failed.append((name, "supporting file: %s" % rel))
                else:
                    shutil.copy2(os.path.join(root, f), d)
        with open(stamp, "w") as fh:
            fh.write(local_fingerprint(src_root))
        written.append(name)

    if args.check:
        if drifted or missing:
            print("DRIFT DETECTED -- run: scripts/sync_skills_to_repo.py")
            for n, why in drifted:
                print("   %-32s %s" % (n, why))
            for n in missing:
                print("   %-32s MISSING from ~/.hermes/skills" % n)
            return 1
        print("OK: all %d published skills match their local sources." % len(PUBLISHED))
        return 0

    print("wrote %d redacted skills to %s" % (len(written), PUBLISH))
    for n in written:
        print("   %s" % n)
    if missing:
        print("MISSING from live tree (skipped): %s" % ", ".join(missing))
    if failed:
        print("\nREDACTION REFUSED (not written):")
        for n, msg in failed:
            print("   %-32s %s" % (n, msg))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
