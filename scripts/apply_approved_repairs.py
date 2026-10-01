"""Apply the two repairs that are independently verified, and nothing else.

ITEM B  -- drop the finance DOI from AI-Architecture/Neuromorphic-Computing.md
           10.1142/10269 resolves to "Real Options in Energy and Commodity
           Markets" (World Scientific, 2016). The file mentions it ZERO
           times. Whole line, exact match, asserted count.

ITEM B2 -- drop the DEAD duplicate from Consolidation/Adaptive-Forgetting.md
           The handoff (§3b) says the French-1999 correction was "already
           applied", but it was applied ADDITIVELY: line 35 still carries the
           dead 10.1037/0033-295X.96.2.323 right beside the corrected
           10.1016/S1364-6613(99)01294-2 on line 36, and the Sources entry
           [17] still resolves the dead one. That is why the row is still
           unresolvable. Verified: Crossref 404s the dead DOI, and returns
           the corrected one as French (1999), TiCS 3(4):128-135.

Both are whole-line deletions, so no DOI-prefix boundary hazard applies
(trap §7.1) -- doi_replace.py is for substituting a DOI inside a line, not
for removing a line. Each deletion asserts an exact expected count, and
the file is re-parsed as YAML afterwards (trap §7.4: never strip() a
frontmatter line before rebuilding it -- we pass lines through verbatim).
"""
import json
import os
import shutil
import sys
import time

VAULT = "/home/operator/.hermes/oracle/brain"
STAMP = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

JOBS = [
    {
        "path": os.path.join(VAULT, "AI-Architecture/Neuromorphic-Computing.md"),
        "line": '  - "https://doi.org/10.1142/10269"',
        "why": "item B: finance DOI, zero body mentions",
    },
    {
        "path": os.path.join(VAULT, "Consolidation/Adaptive-Forgetting.md"),
        "line": '  - "https://doi.org/10.1037/0033-295X.96.2.323"',
        "why": "item B2: dead duplicate beside the corrected French 1999 DOI",
    },
]

try:
    import yaml
except ImportError:
    yaml = None


def parse_frontmatter(path):
    """Return the parsed frontmatter dict, or raise."""
    text = open(path, encoding="utf-8").read()
    # locate the FIRST closing '---' after the opening one
    if not text.startswith("---"):
        raise SystemExit("no frontmatter in %s" % path)
    rest = text[3:]
    end = rest.find("\n---")
    if end == -1:
        raise SystemExit("unterminated frontmatter in %s" % path)
    block = rest[:end]
    fm = yaml.safe_load(block)
    if not isinstance(fm, dict):
        raise SystemExit("frontmatter is not a mapping in %s" % path)
    if "sources" not in fm:
        raise SystemExit("no sources key in %s" % path)
    return fm, len(fm["sources"])


for job in JOBS:
    path = job["path"]
    if not os.path.exists(path):
        raise SystemExit("missing file: %s" % path)
    before_fm, n_before = parse_frontmatter(path)
    srcs_before = list(before_fm["sources"])

    target = job["line"]
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")

    hits = [i for i, ln in enumerate(lines) if ln == target]
    if len(hits) != 1:
        raise SystemExit("expected exactly 1 occurrence of %r in %s, found %d"
                         % (target, path, len(hits)))

    idx = hits[0]
    # a source entry must sit inside the frontmatter sources: block
    if idx > 60:
        raise SystemExit("refusing: match at line %d is outside frontmatter" % (idx + 1))

    backup = "%s.bak-%s" % (path, STAMP)
    shutil.copy2(path, backup)

    # keep the line UNSTRIPPED everywhere else; drop exactly one line
    del lines[idx]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    after_fm, n_after = parse_frontmatter(path)
    srcs_after = list(after_fm["sources"])

    if n_after != n_before - 1:
        shutil.copy2(backup, path)
        raise SystemExit("source count went %d -> %d, expected -1; rolled back %s"
                         % (n_before, n_after, backup))
    if len(srcs_after) != len(set(map(str, srcs_after))):
        shutil.copy2(backup, path)
        raise SystemExit("duplicate sources after edit; rolled back")

    # the other entries must survive untouched -- this is trap §7.2
    # Compare the SOURCE LINES, not the parsed values: the parsed entry for
    # the line we deleted is the bare URL, whereas `target` is the indented
    # raw line. Comparing those two forms is what made the first run of this
    # script report a false loss and roll back a correct edit.
    # Read "before" from the BACKUP so the comparison is exact rather than
    # reconstructed.
    raw_after = [ln.strip() for ln in lines if ln.strip().startswith('- ')]
    raw_before = [ln.strip() for ln in
                  open(backup, encoding="utf-8").read().split("\n")
                  if ln.strip().startswith('- ')]
    target_raw = target.strip()
    missing = [s for s in raw_before if s != target_raw and s not in raw_after]
    if missing:
        shutil.copy2(backup, path)
        raise SystemExit("edit lost pre-existing sources: %r; rolled back" % missing[:3])

    print("OK  %s" % path)
    print("    reason : %s" % job["why"])
    print("    dropped: %s" % target.strip())
    print("    sources: %d -> %d" % (n_before, n_after))
    print("    backup : %s" % backup)
    print("    all other sources preserved: %d" % (n_after,))

print("\nboth files still parse as YAML and kept every other source.")
