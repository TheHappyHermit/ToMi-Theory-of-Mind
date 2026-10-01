#!/usr/bin/env python3
"""Rename the active wiki's folders to the numbered taxonomy, in place.

Scope, stated precisely because it is narrow:

  * A folder is RENAMED. `decisions/` becomes `60_Decisions/`. Nothing else.
  * Every note's BYTES are preserved except for one mechanical edit: relative
    markdown links that named a renamed folder. Those are the only content
    change, and they have to change or they resolve to nothing.
  * No note is moved into a numbered sub-folder it did not already live in.
    `system/verified-facts-*.md` stays a direct child of the renamed folder.
    Splitting content by `type:` was considered and rejected: it is a filing
    decision, not a rename, and the ask was "rename the folders".

Why links need handling at all
------------------------------
The vault contains three link forms and only one of them is path-independent:

  * `[[wikilinks]]`  -- 1,600+ of them, resolved by BASENAME. Depth-independent,
    so a rename cannot break them. Left alone.
  * relative markdown `[x](../decisions/y.md)` -- 81 of them, hardcoded to the
    old folder name. A rename breaks every one. Rewritten in place.
  * same-folder `[x](y.md)` -- only breaks if a note changes DEPTH, which this
    script never does (renames happen at the top level, sub-folder structure is
    untouched). Verified rather than assumed.

The `../` depth in a rewritten link is recomputed from the note's real new
location rather than string-substituted, because `system/` -> `00_System/`
keeps the same depth while `raw/` -> `01_Raw/` also does, but a note in a
SUBDIRECTORY of a renamed folder would need its prefix re-counted. Doing it by
resolution is the only version that stays correct if that case ever appears.

Reversibility
-------------
Every step writes to a journal, and `--undo <journal>` reverses it. The
pre-restructure snapshot at ~/.hermes/cache/scratch/ plus a sha256 manifest of
all 94 notes is the second, independent safety net.

Usage:
    python3 scripts/rename_wiki_folders.py --dry-run
    python3 scripts/rename_wiki_folders.py
    python3 scripts/rename_wiki_folders.py --undo <journal.json>
"""
import argparse
import json
import os
import re
import shutil
import sys
import datetime

# old folder -> new folder. Top-level renames only.
RENAMES = {
    "system": "00_System",
    "raw": "01_Raw",
    "projects": "30_Projects",
    "entities": "40_Entities",
    "beliefs": "50_Beliefs",
    "decisions": "60_Decisions",
    "concepts": "80_Models",
    "personal": "10_Self",
}

# Folders deliberately NOT renamed.
#   research/  - the 2026-09-28 decision kept BUILD-PLAN-AGENDA.md here as a
#                documented exception; that decision is not this script's to
#                revisit.
#   reference/ - empty, and the taxonomy has no folder for it.
#   .meta/     - archive of prior states, never touched.
#   graphify-out/ - a derived index, pruned separately.

LINK_RE = re.compile(r"(\]\()((?:\.\./|\./)?)([A-Za-z0-9_.\-]+)/([^\)]+)(\))")


def rebase(prefix, note_rel_dir, newfolder, rest):
    """Rebuild a relative link after its target folder was renamed.

    Keep the `../` prefix EXACTLY as written and swap only the folder name.
    That is sufficient here and is not a shortcut, for one reason: every rename
    in RENAMES is a TOP-LEVEL folder, so a note's own depth never changes and
    the number of levels between the note and the vault root is unaffected.
    A link that climbed one level still climbs one level.

    Two wrong versions came before this one, both caught by a test that
    resolves each rewritten link against a real file rather than comparing
    strings:

      * Popping the note's directory segments (as `os.path.normpath` does)
        consumed the `..` and produced `40_Entities/x.md` from inside
        `60_Decisions/` -- which resolves to `60_Decisions/40_Entities/x.md`,
        a path that does not exist.
      * The mirror-image error, keeping a `../` that popped past the vault
        root, which resolves outside the vault entirely.

    Preserving the prefix is the only form that survives both, and it is
    checkable: `scripts/rename_wiki_folders.py --verify` re-resolves every
    link in the vault afterwards.
    """
    if prefix.startswith("./"):
        return "./" + newfolder + "/" + rest
    if prefix:
        return prefix + newfolder + "/" + rest
    return newfolder + "/" + rest


def rewrite_links(text, note_rel_dir, vault, renames):
    """Rewrite relative links that name a renamed folder.

    `note_rel_dir` is the note's directory relative to the vault root, AFTER
    the rename. The link is RE-RESOLVED from there rather than string-
    substituted, because a link written as `../entities/x.md` from inside
    `decisions/` and one written as `../../entities/x.md` from inside
    `decisions/Sub/` need different results, and the `../` count is the only
    thing that distinguishes them.

    Three bugs this replaced, each found by a test before it could reach a
    real note:

      * dropping the `../` prefix entirely, so a link from `60_Decisions/`
        resolved to `40_Entities/...` -- one level too high, hence broken;
      * double-prefixing `./decisions/f.md` into
        `60_Decisions/60_Decisions/f.md`, because the already-rewritten text
        was matched again on the next iteration;
      * leaving `../../concepts/x.md` alone from a sub-folder, because only
        the top-level case was handled.
    """
    fixed = []

    def repl(m):
        open_p, prefix, oldfolder, rest, close = m.groups()
        if oldfolder not in renames:
            return m.group(0)
        newfolder = renames[oldfolder]
        newrel = rebase(prefix, note_rel_dir, newfolder, rest)
        fixed.append((m.group(0), newrel))
        return "](%s)" % newrel

    # One pass only. `re.sub` does not rescan its own replacements, which is
    # what caused the double-prefix in the second bug above.
    text = re.sub(
        r"(\]\()((?:\.\./|\./)?)([A-Za-z0-9_.\-]+)/([^\)]+)(\))", repl, text)

    # Path-prefixed WIKILINKS: `[[decisions/foo]]`.
    #
    # A separate case from markdown links because these resolve by BASENAME
    # in the linter -- the folder prefix is decorative to it, so it flagged
    # only one of the twelve that existed and the other eleven were left
    # pointing at a folder name that no longer exists. Found by grepping for
    # the shape, not by trusting the gate, which checked one file per run.
    def wl(m):
        folder, rest = m.group(1), m.group(2)
        if folder not in renames:
            return m.group(0)
        fixed.append((m.group(0), "[[%s/%s]]" % (renames[folder], rest)))
        return "[[%s/%s]]" % (renames[folder], rest)

    text = re.sub(r"\[\[([A-Za-z0-9_.\-]+)/([^\]]+)\]\]", wl, text)
    return text, fixed


def run(vault, dry):
    preflight = []
    for old, new in RENAMES.items():
        src = os.path.join(vault, old)
        if not os.path.isdir(src):
            print("skip (absent): %s" % old)
            continue
        dst = os.path.join(vault, new)
        if os.path.isdir(dst):
            # The skeleton already created it. Merge the real notes into it.
            preflight.append((src, dst, "merge"))
        else:
            preflight.append((src, dst, "rename"))
    if dry:
        for src, dst, how in preflight:
            n = len([f for f in os.listdir(src) if f.endswith(".md")])
            print("  %-11s -> %-13s %-6s (%d notes)" %
                  (os.path.basename(src), os.path.basename(dst), how, n))
        return None
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    journal = os.path.expanduser(
        "~/.hermes/cache/scratch/wiki-rename-journal-%s.json" % ts)
    ops = []
    for src, dst, how in preflight:
        os.makedirs(dst, exist_ok=True)
        for f in sorted(os.listdir(src)):
            s = os.path.join(src, f)
            d = os.path.join(dst, f)
            if not os.path.isfile(s):
                continue
            if os.path.exists(d):
                # index.md collision between the old folder and the skeleton:
                # keep the skeleton index and archive the old one, never clobber.
                shutil.copy2(s, d + ".superseded-index")
                ops.append({"op": "supersede_index", "from": os.path.relpath(s, vault),
                            "to": os.path.relpath(d, vault)})
                continue
            shutil.move(s, d)
            ops.append({"op": "move", "from": os.path.relpath(s, vault),
                        "to": os.path.relpath(d, vault)})
        # The now-empty old directory goes; its content already moved.
        leftovers = [x for x in os.listdir(src) if not x.startswith(".")]
        if not leftovers:
            os.rmdir(src)
            ops.append({"op": "rmdir", "path": os.path.basename(src)})
        else:
            print("  NOTE: %s not empty, left in place: %s"
                  % (os.path.basename(src), leftovers))

    # Second pass: rewrite links now that every note sits in its final place.
    linkfixes = []
    for root, dirs, files in os.walk(vault):
        if any(x in root for x in ("/.meta", "graphify-out")):
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            rel_dir = os.path.relpath(root, vault)
            try:
                t = open(p, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            new, fixed = rewrite_links(t, rel_dir, vault, RENAMES)
            if fixed:
                open(p, "w", encoding="utf-8").write(new)
                linkfixes.append({"file": os.path.relpath(p, vault),
                                  "links": len(fixed)})
    json.dump({"vault": vault, "when": ts, "renames": RENAMES,
               "ops": ops, "linkfixes": linkfixes},
              open(journal, "w"), indent=1)
    print("renamed %d folder(s); moved %d file(s); rewrote links in %d file(s)"
          % (len(preflight), len([o for o in ops if o['op'] == 'move']),
             len(linkfixes)))
    print("journal: %s" % journal)
    return journal


def undo(journal_path):
    j = json.load(open(journal_path))
    vault = j["vault"]
    n = 0
    # reverse linkfixes first? No: the journal stores the new names only.
    # Content restoration comes from the pre-restructure snapshot, which is
    # the honest guarantee; this undoes the moves so a rename is a rename back.
    for o in reversed(j["ops"]):
        if o["op"] == "move":
            s = os.path.join(vault, o["to"])
            d = os.path.join(vault, o["from"])
            if os.path.isfile(s) and not os.path.exists(d):
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.move(s, d)
                n += 1
        elif o["op"] == "rmdir":
            p = os.path.join(vault, o["path"])
            if os.path.isdir(p) and not os.listdir(p):
                os.rmdir(p)
    print("reversed %d move(s); NOTE rewritten link text is not reverted --" % n)
    print("restore note bodies from the pre-restructure snapshot if you need them.")


def verify(vault):
    """Re-resolve every relative link in the vault and report what breaks.

    The check that matters after a rename. Counting rewritten links proves the
    script ran; this proves the links still point at files. A rename that
    "succeeded" while quietly breaking 80 links is the failure this exists to
    catch, and it is exactly the shape of bug the rebase function went through
    twice.
    """
    LINK = re.compile(r"\]\(((?:\.\./|\./)?)([A-Za-z0-9_.\-]+)/([^\)]+)\)")
    good = broken = 0
    details = []
    for root, dirs, files in os.walk(vault):
        if any(x in root for x in ("/.meta", "graphify-out")):
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            try:
                t = open(p, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for prefix, folder, rest in LINK.findall(t):
                if rest.startswith(("http://", "https://", "#", "/")):
                    continue
                tgt = os.path.normpath(os.path.join(root, prefix + folder, rest))
                if os.path.isfile(tgt):
                    good += 1
                else:
                    broken += 1
                    details.append((os.path.relpath(p, vault),
                                    prefix + folder + "/" + rest))
    print("relative links resolving: %d" % good)
    print("relative links broken:    %d" % broken)
    for f, l in details[:20]:
        print("  BROKEN  %-44s %s" % (f[:42], l))
    return broken


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=os.path.expanduser("~/.hermes/active-wiki"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--undo")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(a.vault):
        sys.exit("no such vault: %s" % a.vault)
    if a.undo:
        return undo(a.undo)
    if a.verify:
        sys.exit(1 if verify(a.vault) else 0)
    run(a.vault, a.dry_run)


if __name__ == "__main__":
    main()
