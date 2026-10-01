import importlib.util, json, os
spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

OUT = '/home/operator/hermes-brain/docs/audit/t2-verification.json'
if not os.path.exists(OUT):
    print('  table not written yet (run still in progress)')
    raise SystemExit
t = json.load(open(OUT))
print(f'  {len(t)} identifiers resolved so far')
mis = [(k, x) for k, x in t.items() if x.get('verdict') == 'mismatch']
print(f'  mismatches: {len(mis)}')
print()
print('  sample mismatches -- is the resolver wrong, or is the citation?')
for k, x in mis[:8]:
    print(f'    {k}')
    print(f'        resolved title: {x.get("title", "")[:78]}')
    print(f'        score: {x.get("score")}')
