#!/usr/bin/env python3
"""Re-score the T2 mismatches. The first pass conflated three different
things under one label, and one of the three is my own bug.

the operator asked whether the mismatches were real errors or a too-strict
matcher. Answer: mostly the matcher. Sampling the 193 showed all three
classes at once:

  written "Construct, Align, and Reason: Large Ontology Models ... (arXiv
  2602.00029, Jan 2026)"
  real    "Construct, Align, and Reason: Large Ontology Models ..."
  sim 0.854   SAME TITLE. The file appends the id and date in
              parentheses. Scored 0.2 because the raw string differs.

  written "D-MEM Critic Router -- Surprise-Based Encoding Gate"
  real    "D-MEM: Dopamine-Gated Agentic Memory via Reward Prediction"
  sim 0.317   A REAL ERROR. Different paper attributed to one id.

  written "Local Lipschitz bands for continuum-armed bandits"
  real    "Contextual Bandits with Continuous Actions: ..."
  sim 0.440   A REAL ERROR, and the claimed title is not a paper at all.

So the first pass produced a number (193) that was mostly noise, and a
report that would have told the operator 193 citations were broken. They are not.

This re-scores properly:
  - strips the "(arXiv NNNNN.NNNNN, Mon YYYY)" tail the lanes append
  - normalises case, punctuation, and stopwords
  - uses difflib ratio with a threshold instead of a raw equality test
  - separates files that write NO title (a bare URL cannot be wrong,
    there is no claim to check) from files that DO write one
  - flags identifiers that appear in no file at all, which are artifacts
    of the table rather than citations

Run dry. Only --apply writes docs/audit/t2-rescored.json.
"""
import argparse
import difflib
import json
import os
import re
import sys

OUT_SRC = '/home/operator/hermes-brain/docs/audit/t2-verification.json'
OUT_DST = '/home/operator/hermes-brain/docs/audit/t2-rescored.json'
ROOTS = ['/home/operator/.hermes/oracle/brain',
         '/home/operator/.hermes/active-wiki']

# The lanes write citations in several shapes. These are the ones that
# actually carry a title; a bare URL line is handled separately.
TAIL = re.compile(
    r'\s*[\(\[]\s*(arxiv[:\s]*|doi[:\s]*)?[0-9]{4}\.[0-9]{4,5}'
    r'[^)\]]*[\)\]]\s*')
TAIL2 = re.compile(
    r'\s*[\(\[]\s*(arxiv|doi)?[:\s]*[0-9]{4}\.[0-9]{4,5}'
    r'(\s*,\s*[A-Z][a-z]{2}\s+\d{4})?[^)\]]*[\)\]]\s*')
ID_RE = re.compile(
    r'(arxiv\.org/abs/|arxiv\.org/pdf/|arxiv:|doi\.org/|doi:)'
    r'\s*([0-9]{4}\.[0-9]{4,5}|[^\s)\],"]+)')
NOT_A_TITLE = re.compile(r'https?://|www\.|\.org|\.com|@|\.{3,}')
QUOTED = re.compile('["“”]([^"“”\n]{12,140}?)["“”]')


def norm(s):
    s = s.lower()
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = re.sub(
        r'\b(the|a|an|of|for|and|in|on|to|with|via|is|as|that|this|'
        r'its|from|by|at|we|our)\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def ratio(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--threshold', type=float, default=0.82,
                    help='ratio at or above which the title is considered '
                         'the same paper written differently')
    args = ap.parse_args()

    d = json.load(open(OUT_SRC, encoding='utf-8'))

    # index every file's lines, and where each identifier appears
    where = {}
    for root in ROOTS:
        for dp, dn, fn in os.walk(root):
            if '.meta' in dp.split(os.sep):
                continue
            for f in fn:
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                try:
                    lines = open(p, encoding='utf-8',
                                 errors='replace').read().split('\n')
                except OSError:
                    continue
                for i, line in enumerate(lines):
                    for m in ID_RE.finditer(line):
                        where.setdefault(m.group(2), []).append(
                            (f, i, line))

    buckets = {'true_mismatch': [], 'wording': [], 'no_title_written': [],
               'not_in_corpus': []}
    for ident, v in d.items():
        if v.get('verdict') != 'mismatch':
            continue
        bare = ident.split(':', 1)[1] if ':' in ident else ident
        real = v.get('title') or ''
        hits = where.get(bare, [])
        if not hits:
            buckets['not_in_corpus'].append((ident, real, []))
            continue
        best = None
        for f, i, line in hits:
            # the claimed title, if this line states one
            tail = TAIL2.sub('', line)
            cand = None
            q = QUOTED.search(tail)
            if q:
                cand = q.group(1)
            else:
                # a line like "- Title Here (Author et al. 2020)"
                m = re.match(r'^\s*[-*]?\s*([A-Z][^:]{10,120}?)\s*'
                             r'\((?:[^)]*)\)\s*$', tail.strip())
                if m:
                    cand = m.group(1)
            # A URL fragment or a bare id is not a claim about a
            # paper's title. Reject it before the similarity test,
            # or every bare-URL citation becomes a false error.
            if cand:
                cand = cand.strip().strip('.,;:-')
                letters = sum(ch.isalpha() for ch in cand)
                if (NOT_A_TITLE.search(cand)
                        or letters < max(8, len(cand) * 0.55)):
                    cand = None
            if cand:
                r = ratio(cand, real)
                if best is None or r > best[0]:
                    best = (r, f, cand)
        if best is None:
            buckets['no_title_written'].append((ident, real, hits[:1]))
        elif best[0] >= args.threshold:
            buckets['wording'].append((ident, real, [best]))
        else:
            buckets['true_mismatch'].append((ident, real, [best]))

    total = sum(len(b) for b in buckets.values())
    print(f'\n  re-scoring {total} first-pass mismatches '
          f'(threshold {args.threshold})')
    print()
    for k in ('true_mismatch', 'wording', 'no_title_written',
              'not_in_corpus'):
        print(f'    {len(buckets[k]):>4}  {k}')
    print()

    if buckets['true_mismatch']:
        print('  REAL ERRORS -- the file attributes a different paper,')
        print('  or a title that does not exist, to a real identifier:')
        for ident, real, info in sorted(
                buckets['true_mismatch'],
                key=lambda x: x[2][0][0] if x[2] else 0)[:20]:
            r, f, cand = info[0]
            print(f'    {os.path.basename(f)[:40]}')
            print(f'      id    : {ident}')
            print(f'      claims: {cand[:88]}')
            print(f'      real  : {real[:88]}')
            print(f'      sim   : {r:.2f}')
        if len(buckets['true_mismatch']) > 20:
            print(f'    ... and '
                  f'{len(buckets["true_mismatch"]) - 20} more')

    print()
    print('  NOT errors:')
    print(f'    {len(buckets["wording"])}  same title, wording/prefix '
          f'differs -- these citations are correct')
    print(f'    {len(buckets["no_title_written"])}  a bare URL with no '
          f'title stated -- no claim to check')
    print(f'    {len(buckets["not_in_corpus"])}  identifier not found in '
          f'any file -- table artifact')

    if not args.apply:
        print('\n  DRY RUN. Pass --apply to write '
              'docs/audit/t2-rescored.json')
        return 0

    out = {}
    for k, items in buckets.items():
        out[k] = [{'id': i, 'real_title': rt, 'evidence': ev}
                  for i, rt, ev in items]
    with open(OUT_DST, 'w', encoding='utf-8') as fh:
        json.dump({'threshold': args.threshold, 'summary':
                   {k: len(v) for k, v in buckets.items()},
                   'items': out}, fh, indent=1)
    print(f'\n  written: {OUT_DST}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
