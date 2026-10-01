import importlib.util
import re

spec = importlib.util.spec_from_file_location(
    'v', '/home/operator/hermes-brain/scripts/verify_t2_titles.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

# The real question: is a mismatch a WRONG citation, or is the matcher
# comparing every label against every id? Take a known arXiv paper and
# its true title, and check the matcher accepts it.
real = [
    ('1706.03762', 'Attention Is All You Need'),
    ('1810.04805', 'BERT: Pre-training of Deep Bidirectional Transformers '
                   'for Language Understanding'),
    ('2005.11401', 'Retrieval-Augmented Generation for Knowledge-Intensive '
                   'NLP Tasks'),
    ('1512.03385', 'Show, Attend and Tell'),
]
print('  SANITY: does the matcher accept a true title for a real id?')
allok = True
for aid, title in real:
    got = v.fetch_arxiv(aid)
    ok, sc = v.title_match(title, got or '')
    if not ok:
        allok = False
    print(f'    {"PASS" if ok else "FAIL"}  score={sc:.2f}  {aid}')
    print(f'          real: {(got or "")[:64]}')
    if got and got.strip().lower() != title.lower():
        print(f'          NOTE real differs from my memory: {title[:60]}')
print(f'  all true-title cases pass: {allok}')
print()
print('  Now the reverse -- a WRONG title must fail:')
for aid, wrong in [('1706.03762', 'A Survey of Retrieval Augmentation'),
                   ('2005.11401', 'Attention Is All You Need')]:
    got = v.fetch_arxiv(aid)
    ok, sc = v.title_match(wrong, got or '')
    print(f'    {"PASS" if not ok else "FAIL"}  rejected={not ok}  '
          f'score={sc:.2f}  {aid} vs {wrong[:34]}')
