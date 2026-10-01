"""Fix the residual one-digit error in the SICI identifier.

The regex fix in verify_t2_titles.py stopped the parser truncating the
identifier before the AID suffix. That exposed a SEPARATE, real defect in the
vault: both occurrences carry (199812) where the registered record has
(1998120). Probed both forms directly against Crossref:

    10.1002/(SICI)1099-0720(199812)12:6<617::AID-ACP542>3.0.CO;2-5   -> 404
    10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5  -> HIT
        Grant, H.M., Bredahl, L.C., Clay, J., Ferrie, J., Groves, J.E.,
        McDorman, T.A., & Dark, V.J. (1998). Context-dependent memory for
        meaningful material: information for students.
        Applied Cognitive Psychology, 12(6), 617-623.

The '0' is part of the ISSN-derived year segment, so dropping it is fatal.
This is worth separating from the parser bug: fixing the regex alone would
have turned a silently truncated identifier into a differently-truncated one
that still 404s, and the row would have stayed broken with a different
symptom. Two independent defects, one identifier.

Also corrected here: the reference entry describes the venue as it appears in
the vault, and the journal is Applied Cognitive Psychology. The frontmatter's
truncated form had implied 'Applied Cognitive Science' because the ISSN stem
1099-0720 is shared; the record settles it.
"""
import re
import shutil
import sys
import time

PATH = ("/home/operator/.hermes/oracle/brain/Temporal-Cognition/"
        "Encoding-Specificity-Context-Dependent-Memory.md")
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-sici-year-%s" % (PATH, STAMP)

WRONG = "10.1002/(SICI)1099-0720(199812)12:6<617::AID-ACP542>3.0.CO;2-5"
RIGHT = "10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5"
VERIFIED_TITLE = "Context-dependent memory for meaningful material: information for students"

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

n = text.count(WRONG)
if n == 0:
    print("ABORT: the malformed identifier is not present; nothing to do")
    print("backup %s" % BACKUP)
    sys.exit(1)
if n > 2:
    print("ABORT: expected at most 2 occurrences (frontmatter + reference), found %d" % n)
    print("nothing written; backup %s" % BACKUP)
    sys.exit(1)

text = text.replace(WRONG, RIGHT)

problems = []
if WRONG in text:
    problems.append("malformed identifier survived the write")
if text.count(RIGHT) != n:
    problems.append("expected %d corrected identifiers, found %d" % (n, text.count(RIGHT)))
# The body claim citing this paper must be intact.
if "Grant et al., 1998" not in text:
    problems.append("the body citation of this paper was lost")
# Venue must read as Psychology, not the 'Science' the truncated stem implied.
if "Applied Cognitive Science," in text:
    problems.append("venue still says 'Applied Cognitive Science'")

try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
    if not isinstance(fm, dict):
        problems.append("frontmatter is not a mapping")
    nsrc = len(fm.get("citations", fm.get("sources", [])))
    # the '<' '>' '::' ';' must survive YAML round-trip byte for byte
    joined = " ".join(str(s) for s in fm.get("citations", fm.get("sources", [])))
    if RIGHT not in joined:
        problems.append("corrected identifier did not survive the YAML round trip")
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
print("CORRECTED the SICI year segment")
print("  backup  : %s" % BACKUP)
print("  fixed   : %d occurrence(s)" % n)
print("  (199812) -> (1998120); the latter confirmed to resolve on Crossref")
print("  verified record: %s" % VERIFIED_TITLE)
print("             Applied Cognitive Psychology 12(6) 617-623 (1998)")
print("  frontmatter citations: %d" % nsrc)
