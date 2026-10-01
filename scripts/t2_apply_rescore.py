#!/usr/bin/env python3
"""Repair t2-verification.json so grade_all.py is not blocked by verdicts
that are not real citation errors.

The T2 run finished with:

    match 256   mismatch 193   untitled_citation 168   unresolvable 42

grade_all.t2_all_match() promotes a file from medium to high only if
EVERY T2 identifier in it has verdict == 'match'. One non-match blocks
the promotion, which is the right rule. The problem is that 123 of the
193 'mismatch' verdicts are not mismatches at all, so 123 identifiers
are wrongly blocking files that would otherwise promote.

WHERE THE 123 COME FROM, and it is my own bug, not the corpus
The first pass scored a raw string equality on the title, and took the
claimed title with a regex that matched ACROSS unrelated text. Three
distinct failure modes, all producing 'mismatch':

1. The lanes append the id and date to the title they write:
     claimed  "Construct, Align, and Reason: Large Ontology Models ...
                (arXiv 2602.00029, Jan 2026)"
     real     "Construct, Align, and Reason: Large Ontology Models ..."
   Same paper. Ratio 0.854, scored 0.2.

2. A wiki-link's pipe label was taken as the title:
     [[https://arxiv.org/abs/2605.11234|"The Semantic Training Gap"]]
   The real title is "The Semantic Training Gap". The citation is
   correct. The regex grabbed the label and the surrounding prose.

3. A bare URL line was treated as a title claim:
     - https://arxiv.org/abs/1902.01520
   produced the candidate "https://arxi", which cannot match anything.
   A URL fragment is not a claim about a paper.

After fixing the extractor, the 193 become:

      4  looked like real errors; all 4 checked by hand and ALL FOUR
         are correct citations, each a different instance of the
         regex grabbing the wrong span
      5  same title, wording differs  -> genuine 'match'
    118  bare URL, no title stated   -> no claim to check
     66  identifier in no file       -> table artifact

So the honest count of real citation errors in this corpus, from this
run, is ZERO. Not because nothing is wrong, but because every candidate
this run produced turned out to be my own error. That is a statement
about the evidence gathered, not a guarantee about all 2,700 files.

WHAT THIS SCRIPT CHANGES
For each identifier, if the rescoring found a title claim that matches
the real title, the verdict becomes 'match' and the score is the
similarity. Identifiers that are bare-URL or absent are left ALONE
rather than promoted: t2_all_match already requires verdict 'match', and
inventing a match for a citation whose title nobody wrote would be
fabricating the check this project exists to perform.

Dry run by default. --apply writes.
"""
import argparse
import json
import os
import shutil
import sys

SRC = '/home/operator/hermes-brain/docs/audit/t2-verification.json'
RES = '/home/operator/hermes-brain/docs/audit/t2-rescored.json'
N = chr(10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    tbl = json.load(open(SRC, encoding='utf-8'))
    res = json.load(open(RES, encoding='utf-8'))
    items = res['items']

    # wording == the title IS written and it matches: promote to match
    promote = {}
    for it in items.get('wording', []):
        ev = it.get('evidence') or []
        if ev and ev[0]:
            promote[it['id']] = round(float(ev[0][0]), 3)

    print(f'{N}  t2-verification.json: {len(tbl)} identifiers')
    print(f'  confirmed matches from rescoring: {len(promote)}')
    print()

    changes = []
    for ident, score in promote.items():
        v = tbl.get(ident)
        if not v:
            continue
        if v.get('verdict') == 'match':
            continue
        changes.append((ident, v.get('verdict'), 'match', score))

    print(f'  verdicts that will change: {len(changes)}')
    for ident, old, new, score in changes:
        print(f'    {ident[:44]:44} {old:>18} -> {new}  ({score})')

    still = {}
    for v in tbl.values():
        still[v.get('verdict')] = still.get(v.get('verdict'), 0) + 1
    print()
    print('  before: ', still)
    after = dict(still)
    after['match'] = after.get('match', 0) + len(changes)
    for _, old, _, _ in changes:
        after[old] = after.get(old, 1) - 1
    print('  after : ', after)

    if not args.apply:
        print(f'{N}  DRY RUN. Pass --apply.')
        return 0

    bak = SRC + '.pre-rescore.bak'
    shutil.copy2(SRC, bak)
    for ident, _old, _new, score in changes:
        tbl[ident]['verdict'] = 'match'
        tbl[ident]['score'] = score
        tbl[ident]['rescored'] = True
    with open(SRC, 'w', encoding='utf-8') as fh:
        json.dump(tbl, fh, indent=1, sort_keys=True)
    print(f'{N}  written. backup: {bak}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
