#!/usr/bin/env python3
"""Regression tests for title_match() containment handling in
verify_t2_titles.py.

A fourth shape of false accusation, found by hand in the vault after the
T2 pending table was regenerated from live files:

  4a. Project name used where arXiv uses the paper title.
      vault  "NEMORI: Adaptive Memory Distillation"
      arXiv  "What Deserves Memory: Adaptive Memory Distillation for LLM
             Agents"
      The leading-run rule never fires (they diverge on token 1) and token
      overlap landed at 0.625, under the 0.80 floor. A correct citation
      was recorded as a mismatch.

  4b. Transposed wording.
      vault  "Ontology Design Patterns Applied to Cultural Heritage
             Knowledge Graphs"
      arXiv  "Pattern-based design applied to cultural heritage knowledge
             graphs"
      Same paper. Overlap 0.6, also under the floor. Also recorded as a
      mismatch.

Both are fixed by a containment rule: a contiguous span of >= 4 tokens
covering >= 60% of the shorter title, found anywhere in the longer one.

THE DANGER THIS RULE CREATES
----------------------------
Containment is a similarity check wearing a specific rule's clothes, and
it will happily match a different paper that shares a generic phrase. The
negative cases below exist to keep it honest -- in particular
"Attention Is All You Need" vs "You Ignore", which a 4-token floor alone
would match on the span "is all you".

Rule: a new matching rule ships with the case that motivated it AND with
the near-miss it could plausibly break.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    'v', os.path.join(HERE, 'verify_t2_titles.py'))
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)

CASES = [
    # (a, b, expected_match, why)
    ("NEMORI: Adaptive Memory Distillation",
     "What Deserves Memory: Adaptive Memory Distillation for LLM Agents",
     True,
     "4a: project name vs paper title. The motivating case."),

    ("Ontology Design Patterns Applied to Cultural Heritage Knowledge Graphs",
     "Pattern-based design applied to cultural heritage knowledge graphs",
     True,
     "4b: transposed wording. Second motivating case."),

    ("Adaptive Memory Distillation",
     "What Deserves Memory: Adaptive Memory Distillation for LLM Agents",
     True,
     "short label is a strict prefix of the real title"),

    # ── negatives: containment must NOT fire here ──────────────────────
    ("Attention Is All You Need",
     "Attention Is All You Ignore",
     False,
     "the classic over-match. 'is all you' is a 4-token span but is "
     "generic; a 4-token floor alone would match this."),

    ("Krishnamurthy et al. 2020",
     "Contextual Bandits with Continuous Actions: Smoothing, Zooming, "
     "and Adapting",
     False,
     "a genuine mismatch: different author, different paper. Must stay "
     "a mismatch or the verifier is useless."),

    ("A Survey of Graph Retrieval Methods",
     "Attention Is All You Need",
     False,
     "no shared span at all"),

    ("RUBAS: Rubric-Based Reinforcement Learning for Agent Safety",
     "Rubric-Based Reinforcement Learning",
     True,
     "KNOWN OVER-MATCH, accepted on purpose. The all-caps-alias rule that "
     "makes 'NEMORI: ...' match also fires here, where it is wrong: these "
     "are different papers. Nothing in the two strings separates them -- "
     "neither acronym appears in the other title, both share a 4-token "
     "set, same ratio band. Accepted because the costs are asymmetric: a "
     "missed alias is a visible false mismatch, a false alias is a real "
     "wrong citation silently scoring as a match. Flip to False if the "
     "mismatch rate becomes tolerable and false confidence is the worse "
     "risk."),

    ("Part 1: Foundations",
     "Part 2: Applications",
     False,
     "'Part 1' vs 'Part 2' must never match"),

    # ── TRUNCATED CITATION: vault records the SHORT title, the registry
    # returns the FULL one. Neither token set contains the other, the
    # vault side carries the journal and volume, and the registry side
    # carries the subtitle. The title proper is a shared PREFIX.
    ("The demise of short-term memory revisited. *Psychological Review*, "
     "112(1), 3-24",
     "The Demise of Short-Term Memory Revisited: Empirical and "
     "Computational Investigation",
     True,
     "vault cites the short title of a paper the registry titles in "
     "full. Journal name + volume(issue) mark the end of the title "
     "proper; the shared 7-token prefix covers it exactly"),

    # The journal-name cut must not fire on a title that merely CONTAINS
    # a journal-ish word. 'knowledge graphs' is a subject, not a journal.
    ("Ontology Design Patterns Applied to Cultural Heritage Knowledge Graphs",
     "Pattern-based design applied to cultural heritage knowledge graphs",
     True,
     "transposed head, shared tail; the journal-name list must not cut "
     "'knowledge graphs' out of a real title"),

    # A colon is a SUBTITLE boundary and must never end the title proper.
    ("Position: A Three-Layer Probabilistic Assume-Guarantee Architecture",
     "Position: A Three-Layer Probabilistic Assume-Guarantee Architecture "
     "Is Structurally Required",
     True,
     "cutting at the colon would compare the single word 'Position' "
     "against the whole title"),

    # A bare volume-shaped number pair must not make two unrelated titles
    # look truncated.
    ("Deep Residual Learning for Image Recognition, 2016 1",
     "Adam: A Method for Stochastic Optimization",
     False,
     "'2016 1' looks like a volume(issue) marker; these are still "
     "different papers and must not match"),

    # ── BOLD REFERENCE SHORTHAND: "*Surname & Surname (YEAR)**" with no
    # initials. The author strip had to learn this form.
    #
    # What is asserted here is only that the author run, the year, the
    # journal, the volume, the pages and the trailing DOI are stripped
    # OFF THE FRONT. What remains is a bare journal citation with no
    # title in it, so title_match cannot match -- and must not. The
    # honest verdict for this shape is untitled_citation, which is
    # decided by the caller, not by the matcher.
    ("*Itti & Baldi (2009)**, *Vision Research* 49(10):1295 1306, "
     "10.1016/j.visres.2009.06.037",
     "Bayesian surprise attracts human attention",
     False,
     "after stripping the author run this is journal+volume+pages+DOI "
     "with no title. It must not match, and must not be read as a wrong "
     "citation either -- there is simply no title to check"),

    # The year-in-parens rule must not eat a real title that happens to
    # contain a parenthetical year.
    ("Attention (2019) revisited: a study of visual search",
     "Attention (2019) revisited: a study of visual search",
     True,
     "a title beginning with a capitalised word and a 4-digit year must "
     "survive the bold-reference strip intact"),

    ("Deep Learning",
     "Deep Learning for Image Recognition",
     False,
     "2-token span, below the floor, and 'deep learning' is generic"),

    ("Retrieval Augmented Generation for Knowledge Intensive Tasks",
     "Retrieval-Augmented Generation for Natural Language Processing: "
     "A Survey",
     False,
     "shares a leading run but then diverges; the shorter title is not "
     "contained in the longer, so containment must not rescue it"),
]

passed = failed = 0
for a, b, expected, why in CASES:
    got, score = V.title_match(a, b)
    ok = (got == expected)
    if ok:
        passed += 1
    else:
        failed += 1
    flag = 'PASS' if ok else 'FAIL'
    print(f'  [{flag}] expect={expected!s:5} got={got!s:5} '
          f'score={score:.2f}  {why}')
    if not ok:
        print(f'         a={a!r}')
        print(f'         b={b!r}')

print(f'\n  {passed} passed, {failed} failed')
sys.exit(1 if failed else 0)
