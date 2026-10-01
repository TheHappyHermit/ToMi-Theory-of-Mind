#!/usr/bin/env python3
"""Fix the page template that taught untitled citations, in every profile.

The problem
-----------
Six researcher SOUL.md files carried this in their page template:

    sources:
      - "https://... or Local research stack: Camofox + Firecrawl + SearXNG (YYYY-MM-DD)"

A model copying that template writes a bare URL with no title. The T2 verifier
resolves the identifier, fetches the real document, and compares the real title
against the title recorded here -- with nothing to compare, the row is recorded
`untitled_citation` and the page is capped at `medium` permanently, with no
error shown to the writer.

So the template was not merely incomplete, it was actively teaching the exact
shape that fails. Measured: 1,605 of 2,661 identifier-bearing citations in the
corpus carry no title.

The fix
-------
Replace the placeholder with a shape that includes the title, and add a short
rule next to it. The block is deliberately short: SOUL.md loads on every turn
of that profile, so a long essay here taxes every request to save one
class of bad write. The full rationale lives in docs/CITATION-WRITING.md and
is pointed at rather than restated.

Idempotent, and --check reports without writing.
"""
import argparse
import glob
import os
import re
import shutil
import sys

PROFILES = os.path.expanduser("~/.hermes/profiles")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLD_LINE_MARKER = 'https://... or Local research stack'


def build_block(indent):
    """The replacement, indented to match the template being replaced.

    Hardcoding six spaces would leave 3090-researcher's two-space template
    malformed -- a YAML list whose items are indented deeper than the key is
    still legal, but the block would no longer read as part of the template
    it sits in, and the next edit to that file would likely re-break it.
    """
    lines = [
        f"{indent}sources:",
        f"{indent}  # Every source entry with a DOI or arXiv id MUST carry the",
        f"{indent}  # paper's TITLE. The grader fetches the real document and",
        f"{indent}  # compares its title against the one written here; with nothing",
        f"{indent}  # to compare, the page is capped at `medium` forever and",
        f"{indent}  # nothing reports the problem.",
        f'{indent}  - "arXiv:2509.20021 (Embodied AI Survey)"                 # GOOD',
        f'{indent}  - "doi:10.1109/PROC.1975.9939 (The protection of information in computer systems)"',
        f'{indent}  - "https://... (exact title as the source states it)"      # untiered web source',
        f'{indent}  - "home.example.com (homelab service index)"',
        f'{indent}  - "Local research stack: Camofox + Firecrawl + SearXNG (YYYY-MM-DD)"',
        f"{indent}  # Fetch the title from the source -- never from memory or a",
        f"{indent}  # snippet. If you cannot retrieve it, write the identifier",
        f"{indent}  # alone and set status: unverified. Never invent a title; a",
        f"{indent}  # wrong one is a fabrication and is capped at `low`, which is",
        f"{indent}  # worse than having none.",
        f"{indent}  # Full rationale: /home/operator/hermes-brain/docs/CITATION-WRITING.md",
        f"{indent}  # Verify before finishing:  python3 /home/operator/hermes-brain/scripts/okf_gate.py <file>",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    targets = sorted(glob.glob(os.path.join(PROFILES, "*", "SOUL.md")))
    changed, already = [], []

    for f in targets:
        try:
            text = open(f, encoding="utf-8").read()
        except Exception:
            continue
        if OLD_LINE_MARKER not in text:
            if "CITATION-WRITING.md" in text:
                already.append(f)
            continue

        # Replace the whole sources: block, from the key through every
        # following list item, so the indentation and the surrounding
        # template stay coherent.
        #
        # The indentation is captured rather than hardcoded. 3090-researcher
        # indents its list items by 2 spaces while the other five use 6, and
        # it carries a SECOND source line ("home.example.com (...)")
        # that a single-line pattern would have left dangling under a
        # rewritten block. Matching the full list keeps the block together.
        pattern = re.compile(
            r"^([ \t]*)sources:[ \t]*\n"
            r"(?:\1[ \t]*-[^\n]*\n)+",
            re.M)
        pm = pattern.search(text)
        if pm is None:
            print("SKIP (pattern did not match cleanly): %s" % f)
            continue
        block = build_block(pm.group(1))
        new_text, n = pattern.subn(block, text, count=1)
        if n != 1:
            print("SKIP (pattern did not match cleanly): %s" % f)
            continue

        if args.check:
            changed.append(f)
            continue

        backup = f + ".bak-pre-citation-template"
        shutil.copy2(f, backup)
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        changed.append(f)
        print("fixed %s  (backup: %s)" % (
            os.path.relpath(f, PROFILES), os.path.basename(backup)))

    todo = [f for f in changed if True]
    if args.check:
        print("\nSOUL.md files still teaching the untitled pattern: %d" % len(todo))
        for f in todo:
            print("   %s" % os.path.relpath(f, PROFILES))
        return 1 if todo else 0

    print("\n%d file(s) updated; %d already correct" % (len(changed), len(already)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
