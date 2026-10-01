import importlib.util
import re

spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

N = chr(10)
import csv
import yaml

R = {'active-wiki': '/home/operator/.hermes/active-wiki',
     'oracle': '/home/operator/.hermes/oracle/brain'}
rows = list(csv.DictReader(
    open('/home/operator/hermes-brain/docs/audit/grade-decisions.csv')))
pend = [r for r in rows if 'title match unverified' in r['reason']]

# For each of a few files: show the reference label that sits on the SAME
# line as / near the arXiv id, versus the real title.
shown = 0
for r in pend:
    rel = r['path']
    for pre in ('active-wiki/', 'oracle/brain/'):
        if rel.startswith(pre):
            rel = rel[len(pre):]
    p = R[r['vault']] + '/' + rel
    try:
        text = open(p, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    e = text.find(N + '---', 3)
    m = yaml.safe_load(text[3:e]) or {}
    srcs = [str(s) for s in (m.get('sources') or [])]
    ids = [(i, re.search(r'arxiv[:/](\d{4}\.\d{4,5})', s, re.I).group(1))
           for i, s in enumerate(srcs)
           if re.search(r'arxiv[:/](\d{4}\.\d{4,5})', s, re.I)]
    if not ids:
        continue
    print('=' * 68)
    print(f'  {rel[:60]}')
    for i, aid in ids[:2]:
        print(f'    source entry: {srcs[i][:70]}')
        try:
            real = v.fetch_arxiv(aid)
        except Exception as ex:
            print(f'      -> ERROR {str(ex)[:40]}')
            continue
        print(f'      REAL TITLE : {(real or "")[:66]}')
    shown += 1
    if shown >= 3:
        break
