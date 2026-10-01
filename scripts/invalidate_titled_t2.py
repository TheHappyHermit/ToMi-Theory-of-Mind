"""Invalidate the T2 rows for files whose sources were just titled.

Same mechanism as the citation repair: the verdict cache is keyed by
path::identifier, so a row the vault edit could have changed has to be
deleted before the verifier will look at it again. Without this the
verifier reports "0 resolved this run, 954 cached" and the new titles
are never compared against anything -- which looks exactly like the
titles having had no effect.

Filters on the FILES actually edited, not the identifier, because every
row in an edited file is affected: the file's source block changed, so
its whole label set was recomputed.
"""
import json
import os
import sys

REPO = '/home/operator/hermes-brain'
AUDIT = os.path.join(REPO, 'docs/audit/t2-source-titling.json')
VER = os.path.join(REPO, 'docs/audit/t2-verification.json')
ADJ = os.path.join(REPO, 'docs/audit/t2-adjudication.json')


def main():
    if not os.path.exists(AUDIT):
        raise SystemExit('no titling audit at %s' % AUDIT)
    audit = json.load(open(AUDIT, encoding='utf-8'))
    edited = {p: v for p, v in audit['files'].items() if v['edits']}

    ver = json.load(open(VER, encoding='utf-8'))
    drop = [k for k in ver
            if k.split('::')[0] in edited]
    # A hand adjudication for a row that is about to be re-derived
    # would be silently overwritten, so those keys go too.
    adj = json.load(open(ADJ, encoding='utf-8'))
    drop_adj = [k for k in adj if k.split('::')[0] in edited]

    print('  files edited        : %d' % len(edited))
    print('  rows in verify table: %d' % len(drop))
    print('  rows in adjud. table: %d' % len(drop_adj))
    if '--apply' not in sys.argv:
        print('  dry run; pass --apply')
        return
    for k in drop:
        ver.pop(k, None)
    for k in drop_adj:
        adj.pop(k, None)
    json.dump(ver, open(VER, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    json.dump(adj, open(ADJ, 'w', encoding='utf-8'), indent=1, sort_keys=True)
    print('  wrote tables: %d / %d rows' % (len(ver), len(adj)))


if __name__ == '__main__':
    main()
