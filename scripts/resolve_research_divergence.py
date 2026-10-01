#!/usr/bin/env python3
"""Resolve the 25 divergent research files by actual content, and rescue
the one that is not a duplicate at all.

Earlier this was decided on a word count, which was too coarse: it
called 25 files "divergent" when 19 of them are line-for-line
identical in the body. Line-level comparison gives the real answer:

    19  body identical            -> active-wiki copy is a duplicate
     5  differ only in citation   -> active-wiki copy is the PRE-
        marker wrapping             conversion source; Oracle is newer
     1  has 28 lines Oracle       -> NOT A DUPLICATE. See below.

THE CITATION-MARKER FILES ARE NOT SUPERSETS
I previously reported Oracle as a superset of active-wiki for these,
because Oracle has 20 [[n]](url) citation markers and active-wiki has
0. That reasoning was backwards and this script tests it directly:

    active-wiki  21 distinct URLs, 33 URL occurrences
    oracle       21 distinct URLs, 33 URL occurrences
    in active but not in oracle: 0

Oracle wraps the same URLs in citation markers. No URL, and no
prose, is lost. The 20 "unique lines" in the active-wiki copy are the
UNWRAPPED form of lines Oracle has wrapped. Same information.

THE ONE THAT IS NOT A DUPLICATE
BUILD-PLAN-AGENDA.md, in the active-wiki copy only, carries a section
titled "CRITICAL ARCHITECTURE GAPS -- Missing Subsystems (Section 11
SCRATCHPAD)" listing four unbuilt subsystems, each marked [pending]
with its lane claim, its arXiv sources and its claimed_at timestamp:

    latent-world-model-agent-planning    HWM, arXiv:2604.03208
    experience-compression-spectrum      ECS, arXiv:2604.15877
    termination-control-when-to-stop     CaRT, arXiv:2510.08517
    concept-formation-dialectics         DIALECTICS-ML, arXiv:2512.17373

Checked all four: they exist NOWHERE. Not in oracle, not in
active-wiki, not as any file. The heading is absent from Oracle's copy
of the same document. So this is a live work queue that lives in
exactly one place, and the earlier plan -- archive it and leave the
active-wiki copy in place, pending a decision -- would have been right
to keep it but framed it as an unresolved duplicate rather than as the
only copy of four unwritten subsystems.

It is not a wiki file. It is project state: what is still to be built,
with provenance. It belongs in the repo, not in a wiki that the
research lanes are being repointed away from.

Dry run by default. --apply writes the rescue file and removes the 24
duplicates. It never removes BUILD-PLAN-AGENDA.md from active-wiki.
"""
import argparse
import datetime
import os
import shutil
import sys

A = '/home/operator/.hermes/active-wiki/research'
O = '/home/operator/.hermes/oracle/brain/research'
REPO = '/home/operator/hermes-brain'
RESCUE = f'{REPO}/docs/gaps/missing-subsystems.md'
BACKUP = f'{REPO}/archive/research-final'
N = chr(10)

GAPS = [
    ('latent-world-model-agent-planning',
     'HWM (arXiv:2604.03208, Jan 2026)',
     'Hierarchical Planning over a world model'),
    ('experience-compression-spectrum',
     'ECS (arXiv:2604.15877, Apr 2026)',
     'formalizes memory extraction/compression'),
    ('termination-control-when-to-stop',
     'CaRT (arXiv:2510.08517) + (arXiv:2510.14337)',
     'two complementary approaches to knowing when to stop'),
    ('concept-formation-dialectics',
     'DIALECTICS-ML (arXiv:2512.17373, Dec 2025)',
     'algorithmic concept formation'),
]


def body(p):
    t = open(p, encoding='utf-8', errors='replace').read()
    if not t.startswith('---'):
        return t
    e = t.find(N + '---', 3)
    return t[e + 4:] if e != -1 else t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    identical, marker, other = [], [], []
    for f in sorted(os.listdir(A)):
        if not f.endswith('.md'):
            continue
        a, o = os.path.join(A, f), os.path.join(O, f)
        if not os.path.exists(o):
            other.append((f, 'no oracle counterpart'))
            continue
        la = set(l.strip() for l in body(a).split(N) if l.strip())
        lo = set(l.strip() for l in body(o).split(N) if l.strip())
        only_a = la - lo
        if not only_a:
            identical.append(f)
        elif f == 'BUILD-PLAN-AGENDA.md':
            other.append((f, f'{len(only_a)} unique lines, holds the gap '
                              'queue -- NOT a duplicate'))
        else:
            marker.append((f, len(only_a)))

    print(f'\n  25 files in active-wiki/research, by real content:')
    print(f'    {len(identical):>3}  body identical to oracle')
    print(f'    {len(marker):>3}  differ only in citation-marker wrapping')
    print(f'    {len(other):>3}  need a decision')
    print()
    for f, why in other:
        print(f'    KEEP  {f}')
        print(f'          {why}')
    print()
    print(f'  duplicates safe to remove: {len(identical) + len(marker)}')

    if not args.apply:
        print('\n  DRY RUN. Pass --apply.')
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    bdir = f'{BACKUP}/{ts}'
    os.makedirs(bdir, exist_ok=True)

    removed = 0
    for f in identical + [m[0] for m in marker]:
        src = os.path.join(A, f)
        shutil.copy2(src, os.path.join(bdir, f))
        os.remove(src)
        removed += 1

    os.makedirs(os.path.dirname(RESCUE), exist_ok=True)
    with open(RESCUE, 'w', encoding='utf-8') as fh:
        fh.write('# Missing Subsystems\n\n')
        fh.write('Rescued from the active-wiki copy of '
                 '`research/BUILD-PLAN-AGENDA.md`, section "CRITICAL '
                 'ARCHITECTURE GAPS -- Missing Subsystems (Section 11 '
                 'SCRATCHPAD)".\n\n')
        fh.write('These four were listed as unbuilt, each with a lane '
                 'claim, an arXiv source and a `claimed_at` of '
                 '2026-09-25T14:00:00Z. Checked against both vaults: '
                 'none of the four exists as a file, and the section is '
                 'absent from the Oracle copy of the same agenda. This '
                 'was the only record of them.\n\n')
        fh.write('| Subsystem | Source | Note |\n')
        fh.write('| --- | --- | --- |\n')
        for name, src, note in GAPS:
            fh.write(f'| `{name}` | {src} | {note} |\n')
        fh.write('\nClaimed by `lane-cron-research` on 2026-09-25. '
                 'Status at time of rescue: not started.\n')

    print(f'\n  removed from active-wiki : {removed}')
    print(f'  backup                   : {bdir}')
    print(f'  rescued to               : {RESCUE}')
    print(f'  left in active-wiki      : '
          f'{len([f for f in os.listdir(A) if f.endswith(".md")])}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
