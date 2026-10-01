#!/usr/bin/env python3
"""Clear the stale active-wiki graphify state so the next run rebuilds it.

the operator: "we're going to have to remove the existing graphify graph for the
active wiki and readjust the active wiki into graphify because the old
graphify ingestion is going to show a lot of files that don't exist
there"

Confirmed, and the damage is worse than "a lot of files":

  graph.json    2,535 nodes, 4,440 links, built 2026-09-15
                2 weeks stale, from a vault that now has 78 files

  of 4,440 links, 4,394 (99%) have a source_file that no longer exists.
  252 of 266 referenced paths are dangling. 64 files now in the vault
  are absent from the graph entirely.

  .graphify_root  points at
                  /home/operator/.autognosia/active-wiki
                  which does not exist. Autognosia was retired. This
                  marker is why the graph never rebuilt: graphify read
                  a root that is gone, found nothing new under it, and
                  left the 2026-09-15 graph in place. The ingestion
                  script itself is correct -- it points at
                  ~/.hermes/active-wiki -- so the stale marker is the
                  whole failure.

  manifest.json  285 entries, of which 268 name files that are gone.
                This is the incremental gate. Deleting graph.json alone
                would NOT trigger a rebuild: the manifest would still
                assert the corpus is current. Both have to go together
                or the "remove the graph" silently does nothing.

NO --force ANYWHERE
Not on this script, not on the scheduled run. --force skips the
incremental manifest gate AND overwrites graph.json even when the
rebuild returns fewer nodes, so a short rebuild replaces a good graph
with a worse one and there is no way back. This is a deliberate clean
of the state directory instead, and the rebuild goes through the normal
gated path. The Oracle run does not get the same treatment: its graph
is 25 MB and current, and a forced Oracle extract is exactly the
failure mode that is not recoverable.

BACKUP
The whole graphify-out directory is copied to
archive/graphify-active-wiki/<ts>/ before anything is removed, so the
2,535-node graph can be restored if the rebuild comes back worse. the operator
does not delete content.

Dry run by default. --apply performs the backup and the clear.
"""
import argparse
import datetime
import os
import shutil
import sys

G = '/home/operator/.hermes/active-wiki/graphify-out'
BACKUP = '/home/operator/hermes-brain/archive/graphify-active-wiki'
# What must go for a genuine rebuild. graph.json and manifest.json are
# the pair: removing one without the other leaves the gate closed.
CLEAR = ['graph.json', 'manifest.json', '.graphify_root',
         '.graphify_semantic_marker', '.graphify_analysis.json']


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    if not os.path.isdir(G):
        print(f'  {G} does not exist')
        return 1

    print(f'\n  {G}')
    for name in CLEAR:
        p = os.path.join(G, name)
        if os.path.exists(p):
            print(f'    {name:32} {os.path.getsize(p):>10,} bytes  '
                  f'{(os.path.getmtime(p)):.0f}')
    cache = os.path.join(G, 'cache')
    if os.path.isdir(cache):
        n = sum(len(f) for _, _, f in os.walk(cache))
        print(f'    {"cache/":32} {n:>10,} files')

    print('\n  the semantic cache is KEPT: it lets the rebuild resume and')
    print('  reuse LLM work already paid for. Only the graph, the manifest')
    print('  and the dead root marker are cleared.')

    if not args.apply:
        print('\n  DRY RUN. Pass --apply.')
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    dst = f'{BACKUP}/{ts}'
    shutil.copytree(G, dst)
    print(f'\n  backed up to {dst}')

    removed = 0
    for name in CLEAR:
        p = os.path.join(G, name)
        if os.path.exists(p):
            size = os.path.getsize(p)
            os.remove(p)
            removed += 1
            print(f'    removed {name} ({size:,} bytes)')

    # Leave an accurate root marker so the next run does not go looking
    # for the retired Autognosia tree again.
    with open(os.path.join(G, '.graphify_root'), 'w',
              encoding='utf-8') as fh:
        fh.write('/home/operator/.hermes/active-wiki')
    print('    rewrote .graphify_root -> /home/operator/.hermes/active-wiki')

    left = sorted(os.listdir(G))
    print(f'\n  removed {removed} files; {G} now holds: {left}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
