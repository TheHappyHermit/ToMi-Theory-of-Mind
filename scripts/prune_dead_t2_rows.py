#!/usr/bin/env python3
"""Prune the 213 dead active-wiki rows out of the T2 pending table.

WHY
---
docs/audit/grade-decisions.csv carries `title match unverified` rows for
files that no longer exist. All 213 are active-wiki research paths removed
by the 2026-09-29 consolidation, after confirming Oracle already held
byte-identical copies. The 362 live rows are all Oracle.

While they sat in the CSV, every consumer had to defend against them:
`verify_t2_titles.py` skipped them with a bare `except: continue`, so a
deleted file and a malformed file were indistinguishable, and the run
summary counted a table that was 37% dead weight. Any confidence derived
from that table was partly evidence about paths that no longer exist.

WHAT THIS DOES
--------------
Two options were available and only one is honest:

  (a) delete the 213 rows.
  (b) leave them and mark them superseded.

(b) was rejected: a row that can never be verified should not sit in a
table whose purpose is "rows awaiting verification". Keeping it invites
the same silent-skip behaviour it caused. The audit trail belongs in git
history and in docs/audit/, not in the working table.

DRY RUN BY DEFAULT. --apply writes. A backup is taken before writing.
"""
import csv
import os
import shutil
import sys
from collections import Counter

CSV = '/home/operator/hermes-brain/docs/audit/grade-decisions.csv'
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
MARKER = 'title match unverified'


def rel_to_abs(row):
    rel = row['path']
    for pre in ('active-wiki/', 'oracle/brain/'):
        if rel.startswith(pre):
            rel = rel[len(pre):]
    return ROOTS[row['vault']] + '/' + rel


def main():
    apply = '--apply' in sys.argv
    rows = list(csv.DictReader(open(CSV, encoding='utf-8')))
    fields = list(rows[0])

    keep, drop = [], []
    for r in rows:
        if MARKER in r['reason'] and not os.path.exists(rel_to_abs(r)):
            drop.append(r)
        else:
            keep.append(r)

    print(f'  rows in   : {len(rows)}')
    print(f'  dead (T2) : {len(drop)}')
    print(f'  kept      : {len(keep)}')
    if drop:
        print(f'  dead by vault: {dict(Counter(r["vault"] for r in drop))}')

    # Sanity gate. A prune that removes live rows, or removes anything
    # outside the known consolidation, means the reasoning above no
    # longer holds and must not be applied on autopilot.
    wrong_vault = [r for r in drop if r['vault'] != 'active-wiki']
    live_in_drop = [r for r in drop if os.path.exists(rel_to_abs(r))]
    if wrong_vault or live_in_drop:
        print(f'\n  REFUSING: {len(wrong_vault)} non-active-wiki rows, '
              f'{len(live_in_drop)} of which still exist on disk.')
        return 1

    if not apply:
        print('\n  dry run only. Re-run with --apply to write.')
        return 0

    bak = CSV + '.prune.bak'
    shutil.copy2(CSV, bak)
    with open(CSV, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(keep)
    print(f'\n  wrote {len(keep)} rows. Backup: {bak}')

    # Prove the write landed rather than reporting success on faith.
    back = list(csv.DictReader(open(CSV, encoding='utf-8')))
    still_dead = [r for r in back
                  if MARKER in r['reason'] and not os.path.exists(rel_to_abs(r))]
    print(f'  verify: {len(back)} rows now, {len(still_dead)} dead T2 rows remain')
    return 1 if still_dead or len(back) != len(keep) else 0


if __name__ == '__main__':
    sys.exit(main())
