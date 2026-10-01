import importlib.util
import time

spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# Exactly the cases the broken matcher called mismatches.
cases = [
    'arXiv:2605.00081 - Alignment Contracts for Agentic Security Systems (DATE-TRACKED)',
    'arXiv:2605.18672 - Three-Layer Probabilistic A/G Architecture (Bensalir)',
    'arXiv:2609.05269 - CONTINUITY: Security-Context Contracts for Composable LLM Agent Controls',
    'https://scirate.com/arxiv/2603.14597',
]
ids = ['2605.00081', '2605.18672', '2609.05269', '2603.14597']
print('  the fix, on the entries that were wrongly flagged:')
for entry, aid in zip(cases, ids):
    got = v.fetch_arxiv(aid)
    inline = v.inline_title(entry)
    ok_i, sc_i = v.title_match(inline, got or '')
    print(f'    {aid}  inline-compare -> {"MATCH" if ok_i else "no"} '
          f'({sc_i:.2f})')
    print(f'       real   : {(got or "")[:62]}')
    print(f'       inline : {inline[:62]}')
    time.sleep(3.0)
