"""Strengthen the Bjork 1992 note with page-occupancy evidence.

The repair already applied cites the right chapter with no DOI, and that is
correct. But the *evidence* recorded in the file rested only on the identifier
failing to resolve, and a 404 proves less than it appears to: it shows the
identifier is not registered, not that the claimed article never existed.

Enumerating every Crossref record for JEP:Learning, Memory, and Cognition
volume 18 issue 6 (18 records, 11 distinct articles) closes that gap. The
claimed pages 1280-1296 are fully occupied by other papers -- Bentin,
Moscovitch & Heth at 1270-1283 covers 1280-1283, and Light, LaVoie &
Valencia-Laver at 1284-1297 covers 1284-1296 -- and no Bjork paper appears
anywhere in the issue.

This is the same kind of proof that settled the fabricated Anderson 1991
paper: another article demonstrably sits on the pages the citation claims, so
the citation cannot be a garbled version of a real paper at that location.
"""
import shutil
import sys
import time

PATH = "/home/operator/.hermes/oracle/brain/Learning/Desirable-Difficulties-Bjork.md"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-bjork92-pages-%s" % (PATH, STAMP)

OLD = ("a different decade. That identifier does not resolve, and neither do the "
       "APA-style identifiers implied by the claimed venue or by the commonly cited "
       "*Memory & Cognition* 19(5) 594–605 location, so no article ever occupied the "
       "position claimed.")

NEW = ("a different decade. That identifier does not resolve, and neither do the "
       "APA-style identifiers implied by the commonly cited *Memory & Cognition* 19(5) "
       "594–605 location. More decisively, the claimed pages are **occupied by other "
       "papers**: in *JEP:LMC* 18(6), Bentin, Moscovitch & Heth occupies 1270–1283 and "
       "Light, LaVoie & Valencia-Laver occupies 1284–1297, together covering every page "
       "of the claimed 1280–1296 range. No Bjork paper appears anywhere in that issue. "
       "So the original citation was not a garbled reference to a real article at that "
       "location — no article was there to be garbled. There is also no 1991 version: "
       "the year usually attached to this account is a mis-citation of this 1992 chapter.")

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

if text.count(OLD) != 1:
    print("ABORT: target sentence occurs %d time(s), expected 1" % text.count(OLD))
    print("nothing written; backup %s" % BACKUP)
    sys.exit(1)

text = text.replace(OLD, NEW, 1)

problems = []
if "Bentin, Moscovitch & Heth" not in text:
    problems.append("page-occupancy evidence missing after write")
if "no 1991 version" not in text:
    problems.append("the 1991 mis-citation note is missing")
# The corrected chapter citation and the load-bearing claim must be untouched.
for frag in ("A new theory of disuse and an old theory of stimulus fluctuation",
             "builds SS", "No DOI"):
    if frag not in text:
        problems.append("lost required content: %r" % frag)

try:
    import yaml
    yaml.safe_load(text[3:text.find("\n---")])
except Exception as exc:
    problems.append("YAML parse failed: %s" % exc)

if problems:
    print("ABORT -- nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("STRENGTHENED the Bjork 1992 audit note with page-occupancy evidence")
print("  backup: %s" % BACKUP)
print("  404-only reasoning replaced by proof the claimed pages hold other papers")
print("  the 1991 mis-citation is now noted in the file itself")
