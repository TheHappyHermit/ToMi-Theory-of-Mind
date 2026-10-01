# WIKI STANDARDS — the one reference point for corpus rules

**Everything that touches wiki Markdown points here. Nothing restates these rules.**

- **Format authority:** [`okf-schema.yaml`](okf-schema.yaml) — machine-readable, the
  single source of truth for fields, enums, shapes, and repair policy.
- **Narrative authority:** `~/.hermes/oracle/brain/SCHEMA.md` (OKF v0.2, stable).
  If the two ever disagree, `okf-schema.yaml` wins for machines and this repo's copy
  gets corrected. Never add a third definition.

Consumers that must import the schema rather than re-declare it:
`okf_lint.py`, `okf_repair.py`, `research_quality_check.py`, `brain_sync.py`,
`fill_oracle_gaps.py`, the ingestion/research crons, and the wiki-writing skills.

---

## S1 · One writer emits; many read

Most corpus defects are *emission* defects, not authoring defects — a broken
anchor, a literal `\n` in a table cell, a boilerplate "See Also" block repeated
verbatim across 14 of 110 files. Those come from a generator, so they must be
fixed at the generator.

**Rule.** No page is considered written until it passes `okf_lint.py --strict`.
Warnings do not block. Failures do.

## S2 · Structure and content are validated separately

A page can have a perfect table of contents, real volume-and-page citations, and
a populated `verified:` block — and still contain an invented Nobel attribution.
This was observed, not hypothesised: the apparatus is generated and checked as an
artifact; the prose it decorates comes from a different path and is not.

**Rule.** A structural pass never implies a content pass. `confidence` and
`verified` are self-reports and MUST NOT be used as evidence weights — only
executed checks confer authority.

## S3 · Provenance is not authority

`source` says where a claim came from. `authority` says how much it can be
relied on. These are different fields and conflating them is a category error: a
file with 13 unresolved citation markers and `confidence: high` is not a
confidence problem, it is a wrong field.

## S4 · Paths are canonical and case-exact

`Entities/` (110 files) and `entities/` (14) coexist, and neither has an index.
One character of case broke 9 of 11 links found in a 20-file sample.

**Rule.** One canonical spelling per target, recorded in the lexicon. Links are
existence-checked at write time, case-sensitively.

## S5 · Every directory index is machine-checked

Indexes exist and are wrong — that is the failure mode. One listed 1 of 7 files;
one omitted 12 of 19. Existence of an index proves nothing.

**Rule.** `index ↔ directory` set-equality, plus a freshness comparison, both
deterministic. A stale index fails even when the sets happen to match.

### S5.1 · The two vaults and what belongs in each

The corpus is split by *kind* of knowledge, not by age. Research output
lives in one; everything the operator works with lives in the other.

**Oracle** (`~/.hermes/oracle/brain/`) — the research library. The six
research cron lanes write here and nowhere else. Roughly 2,300 files.

**Active wiki** (`~/.hermes/active-wiki/`) — the working layer. Small,
static, and read often. Current folders:

| Folder | Holds |
|-------|-------|
| `decisions/` | What was chosen, and why |
| `concepts/` | Ideas worked out |
| `entities/` | Projects, systems, tools |
| `system/` | How the setup works |
| `projects/` | Project documentation |
| `beliefs/` | Held beliefs, with what would change them |
| `research/` | One file only: `BUILD-PLAN-AGENDA.md`, the gap queue |

`beliefs/` is distinct from `decisions/`. A decision is settled and has a
rationale behind it; a belief is provisional and carries what would
falsify it.

Every folder above has an `index.md`, required by S5. `beliefs/` starts
with an index and no entries, so the folder exists in a fresh clone
rather than vanishing because it is empty — git does not track empty
directories, which is why the index is the folder's real content.

**Rule.** The active wiki holds no research output. If a file in
`active-wiki/research/` also exists in `oracle/brain/research/`, it is a
duplicate, not a second copy, and is consolidated. The exception is
`BUILD-PLAN-AGENDA.md`, which is the only record of four claimed-but-
unwritten subsystems (see `docs/gaps/missing-subsystems.md`).

## S6 · Live state is never prose

"Running, accessible", container counts, sync cadences. A monthly-vs-hourly sync
mismatch once left the largest store's semantic index a month stale *by design*,
stated without comment.

**Rule.** Point-in-time assertions carry `observed_at` or live in a regenerated
snapshot file. Never in body text under a confidence value.

## S7 · Repair is bounded by policy

The linter fixes what a rule can decide and reports what needs judgement.

- **Auto:** missing required fields, enum mapping, version, datetime format,
  existence-verified link case, index-suffix stripping, repeated headers.
- **Report only:** attributions, fabricated claims, stale state, truncation,
  unresolved citations, index gaps, prose defects. These need a source or a
  judgement, and auto-editing them destroys the evidence of the defect.

## S8 · Archives and supersession over deletion

Archive, supersede, complete, or cancel. Silently deleting loses the history that
makes an audit possible. Every destructive change names its own reason.

## S9 · Scale discipline

Any rule that works only because a human read every file is a habit, not a rule,
and must be labelled as one. The design target is 14,589 files (R-J5); the corpus
is 2,325.

## S10 · Timestamps are RFC3339 UTC

`YYYY-MM-DDTHH:MM:SSZ`. Never space-separated. Never mixed within one column —
mixed formats silently break sorting and indexes.

---

## Enforcement

| Check | Enforced by | Mode |
|---|---|---|
| Schema conformance | `okf_lint.py` | auto-repairable |
| Link resolution | `okf_lint.py` | auto for case, report for absent |
| Index set-equality | `okf_lint.py` | report |
| Structure (TOC/anchors/fences) | `okf_lint.py` | report |
| Content correctness | external verification queue | report, never auto |
| Pre-write gate | every writer | blocking |

Binding project rules live in `SCRATCHPAD.md` at the repo root (R-J1…R-J5) and are
restated nowhere else.
