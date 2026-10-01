"""Invalidate exactly the rows whose vault citation was repaired.

Filtering by FILE would have wiped 70 rows, because a repaired file
holds many adjudications that are still perfectly valid. Only the
identifier that was actually rewritten can have changed verdict, so
the key is (repaired file, replaced identifier) -- never the file
alone.

Deleting the row is what makes the verifier re-resolve it: rows it has
already judged are skipped, so a stale verdict would otherwise survive
the vault edit and quietly become the evidence.
"""
import json
import os
import sys

REPO = '/home/operator/hermes-brain'
VER = os.path.join(REPO, 'docs/audit/t2-verification.json')
ADJ = os.path.join(REPO, 'docs/audit/t2-adjudication.json')

# The replacements scripts/repair_t2_citations.py makes, expressed as
# (file, identifier-being-removed). New identifiers are NOT listed:
# they have no row yet, and the verifier will create them.
STALE = [
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11-'
     'supplement-v2.md', 'arxiv:2605.11610'),
    ('research/frontier-research-taxonomy-september-2026-supplement-v2.md',
     'arxiv:2605.24601'),
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11.md',
     'arxiv:2505.10468'),
    ('research/frontier-research-taxonomy-comprehensive-2026-09-11.md',
     'arxiv:2602.06052'),
    ('research/frontier-research-taxonomy-comprehensive-2026-09-10-v2.md',
     'arxiv:2505.10468'),
    ('research/frontier-research-taxonomy-2027-supplement-v2.md',
     'arxiv:2601.12560'),
    ('research/frontier-research-taxonomy-2027-supplement.md',
     'arxiv:2602.06052'),
]


def main():
    ver = json.load(open(VER, encoding='utf-8'))
    adj = json.load(open(ADJ, encoding='utf-8'))
    drop = {'%s::%s' % (f, i) for f, i in STALE}

    hit_v = sorted(drop & set(ver))
    hit_a = sorted(drop & set(adj))
    print('  keys to invalidate : %d' % len(drop))
    print('  present in verify  : %d' % len(hit_v))
    print('  present in adjud.  : %d' % len(hit_a))
    missing = sorted(drop - set(ver))
    for k in missing:
        print('      NOT IN TABLE: %s' % k[70:])
    if missing:
        raise SystemExit('refusing: a repaired row is not in the table; '
                         'the vault and the evidence have drifted apart')
    if '--apply' not in sys.argv:
        print('  dry run; pass --apply')
        return
    for d in drop:
        ver.pop(d, None)
        adj.pop(d, None)
    json.dump(ver, open(VER, 'w', encoding='utf-8'), indent=1,
              sort_keys=True)
    json.dump(adj, open(ADJ, 'w', encoding='utf-8'), indent=1,
              sort_keys=True)
    print('  wrote tables: %d and %d rows'
          % (len(ver), len(adj)))


if __name__ == '__main__':
    main()
