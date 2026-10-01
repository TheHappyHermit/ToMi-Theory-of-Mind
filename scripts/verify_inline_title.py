#!/usr/bin/env python3
"""Regression tests for inline_title() in verify_t2_titles.py.

These exist because inline_title() produced THREE separate false
accusations of wrong citations, each from a different shape of input,
and each was only found by reading the actual citation in the file
rather than by reading the code:

  1. "- https://arxiv.org/abs/2012.00073"
     The bare-URL guard checked `s.startswith('http')`, so a leading
     markdown bullet defeated it, the whole URL survived as a candidate
     "title", and a correct citation was scored 0 and reported as a
     mismatch.

  2. A wiki-link pipe label:
     [[https://arxiv.org/abs/2605.11234|"The Semantic Training Gap"]]
     The label was taken as the title. The citation was correct.

  3. Rejecting "/" to catch URL paths also killed DOIs:
     "10.1038/nrn2236 - Actin-binding proteins take the reins"
     The slash belongs to the identifier. This one was introduced by
     the fix for (1) and caught only because the test below covers DOI
     shapes as well as arXiv ones. Fixing a bug with a broader rule and
     testing only the case that bug was found on is how bug (3) exists.

The rule these encode: a citation that states NO title cannot be a
mismatched citation. There is no claim to contradict. Returning a
non-empty candidate for a bare URL manufactures a false accusation.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'v', os.path.join(HERE, 'verify_t2_titles.py'))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

# (input, expected, why)
NO_TITLE = [
    ('- https://arxiv.org/abs/2012.00073',
     'leading bullet defeated the bare-URL guard'),
    ('https://arxiv.org/abs/2012.00073', 'plain bare URL'),
    ('- arxiv:2012.00073', 'bare id, no title'),
    ('  - arxiv:2403.01590', 'bare id, indented'),
    ('* arxiv:2403.01590', 'bare id, asterisk bullet'),
    ('- https://scirate.com/arxiv/2603.14597', 'scirate mirror'),
    ('- https://doi.org/10.1038/nrn2236', 'bare DOI URL'),
    ('https://arxiv.org/pdf/2012.00073', 'pdf mirror'),
    ('- "https://doi.org/10.1038/nn1516"',
     'quoted bare DOI, stripped to leftover quote marks'),
    ('"https://doi.org/10.1016/j.cobeha.2016.06.003"',
     'quoted URL with no leading bullet'),
]

HAS_TITLE = [
    ('arXiv:2605.00081 - Alignment Contracts for Agentic Security Systems',
     'arXiv with inline title'),
    ('- arxiv:2012.00073 TimeSHAP: Explaining Recurrent Models',
     'bare id then title on same line'),
    ('10.1038/nrn2236 - Actin-binding proteins take the reins',
     'DOI with inline title, slash must survive'),
    ('doi:10.1126/science.1207745 - Google Effects on Memory',
     'doi: prefix form'),
    ('5. Bengtsson SL, Nagy Z, Skare S, Forsman L, Forssberg H, Ullén F. '
     'Extensive piano practicing has regionally specific effects on white '
     'matter development. Nat Neurosci. 2005;8(9):1148',
     'numbered reference: author list must be stripped, title kept'),
    ('2. Smith J, Jones A. Attention Is All You Need. NeurIPS. 2017',
     'two authors then title'),
]


def main():
    bad = 0
    for text, why in NO_TITLE:
        got = V.inline_title(text)
        if got != '':
            bad += 1
            print(f'  LEAK   {text[:52]!r}')
            print(f'         -> {got!r}  ({why})')
    for text, why in HAS_TITLE:
        got = V.inline_title(text)
        if not got:
            bad += 1
            print(f'  LOST   {text[:52]!r}')
            print(f'         -> empty, title should have been extracted ({why})')
    total = len(NO_TITLE) + len(HAS_TITLE)
    if bad:
        print(f'\n  {bad} of {total} cases wrong')
        return 1
    print(f'  all {total} inline_title cases correct')
    print(f'    {len(NO_TITLE)} must yield no title (no claim to check)')
    print(f'    {len(HAS_TITLE)} must yield a title (real citations)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
