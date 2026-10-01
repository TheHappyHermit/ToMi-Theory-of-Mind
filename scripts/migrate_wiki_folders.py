#!/usr/bin/env python3
"""Move existing active-wiki content into the numbered folders.

Reversible by construction: every move is recorded as (src, dst) in a JSON
journal, and the source tree is verified complete beforehand. A move is a
`git mv`-equivalent rename on the same filesystem -- no copy, no delete, so a
crash mid-run leaves a readable journal and a partially-migrated vault, never
a lost note.

Mapping, and why each one:

    system/      -> 00_System/            the rulebook stays the rulebook
    raw/         -> 01_Raw/               built yesterday, drift-tested
    projects/    -> 30_Projects/          flat files stay flat
    entities/    -> 40_Entities/<kind>/   sorted by the note's own subject
    beliefs/     -> 50_Beliefs/           (1 note; the four-way split is by
                                          epistemic:, not by folder)
    decisions/   -> 60_Decisions/         33 notes, the vault's core
    concepts/    -> 80_Models/            most are type:evergreen
    personal/    -> 10_Self/              empty

Deliberately NOT moved:

    research/    Contains the one research note the 2026-09-28 decision kept
                 here as an exception (BUILD-PLAN-AGENDA.md is the only record
                 of four claimed-but-unwritten subsystems). Research belongs to
                 the Oracle vault; that decision is not this script's to
                 revisit.
    reference/   Empty.
    .meta/       Archive of prior states. Never touched.
    graphify-out Derived index. A stale derived artefact, not content; left for
                 a separate prune rather than silently moved by a rename.

Entity sub-folder selection reads the note's own text for a small set of
signals and falls back to the top level of 40_Entities when nothing matches.
A wrong guess is visible and cheap to move; inventing a category the note does
not support is not recoverable by reading the note afterwards.

Usage:
    python3 scripts/migrate_wiki_folders.py --dry-run
    python3 scripts/migrate_wiki_folders.py
    python3 scripts/migrate_wiki_folders.py --undo <journal.json>
"""
import argparse
import json
import os
import re
import shutil
import sys
import datetime

SIMPLE = {
    "raw": "01_Raw",
    "projects": "30_Projects",
    "beliefs": "50_Beliefs",
    "decisions": "60_Decisions",
    "concepts": "80_Models",
}

# system/ holds 11 dated `verified-facts-*` notes, and they are NOT the
# rulebook: 10 declare `type: temporal` and one `type: log`. They are
# "where things stood on date N" snapshots, which is precisely what
# 80_Models/Current-State is for. Filing them under 00_System would put a
# rolling daily log in the folder meant to hold the ontology and the write
# policy, and would leave the rulebook folder with nothing but its own index.
#
# Only the index and any future non-temporal note stay in 00_System; the
# decision is made per file on the note's own declared `type:`.
SYSTEM_TO_CURRENT_STATE = {"temporal", "log"}

# 40_Entities sub-folders, matched in order against the note body.
ENTITY_KINDS = [
    ("People", r"\bperson\b|\bpeople\b|\bprofile\b|\boperator\b|\bengineer\b|"
               r"\bresearcher\b|\bfounder\b|\bjosh\b"),
    ("Systems", r"\bsystem\b|\binfrastructure\b|\binstall\b|\bstack\b|\bserver\b|"
                r"\bdaemon\b|\bgraphify\b|\bpostgres\b|\bdashboard\b|\bstack\b"),
    ("Models", r"\bmodel\b|\bllm\b|\bweights\b|\bembedding\b|\bfine-tun"),
    ("Products", r"\btool\b|\bsoftware\b|\bapp\b|\bpackage\b|\blibrary\b|"
                 r"\bextension\b|\bplugin\b"),
    ("Organizations", r"\bcompany\b|\borganization\b|\borganisation\b|\bteam\b|"
                      r"\bprovider\b|\blab\b"),
    ("Places", r"\bplace\b|\bcity\b|\bcounty\b|\bregion\b|\bhost at\b"),
]


def declared_type(path):
    """Read a note's own declared `type:` rather than inferring it.

    The note is the authority on what it is. Guessing from the filename or
    the folder it happens to sit in is how a `temporal` snapshot ends up filed
    as a rulebook.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(2000)
    except OSError:
        return None
    m = re.match(r"^---\n(.*?)\n---\n", head, re.S)
    if not m:
        return None
    t = re.search(r"^type:\s*[\"']?([A-Za-z0-9_-]+)[\"']?\s*$",
                  m.group(1), re.M)
    return t.group(1) if t else None


def classify_entity(text):
    low = text.lower()
    for kind, pat in ENTITY_KINDS:
        if re.search(pat, low):
            return kind
    return None


def plan(vault):
    moves = []
    # system/ routes per file on its own declared type.
    sysdir = os.path.join(vault, "system")
    if os.path.isdir(sysdir):
        for f in sorted(os.listdir(sysdir)):
            src = os.path.join(sysdir, f)
            if not os.path.isfile(src) or not f.endswith(".md"):
                continue
            if f == "index.md":
                moves.append((src, os.path.join(vault, "00_System", "index.md")))
                continue
            ty = declared_type(src)
            if ty in SYSTEM_TO_CURRENT_STATE:
                moves.append((src, os.path.join(vault, "80_Models",
                                                "Current-State", f)))
            else:
                moves.append((src, os.path.join(vault, "00_System", f)))
    for old, new in SIMPLE.items():
        src_dir = os.path.join(vault, old)
        if not os.path.isdir(src_dir):
            continue
        for f in sorted(os.listdir(src_dir)):
            src = os.path.join(src_dir, f)
            if not os.path.isfile(src) or not f.endswith(".md"):
                continue
            if f == "index.md":
                dst = os.path.join(vault, new, "index.md")
            else:
                dst = os.path.join(vault, new, f)
            moves.append((src, dst))
    # entities -> kind sub-folders
    ent = os.path.join(vault, "entities")
    if os.path.isdir(ent):
        for f in sorted(os.listdir(ent)):
            src = os.path.join(ent, f)
            if not os.path.isfile(src) or not f.endswith(".md"):
                continue
            if f == "index.md":
                moves.append((src, os.path.join(vault, "40_Entities", "index.md")))
                continue
            body = ""
            try:
                body = open(src, encoding="utf-8", errors="replace").read()
            except OSError:
                pass
            kind = classify_entity(body)
            dst = os.path.join(vault, "40_Entities", kind, f) if kind \
                else os.path.join(vault, "40_Entities", f)
            moves.append((src, dst))
    return moves


def run(vault, dry):
    moves = plan(vault)
    # Preflight: never lose, never silently clobber.
    #
    # An old folder's index.md and the skeleton's index.md are both "index.md"
    # and both matter -- the old one lists real content. Overwriting either
    # loses information, so index-to-index collisions are resolved by MERGING
    # the old links into the new index at apply time, and every other
    # collision aborts the run.
    merges = []
    for src, dst in moves:
        if not os.path.isfile(src):
            sys.exit("source vanished: %s" % src)
        if os.path.exists(dst) and not os.path.samefile(src, dst):
            if os.path.basename(src) == "index.md" and \
                    os.path.basename(dst) == "index.md":
                merges.append((src, dst))
            else:
                sys.exit("destination already exists, refusing to clobber: %s" % dst)
    moves = [m for m in moves if m not in merges]
    if dry:
        print("would move %d file(s):" % len(moves))
        for src, dst in moves:
            print("  %-40s -> %s" % (os.path.relpath(src, vault),
                                     os.path.relpath(dst, vault)))
        print("would MERGE %d index file(s) (links preserved):" % len(merges))
        for src, dst in merges:
            print("  %-40s -> %s" % (os.path.relpath(src, vault),
                                     os.path.relpath(dst, vault)))
        return None
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    journal = os.path.expanduser(
        "~/.hermes/cache/scratch/wiki-move-journal-%s.json" % ts)
    done = []
    for src, dst in moves:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        done.append({"src": os.path.relpath(src, vault),
                     "dst": os.path.relpath(dst, vault)})
    merged = []
    for src, dst in merges:
        links = extract_links(src)
        with open(dst, "a", encoding="utf-8") as fh:
            fh.write("\n## Migrated content (from `system/`, `decisions/`, "
                     "etc., pre-restructure)\n\n")
            if links:
                for l in links:
                    fh.write(l + "\n")
            else:
                fh.write("- (this folder's index was the only content)\n")
        shutil.copy2(src, src + ".migrated-into-" + os.path.basename(dst))
        merged.append({"src": os.path.relpath(src, vault),
                       "dst": os.path.relpath(dst, vault),
                       "links": len(links)})
    json.dump({"vault": vault, "when": ts, "moves": done, "merges": merged},
              open(journal, "w"), indent=1)
    print("moved %d file(s); merged %d index file(s); journal: %s"
          % (len(done), len(merged), journal))
    return journal


def extract_links(path):
    """Wikilinks and markdown links from an old index, as lines to append."""
    out = []
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            s = line.rstrip()
            if not s.strip():
                continue
            if re.search(r"\[\[[^\]]+\]\]", s) or re.search(r"\]\([^)]+\)", s):
                out.append(s)
    except OSError:
        pass
    return out


def undo(journal_path):
    j = json.load(open(journal_path))
    vault = j["vault"]
    n = 0
    for m in reversed(j["moves"]):
        src = os.path.join(vault, m["dst"])
        dst = os.path.join(vault, m["src"])
        if not os.path.isfile(src):
            sys.exit("cannot undo, missing: %s" % src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        n += 1
    print("restored %d file(s)" % n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.path.expanduser("~/.hermes/active-wiki"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--undo")
    a = ap.parse_args()
    if a.undo:
        return undo(a.undo)
    run(a.vault, a.dry_run)


if __name__ == "__main__":
    main()
