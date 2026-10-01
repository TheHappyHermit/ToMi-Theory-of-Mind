"""Final T2 repair: reference [2] in Desirable-Difficulties-Bjork.md.

The vault claimed

  Bjork, R.A. & Bjork, E.L. (1992). "New theories of discard and forgetting."
  JEP:Learning Memory and Cognition 18(6), 1280-1296.
  doi:10.1037/0033-2909.124.4.421

Three separate problems, all now settled:

  1. The TITLE does not exist. A title search for 'discard and forgetting'
     returns nothing in this field; the real 1992 chapter is titled 'A new
     theory of disuse and an old theory of stimulus fluctuation'.
  2. The DOI's stem (0033-2909) is JEP:GENERAL and volume 124 corresponds to
     2017, so the identifier contradicts the citation's own journal and year.
     It 404s. Constructing the 'correct' APA-style identifier for the claimed
     venue -- 10.1037/0278-7393.18.6.1280 and 10.1037/0278-7393.19.5.594 --
     also 404s, so the claimed location was never a real article either.
  3. The underlying claim -- the two-strength, storage-versus-retrieval
     account -- IS real, and has a real 1992 source.

The real source, verified independently of the subagent that found it:

  Bjork, R.A. & Bjork, E.L. (1992). "A new theory of disuse and an old theory
  of stimulus fluctuation." In A.F. Healy, S.M. Kosslyn & R.M. Shiffrin
  (Eds.), From Learning Processes to Cognitive Processes: Essays in Honor of
  William K. Estes (Vol. 2, pp. 35-67). Hillsdale, NJ: Erlbaum.

NO DOI EXISTS for this chapter. I confirmed that directly: Crossref holds no
record, and OpenAlex returns the 1992 entry with doi=None. It is a 1992
Erlbaum festschrift chapter, predating widespread DOI registration. So the
correct fix is to cite the chapter WITHOUT a DOI, and say so, rather than to
attach a plausible-looking identifier -- which is the exact error this whole
audit has been correcting.

This reference is load-bearing: it supports the two-strength account at body
lines 53, 63 and 105. It could not simply be removed.
"""
import os
import re
import shutil
import sys
import time

PATH = "/home/operator/.hermes/oracle/brain/Learning/Desirable-Difficulties-Bjork.md"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
BACKUP = "%s.bak-bjork92-%s" % (PATH, STAMP)

OLD_SRC = '  - "https://doi.org/10.1037/0033-2909.124.4.421"'
NEW_SRC = ('  - "A new theory of disuse and an old theory of stimulus fluctuation. '
           'Bjork, R. A., & Bjork, E. L. (1992). In A. F. Healy, S. M. Kosslyn & R. M. Shiffrin '
           '(Eds.), From Learning Processes to Cognitive Processes: Essays in Honor of William '
           'K. Estes (Vol. 2, pp. 35-67). Hillsdale, NJ: Erlbaum. [No DOI: this chapter '
           'predates DOI registration; confirmed absent from Crossref and OpenAlex]"')

OLD_BODY = ('- **Bjork, R. A., & Bjork, E. L. (1992).** "New theories of discard and forgetting." '
            'This laid the theoretical groundwork with the two-strength account. [2]')
NEW_BODY = ('- **Bjork, R. A., & Bjork, E. L. (1992).** "A new theory of disuse and an old theory of '
            'stimulus fluctuation." This laid the theoretical groundwork with the two-strength '
            'account. [2] *(Title and venue corrected 2026-09-30 — the title previously given here '
            'does not correspond to any real paper. See docs/audit/t2-final15-resolution.json.)*')

OLD_REF = ("[2] Bjork, R. A., & Bjork, E. L. (1992). \"New theories of discard and forgetting.\" "
           "*Journal of Experimental Psychology: Learning, Memory, and Cognition*, 18(6), "
           "1280–1296. doi:10.1037/0033-2909.124.4.421")
NEW_REF = ("[2] Bjork, R. A., & Bjork, E. L. (1992). \"A new theory of disuse and an old theory of "
           "stimulus fluctuation.\" In A. F. Healy, S. M. Kosslyn & R. M. Shiffrin (Eds.), "
           "*From Learning Processes to Cognitive Processes: Essays in Honor of William K. Estes* "
           "(Vol. 2, pp. 35–67). Hillsdale, NJ: Erlbaum. **No DOI — this chapter predates DOI "
           "registration, and its absence from both Crossref and OpenAlex was confirmed on "
           "2026-09-30 rather than assumed.** *Repaired 2026-09-30:* the title, journal, volume "
           "and identifier previously recorded here were mutually inconsistent — the identifier's "
           "stem belongs to a different journal than the one cited, and its volume corresponds to "
           "a different decade. That identifier does not resolve, and neither do the "
           "APA-style identifiers implied by the claimed venue or by the commonly cited "
           "*Memory & Cognition* 19(5) 594–605 location, so no article ever occupied the "
           "position claimed. The theoretical claim this reference supports is real; the "
           "bibliographic record above is the real one. Full before/after detail: "
           "docs/audit/t2-final15-resolution.json.")

text = open(PATH, encoding="utf-8").read()
shutil.copy2(PATH, BACKUP)

EDITS = [(OLD_SRC, "frontmatter source"), (OLD_BODY, "body bullet"), (OLD_REF, "reference [2]")]
for old, label in EDITS:
    if text.count(old) != 1:
        print("ABORT: %s occurs %d time(s), expected 1" % (label, text.count(old)))
        print("nothing written; backup %s" % BACKUP)
        sys.exit(1)

for old, _ in EDITS:
    text = text.replace(old, NEW_SRC if old is OLD_SRC else (NEW_BODY if old is OLD_BODY else NEW_REF), 1)

problems = []
if "10.1037/0033-2909.124.4.421" in text:
    problems.append("the fabricated identifier is still present")
if "New theories of discard and forgetting" in text:
    problems.append("the non-existent title still appears")
# The load-bearing claim must survive intact.
for frag in ("builds SS", "two-strength", "[2]"):
    if frag not in text:
        problems.append("lost load-bearing content: %r" % frag)
if text.count("[2]") < 4:
    problems.append("expected the [2] citation markers to remain (expect 4+, found %d)"
                    % text.count("[2]"))

try:
    import yaml
    fm = yaml.safe_load(text[3:text.find("\n---")])
    srcs = fm.get("sources", fm.get("citations", []))
    nsrc = len(srcs)
    joined = " ".join(str(s) for s in srcs)
    if "new theory of disuse" not in joined:
        problems.append("the corrected chapter is not in the frontmatter sources")
    # Check the exact fabricated identifier is gone from the SOURCE LIST.
    # The check must NOT be a bare '0033-2909' stem test: that stem is
    # Psychological Bulletin's, and entry [7] here is the genuine Cepeda et al.
    # (2006) distributed-practice review under the same stem. Matching the
    # stem flagged a correct citation as fabricated.
    if any("10.1037/0033-2909.124.4.421" in str(s) for s in srcs):
        problems.append("the fabricated identifier survived in the frontmatter")
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
print("APPLIED Bjork 1992 repair")
print("  backup  : %s" % BACKUP)
print("  non-existent title and self-contradictory identifier removed")
print("  replaced with the real 1992 chapter, cited WITHOUT a DOI because none exists")
print("  absence from Crossref and OpenAlex was verified, not assumed")
print("  load-bearing two-strength claim retained at all three body sites")
print("  frontmatter sources: %d" % nsrc)
