"""Invalidate exactly the untitled/mismatch rows so the next verifier
run re-derives them from disk.

Only those verdicts. A file is stale when its source lines have been
edited, not when some other file changed, so invalidating by filename
would throw away hundreds of rows that are still perfectly correct --
which is what happened once already, deleting 70 valid rows.

The two rows for arXiv:2505.10468 are also dropped outright: that source
was deliberately replaced with the real DOI 10.1017/langcog.2025.10, so
the row describes a citation that no longer exists. The verifier will
not re-add it, so removing it here keeps the table honest about what the
vault actually cites.
"""
import json
import sys

TABLE = '/home/operator/hermes-brain/docs/audit/t2-verification.json'
ADJ = '/home/operator/hermes-brain/docs/audit/t2-adjudication.json'
DROP_SUFFIX = '::arxiv:2505.10468'
DROP_PATHS = {
    'research/frontier-research-taxonomy-metadata-categorization-'
    'linguistic-philosophical-2026-09-10.md',
    'research/frontier-research-taxonomy-september-2026-supplement-v3.md',
}


def main():
    apply = '--apply' in sys.argv
    rows = json.load(open(TABLE, encoding='utf-8'))

    drop = [k for k in rows
            if k.endswith(DROP_SUFFIX) and k.split('::')[0] in DROP_PATHS]
    stale = [k for k, v in rows.items()
             if v.get('verdict') in ('untitled_citation', 'mismatch')
             and k not in drop]

    print('  rows to re-derive : %d' % len(stale))
    print('  rows to drop      : %d (source replaced by the real DOI)'
          % len(drop))
    for k in drop:
        print('     DROP %s' % k)
    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    removed = 0
    for k in drop:
        if rows.pop(k, None) is not None:
            removed += 1
    # THE ROWS THAT MATTER. This loop used to be absent: `stale` was
    # computed, printed, and then ignored, so --apply rewrote the table
    # byte-identical and the next verifier run resumed from the very
    # verdicts it was supposed to re-derive. Four runs in a row
    # reported an unchanged table for that reason alone, and the bare
    # identifier fix looked like it had not worked when it had.
    for k in stale:
        if rows.pop(k, None) is not None:
            removed += 1
    json.dump(rows, open(TABLE, 'w', encoding='utf-8'),
              indent=1, sort_keys=True)
    after = json.load(open(TABLE, encoding='utf-8'))
    still = [k for k in stale if k in after]
    if still:
        raise SystemExit(
            'invalidate_stale_t2: %d row(s) survived the write, so the '
            'next run would resume from stale verdicts: %s'
            % (len(still), still[:3]))
    print('  wrote %s (%d rows, %d invalidated: %d dropped, %d to '
          're-derive)' % (TABLE, len(after), removed, len(drop), len(stale)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
