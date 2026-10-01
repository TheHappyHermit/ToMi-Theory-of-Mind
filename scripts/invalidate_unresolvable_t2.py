"""Invalidate the unresolvable rows after identifier repairs.

Unresolvable verdicts are also cacheable. Six of them were fixed on
disk -- the identifier now resolves to a live DOI -- but the table
still carried the old 404 verdict, because the invalidation script only
dropped untitled and mismatch rows.

A stale unresolvable verdict is worse than a missing one: it says "we
looked and this does not exist", which is a claim about the world
rather than about a file. It has to be re-derived whenever the
identifier on disk changes.

This drops every unresolvable row so the next run re-checks all of
them against both resolvers. Rows that are still dead come back as
unresolvable on their own merits; rows whose identifier was repaired
come back resolved.
"""
import json
import sys

TABLE = ('/home/operator/hermes-brain/docs/'
         'audit/t2-verification.json')


def main():
    if '--apply' not in sys.argv:
        print('  DRY RUN. Pass --apply.')
        return 0
    with open(TABLE, encoding='utf-8') as fh:
        rows = json.load(fh)
    before = len(rows)
    stale = [k for k, v in rows.items()
             if v.get('verdict') == 'unresolvable']
    for k in stale:
        rows.pop(k, None)
    with open(TABLE, 'w', encoding='utf-8') as fh:
        json.dump(rows, fh, indent=1, sort_keys=True)
    removed = before - len(rows)
    if removed != len(stale):
        raise SystemExit(
            'expected to drop %d rows, dropped %d' % (len(stale), removed))
    print('  dropped %d unresolvable rows (%d -> %d rows); they will be '
          're-derived against both resolvers' % (removed, before, len(rows)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
