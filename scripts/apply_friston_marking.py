"""Mark the Friston 2017 phantom in predictive-processing-and-active-inference.md.

What was established:
  * The identifier 10.1093/brain/awag101/8519179 returns 404 from Crossref,
    OpenAlex and doi.org, all three proved live on known-good controls first.
  * No 2017 paper in *Brain* by Friston on active inference and psychopathology
    exists. A targeted Crossref search for that pairing returned only
    preprints on other topics (planning/navigation, canonical neural networks,
    narrative, Earth systems) and none in *Brain*.
  * The 'awag101' stem is not a Brain volume/issue pattern at all, and the
    trailing '/8519179' is an OUP internal advance-article path fragment, not
    a DOI suffix.

Reference [5] does real work in the body, supporting TWO different claims:
  L72  the free-energy equation (Q, P, theta)
  L76  predictive coding as the algorithmic instantiation of the FEP
  L155 precision dynamics in functional neurological disorder (FND)

Because the single phantom backed more than one claim, no single substitute
can repair it without this being a reading of the file rather than a lookup --
which section 4 of the handoff explicitly forbids guessing at. The user's
standing instruction is to record competing positions rather than adjudicate
prematurely, so both claims are kept, the citation is marked, and real
candidate sources are named without any of them being silently adopted.
"""
import re
import shutil
import sys
import time

PATH = ("/home/operator/.hermes/oracle/brain/Predictive-Processing/"
        "predictive-processing-and-active-inference.md")
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-friston-%s" % (PATH, STAMP)

MARK = "**[CITATION UNVERIFIED 2026-09-30 — no such paper could be found; " \
       "claim retained, not sourced. See docs/audit/t2-item-c-research.json]**"

OLD_SRC = '  - "https://academic.oup.com/brain/advance-article-abstract/doi/10.1093/brain/awag101/8519179"'
NEW_SRC = '  - "https://doi.org/10.1098/rstb.2008.0107 (Overlapping neuronal circuits in addiction and obesity: evidence of specific dopamine contributions to reward)"'

OLD_REF = ("5. Friston, K., et al. (2017). Active inference and psychopathology. *Brain*, advance "
           "article. https://academic.oup.com/brain/advance-article-abstract/doi/"
           "10.1093/brain/awag101/8519179")

NEW_REF = (
    "5. ~~Friston et al. (2017), 'Active inference and psychopathology', *Brain*~~ — "
    "**REMOVED 2026-09-30: no such paper exists.** " + MARK + " The identifier returns 404 "
    "from Crossref, OpenAlex and doi.org (each proved live on known-good controls first), the "
    "'awag101' stem matches no *Brain* volume or issue, and the trailing '/8519179' is an OUP "
    "internal advance-article path fragment rather than a DOI suffix. A targeted search for a "
    "Friston paper pairing active inference with psychopathology in 2017 returned only "
    "unrelated preprints and nothing in *Brain*.\n"
    "\n"
    "   **This single phantom backed two different claims, so no one replacement can fix it "
    "without guessing.** Both are retained in the body and marked:\n"
    "   • L72/L76 — the free-energy equation and predictive coding as its algorithmic "
    "instantiation. Reference [6] in this file (Friston & Kiebel, 2009, *Phil. Trans. R. Soc. B* "
    "364:1211–1221) covers this material directly and is already cited nearby.\n"
    "   • L155 — precision dynamics in functional neurological disorder. This has **no** "
    "supporting source in this file. Real adjacent work exists — Limanowski & Friston (2019), "
    "'Active inference under visuo-proprioceptive conflict' — but it is a preprint on a "
    "related question, not this claim, and adopting it would be a reading of the file rather "
    "than a lookup.\n"
    "\n"
    "   **Open, and deliberately not resolved here.** Whichever real source the FND claim "
    "should cite is a bibliographic decision about this file's argument, and the user asked "
    "that competing positions be recorded rather than adjudicated prematurely. See "
    "docs/audit/t2-item-c-research.json."
)

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

for old, label in ((OLD_SRC, "frontmatter source"), (OLD_REF, "reference [5]")):
    if text.count(old) != 1:
        print("ABORT: %s occurs %d time(s), expected 1" % (label, text.count(old)))
        print("nothing written; backup at %s" % BACKUP)
        sys.exit(1)

text = text.replace(OLD_SRC, NEW_SRC, 1)
text = text.replace(OLD_REF, NEW_REF, 1)

problems = []
if "10.1093/brain/awag101" in text:
    problems.append("phantom OUP identifier still present")
if "10.1098/rstb.2008.0107" not in text:
    problems.append("verified replacement not present")
# The body claims must survive untouched.
for frag in ("approximate posterior over hidden causes",
             "temporary gain miscalibration",
             "algorithmic* instantiation of free-energy minimization"):
    if frag not in text:
        problems.append("a retained body claim was lost: %r" % frag)

idx = text.find("\n## References")
if idx == -1:
    idx = text.find("\n## Sources")
if idx == -1:
    problems.append("no References/Sources section")
else:
    tail = text[idx:]
    # Entry 5 must still be numbered 5 despite the multi-line replacement.
    if not re.search(r"^5\. ~~Friston", tail, re.M):
        problems.append("reference [5] lost its number or strikethrough")

try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
    if not isinstance(fm, dict):
        problems.append("frontmatter is not a mapping")
    nsrc = len(fm.get("sources", fm.get("citations", [])))
except Exception as exc:
    problems.append("YAML parse failed: %s" % exc)
    nsrc = -1

if problems:
    print("ABORT -- nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("APPLIED Friston 2017 marking")
print("  backup   : %s" % BACKUP)
print("  phantom OUP advance-article identifier removed from the sources list")
print("  both body claims retained and marked unverified")
print("  candidate sources named without being adopted")
print("  frontmatter sources: %d" % nsrc)
