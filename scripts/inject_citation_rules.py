#!/usr/bin/env python3
"""Inject the citation-title requirement into every authoring cron job.

Why this script exists
----------------------
The schema listed `title` as OPTIONAL in a source entry, while the T2
verifier required one in order to match a citation against the resolved
document. A writer that followed the schema exactly still produced a page
that could never be graded above `medium` -- 1,605 of 2,661 identifier-bearing
citations corpus-wide had no title.

The schema is now fixed and okf_lint blocks the write. But a block only helps
a job that mentions it, and of the eight authoring jobs, exactly ONE
referenced the gate at all. This closes that gap mechanically rather than
job-by-job, so a newly added authoring job can be checked with --check.

Idempotent: re-running is a no-op, and --check reports which jobs still need
it without writing.
"""
import argparse
import json
import os
import shutil
import sys

JOBS = os.path.expanduser("~/.hermes/cron/jobs.json")
MARKER = "CITATION-WRITING.md"

# The block is appended so it cannot displace a job's existing instructions.
# It is written to be read by a model with no other context: it says what
# to do, what the failure costs, and where the long version lives.
BLOCK = """
---

## 📚 CITATIONS MUST CARRY TITLES — read before writing any page

If you write a page with a `sources:` list, every entry carrying a DOI or an
arXiv id must ALSO carry the paper's title.

```yaml
sources:
  - arXiv:2509.20021 (Embodied AI Survey)              # GOOD
  - doi:10.1109/PROC.1975.9939 (The protection of information in computer systems)
  - https://arxiv.org/abs/2607.18704                    # BAD — no title
```

**Why this is not cosmetic.** The grader resolves each identifier, fetches the
real document, and compares the real title against the title you wrote. A
titled citation can be graded `high`. An untitled one is capped at `medium`
permanently, with no error message. A title that differs from the real one is
worse — it is treated as a fabrication and capped at `low`.

On the current corpus, 1,605 of 2,661 identifier-bearing citations had no
title. This is the single largest reason pages are not graded `high`.

**Rules:**
- Fetch the title from the source — the arXiv abstract page, the DOI landing
  page, the PDF. Never from memory, never from a search snippet, never
  paraphrased.
- Do not fabricate one. If you cannot retrieve it, write the identifier alone
  and set `status: unverified`. An honest gap is fixable later; a fabricated
  title is a permanent defect.
- Take the title from the source, exactly as the source states it.

**Before finishing any page you wrote:**

```bash
python3 /home/operator/hermes-brain/scripts/okf_gate.py <file>
```

A non-zero exit means the page cannot be graded. Fix the citations or mark
them honestly unverified. Never resolve it by deleting the source.

Full rationale and the full good/bad table: /home/operator/hermes-brain/docs/CITATION-WRITING.md
Schema (read it, do not recite it from memory): /home/operator/hermes-brain/schemas/okf-schema.yaml
Rules: /home/operator/hermes-brain/docs/WIKI-STANDARDS.md
"""


def load():
    with open(JOBS, encoding="utf-8") as fh:
        d = json.load(fh)
    return d, d if isinstance(d, list) else d.get("jobs", [])


# Phrases that mean "this job CREATES or EDITS a vault page".
#
# The first version of this detector matched any mention of "wiki page" or
# "frontmatter", which caught the two lint jobs and a read-only prompt-me job
# that never write a page -- they only read one. Telling a linter how to cite
# is noise, and it buried the four jobs that actually needed it.
AUTHORS_PHRASES = (
    "write findings directly",
    "create or update the appropriate wiki page",
    "write the page",
    "write to oracle",
    "create the wiki page",
    "write a new page",
    "update the page",
)

# Phrases that mean "this job only READS or REPORTS".
#
# Scoped deliberately. A global veto on "read-only" suppressed the single
# most important job in the set: Oracle Night Research contains the phrase
# only inside the WRITE BOUNDARY block it must hand to its CHILDREN, which
# is an instruction about what a child may not do, not a statement about
# what the job itself does. The job's whole purpose is to write pages.
#
# So the veto applies only when the prompt shows no authoring phrase at all
# -- i.e. as a tie-breaker, not a gate.
READ_ONLY_PHRASES = (
    "read-only",
    "report_only",
    "summarise the results",
    "summarize the results",
    "is a linter",
    "runs the linter",
)


def authors_pages(job) -> bool:
    """True for a job whose prompt tells it to create or update a page.

    An explicit authoring phrase wins over a read-only phrase, because a
    read-only phrase inside a child-boundary block describes the child's
    restriction, not the parent's job.
    """
    prompt = (job.get("prompt") or "").lower()
    if not prompt:
        return False
    if any(k in prompt for k in AUTHORS_PHRASES):
        return True
    if any(k in prompt for k in READ_ONLY_PHRASES):
        return False
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report which jobs lack the block; write nothing")
    args = ap.parse_args()

    d, jobs = load()
    changed = []
    for j in jobs:
        if not authors_pages(j):
            continue
        prompt = j.get("prompt") or ""
        if MARKER in prompt:
            continue
        j["prompt"] = prompt.rstrip() + "\n" + BLOCK
        changed.append(j.get("name"))

    if args.check:
        _, jobs2 = load()
        missing = [j.get("name") for j in jobs2
                   if authors_pages(j) and MARKER not in (j.get("prompt") or "")]
        print("jobs authoring pages WITHOUT the citation block: %d" % len(missing))
        for n in missing:
            print("   %s" % n)
        return 1 if missing else 0

    if not changed:
        print("no changes needed -- all authoring jobs already carry the block")
        return 0

    backup = JOBS + ".bak-pre-citation-block"
    shutil.copy2(JOBS, backup)
    with open(JOBS, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=2)
    print("updated %d jobs (backup: %s)" % (len(changed), backup))
    for n in changed:
        print("   %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
