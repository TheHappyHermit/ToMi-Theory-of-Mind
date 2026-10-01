"""Item C: mark the three fabricated RIF citations in Adaptive-Forgetting.md.

USER DECISION (2026-09-30): mark the claims, do not delete them. The point of
this job is that a reader must be able to see a check FAILED. Silently dropping
the numbers would leave the file asserting specific figures with no source at
all, which is worse than a dead DOI.

So: every claim is KEPT and LABELLED, every dead DOI is removed from the
sources list, and the reference entries are rewritten to say plainly that the
work could not be verified. Three REAL papers found during the survey are added
in their place so the section still carries verifiable evidence.

Verified before writing (both resolvers unless noted):
  Murayama, Miyatsu & Buchli (2014) Psych Bull 140(5):1383-1409
      doi 10.1037/a0037505, PMID 25180807 -- the only RIF meta-analysis
  Cinel, Cortis Mack & Ward (2018) JEP:General 147(5):632-661
      doi 10.1037/xge0000441, PMID 29745709 -- RIF robust in naturalistic tasks
  Clark, Todorovic, Levy, Eschmann, Klein & Anderson (2026)
      JEP:General 155(5):1318-1346, doi 10.1037/xge0001922, PMID 42060405
      -- meta-analysis of SUPPRESSION-induced forgetting (think/no-think),
         NOT RIF. Included only where the file already claims a meta-analytic
         suppression figure. Its aggregate is d ~ 0.20-0.40 and it concludes
         robustness, so it must NOT be used for the RIF publication-bias claim.

CRITICAL: Clark et al. is SIF, not RIF. Using it to support the old
'publication bias drops RIF to d=0.15' claim would recreate the exact error
being repaired. The distinction is preserved in the text below.
"""
import os
import re
import shutil
import sys
import time

PATH = "/home/operator/.hermes/oracle/brain/Consolidation/Adaptive-Forgetting.md"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-itemC-%s" % (PATH, STAMP)

MARK = "**[CITATION UNVERIFIED 2026-09-30 — no such paper could be found; " \
       "claim retained, not sourced. See docs/audit/t2-item-c-research.json]**"

# ---------------------------------------------------------------- body block
OLD_BODY = """The RIF paradigm has been subject to significant replication scrutiny since the 2010s:

**Basden et al. (2014)** — Failed replication of RIF in a large sample.

- **Design**: N = 288; multiple RIF paradigm variants tested.
- **Finding**: No significant RIF effect in any variant. Rp- and Ur items showed equivalent recall.
- **Interpretation**: RIF may be an artifact of small samples and p-hacking, not a robust phenomenon.

**Huettl et al. (2021)** — Large-scale preregistered replication.

- **Design**: N = 630; preregistered; multiple labs.
- **Finding**: Small but reliable RIF effect (d ≈ 0.15–0.20), much smaller than original reports.
- **Interpretation**: RIF exists but is far weaker than originally claimed.

**Depret, Erlbaum & Eerland (2020)** — Meta-analysis.

- **Design**: 105 experiments, 72 independent tests, 39,000+ participants.
- **Finding**: Overall RIF effect size d = 0.31 (moderate), but significant **publication bias** — the effect size drops to ~0.15 when publication bias is corrected.
- **Interpretation**: RIF is real but smaller than the original literature suggests.

**The controversy**: The RIF field exemplifies a broader replication crisis in cognitive psychology. Original effects (d = 0.47–0.65) appear to be inflated by small samples, publication bias, and flexible analysis choices. The corrected effect (~d = 0.15) is small but non-zero, suggesting the phenomenon exists but is more fragile than previously thought."""

NEW_BODY = """**This section previously rested entirely on three citations that do not exist.** A citation audit on 2026-09-30 could not find any of them, and none has a real counterpart at the stated authorship or figures. The claims are retained below, clearly labelled, because a reader is better served by a visible failed check than by a silently removed number. They are **not** evidence. Verified papers that do bear on this question are given underneath.

**Basden et al. (2014)** — Claimed failed replication of RIF in a large sample. """ + MARK + """

- **Design**: N = 288; multiple RIF paradigm variants tested.
- **Finding**: No significant RIF effect in any variant. Rp- and Ur items showed equivalent recall.
- **Interpretation**: RIF may be an artifact of small samples and p-hacking, not a robust phenomenon.
- **Audit note**: Basden's only retrieval-induced-forgetting publication is Basden, Basden & Morales (2003), "The role of retrieval practice in directed forgetting," *JEP:LMC* 29(3):389–397 — a different topic, 11 years earlier, and not a replication attempt. No N=288 RIF replication by this author was found.

**Huettl et al. (2021)** — Claimed large-scale preregistered replication. """ + MARK + """

- **Design**: N = 630; preregistered; multiple labs.
- **Finding**: Small but reliable RIF effect (d ≈ 0.15–0.20), much smaller than original reports.
- **Interpretation**: RIF exists but is far weaker than originally claimed.
- **Audit note**: No such paper exists. PubMed holds 145 records for an author named Huettl and every one belongs to a different person (surgery, oncology, neurosurgery, limb regeneration). No Huettl has published in psychology on RIF. The N = 630 figure has no traceable source.

**Depret, Erlbaum & Eerland (2020)** — Claimed meta-analysis. """ + MARK + """

- **Design**: 105 experiments, 72 independent tests, 39,000+ participants.
- **Finding**: Overall RIF effect size d = 0.31 (moderate), but significant **publication bias** — the effect size drops to ~0.15 when publication bias is corrected.
- **Interpretation**: RIF is real but smaller than the original literature suggests.
- **Audit note**: No such paper exists. Murayama, Miyatsu & Buchli (2014) is the *only* meta-analysis of RIF in existence, and it reports no publication-bias correction and no d = 0.31 → 0.15 result. The figures above are unsupported.

**The controversy**: The RIF field exemplifies a broader replication crisis in cognitive psychology. Original effects (d = 0.47–0.65) appear to be inflated by small samples, publication bias, and flexible analysis choices. The corrected effect (~d = 0.15) is small but non-zero, suggesting the phenomenon exists but is more fragile than previously thought.

> ⚠️ **The paragraph above is retained as the file's original argument and is now unsupported.** Its three supporting citations do not exist, and the "corrected effect (~d = 0.15)" it rests on has no traceable source. Read it as a historical claim about how this literature was previously summarised, not as a current finding.

### What the verified literature actually shows

These are real, and both were checked against Crossref and PubMed on 2026-09-30.

- **Murayama, Miyatsu & Buchli (2014)**, "Forgetting as a consequence of retrieval: a meta-analytic review of retrieval-induced forgetting," *Psychological Bulletin* 140(5), 1383–1409. DOI [10.1037/a0037505](https://doi.org/10.1037/a0037505) (PMID 25180807). The first major meta-analysis of RIF. Its results **largely supported inhibition accounts** while also providing challenging evidence, with conclusions varying as a function of how RIF was assessed. It reports no publication-bias correction and licenses no specific effect size.
- **Cinel, Cortis Mack & Ward (2018)**, "Towards augmented human memory: Retrieval-induced forgetting and retrieval practice in an interactive, end-of-day review," *JEP:General* 147(5), 632–661. DOI [10.1037/xge0000441](https://doi.org/10.1037/xge0000441) (PMID 29745709). Six experiments with naturalistic materials reporting **reliable RIF** in real-world settings — evidence on the *opposite* side of the replication-scepticism argument above, and worth weighing against it.
- **Clark, Todorovic, Levy, Eschmann, Klein & Anderson (2026)**, "Forgetting as a consequence of retrieval suppression: a meta-analytic review," *JEP:General* 155(5), 1318–1346. DOI [10.1037/xge0001922](https://doi.org/10.1037/xge0001922) (PMID 42060405). A meta-analysis of **suppression-induced forgetting** in the think/no-think paradigm — 500 effects from 120 studies, aggregate d ≈ 0.20–0.40, with substantial heterogeneity. **This is SIF, not RIF**, and must not be read as evidence about RIF effect sizes. It is listed because this file makes a separate meta-analytic claim about suppression."""

# ------------------------------------------------------------ reference list
OLD_REF_DEPRET = """12. **Depret, E., Erlbaum, L. & Eerland, A. (2020)**. "Publication bias in the retrieval-induced forgetting literature." *Advances in Methods and Practices in Psychological Science*, 3(3), 301–315. Meta-analysis showing significant publication bias in RIF literature; corrected effect size d ≈ 0.15 vs. uncorrected d ≈ 0.31. [DOI: 10.1177/2515245920933748](https://doi.org/10.1177/2515245920933748)"""
NEW_REF_DEPRET = """12. ~~Depret, Erlbaum & Eerland (2020)~~ — **REMOVED 2026-09-30: no such paper exists.** The identifier recorded for it does not resolve to any record, and no paper by these authors on this topic could be found in any index checked. The claims it supported in the body are retained there but marked unverified. See docs/audit/t2-item-c-research.json."""

OLD_REF_HUETTL = """13. **Huettl, F., Hutter, C. & Wozniak, R. (2021)**. "A large-scale preregistered replication of retrieval-induced forgetting." *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 47(5), 631–645. Preregistered replication (N = 630) showing small but reliable RIF effect (d ≈ 0.15–0.20). [DOI: 10.1037/xlm0000908](https://doi.org/10.1037/xlm0000908)"""
NEW_REF_HUETTL = """13. ~~Huettl, Hutter & Wozniak (2021)~~ — **REMOVED 2026-09-30: no such paper exists.** The identifier recorded for it does not resolve, and no psychology publication by an author named Huettl on RIF exists; all 145 PubMed records for that surname belong to other people in other fields. See docs/audit/t2-item-c-research.json."""

OLD_REF_BASDEN = """14. **Basden, B.H., Basden, D.R. & Hatfield, J.L. (2014)**. "Failed replication of retrieval-induced forgetting in a large sample." *Memory & Cognition*, 42(7), 1120–1128. Large-scale failure to replicate RIF (N = 288); argues RIF may be an artifact of small samples. [DOI: 10.3758/s13421-014-0408-9](https://doi.org/10.3758/s13421-014-0408-9)"""
NEW_REF_BASDEN = """14. ~~Basden, Basden & Hatfield (2014)~~ — **REMOVED 2026-09-30: no such paper exists.** The identifier recorded for it does not resolve to it. The authors' only RIF publication is a 2003 paper on directed forgetting. See docs/audit/t2-item-c-research.json."""

DEAD = [
    '  - "https://doi.org/10.1177/2515245920933748"',
    '  - "https://doi.org/10.1037/xlm0000908"',
    '  - "https://doi.org/10.3758/s13421-014-0408-9"',
]
NEW_SRC = [
    '  - "https://doi.org/10.1037/a0037505 (Forgetting as a consequence of retrieval: a meta-analytic review of retrieval-induced forgetting)"',
    '  - "https://doi.org/10.1037/xge0000441 (Towards augmented human memory: Retrieval-induced forgetting and retrieval practice in an interactive, end-of-day review)"',
    '  - "https://doi.org/10.1037/xge0001922 (Forgetting as a consequence of retrieval suppression: A meta-analytic review)"',
]

EDITS = [
    (OLD_BODY, NEW_BODY, 1),
    (OLD_REF_DEPRET, NEW_REF_DEPRET, 1),
    (OLD_REF_HUETTL, NEW_REF_HUETTL, 1),
    (OLD_REF_BASDEN, NEW_REF_BASDEN, 1),
]
LINE_SWAPS = list(zip(DEAD, NEW_SRC))

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

for old, new, want in EDITS:
    got = text.count(old)
    if got != want:
        print("ABORT: block occurs %d time(s), expected %d:\n  %r" % (got, want, old[:80]))
        print("nothing written; backup at %s" % BACKUP)
        sys.exit(1)
for old, new in LINE_SWAPS:
    got = text.count(old + "\n")
    if got != 1:
        print("ABORT: source line occurs %d times, expected 1: %r" % (got, old))
        print("nothing written; backup at %s" % BACKUP)
        sys.exit(1)

for old, new, _ in EDITS:
    text = text.replace(old, new, 1)
for old, new in LINE_SWAPS:
    text = text.replace(old + "\n", new + "\n", 1)

# ------------------------------------------------------------- invariants
problems = []
for dead_doi in ("2515245920933748", "xlm0000908", "s13421-014-0408-9"):
    if dead_doi in text:
        problems.append("dead DOI still present: %s" % dead_doi)
for keep in ("10.1037/a0037505", "10.1037/xge0000441", "10.1037/xge0001922"):
    if keep not in text:
        problems.append("verified substitute missing: %s" % keep)
if text.count("CITATION UNVERIFIED") != 3:
    problems.append("expected 3 UNVERIFIED markers, found %d"
                    % text.count("CITATION UNVERIFIED"))
for frag in ("N = 288", "N = 630", "d = 0.31"):
    if frag not in text:
        problems.append("a retained claim was lost: %s" % frag)

idx = text.find("\n## Sources")
if idx == -1:
    problems.append("no '## Sources' section")
else:
    nums = [int(m) for m in re.findall(r"^(\d+)\. ", text[idx:], re.M)]
    if nums != list(range(1, len(nums) + 1)):
        problems.append("reference numbering broken: %r" % nums[:25])
    if len(nums) != 20:
        problems.append("expected 20 references, found %d" % len(nums))

try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
    if not isinstance(fm, dict) or "sources" not in fm:
        problems.append("frontmatter lost sources")
    n_src = len(fm["sources"])
    untitled = sum(1 for s in fm["sources"] if "(" not in str(s))
except Exception as e:
    problems.append("YAML parse failed: %s" % e)
    n_src, untitled = -1, -1

if problems:
    print("ABORT -- nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("APPLIED item C marking -> %s" % PATH)
print("  backup        : %s" % BACKUP)
print("  sources       : %d (3 dead replaced by 3 verified)" % n_src)
print("  untitled srcs : %d" % untitled)
print("  UNVERIFIED    : 3 markers, all three claims retained verbatim")
print("  references    : 1..20 contiguous")
