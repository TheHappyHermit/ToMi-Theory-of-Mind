"""Profile the 496 unsourced synthesis files so the research effort can
be batched by subject rather than by file."""
import csv
from collections import Counter
rows = list(csv.DictReader(
    open('/home/operator/hermes-brain/docs/audit/overstatement-classes.csv')))
syn = [r for r in rows if r['work_class'] == 'a_unsourced_synthesis']
print(f'  {len(syn)} synthesis files')
print()
print('  by top-level directory:')
d = Counter('/'.join(r['path'].split('/')[:-1]) or '(root)' for r in syn)
for k, v in d.most_common(14):
    print(f'    {v:>4}  {k}')
print()
print('  words: ')
w = sorted(int(r['body_words']) for r in syn)
n = len(w)
print(f'    median {w[n//2]}, p90 {w[int(n*.9)]}, max {w[-1]}')
tot = sum(w)
print(f'    total {tot:,} words to source and verify')
