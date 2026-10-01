import json
import os

d = json.load(open(os.path.expanduser('~/.hermes/cron/jobs.json')))
jobs = d if isinstance(d, list) else d.get('jobs', [])
for j in jobs:
    if str(j.get('name')) not in ('Wiki Lint Weekly Deep',
                                  'Research Quality Check'):
        continue
    print('=' * 70)
    print(f"  {j['name']}")
    for i, ln in enumerate((j.get('prompt') or '').split('\n')):
        if '--source' in ln:
            print(f'    L{i}: {ln.strip()[:80]!r}')
