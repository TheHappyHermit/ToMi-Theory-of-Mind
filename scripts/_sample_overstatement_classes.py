import csv

rows = list(csv.DictReader(
    open('/home/operator/hermes-brain/docs/audit/overstatement-classes.csv')))
by = {}
for r in rows:
    by.setdefault(r['work_class'], []).append(r)

# deterministic spread: take every Nth rather than random, so a
# re-run shows the same sample and there is no import of random
# (a stale scratch/bisect.py shadows the stdlib one on sys.path)
for k in sorted(by):
    lst = by[k]
    n = len(lst)
    step = max(1, n // 3)
    picks = [lst[i] for i in range(0, n, step)][:3]
    print('=' * 68)
    print(f'  {k}  ({n} files)')
    for r in picks:
        print(f'    - {r["path"][:58]}')
        print(f'        type={r["file_type"]} words={r["body_words"]} '
              f'link_share={r["link_share"]}%')
