import importlib.util

spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Probe a handful of the arXiv IDs this corpus actually uses, and see
# what the real title is versus what the wiki claims.
import re
N = chr(10)
import yaml
p = ('/home/operator/.hermes/oracle/brain/research/'
     'frontier-research-ontology-comprehensive-update-2026.md')
import os
if not os.path.exists(p):
    import glob
    c = glob.glob('/home/operator/.hermes/oracle/brain/research/'
                  'frontier-research-ontology-comprehensive*')
    p = c[0] if c else None
print('  file:', p.split('/')[-1][:60] if p else None)
t = open(p, encoding='utf-8', errors='replace').read()
e = t.find(N + '---', 3)
m = yaml.safe_load(t[3:e]) or {}
labels = v.cited_titles(p, t)
print(f'  {len(m.get("sources") or [])} sources, {len(labels)} reference labels')
print()
ids = []
for s in (m.get('sources') or []):
    mm = re.search(r'arxiv[:/](\d{4}\.\d{4,5})', str(s), re.I)
    if mm:
        ids.append(mm.group(1))
print(f'  arXiv ids: {len(ids)} -> {ids[:6]}')
print()
for aid in ids[:4]:
    try:
        title = v.fetch_arxiv(aid)
    except Exception as ex:
        print(f'    {aid} -> ERROR {str(ex)[:50]}')
        continue
    best, sc = 0.0, 0.0
    bl = ''
    for lab in labels:
        ok, s2 = v.title_match(lab, title or '')
        if s2 > sc:
            sc, bl, bok = s2, lab, ok
    print(f'    {aid}')
    print(f'        real  : {(title or "")[:72]}')
    print(f'        cited : {bl[:72]}')
    print(f'        score {sc:.2f}  match={bok}')
