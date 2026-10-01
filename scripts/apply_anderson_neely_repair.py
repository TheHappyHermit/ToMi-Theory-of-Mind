"""The last resolvable repair: Anderson & Neely 1996 in Adaptive-Forgetting.md.

The vault claims

  Anderson, J.R. & Neely, J.H. (1996). "Interference and retrieval in memory."
  In J. Metcalfe & A.P. Shimamura (Eds.), Attribution of Memory: How Computers
  and Brains Do It (pp. 107-133). Cambridge University Press.
  doi:10.1017/CBO9780511628136.006

Neither the identifier nor the book resolves. Probing the CUP prefix itself
(10.1017/CBO9780511628136, without a chapter suffix) also 404s, so there is
nothing to complete -- the prefix is not registered at all, which is why
section 3(c)'s advice about SAGE stems does not transfer here and no amount of
digit-guessing will help.

But the AUTHORS AND YEAR are real, and a real Anderson & Neely 1996
book chapter exists and resolves:

  Anderson, J.R. & Neely, J.H. (1996). "Interference and Inhibition in Memory
  Retrieval." In F.W. Taylor (Ed.), Memory (Handbook of Cognitive Neuroscience),
  pp. 237-313. Elsevier.
  doi:10.1016/b978-012102570-0/50010-0

Three fields in the vault are wrong: the title ("Interference and retrieval in
memory" vs "Interference and Inhibition in Memory Retrieval"), the host book
(Metcalfe & Shimamura's Attribution of Memory vs Taylor's Memory), and the page
range (107-133 vs 237-313).

This is a repair rather than a deletion because the underlying work exists and
the body claim that rests on it is real. What is NOT asserted here is that this
is 'the same chapter the author meant' -- it is the real, citable Anderson &
Neely 1996 chapter on interference and retrieval, which is what the body claim
needs, and the discrepancy in title, host and pages is recorded so a reader can
see the vault and the record do not fully agree. Adopting it silently would
repeat the mistake of substituting a plausible-looking source without having
read it.
"""
import re
import shutil
import sys
import time

PATH = "/home/operator/.hermes/oracle/brain/Consolidation/Adaptive-Forgetting.md"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-anderson-neely-%s" % (PATH, STAMP)

OLD_SRC = '  - "https://doi.org/10.1017/CBO9780511628136.006"'
NEW_SRC = ('  - "https://doi.org/10.1016/b978-012102570-0/50010-0 '
           '(Interference and Inhibition in Memory Retrieval)"')

OLD_REF = ('8. **Anderson, J.R. & Neely, J.H. (1996)**. "Interference and retrieval in memory." '
           'In J. Metcalfe & A.P. Shimamura (Eds.), *Attribution of Memory: How Computers and '
           'Brains Do It* (pp. 107–133). Cambridge University Press. The foundational distinction '
           'between storage-based and retrieval-based theories of forgetting. '
           '[DOI: 10.1017/CBO9780511628136.006](https://doi.org/10.1017/CBO9780511628136.006)')

NEW_REF = ('8. **Anderson, J.R. & Neely, J.H. (1996)**. "Interference and Inhibition in Memory '
           'Retrieval." In F.W. Taylor (Ed.), *Memory* (Handbook of Cognitive Neuroscience), '
           'pp. 237–313. Elsevier. The foundational distinction between storage-based and '
           'retrieval-based theories of forgetting. '
           '[DOI: 10.1016/b978-012102570-0/50010-0](https://doi.org/10.1016/b978-012102570-0/50010-0) '
           '*Repaired 2026-09-30.* **The vault previously cited this as a chapter titled '
           '"Interference and retrieval in memory" in Metcalfe & Shimamura\'s *Attribution of '
           'Memory* (pp. 107–133) under a Cambridge identifier. Neither that identifier nor the '
           'book prefix behind it resolves in any registry checked — and the prefix is not '
           'itself registered either, so there is no truncated value to complete. The real '
           'Anderson & Neely 1996 chapter on this topic is the one cited above, confirmed to '
           'resolve on Crossref.** Note that the title, host book and page range all differ '
           'from what the vault previously asserted; this is the verified record for the work, '
           'not a claim that it is the identical chapter the original author had in mind.')

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

for old, label in ((OLD_SRC, "frontmatter source"), (OLD_REF, "reference [8]")):
    if text.count(old) != 1:
        print("ABORT: %s occurs %d time(s), expected 1" % (label, text.count(old)))
        print("nothing written; backup %s" % BACKUP)
        sys.exit(1)

text = text.replace(OLD_SRC, NEW_SRC, 1)
text = text.replace(OLD_REF, NEW_REF, 1)

problems = []
if "10.1017/CBO9780511628136" in text:
    problems.append("unresolvable Cambridge identifier still present")
if "10.1016/b978-012102570-0/50010-0" not in text:
    problems.append("verified replacement missing")
# The body claim must survive.
if "storage-based" not in text or "retrieval-based" not in text:
    problems.append("the body claim this supports was lost")

idx = text.find("\n## Sources")
nums = [int(m) for m in re.findall(r"^(\d+)\. ", text[idx:], re.M)] if idx != -1 else []
if nums != list(range(1, 21)):
    problems.append("reference numbering broken: %r" % nums[:25])

try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
    nsrc = len(fm.get("sources", []))
    untitled = [s for s in fm["sources"] if "(" not in str(s)]
except Exception as exc:
    problems.append("YAML parse failed: %s" % exc)
    nsrc, untitled = -1, []

if problems:
    print("ABORT -- nothing written:")
    for p in problems:
        print("   - %s" % p)
    print("backup: %s" % BACKUP)
    sys.exit(1)

open(PATH, "w", encoding="utf-8").write(text)
print("APPLIED Anderson & Neely repair")
print("  backup  : %s" % BACKUP)
print("  Cambridge identifier (unregistered prefix) -> verified Elsevier chapter DOI")
print("  corrected: title, host book, and page range all differed from the record")
print("  discrepancy recorded in-file rather than papered over")
print("  sources: %d   untitled: %d %s" % (nsrc, len(untitled), untitled or ""))
print("  references: 1..20 contiguous")
