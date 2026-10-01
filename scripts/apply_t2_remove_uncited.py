"""Remove the 9 dead, uncited frontmatter sources (handoff section 3c).

Why removal is safe here, established by measurement rather than assumption:

  All nine appear ZERO times outside the frontmatter. They have no title, no
  author, no reference-list entry, and no body sentence depends on them. So
  there is no claim to orphan -- unlike the McCloskey row, which WAS body-cited
  and had to be repaired rather than removed. The distinction is the whole
  reason this script checks for body usage before it deletes anything, and
  refuses to proceed if a row turns out to be cited.

  The identifiers themselves are dead: three independent registries (Crossref,
  OpenAlex, doi.org), each proved live on two known-good controls first, return
  404 for all nine. The verifier's own docstring defines that verdict as
  'could not check' rather than 'does not exist'. But for a bare source with
  no attached claim, "cannot be checked" and "supports nothing" point the same
  way: it is unverifiable scaffolding, and leaving it asserts a source the
  registry cannot produce.

  Bibliographic searches for plausible intended papers were run for each
  topic and are recorded in docs/audit/t2-item-c-research.json. No candidate
  was a confident enough match to substitute blindly -- a bare DOI with no
  title does not tell you what the author meant, and inventing an attribution
  would be fabrication of exactly the kind this audit exists to remove.

  Per the user's standing decision, nothing is deleted silently: each removal
  is recorded in the file's own audit log below the sources, so the next reader
  can see what was dropped and why.
"""
import os
import re
import shutil
import sys
import time

import yaml

VAULT = "/home/operator/.hermes/oracle/brain"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

# file -> list of exact frontmatter source lines to remove
REMOVALS = {
    "Belief-Revision/Belief-Revision-Safe-Belief-Updating.md": [
        "https://doi.org/10.1016/j.artint.2014.01.1475",
    ],
    "Cellular-Neuroscience/Pyramidal-Neuron-Apical-Dendrite-Computations.md": [
        "https://doi.org/10.1038/nn1199_989",
    ],
    "Executive-Control/Habit-Formation.md": [
        "https://doi.org/10.1037/a0046060",
        "https://doi.org/10.1146/annurev-psych-010418-103041",
    ],
    "Knowledge-Representation/Cognitive-Maps-Beyond-Space.md": [
        "https://journals.sagepub.com/doi/10.1177/0956797615621371",
    ],
    "Learning/Desirable-Difficulties-Bjork.md": [
        "https://doi.org/10.1016/S0010-0277(85)80010-3",
        "https://doi.org/10.1016/j.memco.2008.10.002",
        "https://doi.org/10.1037/0096-3445.137.4.595",
    ],
    "Social-Cognition/Cognitive-Dissonance-and-Self-Justification.md": [
        "https://journals.sagepub.com/doi/10.1177/1754073917724993",
    ],
}

NOTE = (
    "<!-- T2 audit %s: removed %d unverifiable, uncited source(s) from the "
    "citations list above. Each returned HTTP 404 from Crossref, OpenAlex and "
    "doi.org (all three proved live against known-good controls first), had no "
    "title, no author and no reference-list entry, and appeared nowhere in the "
    "body -- so no claim was lost. A 'could not check' verdict is not a "
    "'does not exist' verdict, and no substitute was invented: a bare DOI does "
    "not record what was meant. Rationale and per-source search results: "
    "docs/audit/t2-item-c-research.json. -->\n"
)

print("=" * 78)
print("PRE-FLIGHT: every target must be UNCITED in the body")
abort = []
for rel, urls in REMOVALS.items():
    path = os.path.join(VAULT, rel)
    text = open(path, encoding="utf-8").read()
    split = text.find("\n---", 4)
    fm, body = text[:split], text[split:]
    for u in urls:
        in_body = body.count(u)
        in_fm = fm.count(u)
        status = "OK (uncited)" if in_body == 0 and in_fm == 1 else "PROBLEM"
        if status != "OK (uncited)":
            abort.append((rel, u, in_body, in_fm))
        print("  %-9s body=%d fm=%d  %s" % (status, in_body, in_fm, u[:60]))
if abort:
    print("\nABORT -- at least one target is cited in the body or ambiguous:")
    for rel, u, b, f in abort:
        print("   %s :: %s (body=%d fm=%d)" % (rel, u, b, f))
    sys.exit(1)
print("all targets confirmed uncited\n")

total = 0
for rel, urls in REMOVALS.items():
    path = os.path.join(VAULT, rel)
    text = open(path, encoding="utf-8").read()
    backup = "%s.bak-t2-clean-%s" % (path, STAMP)
    shutil.copy2(path, backup)

    lines = text.split("\n")
    kept, dropped = [], []
    for line in lines:
        if any(u in line for u in urls):
            dropped.append(line)
            continue
        kept.append(line)
    if len(dropped) != len(urls):
        print("ABORT: %s dropped %d lines, expected %d" % (rel, len(dropped), len(urls)))
        sys.exit(1)
    new = "\n".join(kept)

    # Validate YAML round-trip before writing.
    try:
        parsed = yaml.safe_load(new[3:new.find("\n---")])
        if not isinstance(parsed, dict):
            raise ValueError("frontmatter is not a mapping")
        listy = [k for k in ("citations", "sources")
                 if isinstance(parsed.get(k), list)]
        for k in listy:
            for s in parsed[k]:
                for u in urls:
                    if u in str(s):
                        raise ValueError("%s survived in %s" % (u, k))
    except Exception as exc:
        print("ABORT: %s failed validation: %s" % (rel, exc))
        print("nothing written for this file; backup %s" % backup)
        sys.exit(1)

    # Append the audit note just after the frontmatter so it is visible.
    end = new.find("\n---", 4) + len("\n---")
    note = "\n" + (NOTE % (STAMP, len(urls)))
    new = new[:end] + note + new[end:]

    open(path, "w", encoding="utf-8").write(new)
    total += len(dropped)
    print("  cleaned %-62s removed %d" % (rel.split("/")[-1][:60], len(dropped)))
    print("           backup: %s" % backup.split("/")[-1])

print("\ntotal sources removed: %d" % total)
print("every removal is annotated in-file and listed in "
      "docs/audit/t2-item-c-research.json")
