#!/usr/bin/env python3
"""Publish live profiles and skills into their tracked repo folders.

The gap this fills
------------------
The repo tracks `skills/`, `profiles/` and `cron/`, but the canonical copies
live outside it:

    ~/.hermes/skills/...          -> repo: skills/<category>/<name>/SKILL.md
    ~/.hermes/profiles/<p>/...    -> repo: profiles/<p>/SOUL.md
    ~/.hermes/cron/jobs.json      -> repo: cron/jobs.template.json  (different tool)

Nothing connected them. `scripts/sync_skills_to_repo.py` covers only
`public-skills/`, which is the flat redacted publish folder built for GitHub
distribution -- not the category-structured `skills/` tree the repo already
tracks, and not `profiles/` at all.

So six profiles and two skills could be edited locally and the repo copies
would sit stale indefinitely, which is exactly what happened: every profile
SOUL.md and both changed SKILL.md files had drifted. A reader of the repo
would have seen the old, wrong citation guidance and no way to know it was
wrong.

Why redaction, not a raw copy
-----------------------------
The live files carry this host's identity: 110 home paths, 35 LAN addresses,
the real username. Those belong in the local copy -- that is what makes them
useful on this machine -- and must not be published. So every file passes
through scripts/redact_skill.py, which is fail-closed: it exits non-zero and
writes nothing when it cannot confidently remove a pattern. The live
jobs.json goes to cron/jobs.template.json via generate_cron_template.py
instead, which emits ${VARIABLE} placeholders rather than generic redaction,
so an operator can fill them in.

What gets published
-------------------
  profiles/<name>/SOUL.md    every profile that has one
  skills/<...>/SKILL.md      only skills already tracked by the repo, or
                             newly tracked and passing the residue scan

The skills set is deliberately NOT "all of ~/.hermes/skills". That tree holds
241 skills, many bundled, and publishing all of them would sweep in content
the repo has never carried and was never reviewed for publication. This
publishes what the repo already tracks, plus explicitly named additions, so
an unreviewed skill cannot enter the public tree by being created locally.

    scripts/publish_profiles_and_skills.py           # write
    scripts/publish_profiles_and_skills.py --check   # drift report, no writes
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERMES = os.path.expanduser("~/.hermes")
LIVE_PROFILES = os.path.join(HERMES, "profiles")
LIVE_SKILLS = os.path.join(HERMES, "skills")
REDACTOR = os.path.join(REPO, "scripts", "redact_skill.py")

# Independent residue check. Deliberately NOT the redactor's own rules: a
# scanner that shares the redactor's assumptions cannot find a leak the
# redactor does not know it has. This is the lesson from the public-skills
# audit, which found id_ed25519_lab, `ssh the operator@...` and the project
# name embedded in a filename -- none of which the redactor's own check
# flagged.
RESIDUE = {
    "real username": r"operator",
    "home path": r"/home/operator",
    "github handle": r"TheHappyHermit",
    "LAN IP": r"\b10\.\d+\.\d+\.\d+\b",
    "email": r"[\w.+-]+@[\w-]+\.[\w.]{2,}",
    # Matches any key type, matching the redactor's own ssh_key rule. It
    # previously covered only ed25519, so a named id_rsa_lab_key would have
    # passed the independent scan that the redactor would have caught -- the
    # two lists disagreeing about scope, which is the failure mode that let
    # the lowercase handle through in the first place. No such key exists in
    # the current corpus; the point is that the next one is not a miss.
    "ssh key name": r"id_(?:rsa|ed25519|dsa|ecdsa)[^\s\"']*",
    "ssh login": r"\bssh\s+(?:-\S+\s+)*the operator@",
}

# Patterns that LOOK like a leak and are not.
#
# The first version of this scan flagged `~/.ssh/id_ed25519` in two GitHub
# skills, which is ssh-keygen's default output filename and appears in every
# tutorial on earth. A residue check that cries wolf on the standard default
# gets ignored, and then it stops being a check.
#
# `example.com` and `example.org` are the IANA-reserved documentation
# domains. `their-email@example.com` in a setup walkthrough is a placeholder
# by any reading, and a scanner that flags it will be ignored on the ones
# that matter.
#
# The point of the allowlist is to keep the check's positive rate high. Every
# entry here was a false positive observed against real files, not a shape
# anticipated in the abstract.
SAFE_SSH_KEY = re.compile(
    r"\.ssh/id_(?:rsa|ed25519|dsa|ecdsa)(?:\.pub)?(?![A-Za-z0-9_-])")
SAFE_EMAIL = re.compile(
    r"(?:example\.(?:com|org|net)|test\.invalid|localhost)"
    r"(?![A-Za-z0-9.-])", re.I)


def residue_findings(text):
    findings = {}
    for label, pat in RESIDUE.items():
        hits = list(re.finditer(pat, text, re.I))
        if label == "ssh key name":
            # Drop the default filename, keep anything naming a specific key.
            #
            # The guard is tested against the SURROUNDING text, not the
            # match. The pattern `id_ed25519[^\s"']*` captures from `id_`
            # onward, so `.ssh/` is not inside the match and a test against
            # the match text could never see the prefix -- which is how the
            # first attempt flagged ssh-keygen's own default in every
            # tutorial. A short lookbehind window puts the prefix back in
            # scope, and `search` rather than `match` because that window
            # starts mid-token.
            hits = [h for h in hits
                    if not SAFE_SSH_KEY.search(
                        text[max(0, h.start() - 12):h.start() + len(h.group(0))])]
        elif label == "email":
            # Drop IANA-reserved documentation domains.
            hits = [h for h in hits if not SAFE_EMAIL.search(h.group(0))]
        if hits:
            findings[label] = len(hits)
    return findings


def tracked_skills():
    out = subprocess.run(["git", "-C", REPO, "ls-files", "skills/"],
                         capture_output=True, text=True)
    return {f for f in out.stdout.split("\n") if f.endswith("SKILL.md")}


def live_skill_paths():
    """Map repo-relative path -> live path, for skills the repo tracks."""
    pairs = []
    for rel in sorted(tracked_skills()):
        # skills/<category>/<name>/SKILL.md  and  skills/<name>/SKILL.md
        parts = rel.split("/")
        name = parts[-2]
        cat = parts[-3] if len(parts) > 3 else None
        cands = []
        if cat:
            cands.append(os.path.join(LIVE_SKILLS, cat, name, "SKILL.md"))
        cands.append(os.path.join(LIVE_SKILLS, name, "SKILL.md"))
        live = next((c for c in cands if os.path.exists(c)), None)
        if live:
            pairs.append((rel, live))
    return pairs


def publish(rel, live, tmpdir, apply):
    """Redact one file to the repo path. Returns (status, detail)."""
    dst = os.path.join(REPO, rel)
    text = open(live, encoding="utf-8").read()
    name = rel.replace("/", "_")
    staged = os.path.join(tmpdir, name)
    r = subprocess.run([sys.executable, REDACTOR, live, staged],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(staged):
        return "BLOCKED", (r.stdout + r.stderr).strip()[:160]
    red = open(staged, encoding="utf-8").read()
    found = residue_findings(red)
    if found:
        return "LEAK", "residue after redaction: %s" % found
    if not apply:
        same = os.path.exists(dst) and open(dst, encoding="utf-8").read() == red
        return ("IN-SYNC" if same else "DRIFT"), rel
    if os.path.exists(dst) and open(dst, encoding="utf-8").read() == red:
        return "IN-SYNC", rel
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(staged, dst)
    return "WROTE", rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report drift; write nothing")
    args = ap.parse_args()

    tmpdir = "/tmp/publish_pps"
    shutil.rmtree(tmpdir, ignore_errors=True)
    os.makedirs(tmpdir, exist_ok=True)

    targets = []
    for soul in sorted(glob.glob(os.path.join(LIVE_PROFILES, "*", "SOUL.md"))):
        prof = os.path.basename(os.path.dirname(soul))
        targets.append(("profiles/%s/SOUL.md" % prof, soul))
    targets.extend(live_skill_paths())

    counts = {}
    problems = []
    for rel, live in targets:
        status, detail = publish(rel, live, tmpdir, not args.check)
        counts[status] = counts.get(status, 0) + 1
        if status in ("BLOCKED", "LEAK", "DRIFT", "WROTE"):
            print("  %-8s %s" % (status, detail if status in
                                 ("BLOCKED", "LEAK") else rel))

    print("\n  %d file(s) examined" % len(targets))
    for k in sorted(counts):
        print("    %-8s %d" % (k, counts[k]))

    if args.check:
        drift = counts.get("DRIFT", 0) + counts.get("LEAK", 0) + counts.get("BLOCKED", 0)
        print("\n  %d file(s) differ from their live source; run without "
              "--check to publish" % drift)
        return 1 if drift else 0

    leaked = counts.get("LEAK", 0) + counts.get("BLOCKED", 0)
    if leaked:
        print("\n  %d file(s) REFUSED publication. Nothing partial was "
              "committed for them." % leaked)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
