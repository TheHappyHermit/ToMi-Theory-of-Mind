import importlib.util, json
spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

print('  --- title_match unit checks (no network) ---')
cases = [
    ('On the Semantics of Generative SPARQL',
     'On the Semantics of Generative SPARQL (Extended Abstract)', True),
    ('LLM-empowered knowledge graph construction: A survey',
     'LLM-empowered knowledge graph construction: A survey', True),
    ('Securing RAG: Slot Taxonomy',
     'A Survey of Retrieval Augmented Generation Security', False),
    ('Part 1: The limits of scale',
     'Part 2: The limits of compression', False),
]
ok = True
for a, b, want in cases:
    got, sc = v.title_match(a, b)
    flag = 'PASS' if got == want else 'FAIL'
    if got != want:
        ok = False
    print(f'    {flag}  score={sc:.2f}  {a[:38]!r} vs {b[:38]!r}')
print('  all title_match cases pass:', ok)
print()
print('  --- one real Crossref DOI ---')
try:
    d = v.fetch_crossref('10.1038/nrn.2019.018')
    t = d['message']['title'][0]
    print('    resolved title:', t[:70])
    got, sc = v.title_match('Neuropeptide communication ... ', t)
    print(f'    vs a bad citation -> {got} score {sc:.2f}')
except Exception as ex:
    print('    network error:', str(ex)[:100])
print()
print('  --- one real arXiv id ---')
try:
    print('    resolved title:', (v.fetch_arxiv('1706.03762') or '')[:70])
except Exception as ex:
    print('    network error:', str(ex)[:100])