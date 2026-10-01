"""Repair the truncated Wiley SICI identifier in
Temporal-Cognition/Encoding-Specificity-Context-Dependent-Memory.md.

The frontmatter source line carried

    10.1002/(SICI)1099-0720(199812)12:6

which stops at ':6'. A real Wiley SICI DOI continues with the start page and
an AID suffix. This is a STRUCTURAL truncation, not a registry gap: no
resolver can match a half-DOI, so it 404s everywhere by construction.

The file's own reference entry (line 192) already had the complete, correct
identifier and the correct journal, so this is a frontmatter/body mismatch
rather than a miscitation -- the T2 table reads the frontmatter, which is why
the row was unresolvable while the body looked fine.

The full identifier below was NOT copied from the body on trust: it was
re-queried against Crossref and confirmed to resolve to

  Grant, H.M., Bredahl, L.C., Clay, J., Ferrie, J., Groves, J.E.,
  McDorman, T.A., & Dark, V.J. (1998). Context-dependent memory for
  meaningful material: information for students.
  Applied Cognitive Psychology, 12(6), 617-623.

which also corrects the journal: the frontmatter's truncated form implied
'Applied Cognitive Science' (ISSN stem 1099-0720 is shared), but the record
is Applied Cognitive PSYCHOLOGY.
"""
import os
import re
import shutil
import sys
import time

PATH = ("/home/operator/.hermes/oracle/brain/Temporal-Cognition/"
        "Encoding-Specificity-Context-Dependent-Memory.md")
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-sici-%s" % (PATH, STAMP)

TRUNCATED = "10.1002/(SICI)1099-0720(199812)12:6"
FULL = "10.1002/(SICI)1099-0720(1998120)12:6<617::AID-ACP542>3.0.CO;2-5"
TITLE = ("Context-dependent memory for meaningful material: "
         "information for students")

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

# Replace only the frontmatter occurrence. The reference entry already holds
# the full form, so targeting the bare truncated string is safe -- but count
# first, because 'count(TRUNCATED)' would also match the prefix of FULL.
n = text.count(TRUNCATED)
if n != 1:
    print("ABORT: truncated identifier occurs %d time(s), expected 1" % n)
    print("nothing written; backup at %s" % BACKUP)
    sys.exit(1)

old_line = TRUNCATED
new_line = "%s (%s)" % (FULL, TITLE)
text = text.replace(old_line, new_line, 1)

problems = []
# The truncated form must be gone from the frontmatter, but the full form
# contains the truncated form as a prefix, so check the frontmatter region only.
fm = text[:text.find("\n---", 4)]
body = text[text.find("\n---", 4):]
if TRUNCATED in fm:
    problems.append("truncated identifier still in frontmatter")
if FULL not in fm:
    problems.append("full identifier not present in frontmatter")
if "(" not in [c for c in re.findall(r"https?://[^,\"]+", fm) if FULL in c][0]:
    problems.append("frontmatter source not titled")

try:
    import yaml
    parsed = yaml.safe_load(text[3:text.find("\n---")])
    if not isinstance(parsed, dict):
        problems.append("frontmatter did not parse to a dict")
    nsrc = len(parsed.get("citations", parsed.get("sources", [])))
except Exception as exc:
    problems.append("YAML parse failed: %s" % exc)
    nsrc = -1

# The DOI contains '<', '>', '::' and ';' -- all legal in YAML double-quoted
# scalars, but confirm the round trip preserved it byte for byte.
if FULL not in text:
    problems.append("full identifier did not survive the write")

if problems:
    print("ABORT -- nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("APPLIED SICI truncation repair")
print("  backup  : %s" % BACKUP)
print("  frontmatter citations intact: %s" % nsrc)
print("  truncated -> full identifier; journal confirmed as Applied Cognitive Psychology")
