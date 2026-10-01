#!/usr/bin/env python3
"""Detect drift in the active wiki's immutable raw/ layer.

Why this exists
---------------
`raw/` is Layer 1 of the wiki: verbatim source material the agent reads but
never edits. Each file carries a `sha256:` of its own body, so a re-ingest
of the same URL can tell "unchanged" from "the source moved under us" in one
hash.

A hash nobody ever recomputes is documentation, not detection. This is that
recompute. The same reasoning applies as to grade_all.py writing its report
unconditionally, and to the stale `title match unverified` selector: a
mechanism that exists but is never exercised cannot fail, and so cannot
report anything.

Three outcomes per file:
  OK        the body still hashes to the stored value
  CHANGED   it no longer does -- either edited in place (it should not have
            been) or the upstream source changed since ingestion
  MISSING   no sha256 in the frontmatter, so drift cannot be checked at all

CHANGED and MISSING are reported, never fixed. Silently rewriting a stored
hash would destroy the only evidence that something moved; a raw file edited
in place is exactly the event the hash exists to catch, and overwriting the
value would hide it forever.

    scripts/check_raw_drift.py             # report
    scripts/check_raw_drift.py --write     # add missing hashes (first ingest)
    scripts/check_raw_drift.py --strict    # exit 1 on any drift
"""
import argparse
import glob
import hashlib
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AW = os.path.expanduser("~/.hermes/active-wiki")
# Overridable so the test suite can point this at a seeded directory without
# touching the live wiki. A test that has to mutate the real tree to prove a
# check works is a test that will eventually damage it.
RAW = os.environ.get("HERMES_RAW_DIR") or os.path.join(AW, "raw")

FM_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


def split_frontmatter(text):
    """Return (frontmatter_text, body). Body excludes the frontmatter block."""
    m = FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def sha256_of(body):
    """Hash the body only, never the frontmatter.

    The frontmatter carries the hash, so hashing the whole file makes the
    value self-referential and permanently mismatched. Everything after the
    closing --- is the content, and the content is what must not change.
    """
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def stored_hash(fm_text):
    m = re.search(r"^sha256:\s*([0-9a-f]{64})\s*$", fm_text, re.M)
    return m.group(1) if m else None


def set_hash(fm_text, digest):
    if re.search(r"^sha256:.*$", fm_text, re.M):
        return re.sub(r"^sha256:.*$", "sha256: %s" % digest, fm_text,
                      count=1, flags=re.M)
    return fm_text.rstrip() + "\nsha256: %s\n" % digest


def raw_files():
    if not os.path.isdir(RAW):
        return []
    out = []
    for f in glob.glob(os.path.join(RAW, "**", "*.md"), recursive=True):
        if os.path.basename(f) == "index.md":
            continue
        out.append(f)
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="add a sha256 to files that have none (first ingest)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if any file drifted or lacks a hash")
    args = ap.parse_args()

    if not os.path.isdir(RAW):
        print("no raw/ directory at %s" % RAW)
        return 0

    files = raw_files()
    if not files:
        print("raw/ contains no source files yet (index.md does not count).")
        return 0

    ok, changed, missing, wrote = [], [], [], []
    for f in files:
        rel = os.path.relpath(f, AW)
        text = open(f, encoding="utf-8", errors="replace").read()
        fm, body = split_frontmatter(text)
        if fm is None:
            missing.append((rel, "no frontmatter"))
            continue
        actual = sha256_of(body)
        stored = stored_hash(fm)
        if stored is None:
            missing.append((rel, "no sha256"))
            if args.write:
                new_fm = set_hash(fm, actual)
                open(f, "w", encoding="utf-8").write(
                    "---\n" + new_fm + "---\n" + body)
                wrote.append(rel)
            continue
        if stored == actual:
            ok.append(rel)
        else:
            changed.append((rel, stored, actual))

    print("raw/ drift check")
    print("  OK       %d" % len(ok))
    print("  CHANGED  %d" % len(changed))
    print("  NO HASH  %d" % len(missing))
    if wrote:
        print("  wrote a hash to %d file(s)" % len(wrote))

    for rel, s, a in changed:
        print("\n  CHANGED %s" % rel)
        print("    stored   %s" % s)
        print("    actual   %s" % a)
        print("    Either this raw file was edited in place -- it is supposed")
        print("    to be immutable -- or its upstream source changed since")
        print("    ingestion. Both are worth knowing; neither is auto-fixed.")
        print("    If the change was legitimate upstream, update the stored")
        print("    hash deliberately. If it was an accidental edit, restore")
        print("    the original and check what else touched it.")

    for rel, why in missing:
        print("  %-8s %s  (%s)" % ("NO HASH", rel, why))

    if args.strict and (changed or missing):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
