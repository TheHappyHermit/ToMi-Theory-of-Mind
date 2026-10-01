#!/usr/bin/env python3
"""Consolidate active-wiki/research into oracle/brain/research.

the operator: "I also want all of the research outputs that have been put in the
active wiki moved to the Oracle wiki."

THE AUDIT CHANGED WHAT THIS IS
This is not a move. Every one of the 474 files in active-wiki/research
ALREADY has a copy in oracle/brain/research:

  474  basename collisions with oracle
  461  byte-identical
   13  differing -- and of those, 8 differ only in whitespace
        (+0 words), 1 differs by a frontmatter timestamp, and one is a
        genuine version difference

The lanes have been writing to Oracle all along (that is the two-path
write boundary in every lane prompt), and the active-wiki copies are
residue from before that boundary existed, or from the sync copying
back. So the correct operation is: confirm Oracle holds the content,
then remove the duplicate. Not copy over the top, which would silently
discard the longer Oracle version of BUILD-PLAN-AGENDA.md.

WHAT IS SAFE TO REMOVE
  461  byte-identical -- removing the active-wiki copy loses nothing
  449  body-identical, frontmatter differs only in a timestamp
    8  body differs by ZERO words (whitespace only)

WHAT IS NOT REMOVED WITHOUT A DECISION
  BUILD-PLAN-AGENDA.md   active 48,966 words, oracle 55,869
  frontier-research-kg-ontology-memory.md   +33 words in oracle
  and four others with small differences
  These are archived into a holding directory rather than deleted. the operator
  does not delete content, and the difference may be meaningful.

BACKUP
Every file is copied to archive/research-consolidation/<ts>/ before
anything is removed, preserving its active-wiki-relative path.
"""
import argparse
import datetime
import hashlib
import os
import shutil
import sys

A = '/home/operator/.hermes/active-wiki'
O = '/home/operator/.hermes/oracle/brain'
REPO = '/home/operator/hermes-brain'
BACKUP = f'{REPO}/archive/research-consolidation'
HOLD = f'{REPO}/archive/research-divergent'
N = chr(10)


def walk_md(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        if '.meta' in dp.split(os.sep):
            continue
        for f in fn:
            if f.endswith('.md'):
                p = os.path.join(dp, f)
                out[os.path.relpath(p, root)] = p
    return out


def h(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def body(p):
    t = open(p, encoding='utf-8', errors='replace').read()
    if not t.startswith('---'):
        return t
    e = t.find(N + '---', 3)
    return t[e + 4:] if e != -1 else t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--word-tolerance', type=int, default=0,
                    help='treat bodies within N words as identical')
    args = ap.parse_args()

    a = walk_md(A + '/research')
    o = walk_md(O)
    by_base = {}
    for k, v in o.items():
        by_base.setdefault(os.path.basename(k), []).append(v)

    identical, near, divergent, orphan = [], [], [], []
    for rel, p in sorted(a.items()):
        base = os.path.basename(rel)
        hits = by_base.get(base)
        if not hits:
            orphan.append((rel, p))
            continue
        op = hits[0]
        if h(p) == h(op):
            identical.append((rel, p, op))
            continue
        ba, bo = body(p), body(op)
        if ba.strip() == bo.strip():
            near.append((rel, p, op, 'whitespace only'))
            continue
        wa, wo = len(ba.split()), len(bo.split())
        if abs(wa - wo) <= args.word_tolerance and \
                ba.split() == bo.split():
            near.append((rel, p, op, f'token-identical ({wa}w)'))
            continue
        divergent.append((rel, p, op, wa, wo))

    print(f'\n  active-wiki/research: {len(a)} files')
    print(f'    byte-identical in oracle : {len(identical)}')
    print(f'    body equivalent         : {len(near)}')
    print(f'    genuinely different     : {len(divergent)}')
    print(f'    NOT in oracle at all    : {len(orphan)}')
    print()
    if divergent:
        print('  DIVERGENT (will be archived, not deleted):')
        for rel, p, op, wa, wo in divergent:
            flag = 'ORACLE IS LONGER' if wo > wa else (
                'ACTIVE IS LONGER' if wa > wo else 'same size, different')
            print(f'    {os.path.basename(rel)[:52]}')
            print(f'      active {wa}w  oracle {wo}w   {flag}')
    if orphan:
        print('  ORPHANS (no oracle copy; these DO need copying):')
        for rel, p in orphan[:15]:
            print(f'    {rel[:64]}')
    print(f'\n  total files to remove from active-wiki: '
          f'{len(identical) + len(near)}')
    print(f'  total to archive as divergent: {len(divergent)}')

    if not args.apply:
        print('\n  DRY RUN. Pass --apply.')
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    bdir = f'{BACKUP}/{ts}'
    hdir = f'{HOLD}/{ts}'
    os.makedirs(bdir, exist_ok=True)
    os.makedirs(hdir, exist_ok=True)

    removed = backed = 0
    # BUG, and it is the kind that hides: --apply removed only the
    # `near` list. Byte-identical files, which is 444 of 469, were
    # counted, reported as "to remove", and then never touched, because
    # the loop that does the removing did not include them. The dry run
    # said "total files to remove: 449" and the apply run reported
    # "removed: 5". A plan that is not the same set as the action is a
    # plan that cannot be trusted, so this now iterates identical AND
    # near, and asserts that the number removed matches the number the
    # dry run promised.
    for rel, p, op in identical:
        dst = os.path.join(bdir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
        os.remove(p)
        removed += 1
        backed += 1
    for rel, p, op, _why in near:
        dst = os.path.join(bdir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
        os.remove(p)
        removed += 1
        backed += 1
    for rel, p, op, wa, wo in divergent:
        dst = os.path.join(hdir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
        # NOT removed from active-wiki: the difference may matter and
        # the operator does not delete content.
        backed += 1
    for rel, p in orphan:
        dst = os.path.join(bdir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
        backed += 1

    promised = len(identical) + len(near)
    if removed != promised:
        print(f'\n  MISMATCH: planned to remove {promised}, removed '
              f'{removed}. Aborting before claiming success.')
        return 1
    print(f'\n  removed from active-wiki : {removed}  '
          f'(matches the {promised} the dry run promised)')
    print(f'  backed up                : {backed}')
    print(f'  backup dir               : {bdir}')
    print(f'  divergent held at        : {hdir}')
    print(f'  remaining in active      : '
          f'{len(walk_md(A + "/research"))}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
