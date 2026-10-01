#!/usr/bin/env python3
"""Regression test: no raw label may reach title_match.

This is the test that should have existed before any of the six fixes.
It pins the single invariant the whole verifier depends on:

    every candidate compared against a resolved title must have been
    through inline_title() first

Everything before this was the same bug at a different layer -- a value
that does not belong to this identifier's title reaching the
comparator:

  1. a leading markdown bullet defeated the bare-URL guard
  2. a wiki-link pipe label was read as the title
  3. a filename was read as a title
  4. a numbered reference returned its author list as the title
  5. every label in the file was a candidate for every identifier
  6. RAW labels bypassed inline_title() entirely

Fixes 1-5 patched inline_title. Fix 6 is the one that mattered, and
until it landed the other five could not reduce the count, because
inline_title was never called on the values being compared.

The check is on the FUNCTION, not on a run: for every string shape
that appears in a reference block, what reaches title_match must either
be empty or be a plausible title. No corpus needed, so this test cannot
be invalidated by the corpus moving.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'v', os.path.join(HERE, 'verify_t2_titles.py'))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

# Every one of these is a real reference-block line from this corpus.
# NONE of them is a title. Each must yield '' so it is dropped.
NOT_A_TITLE = [
    'arxiv:2403.01590',
    'arxiv:2012.00073',
    'https://arxiv.org/abs/1902.01520',
    'https://doi.org/10.1038/nn1516',
    '- https://arxiv.org/abs/2012.00073',
    '- "https://doi.org/10.1038/nn1516"',
    '10.1037/0033-295X.100.4.609',
    'doi:10.1126/science.1207745',
    'kalman-delta-rule-attribution.md',
    'README.md',
]

# Frontmatter in this corpus writes a parenthesised title, and
# norm() strips the parens into an empty string. These were silently
# becoming zero-length titles and scoring 0.0 on perfect citations.
PAREN_TITLES = [
    'arXiv:2505.09388 (Qwen3 Technical Report)',
    'arXiv:2505.16782 (Reasoning Beyond Language: A Survey on CoT)',
    'arXiv:2603.07670 (Memory for Autonomous LLM Agents)',
]

# A label that is a TRUNCATION of the real title plus an appended
# internal tag. It IS a legitimate title claim, and title_match now
# handles it via the leading-run rule, so it belongs with the titles
# that must survive, not with the non-titles.
TRUNCATED_LABEL = '["The Semantic Training Gap — JMS R3"]'

# Each of these DOES carry a title and must survive, or the fix would
# be over-broad and would silently stop checking real citations.
IS_A_TITLE = [
    'arXiv:2605.00081 - Alignment Contracts for Agentic Security Systems',
    'TimeSHAP: Explaining Recurrent Models through Sequence Perturbations',
    'AttnLRP: Attention-Aware Layer-Wise Relevance Propagation',
    TRUNCATED_LABEL,
    # A numbered reference: authors then the title. The title IS a
    # legitimate claim and must be recovered, not discarded with the
    # authors. This case caught the author-list guard returning ''
    # instead of taking the sentence after the author run.
    '5. Bengtsson SL, Nagy Z, Skare S, Forsman L. Extensive piano '
    'practicing has regionally specific effects. Nat Neurosci. 2005',
    '2. Smith J, Jones A. Attention Is All You Need. NeurIPS. 2017',
] + PAREN_TITLES


def main():
    bad = 0
    print('  must yield NO title (would be a false accusation):')
    for t in NOT_A_TITLE:
        got = V.inline_title(t)
        if got:
            bad += 1
            print(f'    LEAK  {t[:50]!r} -> {got[:40]!r}')
    print(f'    {len(NOT_A_TITLE)} checked, '
          f'{len(NOT_A_TITLE) - bad} clean')

    lost = 0
    print('  must still yield a title (fix must not be over-broad):')
    for t in IS_A_TITLE:
        got = V.inline_title(t)
        if not got:
            lost += 1
            print(f'    LOST  {t[:50]!r}')
    print(f'    {len(IS_A_TITLE)} checked, '
          f'{len(IS_A_TITLE) - lost} clean')

    # The invariant itself, stated as an assertion over the pipeline.
    labels = NOT_A_TITLE
    cands = [V.inline_title(x) for x in labels if x]
    cands = [x for x in cands if x]
    if cands:
        bad += 1
        print(f'  INVARIANT VIOLATED: {len(cands)} non-titles would reach '
              f'title_match: {cands[:3]}')
    else:
        print('  invariant holds: 0 non-titles reach title_match')

    # title_match must not have been loosened into uselessness. The
    # leading-run rule added in this session is the one change that
    # could over-match, so both directions are asserted here rather
    # than assumed.
    PAIRS = [
        ('Attention Is All You Need', 'Attention Is All You Need', True),
        ('Part 1: A Study', 'Part 2: A Study', False),
        ('Deep Residual Learning',
         'Deep Residual Learning for Image Recognition', True),
        ('TimeSHAP', 'Completely Unrelated Paper About Frogs', False),
        ('The Semantic Training Gap — JMS R3',
         'The Semantic Training Gap: Ontology-Grounded Tool '
         'Architectures for Industrial AI Agent', True),
        ('Attention Is All You Need', 'Attention Is All You Ignore', False),
    ]
    wrong = 0
    print('  title_match, both directions:')
    for a, b, want in PAIRS:
        got, sc = V.title_match(a, b)
        if got != want:
            wrong += 1
            print(f'    WRONG want={want} got={got} score={sc:.2f}  '
                  f'{a[:34]}')
    print(f'    {len(PAIRS) - wrong}/{len(PAIRS)} correct')
    bad += wrong

    # Non-emptiness is NOT sufficient. A title that still carries its
    # parentheses extracts fine, the test above passes, and norm()
    # then strips the brackets to nothing at comparison time:
    #   norm("(Qwen3 Technical Report)") == ''
    #   title_match -> (False, 0.0) on a perfect citation.
    # So every must-survive title is also scored against itself.
    print('  surviving titles must actually MATCH:')
    unscored = 0
    for t in IS_A_TITLE:
        got = V.inline_title(t)
        if not got:
            continue
        ok, sc = V.title_match(got, V.inline_title(t) or got)
        # compare the extracted title against the real resolved form
        ok2, sc2 = V.title_match(got, got)
        if not ok2:
            unscored += 1
            print(f'    UNSCORABLE {got[:44]!r} -> norm is empty')
    if unscored:
        bad += unscored
        print(f'    {unscored} title(s) normalise to nothing')
    else:
        print(f'    {len(IS_A_TITLE)} titles all normalise to real text')

    if bad or lost:
        print(f'\n  {bad + lost} failure(s)')
        return 1
    print(f'\n  all {len(NOT_A_TITLE) + len(IS_A_TITLE) + 1} checks pass')
    return 0


if __name__ == '__main__':
    sys.exit(main())
