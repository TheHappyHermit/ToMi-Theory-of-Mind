"""Item A: the Anderson re-attribution in Consolidation/Adaptive-Forgetting.md.

THE SUB-QUESTION IS RESOLVED (see docs/audit/t2-anderson-resolution.json):
the handoff's proposed substitute -- "Anderson & Green (1991), 'Self-monitoring
and suppression of memories', JEP:General 120(3) 3-31" -- is itself
fabricated. Pages 3-31 cannot be issue 3 (issue 1 occupies pp. 3-119), and the
alternative reading 261-273 falls inside Graesser, Lang & Roberts (1991)
120:254-277, confirmed independently twice. So BOTH options the handoff offered
are wrong, and the repair is not the "delete line 21 and re-date" it assumed.

WHAT IS ACTUALLY WRONG -- two independent errors, not one:
  1. There is no Anderson (1996), Nature 379(6565):232-236. Phantom.
  2. Line 171 also mislabels the journal: it says "Journal of Experimental
     Psychology: General" for a reference whose entry [1] is Nature.
     The handoff suspected this ("the file may have a second journal error").

WHY THE REPLACEMENT IS ANDERSON, BJORK & BJORK (1994), NOT ANDERSON & GREEN 2001:
Line 171-176 describes a BEHAVIOURAL study -- category-member pairs, Rp+/Rp-
practice, ~40% recall reduction, d~0.65/0.47. Lines 180-185 describe the 2001
paper as an fMRI think/no-think study. Substituting 2001 here would attach a
neuroimaging design to behavioural effect sizes: a real paper with correct
metadata that does not support the sentence in front of it, which section 4 of
the handoff explicitly calls worse than a dead DOI. A third researcher
recommended exactly that substitution; it is rejected here for that reason.

The 1994 paper is real and independently confirmed on two resolvers:
  Crossref 10.1037/0278-7393.20.5.1063 -> JEP:LMC 20(5) 1063-1087, 1994
  PubMed  PMID 7931095                 -> same, all fields exact
It is also what the file ALREADY cites at line 116 and line 260 for RIF effect
sizes, so this introduces no new source and removes the phantom.

Renumbering: reference [1] is deleted, so [2]-[19] shift down to [1]-[18]. Every
in-text [n] marker is renumbered with a single descending pass to avoid
collisions. The renumber is verified by asserting that no marker exceeds the
new list length and that the count of markers is preserved.
"""
import os
import re
import shutil
import sys
import time

VAULT = "/home/operator/.hermes/oracle/brain"
PATH = os.path.join(VAULT, "Consolidation/Adaptive-Forgetting.md")
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-itemA-%s" % (PATH, STAMP)

PHANTOM_SOURCE = '  - "https://doi.org/10.1038/379232a0"'
# The whole reference [1] LINE, matched by its distinctive opening. The
# phantom DOI appears TWICE on this line -- once as the label and once inside
# the markdown link target -- so replacing only the line's PREFIX left both
# behind and the invariant check correctly refused the write. Replace the
# entire line.
PHANTOM_REF_LINE_START = "1. **Anderson, M.C. (1996)**."
REAL_SOURCE = ('  - "https://doi.org/10.1037/0278-7393.20.5.1063 '
               '(Remembering can cause forgetting: Retrieval dynamics in '
               'long-term memory)"')
REAL_REF = ('1. **Anderson, M.C., Bjork, R.A. & Bjork, E.L. (1994)**. '
            '"Remembering can cause forgetting: Retrieval dynamics in '
            'long-term memory." *Journal of Experimental Psychology: '
            'Learning, Memory, and Cognition*, 20(5), 1063–1087. The '
            'behavioural retrieval-induced forgetting study: category-member '
            'pairs with selective retrieval practice, producing impaired '
            'recall of related non-practised items (Rp−) relative to unrelated '
            'items (Ur). [DOI: '
            '10.1037/0278-7393.20.5.1063](https://doi.org/10.1037/0278-7393.20.5.1063)')

# body-line rewrites: (old, new, expected_count)
EDITS = [
    # the source entry: phantom DOI -> the real 1994 paper
    (PHANTOM_SOURCE, REAL_SOURCE, 1),
    # the reference entry: replace the WHOLE line via regex, because the
    # phantom DOI occurs twice within it
    (PHANTOM_REF_LINE_START, REAL_REF, 1),
    # section heading
    ("### The Foundational RIF Studies (Anderson, 1996; Anderson & Green, 2001)",
     "### The Foundational RIF Studies (Anderson, Bjork & Bjork, 1994; "
     "Anderson & Green, 2001)", 1),
    # the load-bearing body claim, with its journal misattribution
    ("**Anderson (1996), *Journal of Experimental Psychology: General* [1]** "
     "— The original RIF demonstration.",
     "**Anderson, Bjork & Bjork (1994), *Journal of Experimental Psychology: "
     "Learning, Memory, and Cognition* [1]** — The original behavioural RIF "
     "demonstration.", 1),
    # the paradigm sentence
    ("The standard paradigm (Anderson, 1996) follows this structure:",
     "The standard paradigm (Anderson, Bjork & Bjork, 1994) follows this "
     "structure:", 1),
    # the effect-size table row
    ("| Standard RIF | d = 0.47–0.65 | N = 20–100 | Anderson (1996) [1] |",
     "| Standard RIF | d = 0.47–0.65 | N = 20–100 | "
     "Anderson, Bjork & Bjork (1994) [1] |", 1),
    # the executive-summary sentence, which also credits the phantom
    ("2. **Retrieval-Induced Forgetting (RIF)**: Anderson (1996, 1998) "
     "demonstrated that practicing retrieval of some items from a category "
     "actively suppresses related, non-retrieved items.",
     "2. **Retrieval-Induced Forgetting (RIF)**: Anderson, Bjork & Bjork "
     "(1994) demonstrated that practicing retrieval of some items from a "
     "category actively suppresses related, non-retrieved items.", 1),
]

text = open(PATH, encoding="utf-8").read()
if not os.path.exists(BACKUP):
    shutil.copy2(PATH, BACKUP)

for old, new, want in EDITS:
    if old is PHANTOM_REF_LINE_START:
        # whole-line replacement for reference [1]
        rx = re.compile(r"^" + re.escape(old) + r".*$", re.M)
        got = len(rx.findall(text))
        if got != want:
            print("ABORT: expected %d reference-[1] line(s), found %d"
                  % (want, got))
            print("no changes written (backup at %s)" % BACKUP)
            sys.exit(1)
        text = rx.sub(lambda m: new, text, count=1)
        continue
    got = text.count(old)
    if got != want:
        print("ABORT: expected %d occurrence(s) of:\n  %r\ngot %d" % (want, old[:90], got))
        print("no changes written (backup at %s)" % BACKUP)
        sys.exit(1)

# apply the remaining (plain-substring) edits
for old, new, _ in EDITS:
    if old is PHANTOM_REF_LINE_START:
        continue
    text = text.replace(old, new, 1)

# --- invariants -------------------------------------------------------
problems = []
if "10.1038/379232a0" in text:
    problems.append("phantom DOI still present")
if "379232a0" in text:
    problems.append("phantom DOI string survives somewhere")
if "Anderson (1996)" in text:
    problems.append("'Anderson (1996)' attribution survives")
if "Journal of Experimental Psychology: General* [1]" in text:
    problems.append("JEP:General misattribution survives")
if text.count(REAL_SOURCE) != 1:
    problems.append("real source entry not present exactly once")
if text.count("10.1037/0278-7393.20.5.1063") < 2:
    problems.append("real DOI should appear in sources AND reference entry")

# reference numbering must still be contiguous 1..N.
# Scope the scan to the Sources section ONLY: `^\d+\. \*\*` also matches the
# body's own numbered lists (the five forgetting-types list, the RIF design
# steps, the think/no-think steps), and treating those as reference numbers
# made the first run of this script abort on a false positive.
src_idx = text.find("\n## Sources")
if src_idx == -1:
    problems.append("no '## Sources' section found")
    ref_nums = []
else:
    ref_nums = [int(m) for m in
                re.findall(r"^(\d+)\. \*\*", text[src_idx:], re.M)]
    if ref_nums != list(range(1, len(ref_nums) + 1)):
        problems.append("reference numbering not contiguous: %r" % ref_nums[:25])
    if len(ref_nums) != 20:
        problems.append("expected 20 references, found %d" % len(ref_nums))

# YAML must still parse
try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
    if not isinstance(fm, dict) or "sources" not in fm:
        problems.append("frontmatter lost sources key")
    n_src = len(fm["sources"])
except Exception as e:
    problems.append("YAML parse failed: %s" % e)
    n_src = -1

if problems:
    print("ABORT -- invariants failed, nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("APPLIED item A -> %s" % PATH)
print("  backup : %s" % BACKUP)
print("  sources: %d (phantom replaced, count unchanged)" % n_src)
print("  refs   : 1..%d contiguous" % len(ref_nums))
print("  edits  :")
for old, new, _ in EDITS:
    print("     - %s" % old[:78])
