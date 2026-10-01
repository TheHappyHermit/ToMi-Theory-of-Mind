#!/usr/bin/env python3
"""Extract the reference lists that 496 "unsourced" files already contain.

THE DISCOVERY
The Phase 5 pilot called 496 files unsourced because their FRONTMATTER
`sources:` was empty. Reading the files shows that is only half true: a
large share already carry a full reference list in the BODY, with
numbered markers in the prose pointing into it. The work has already
been done once; it just never made it into the frontmatter.

Measured over the 496:
  - 108 have both numbered markers and a References/Sources heading
  - the rest have neither, which is the genuinely unsourced group

THREE REAL FORMATS, NOT ONE
  A. "- Label: https://..."        bare bullets, URL at end
  B. "[1] Label - https://..."    numbered, URL at end
  C. "[1] Label (venue, year)"    numbered, NO URL anywhere

Format C matters. A citation with no resolvable URL cannot be tiered,
because the rubric's whole method is "check the host plus the document
status line". It is a real citation -- a real paper with a real venue --
but it is not yet a resolvable source. Those are counted separately and
flagged, because silently grading them as if they were verified would
reproduce the exact error this whole project exists to fix.

WHAT THIS SCRIPT DOES
Extracts, counts, and reports. It does not write. Grades depend on
resolving the host, which is a separate step and the only step that can
legitimately produce high.
"""
import csv
import os
import re
import sys
from collections import Counter

N = chr(10)
REPO = '/home/operator/hermes-brain'
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
CLASSES_CSV = f'{REPO}/docs/audit/overstatement-classes.csv'
OUT_CSV = f'{REPO}/docs/audit/synthesis-sources-found.csv'

REF_HEAD = re.compile(
    r'^#{1,4}\s*(References|Bibliography|Sources(?:\s+(?:and|&)\s+'
    r'Citations)?|Citations|Works Cited)\s*:?\s*$', re.I | re.M)
MARKER = re.compile(r'\[(\d{1,3})\]')
URL = re.compile(r'https?://[^\s<>()\[\]"]+')

# A reference line: a bullet, or a [n] marker, or "Author (Year)."
BULLET = re.compile(r'^\s*[-*+]\s+(?P<lab>.+?)\s*$')
NUMBERED = re.compile(r'^\s*\[(\d{1,3})\]\s*(?P<lab>.+?)\s*$')
BARE = re.compile(r'^\s*(?P<lab>.+?\(\d{4}[a-z]?\))\s*$')


def body_of(path):
    t = open(path, encoding='utf-8', errors='replace').read()
    if not t.startswith('---'):
        return None, None
    e = t.find(N + '---', 3)
    if e == -1:
        return None, None
    return t, t[e + 4:]


def parse_refs(body):
    """Return (list_of_refs, fmt) where each ref is (label, url_or_None)."""
    m = REF_HEAD.search(body)
    if not m:
        return [], None
    tail = body[m.end():]
    # stop at the next heading of the same or higher level
    nxt = re.search(r'\n#{1,4}\s+', tail)
    if nxt:
        tail = tail[:nxt.start()]
    refs = []
    fmt = None
    for line in tail.split(N):
        if not line.strip():
            continue
        if line.lstrip().startswith('#'):
            continue
        mm = NUMBERED.match(line)
        bb = BULLET.match(line)
        if mm:
            fmt = fmt or 'numbered'
            lab = mm.group('lab')
        elif bb:
            fmt = fmt or 'bullet'
            lab = bb.group('lab')
        elif BARE.match(line):
            fmt = fmt or 'bare'
            lab = line.strip()
        else:
            continue
        u = URL.search(lab)
        refs.append((lab, u.group(0).rstrip('.,;') if u else None))
    return refs, fmt


def main():
    rows = list(csv.DictReader(open(CLASSES_CSV, encoding='utf-8')))
    syn = [r for r in rows if r['work_class'] == 'a_unsourced_synthesis']

    out = []
    fmt_count = Counter()
    gradeable = 0
    for r in syn:
        p = ROOTS[r['vault']] + '/' + r['path']
        try:
            _, body = body_of(p)
        except Exception:
            body = None
        refs, fmt = parse_refs(body) if body else ([], None)
        n_url = sum(1 for _, u in refs if u)
        rec = {'vault': r['vault'], 'path': r['path'],
               'file_type': r['file_type'], 'body_words': r['body_words'],
               'n_refs': len(refs), 'n_with_url': n_url,
               'format': fmt or 'none',
               'urls': ' | '.join(u for _, u in refs if u)[:4000]}
        out.append(rec)
        if not refs:
            fmt_count['none_no_reference_section'] += 1
        elif n_url == 0:
            fmt_count['citations_but_no_url'] += 1
        else:
            fmt_count['has_resolvable_urls'] += 1
            gradeable += 1
        fmt_count['fmt_' + (fmt or 'none')] += 1

    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    print(f'\n  {len(syn)} synthesis files\n')
    print('  what is actually in them:')
    for k, v in sorted(fmt_count.items(), key=lambda x: -x[1]):
        print(f'    {v:>4}  {k}')
    print()
    tot_refs = sum(int(r['n_refs']) for r in out)
    tot_urls = sum(int(r['n_with_url']) for r in out)
    print(f'  reference entries found: {tot_refs}')
    print(f'  of which carry a URL:   {tot_urls}')
    print(f'  files gradeable now:    {gradeable} of {len(syn)}')
    print(f'  files needing research: {len(syn) - gradeable}')
    print(f'\n  audit -> {OUT_CSV}')
    print('  NOTHING WRITTEN TO ANY WIKI FILE.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
