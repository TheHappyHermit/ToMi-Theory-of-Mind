"""Correct my own bad edit: the Volkow substitution was a mismatch.

What went wrong. When the Friston 2017 phantom was removed I replaced the
frontmatter source line with

    10.1098/rstb.2008.0107 (Overlapping neuronal circuits in addiction and
    obesity: evidence of specific dopamine contributions to reward)

That was a substitution I had not earned. It resolved, but it is a paper
about dopamine, addiction and obesity, and it has nothing to do with either
claim reference [5] was supporting -- the free-energy equation, or precision
dynamics in functional neurological disorder. The verifier correctly returned
'mismatch', the one verdict that means the file cites the wrong paper.

Worse, the title I typed did not even match the record: Crossref returns that
DOI as 'Overlapping neuronal circuits in addiction and obesity: evidence of
SYSTEMS PATHOLOGY', not 'evidence of specific dopamine contributions to
reward'. I typed a plausible-sounding title for a paper I had not read. That is
exactly the fabrication pattern this audit exists to remove, and introducing it
while auditing for it is the failure mode worth recording plainly.

The fix is to remove the source line, not to substitute again. The file
already carries two real Friston sources for the FEP material -- [1] Friston
(2010), 'The free-energy principle: a unified brain theory?', Nature Reviews
Neuroscience 11(2):127-138, and [6] Friston & Kiebel (2009), 'Predictive
coding under the free-energy principle' -- so the free-energy claims have real
support already. The FND claim remains explicitly open and marked, which is the
correct state for it.
"""
import re
import shutil
import sys
import time

PATH = ("/home/operator/.hermes/oracle/brain/Predictive-Processing/"
        "predictive-processing-and-active-inference.md")
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-volkow-%s" % (PATH, STAMP)

BAD = ('  - "https://doi.org/10.1098/rstb.2008.0107 (Overlapping neuronal '
       'circuits in addiction and obesity: evidence of specific dopamine '
       'contributions to reward)"')

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

if text.count(BAD) != 1:
    print("ABORT: bad source line occurs %d time(s), expected 1" % text.count(BAD))
    print("nothing written; backup %s" % BACKUP)
    sys.exit(1)

text = text.replace(BAD + "\n", "", 1)

problems = []
if "10.1098/rstb.2008.0107" in text:
    problems.append("unearned substitution still present")
if "10.1093/brain/awag101" in text:
    problems.append("original phantom still present")
# The honest state must remain: claims retained, reference marked, open noted.
for frag in ("temporary gain miscalibration", "The free-energy principle: a unified brain theory?",
             "Predictive coding under the free-energy principle", "CITATION UNVERIFIED"):
    if frag not in text:
        problems.append("lost required content: %r" % frag)

try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
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
print("REMOVED the unearned Volkow substitution")
print("  backup  : %s" % BACKUP)
print("  frontmatter sources: %d" % nsrc)
print("  reference [5] remains struck and marked; FND claim remains explicitly open")
print("  FEP claims remain supported by the file's own real sources [1] and [6]")
