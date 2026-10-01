import json
import os

d = json.load(open(os.path.expanduser('~/.hermes/cron/jobs.json')))
jobs = d if isinstance(d, list) else d.get('jobs', [])
WANT = ('Wiki Lint Daily', 'Wiki Lint Weekly Deep', 'Research Quality Check',
        'OKF Schema Lint (daily, read-only)', 'OKF Schema Repair (daily, WRITE)')
for j in jobs:
    n = str(j.get('name', ''))
    if not any(n.startswith(w[:20]) for w in WANT):
        continue
    print('=' * 74)
    print(f"  NAME     : {n}")
    print(f"  ID       : {j.get('id')}")
    print(f"  ENABLED  : {j.get('enabled')}")
    print(f"  SCHEDULE : {j.get('schedule_display')}")
    print(f"  LAST RUN : {j.get('last_run_at')}")
    print(f"  STATUS   : {j.get('last_status')}")
    print(f"  NO_AGENT : {j.get('no_agent')}")
    print(f"  SCRIPT   : {str(j.get('script'))[:70]}")
    print(f"  DELIVER  : {str(j.get('deliver'))[:70]}")
    print('  --- PROMPT ---')
    print('  ' + (j.get('prompt') or '').replace('\n', '\n  '))
    print()
