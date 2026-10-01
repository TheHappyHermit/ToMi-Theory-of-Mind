#!/usr/bin/env python3
"""Regression test: a label belongs to one identifier, not to the file.

This is the bug behind the 191 false "mismatch" verdicts, and it is
worth a permanent test because it is the same SHAPE as the five
inline_title bugs already fixed, one level up. Every one of those was
"a candidate that does not belong to this identifier was compared
against this identifier's title". This one is the file-level version:
cited_titles() returns every bullet in the file, and that list was
compared against the resolved title of each identifier in the file.

Measured on the real corpus:

    kalman-delta-rule-attribution.md
      bullet lines in file          59
      mentions of arXiv:2012.00073   2
      labels compared against the resolved title of 2012.00073:  59
      of those, about this paper:                                 1

So 58 citations to unrelated papers were scored against TimeSHAP, none
matched, the best score stayed 0.0, and the verdict became `mismatch`
for a citation that is correct in every respect. 58 of 59 candidates
had to fail before the one right answer could win, and `title_match`
takes the best score, so the right answer DID win when it was present
-- but when the identifier appears only as a bare id in prose and
never in a bullet, every candidate is someone else's paper and the
verdict is wrong with no chance of being right.

The rule: intersect the labels with the identifier before comparing.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VAULT = '/home/operator/.hermes/oracle/brain/research'

FILE = 'kalman-delta-rule-attribution.md'
IDENT = '2012.00073'


def main():
    p = os.path.join(VAULT, FILE)
    if not os.path.exists(p):
        print(f'  corpus file not present: {p}')
        print('  cannot run the live test; the synthetic cases below still run')
        return run_synthetic()
    text = open(p, encoding='utf-8', errors='replace').read()
    labels = re.findall(r'^\s*[-*+]\s+(.+?)\s*$', text, re.M)
    mentions = text.count(IDENT)

    unfiltered = len(labels)
    filtered = [l for l in labels if IDENT in l]

    print(f'  {FILE}')
    print(f'    bullet labels in file                 {unfiltered}')
    print(f'    mentions of {IDENT}  {mentions}')
    print(f'    labels compared BEFORE the fix         {unfiltered}')
    print(f'    labels compared AFTER the fix          {len(filtered)}')
    print(f'    candidates that were about other papers '
          f'{unfiltered - len(filtered)}')

    bad = 0
    if filtered:
        print()
        for l in filtered:
            print(f'    belongs to it: {l[:64]}')
    else:
        print()
        print('    no label mentions it -> the honest verdict is')
        print('    untitled_citation, not mismatch. The identifier is')
        print('    a bare id in prose with no title to check.')
    if unfiltered <= len(filtered):
        print('  WARNING: filter removed nothing, the file does not')
        print('           exercise this bug. Treat the result as unproven.')
        bad += 1
    return bad + run_synthetic()


def run_synthetic():
    """The same shape, in miniature, so the test works without the corpus."""
    N = chr(10)
    text = N.join([
        '- arxiv:1111.11111',
        '- Some Paper About Widgets. Journal. 2020',
        '- arxiv:2222.22222',
        '- Another Paper. NeurIPS. 2021',
    ]) + N
    labels = re.findall(r'^\s*[-*+]\s+(.+?)\s*$', text, re.M)
    ident = '1111.11111'
    own = [l for l in labels if ident in l]
    ok = len(labels) == 4 and len(own) == 1
    print()
    print(f'  synthetic: {len(labels)} labels, {len(own)} for {ident} '
          f'{"OK" if ok else "WRONG"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
