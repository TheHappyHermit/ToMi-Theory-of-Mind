#!/usr/bin/env python3
"""Controls for the UNRELATED_TITLE reclassifier.

The whole point of scripts/reclassify_identifiers.py is that a low
similarity score must NOT be read as a mis-citation. That claim needs its
own tests, because getting it backwards would mean accusing the corpus of
fabricating papers it actually cited correctly.

Each case below is a real shape taken from the corpus.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from reclassify_identifiers import classify   # noqa: E402

CASES = [
    # (identifier, registered title, citation context, expected, why)
    ('2501.13956',
     'Zep: A Temporal Knowledge Graph Architecture for Agent Memory',
     '- Zep (arXiv 2501.13956) + Graphiti issue #1728 -- temporal invalidation',
     'short_name_confirmed',
     'a real sample: cited by its system name only, sim 0.00'),

    ('2601.02744',
     'SYNAPSE: Empowering LLM Agents with Episodic-Semantic Memory via Spreading Activation',
     "- {'Synapse': 'Episodic-Semantic Memory via Spreading Activation (Jiang et al.)}",
     'short_name_confirmed',
     'a real sample: sim 0.00, yet clearly the same work'),

    ('2607.13104',
     'Self-Improvements in Modern Agentic Systems: A Survey',
     '- https://arxiv.org/abs/2607.13104',
     'no_title_restated',
     'a bare URL: no title text exists to match'),

    ('10.1016/j.neuroscience.2019.06.012',
     'Reduced transfer of visuomotor adaptation is associated with aberrant sense of agency',
     '- https://doi.org/10.1016/j.neuroscience.2019.06.012',
     'no_title_restated',
     'a bare DOI URL in a host form the first test did not know about'),

    ('10.1109/ICDM.2013.83',
     'Non-negative Multiple Tensor Factorization',
     'a method for learning sparse representations in large corpora',
     'needs_judgement',
     'THE known-real mismatch: resolves, real, and unrelated'),

    ('2504.19413',
     'Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory',
     '**Sources**: Semantic Anchoring (arXiv 2508.12630), APEX-MEM, ProGraph',
     'no_title_restated',
     'a real sample: the identifier sits in a list about other papers, so there is no title to compare'),

    ('10.1371/journal.pcbi.1014340',
     'pyhgf: A neural network library for predictive coding',
     '- https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1014340',
     'no_title_restated',
     'another host form of a bare DOI'),

    ('2306.05685',
     'Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena',
     'arXiv:2306.05685, NeurIPS 2023 Datasets & Benchmarks. **[V -- abstract fetched]**',
     'no_title_restated',
     'venue only, no title: nothing to match'),
]

failed = []
for ident, reg, ctx, want, why in CASES:
    got = classify(ident, reg, ctx)
    ok = (got == want)
    if not ok:
        failed.append((ident, want, got))
    print(f'  {"ok  " if ok else "FAIL"} {ident:34} {got:24} {why}')

# The load-bearing assertion: a correct short-name citation must NEVER be
# classified as something requiring human judgement. If this regresses, the
# tool is back to accusing the corpus of fabrication.
print()
short_names = [c for c in CASES if c[3] == 'short_name_confirmed']
bad = [c for c in short_names
       if classify(c[0], c[1], c[2]) in ('needs_judgement', 'needs_judgement')]
print(f'  short-name citations misjudged as needing a human: {len(bad)}  (must be 0)')
if bad:
    failed.append(('short_name safety', 'not human-class', str(bad)))

print(f'\n  {len(CASES) + 1 - len(failed)}/{len(CASES) + 1} reclassifier controls passed')
sys.exit(1 if failed else 0)
