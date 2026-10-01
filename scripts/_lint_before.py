import json
import os
import re

bak = os.path.expanduser(
    '~/.hermes/cron/jobs.json.pre-oracle-retarget.bak')
d = json.load(open(bak, encoding='utf-8'))
jobs = d if isinstance(d, list) else d.get('jobs', [])
WANT = ('Wiki Lint Daily', 'Wiki Lint Weekly Deep', 'Research Quality Check')
for j in jobs:
    n = str(j.get('name', ''))
    if n not in WANT:
        continue
    print('=' * 70)
    print(f'  BEFORE: {n}')
    for ln in (j.get('prompt') or '').split('\n'):
        if '--source' in ln or 'both' in ln.lower():
            print(f'    {ln.strip()[:82]}')
    print()
