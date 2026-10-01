import json
import os
import re

d = json.load(open(os.path.expanduser('~/.hermes/cron/jobs.json')))
jobs = d if isinstance(d, list) else d.get('jobs', [])
print('  --source values now:')
for j in jobs:
    p = j.get('prompt') or ''
    for m in re.findall(r'--source[= ]+([a-z-]+)', p):
        print(f"    {str(j.get('name'))[:30]:30} --source {m}")
print()
print('  workdirs mentioning active-wiki:')
for j in jobs:
    wd = j.get('workdir') or ''
    if 'active-wiki' in wd:
        print(f"    {str(j.get('name'))[:38]:38} {wd}")
