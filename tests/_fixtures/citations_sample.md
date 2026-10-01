# Fixture for the citation parser tests (P5b).

Every identifier form the corpus actually uses, in one file. If the parser
misses any of these, a real citation goes unchecked while the report still
looks complete.

Three of the six below are DELIBERATELY WRONG — each resolves to a different
paper than the claim says. That is the error class this tool exists to catch,
so the fixture is the failure case, not a happy path.

Sources
-------

1. Bare DOI, no URL, WRONG CLAIM.
   "10.1037/bul0000100" cited as "Acute stress and episodic memory" (2017) — correct.

2. Bare DOI, no URL, WRONG CLAIM.
   "10.1037/0033-295X.106.4.593" cited as "Implementation intentions and goal
   attainment" (2019) — actually a paper about a different topic entirely.

3. DOI as a URL, WRONG CLAIM.
   "https://doi.org/10.1038/nature09021" cited as "Forgetting and the spacing
   effect in episodic retrieval" (2019) — actually protein folding.

4. arXiv as a URL, WRONG CLAIM.
   "https://arxiv.org/abs/1706.03762" cited as "A comprehensive review of
   hippocampal replay mechanisms" (2019) — actually the transformer paper.

5. Bare `arXiv:` prefix.
   "arXiv:2603.13285" cited as "Belief-writer provenance in a cognitive
   architecture" (2026).

6. Bare dataset DOI (DataCite, not Crossref).
   "10.5061/dryad.abc123" cited as "A Replicated Dataset Of Something
   Interesting" (2021).

Trailing bare DOI in a sentence, to prove the parser does not require line-start
or quotes: see also 10.1146/annurev.psych.57.102904.190214 for the review.
