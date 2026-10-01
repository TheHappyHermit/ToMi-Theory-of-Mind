import importlib.util
spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)

for doi in ('10.1038/nrn2236', '10.1145/3292500.3330701'):
    try:
        d = v.fetch_crossref(doi)
        t = d['message']['title'][0]
        print(f'  {doi} -> {t[:64]}')
        good, sc = v.title_match('Neuropeptide communication: a subject of debate', t)
        bad, sc2 = v.title_match('Something completely different here', t)
        print(f'     good citation -> {good} ({sc:.2f})   '
              f'bad citation -> {bad} ({sc2:.2f})')
    except Exception as ex:
        print(f'  {doi} -> ERROR {str(ex)[:60]}')
