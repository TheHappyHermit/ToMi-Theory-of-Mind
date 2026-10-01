---
name: existing-state-first
description: Use before changing a system that has prior work.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Existing State First

Research that re-derives a settled conclusion, or that reports a confident negative
from one source, is worse than no research: it burns the session, buries the real
answer under revisions, and leaves the rest of the assigned work untouched.

## Step 0 - Read before you search (non-negotiable)

Before any external research on a project with prior work:

1. **Read the project's master working document.** Look for `SCRATCHPAD.md`,
   `DECISIONS.md`, `PROPOSED-*.md`, `NOTES.md`, or a design doc at repo root. Read
   its conclusions, open questions, standing rules, and retractions.
   **Rules the owner wrote there are binding and outrank your default approach** —
   including prohibitions like "don't run your own benchmark, use published numbers."
2. **Read the local knowledge base before searching externally.** For this user that
   is the Oracle vault (`~/.hermes/oracle/brain`). A prior session reported a tool
   "could not be found" after an external-only search while the vault had it ranked
   #2. The negative claim was false and cost a full session.
3. **Two-source rule.** A conclusion needs BOTH external primary sources AND the
   local knowledge base. If they disagree, say so explicitly rather than picking the
   convenient one.

See `references/state-audit.md` for the command-level scan.

## Never report a confident negative from one source

"Does not exist", "could not be found", "no public number exists" are **claims, not
results.** Before any of them, confirm the search covered the right sources and say
which ones. Absence from web search is not absence. Write "not found in \<sources
tried\>", never "does not exist."

A grep hit is also not a finding. When a search suggests a capability exists, **read
the source before believing it** — the apparent parser may be a generator, and `[[`
in Python may be a type annotation rather than a wikilink.

## Settle once, then move on

When a question reaches a conclusion, record it once with its evidence and stop. Do
not re-open it in a later turn unless new evidence appears. Re-arguing a settled
question while other assigned work sits undone is a failure mode — and repeated
revisions are the signal that the first conclusion was never actually investigated.

If the user says "move on," the answer is already captured; start the next task
immediately rather than adding a further caveat.

## Verify system claims by querying, not asserting

When a deliverable will make a claim about a database, schema, table name, file path,
or config value, **query it first** (`sqlite3 <db> .tables`, read the file, `gh api`).
A plausible-looking schema name that does not exist is a defect the reader cannot
detect, and it discredits the claims around it. Querying also frequently upgrades an
assumption into a real finding.

Distinguish four states when reporting on a component, because each implies different
work: **constructed / called / fed real data / policy examined.** A repo can have a
class, a test suite, and a design doc and still have the capability entirely unused.

Fixture data has telltale shapes: small row count, perfectly balanced splits, a
narrow range on a field that should vary, and provenance values that are all
test-ish. "The store holds N records" without checking they are real records
overstates the system by exactly the built-vs-used gap.

## Write to the right place the first time

Ask or infer where the deliverable belongs before writing it. For this user:
reasoning-in-progress goes to the session scratch pad (`~/.hermes/cache/scratch/`);
durable knowledge goes into the project's own `docs/` or the vault. **Scratch
deliverables never go to `$HOME`.** Writing to the wrong place and relocating later
wastes a turn and leaves the user unsure what is authoritative.

For a long document you have only partially read, use `patch` (targeted edits) rather
than `write_file` (whole-file overwrite), which can destroy content you never loaded.

## Record retractions in writing

When your own earlier work turns out wrong, write the retraction into the project's
working document: what was claimed, why it was wrong, what (if anything) survives,
and which conclusion is deferred and why. Naming the error protects the next reader
far better than quietly fixing the file. Mark the superseded artifact itself so
nobody cites it as evidence.

If the owner has set a rule that your output violates, retract the output — do not
merely caveat it and keep building on it.

## Pitfalls

- **Re-litigating a settled question.** Costs more than being wrong once, because it
  consumes the turns the rest of the work needs.
- **External-only research on a topic with a local knowledge base.** Produces
  confident false negatives. Check the vault first.
- **Measuring when told not to.** If the project forbids self-generated benchmarks,
  cite published numbers and label vendor benchmarks as vendor benchmarks. A
  self-measured number that measures a different stage than the one that matters is
  worse than no number.
- **Reporting presence without checking use.** See the constructed/called/fed split.
- **Writing deliverables to the home directory.** Always the scratch pad or the repo.
