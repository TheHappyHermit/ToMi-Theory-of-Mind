import csv

rows = list(csv.DictReader(
    open('/home/operator/hermes-brain/docs/audit/grade-decisions.csv')))
print(f'  {len(rows)} rows graded')

up = [r for r in rows if r['current'] == 'ungraded'
      and r['derived'] in ('medium', 'high')]
down = [r for r in rows if r['current'] in ('high', 'medium')
        and r['derived'] in ('low', 'ungraded')]
print(f'  upgrades (ungraded -> higher): {len(up)}')
print(f'  downgrades:                    {len(down)}')
print()

print('  SAMPLE UPGRADES (these are the surprising ones):')
for r in up[::max(1, len(up) // 6)][:6]:
    print(f'    [{r["vault"][:4]}] {r["path"][:46]}')
    print(f'        ungraded -> {r["derived"]}: {r["reason"][:66]}')
print()

hl = [r for r in down if r['derived'] == 'low']
print('  SAMPLE high -> low:')
for r in hl[::max(1, len(hl) // 5)][:5]:
    print(f'    [{r["vault"][:4]}] {r["path"][:46]}')
    print(f'        {r["reason"][:70]}')
print()

hu = [r for r in rows if r['current'] == 'high'
      and r['derived'] == 'ungraded']
print(f'  high -> ungraded: {len(hu)}   reasons:')
seen = {}
for r in hu:
    k = r['reason'][:44]
    seen[k] = seen.get(k, 0) + 1
for k, v in sorted(seen.items(), key=lambda x: -x[1])[:6]:
    print(f'    {v:>5}  {k}')
