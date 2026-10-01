import json
import os

d = json.load(open(os.path.expanduser('~/.hermes/cron/jobs.json')))
jobs = d if isinstance(d, list) else d.get('jobs', [])
print('  jobs whose workdir mentions oracle:')
for j in jobs:
    wd = j.get('workdir') or ''
    if 'oracle' in wd:
        print(f"    {str(j.get('name','?'))[:38]:38} {wd}")
print()
print('  all distinct workdir values, for style comparison:')
seen = set()
for j in jobs:
    wd = (j.get('workdir') or '').strip()
    if wd and wd not in seen:
        seen.add(wd)
        print(f'    {wd}')
