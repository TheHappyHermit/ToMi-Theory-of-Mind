"""Repairs for the 15 remaining unresolvable rows, in Consolidation/Adaptive-Forgetting.md.

Method note -- why these two are REPAIRS rather than deletions:

  Three independent live routes (Crossref, OpenAlex, doi.org), each proved
  live on two known-good controls first, returned 404 for all fifteen
  identifiers. That establishes a REGISTRY GAP, not a fabrication verdict --
  the verifier's own docstring says so: 'unresolvable: could not check'. So
  each row was then identified by searching for the PAPER rather than probing
  the identifier, and two turned out to be real works under wrong identifiers.

  McCloskey & Cohen 1989 is REAL. Crossref and doi.org both resolve
    10.1016/s0079-7421(08)60536-8 -> 'Catastrophic Interference in
    Connectionist Networks: The Sequential Learning Problem',
    Psychology of Learning and Motivation, pp. 109-165, 1989.
  Note the volume: the file said 'Psychological Review 96(2) 323-357' and
  that APA identifier does not resolve, while the Elsevier serialisation of
  the same work does. Following the handoff's instruction to delete this row
  would have destroyed a genuine, body-cited source.

  Rouder & Morey 2005 does NOT exist. Crossref shows the pages the file
  claims (Psychological Review 112(4)) are actually 841-861:
  Johnson, M.R. & Busemeyer, J.R., 'A Dynamic, Stochastic, Computational
  Model of Preference Reversal Phenomena', 10.1037/0033-295x.112.4.841, which
  RESOLVES. The file's '...842' is the neighbouring article, and two targeted
  Crossref searches returned no Rouder & Morey paper of this title or any
  signal-detection decomposition of the picture-superiority effect. The claim
  it supported in the body is retained and labelled, per the user's decision
  that failed checks must be visible rather than silently deleted.
"""
import os
import re
import shutil
import sys
import time

PATH = "/home/operator/.hermes/oracle/brain/Consolidation/Adaptive-Forgetting.md"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-final15-%s" % (PATH, STAMP)

MARK = "**[CITATION UNVERIFIED 2026-09-30 — no such paper found; claim retained, " \
       "not sourced. See docs/audit/t2-item-c-research.json]**"

# ---- 1. McCloskey: real work, resolvable Elsevier DOI, journal was wrong too
OLD_SRC_MC = '  - "https://doi.org/10.1037/0033-295X.96.2.323 (Catastrophic interference in connectionist networks: The sequential learning problem)"'
NEW_SRC_MC = '  - "https://doi.org/10.1016/S0079-7421(08)60536-8 (Catastrophic interference in connectionist networks: The sequential learning problem)"'

OLD_REF_MC = ('17. **McCloskey, M. & Cohen, N.J. (1989)**. "Catastrophic interference in '
              'connectionist networks." *Psychological Review*, 96(2), 323–357. Foundational '
              'study of catastrophic forgetting in neural networks — the AI analog that '
              'adaptive forgetting reframes as a feature rather than a bug. '
              '[DOI: 10.1037/0033-295X.96.2.323](https://doi.org/10.1037/0033-295X.96.2.323)')

NEW_REF_MC = ('17. **McCloskey, M. & Cohen, N.J. (1989)**. "Catastrophic interference in '
              'connectionist networks: the sequential learning problem." *Psychology of Learning '
              'and Motivation*, 24, 109–165. Foundational study of catastrophic forgetting in '
              'neural networks — the AI analog that adaptive forgetting reframes as a feature '
              'rather than a bug. [DOI: 10.1016/S0079-7421(08)60536-8](https://doi.org/10.1016/S0079-7421(08)60536-8) '
              '*Verified 2026-09-30.* **The identifier previously given here, and the venue '
              '*Psychological Review* 96(2), 323–357, do not resolve in any registry checked.** '
              'The work is real; the Elsevier serialisation above is the citable one.')

# ---- 2. Rouder & Morey: fabricated; real occupant of those pages identified
OLD_SRC_RM = '  - "https://doi.org/10.1037/0033-295X.112.4.842"'
NEW_SRC_RM = '  - "https://doi.org/10.1037/0033-295x.112.4.841 (A dynamic, stochastic, computational model of preference reversal phenomena)"'

OLD_REF_RM = ('6. **Rouder, J.N. & Morey, R.D. (2005)**. "A signal detection decomposition of the '
              'picture-superiority effect." *Psychological Review*, 112(4), 842–855. '
              'Computational model of forgetting as a temperature/noise parameter in retrieval '
              'distributions. [DOI: 10.1037/0033-295X.112.4.842](https://doi.org/10.1037/0033-295X.112.4.842)')

NEW_REF_RM = ('6. ~~Rouder & Morey (2005)~~ — **REMOVED 2026-09-30: no such paper exists.** '
              + MARK + ' The claimed pages are *Psychological Review* 112(4), 841–861, which is '
              'Johnson, M.R. & Busemeyer, J.R., "A dynamic, stochastic, computational model of '
              'preference reversal phenomena" '
              '[DOI: 10.1037/0033-295x.112.4.841](https://doi.org/10.1037/0033-295x.112.4.841) — '
              'a resolvable but unrelated paper, which is why the identifier in the vault never '
              'returned anything. Two Crossref searches for a Rouder & Morey paper of this title, '
              'and for any signal-detection decomposition of the picture-superiority effect, '
              'returned no such work. The body claim that rested on it is retained there and '
              'marked unverified. See docs/audit/t2-item-c-research.json.')

EDITS = [
    (OLD_SRC_MC, NEW_SRC_MC, 1),
    (OLD_REF_MC, NEW_REF_MC, 1),
    (OLD_SRC_RM, NEW_SRC_RM, 1),
    (OLD_REF_RM, NEW_REF_RM, 1),
]

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

for old, new, want in EDITS:
    got = text.count(old)
    if got != want:
        print("ABORT: block occurs %d time(s), expected %d:\n  %r" % (got, want, old[:90]))
        print("nothing written; backup at %s" % BACKUP)
        sys.exit(1)

for old, new, _ in EDITS:
    text = text.replace(old, new, 1)

# ------------------------------------------------------------- invariants
problems = []
for dead in ("10.1037/0033-295X.96.2.323", "10.1037/0033-295X.112.4.842"):
    if dead in text:
        problems.append("unresolvable identifier still present: %s" % dead)
for keep in ("10.1016/S0079-7421(08)60536-8", "10.1037/0033-295x.112.4.841"):
    if keep not in text:
        problems.append("verified identifier missing: %s" % keep)
if "Rouder" not in text:
    problems.append("Rouder & Morey reference vanished entirely; the audit trail must remain")

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
    untitled = [s for s in fm["sources"] if "(" not in str(s)]
except Exception as exc:
    problems.append("YAML parse failed: %s" % exc)
    n_src, untitled = -1, []

if problems:
    print("ABORT -- nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("APPLIED final-15 repairs (Adaptive-Forgetting.md)")
print("  backup        : %s" % BACKUP)
print("  McCloskey     : APA unresolvable -> Elsevier resolvable; venue corrected")
print("                  to Psychology of Learning and Motivation 24, 109-165")
print("  Rouder & Morey: struck; the real occupant of pp. 841-861 recorded instead")
print("  sources       : %d   untitled: %d %s" % (n_src, len(untitled), untitled or ""))
print("  references    : 1..20 contiguous")
