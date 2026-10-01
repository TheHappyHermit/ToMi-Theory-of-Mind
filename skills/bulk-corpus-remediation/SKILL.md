---
name: bulk-corpus-remediation
description: Use when fixing hundreds of files to one schema.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [corpus, bulk-edit, remediation, schema, verification, dry-run]
    related_skills: [verifier-integrity, verifying-scholarly-citations, whole-corpus-reading, file-ops-safety]
---

# Bulk Corpus Remediation

Applying a schema, rubric, confidence rule, or format change across a whole
corpus of files. The unit of work is the *corpus*, not the file, and the
failure modes are all corpus-shaped: one bad assumption repeated two thousand
times, or one correct-looking transformation that quietly discards the very
data it was written to handle.

## When to Use

Applying a schema, rubric, or fix across hundreds or thousands of files — wiki
conformance, dead references, frontmatter, broken links, a confidence rule, or
a defect list a linter reported.

Not for reading a corpus to understand it (`whole-corpus-reading`), and not
for editing one file at a time.

## The core loop

**1. Audit before you touch anything.** Measure the real gap against the
authoritative definition, not a proxy.

- Read the schema's actual `required` list. A grep census over *optional* keys
  overstates the work by orders of magnitude — a census reporting "2,451 files
  missing `created`" can coexist with a real gap of 9 files, because `created`
  is optional. Distinguish required from merely-wished-for, always.
- Exclude machine-generated directories explicitly and say so in the writeup.
  A gate that reports them as failures is correct to report, and its failure
  is not work to do.

**2. Break every bulk finding down before proposing a treatment.** A single
count — "N files have no external source" — is usually several different
situations wearing one number. Acting uniformly is wrong for a large minority.
Group by *what the files are*, not by *what's missing*, and size each group.

The tell that you skipped this: your proposed action is a single verb
("downgrade all 1,229"). A correct proposal names four or five different
treatments and says how many files get each.

**3. Derive, compare, write only the disagreements.** *Where the new system
agrees with the existing value, leave it; where it disputes it, change it.*
Report both counts. Restamping every file is a pass that cannot be audited
against its own diff.

**4. Back up before the first write, and verify by re-reading from disk.** Not
from the diff you intended to produce — from the files, after the fact.

## Safety rules for bulk writes

- Dry-run first, and make the dry run *actually* dry. A script that opens the
  report in write mode before checking its `--apply` flag will destroy the
  previous run on an innocent invocation. Read the write site before trusting
  any tool near a report you care about.
- Every removal is guarded by a **measured zero-occurrence check** in the body
  before removal. A source cited nowhere in the prose is safe to drop; one that
  is cited is not, regardless of whether its identifier resolves.
- Guarded scripts should **abort before writing** when a precondition fails,
  and say which precondition. A script that half-applies is worse than one that
  refuses.
- Keep backups beside the files, not in one shared dump, and do not delete
  them until the pass is verified end to end.
- Preserve unrelated in-progress work. Check the working tree before staging a
  commit and stage only your own paths.

## The bug class that costs the most

**Silent partial success.** A transformation matches a pattern, writes nothing
because nothing matched, and exits 0. The script's own output is not evidence:
confirm with an independent grep that the target strings are gone and the
intended strings are present.

The second-worst variant is a **stale cache**. A verdict table keyed by a
string that no longer exists keeps serving the old row, so a clean re-run
proves nothing. When a count refuses to move, suspect stale cache entries
before you suspect the fix, and invalidate exact keys rather than clearing
everything.

## Verdicts must distinguish failure from absence

A value with no title is `untitled`, never `mismatch`. Collapsing "no evidence"
into "failed" makes the population look worse than it is and buries the real
failures in noise. This distinction is what makes a bulk pass auditable.

## Long jobs: silence is not a hang

Report progress at intervals — files processed, remaining, and what has been
verified so far. A job that prints nothing for an hour is indistinguishable
from a job that is stuck, and the reader cannot tell whether to intervene.

## Reporting honestly

State: what changed, what was deliberately left alone, what remains, and what
was excluded and why. A remediation report that claims a corpus is clean when
three directories were skipped is worse than one that names the gap.

If the user's own working files were damaged during the pass, say so plainly,
preserve the damaged artifact for inspection, restore the last good version,
and report exactly what was lost. Do not quietly move on.
