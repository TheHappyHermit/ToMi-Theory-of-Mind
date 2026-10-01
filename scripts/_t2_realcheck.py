import importlib.util
import time

spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Are arXiv IDs in this corpus even REAL? 2605.xxxxx, 2609.xxxxx are
# future-dated relative to arXiv's actual numbering. Test a spread.
ids = ['2605.00081', '2609.07816', '2606.23875', '2511.17970',
       '2412.06464', '2406.07592']
print('  do these arXiv ids resolve at all?')
for aid in ids:
    try:
        t = v.fetch_arxiv(aid)
        print(f'    {aid} -> {(t or "NO TITLE")[:64]}')
    except Exception as ex:
        print(f'    {aid} -> ERROR {str(ex)[:56]}')
    time.sleep(1.0)

print()
print('  control: a known-real older id')
try:
    print('    1706.03762 ->', (v.fetch_arxiv('1706.03762') or '')[:56])
except Exception as ex:
    print('    ERROR', str(ex)[:60])
