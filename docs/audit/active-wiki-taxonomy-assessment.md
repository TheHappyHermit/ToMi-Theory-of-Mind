# Assessment: the proposed PARA-style taxonomy for the Active Wiki

**Status:** feedback only. Nothing was created, moved, renamed or deleted.
**Date:** 2026-09-30
**Scope:** 94 files in `~/.hermes/active-wiki`; 2,388 in `~/.hermes/oracle/brain`.

---

## Verdict in one paragraph

Scoped as **active-wiki only, Oracle untouched, shared frontmatter** — the
proposal is a coherent design that is simply too large for the vault it would
land in. It asks for 13 top-level folders to hold **94 notes**; **6 of those
13 have no source content at all**, and the ones that do average 7 notes each.
The single hard blocker I raised — 13 of 14 note types rejected by the schema —
I have now tested and it is **solvable without touching Oracle**: adding 13
types to the shared enum leaves all 853 tests passing and blocks nothing. So
the real objection is scale and redundancy, not feasibility.

---

## The finding that reframes everything

`decisions/2026-09-28_research-consolidates-to-oracle-vault.md`, written
yesterday:

> "The Oracle is going to have all the research knowledge in its wiki and the
> active wiki is going to have other things like the decisions, concepts and
> entities and system. **I haven't really fully worked the idea for the active
> wiki out in full but it's good enough for now.**"

The prompt is that unfinished idea, filled in by someone else. It is a
legitimate answer to the question you left open. It is just not *your* answer
yet, and the vault has since been operating against your original five-folder
split (`decisions/ concepts/ entities/ system/ beliefs/`) without trouble.

**The proposal and your five-folder split are not in conflict — they are the
same idea at two sizes.** `decisions/ concepts/ entities/ system/ beliefs/`
maps almost one-to-one onto `60_/80_/40_/00_/50_/`. What the proposal adds is
`01_Raw`, `02_Log`, `10_Self`, `20_Areas`, `70_Questions`, `85_Procedures` and
`90_Archive` — and six of those seven have no content behind them today.

So the question is not "adopt or reject." It is **"do I want seven folders I
am not using yet."** That is a real choice, and it is a smaller one than the
proposal's 13-folder framing suggests.

## 1. The note types — SOLVED with no schema change at all

My original objection was that 13 of the 14 AI-proposed `type:` values are
rejected by `okf-schema.yaml` (only `decision` passes). That was correct as a
test result, and it had a simple fix I initially reached for the wrong way.

**The right answer is to not add anything.** The 13 numbered folders are an
*organisation* decision; `type:` is a *classification* decision. Every
category in the proposal maps onto a type that already exists:

- `50_Beliefs/Claims` → `type: reference`
- `50_Beliefs/Hypotheses` → `type: idea`
- `50_Beliefs/Theses` → `type: evergreen`
- `50_Beliefs/Principles` → `type: lesson`
- `02_Log/Incidents` → `type: incident`
- `10_Self` → `type: profile`
- `85_Procedures/Human-Runbooks` → `type: routine`
- `85_Procedures/Policies` → `type: technical-spec`
- `80_Models/Syntheses` → `type: evergreen`
- `70_Questions` → `type: question`
- and so on across all 13 folders

Verified with 46 fixture notes, one per category, linted individually by the
real gate:

```
46 file(s), 0 blocked    exit 0
19 distinct types, all pre-existing
```

**19 of the schema's 29 types cover all 13 folders.** The 10 unused ones
(`paper`, `preprint`, `journal`, `conference`, `research-report`, `trip`,
`purchase`, `code`, `comparison`, `presentation`) are research-vault types that
the active wiki has no use for — they stay in the schema untouched.

**Do not use `type_map` aliases for this either.** Aliasing `belief →
reference` would pass the gate while discarding the distinction the folder
draws. The distinction is preserved here because the *folder* carries it and
the *type* stays honest about what the note actually is.

Full table: `docs/audit/active-wiki-folder-type-map.md`.

## 2. The Oracle overlap — WITHDRAWN as a blocker

My previous framing treated the shared folder names as a problem. With Oracle
explicitly out of scope, they are not: `50_Beliefs` in the active wiki and
`entities` in Oracle are simply different vaults, and folder names are local.

The measurements are still worth keeping as context, because they explain
*why* the active wiki is small and why the taxonomy has nothing to chew on:

- 94 notes in active-wiki, 2,388 in Oracle.
- Of the 86 active-wiki names that also exist in Oracle, 39 are byte-identical
  and 44 differ only in frontmatter. Only 4 differ in prose.

That duplication is now simply inherited state, not something this project
creates. **Leave it alone** — you said Oracle is left alone, and nothing in
this restructure requires touching it.

One real caveat remains, and it is not about folders: because both vaults use
one shared `okf-schema.yaml`, **any frontmatter change made for the active
wiki's new folders lands on Oracle too.** That is fine for additive type
additions (proven above). It would not be fine for a rename or a removal.

## 3. Cost of the rename, re-measured — smaller than I said

Scoped to active-wiki only, only **6 live files** reference a folder the rename
would actually touch:

| current | -> proposed | files |
|---|---|---|
| `system/` | `00_System/` | 2 (`SKILL.md`, `jobs.json`) |
| `concepts/` | `80_Models/` | 1 (`grade_all.py`) |
| `personal/` | `10_Self/` | 1 |
| `projects/` | `30_Projects/` | 1 |
| `raw/` | `01_Raw/` | 1 |

The other references are to things the rename does not touch — `graphify-out/`
(6), `research/` (5), `_archive/`, `inbox/`.

**The one real hazard: 9 scripts contain both an `active-wiki/<folder>` path
*and* the string `oracle`.** A global `sed` on folder names would corrupt them,
because the same script frequently addresses both vaults. Every edit has to be
per-file and verified, not applied as a batch replace.

Also note `60_Decisions` would hold 33 of the 94 notes — **35% of the vault in
one folder** — which is the existing `decisions/` directory already working.
That is the one rename that plainly earns its keep.

## What I would keep

### 4. The immutable intake layer — the best-evidenced part, keep it

This is the strongest component and the evidence is unusually good.

**arXiv:2605.12978** (May 2026) is close to a direct vindication. In a
controlled environment exposing Retain/Delete/Consolidate, *"agents preserve
raw episodes by default and **double the accuracy** of their
forced-consolidation counterparts."* Even consolidating from ground-truth
solutions, GPT-5.4 **failed on 54% of ARC-AGI problems it had previously solved
without memory**. The paper's own recommendation: treat raw episodes as
first-class evidence and **gate consolidation explicitly**.

**Independent corroboration:** arXiv:2607.26637 found a reorganising pass that
condensed rather than preserved dropped REALTALK correctness **77.6 → 41.2**,
and it took an explicit "keep every fact" instruction to prevent it. Two
independent findings of silent detail loss on rewrite.

You already have this — `raw/` with `check_raw_drift.py` from earlier today,
tested against a seeded directory so the tamper case is proven rather than
assumed.

**One correction to the evidence's direction:** 2605.12978 shows disabling
consolidation *matches* auto-consolidation; it does not show raw-only is best.
And 2607.26637 found the **verbatim dump beat the fully agent-curated store**
on one benchmark. So: *raw-first is supported; "route it" is not.* The
proposal's `brain-curator`, which reclassifies raw on a schedule, sits on the
weak side of that line.

### 5. `brain-hygiene` — already exists, don't rebuild it

This is the one I'd push back on hardest, and it's a *don't do* rather than a
*do*.

You already run, enabled, right now:

- **`Wiki Lint Daily`** (0 4 * * *) — incremental lint, orphans, broken links
- **`Wiki Lint Weekly Deep`** (0 3 * * 0) — full audit: orphans, broken links,
  stale >90d, **contradictions**, hit-counter
- **`Monthly Systems Review`** (0 10 1 * *) — cron, backups, skill usage
- **`Weekly Review`** (0 9 * * 0)

`wiki-maintenance/SKILL.md` already covers orphans, broken links, stale pages,
contradictions, archiving and linking. Nine of the proposal's ten hygiene checks
map onto running jobs.

Creating `brain-hygiene` as a new skill plus `brain-hygiene` as a new Sunday
job would be **a second audit layer reporting the same findings** — and the
failure mode of a duplicate auditor is that neither one gets read.

**Verdict: don't create it. Fix the two jobs that already exist instead.**

### 6. `brain-capture` — the right idea, the wrong shape

The routing-tree-embedded, write-only-to-raw-and-log capture skill is sound,
and `capture-and-triage` + `wiki-ingestion` already cover the ground. But note
the research finding that bears directly on it:

> If your router is an LLM classifying into 13 buckets, you have added a lossy,
> unvalidated transformation to the write path — the exact step that
> 2605.12978 shows degrades memory.

The honest version of this skill **files to `01_Raw/` and stops.** Everything
else in the proposal is an argument for doing more to a note than the evidence
supports.

---

## What I would change or drop

### 7. The epistemic split — right idea, wrong axis, and it needs one more field

The research is unusually clear and worth reading in full: it finds
**no experiment anywhere** showing that separating claims from beliefs in a note
store reduces LLM confabulation or overclaiming. That is the load-bearing
assumption of `50_Beliefs/`, and it is unevidenced.

What *is* evidenced is **differentiated persistence semantics**. arXiv:2604.11364
argues CoALA and JEPA "both lack an explicit Knowledge layer with its own
persistence semantics. This gap produces a **category error**" — and its
decomposition splits on *epistemic status × persistence*, not on folders.
arXiv:2606.27472 shows supersession is a distinct, model-independent failure
(92%→77% on knowledge-update accuracy, and the gap *grows* with conversation
length, not compression ratio).

Two concrete problems with the four-way cut as folders:

- **"Principles" is not a weaker fact — it's a different kind of object.** It
  does not sit on the status axis with Claims and Hypotheses. Research
  explicitly flags this.
- **"Theses" and "Syntheses" (`80_Models/`) are not separable.** Both are
  interpretations built from multiple claims. The routing tree has no rule to
  choose between them, so the same note satisfies two branches.

**And the false-accusation risk is the one I'd actually worry about.** If a
folder name asserts a verdict, the model may inherit it — arXiv:2601.04435
(ACL 2026) documents that LLMs "default to accommodating users' assumptions
and exhibiting insufficient epistemic vigilance." A `Hypotheses/` folder is
close to the safest place to put something you *don't* trust, and to the
most dangerous if the name is treated as a settled classification.

**Verdict: keep epistemic status as a `epistemic:` field — you already have
one — not as four folders. And resolve contradictions deterministically.**
arXiv:2606.01435 is unambiguous: replacing LLM judgement with a deterministic
`max(serial)` beat every published system on fact-consolidation (78.0% vs
Mem0's 18%). Let a serial number decide, never the word "contradicted."

### 8. The 13-folder top level — cut it to 8

The load-bearing source is arXiv:2607.26637, "Filesystem-Based Memory for LLM
Agents" (59pp) — the first systematic study of exactly your medium. Its
headline:

> **"No agent we measure converts organization itself into better answers."**

The win is a **cost** win, not an accuracy win: organised stores roughly halve
per-query search cost on large material, at parity on small.

Three findings that bear on the 13-folder shape:

- **Agents don't build deep trees.** Left to organise themselves, stores
  converged at **depth 4–5**, none exceeding four levels. The proposal's
  13-way top level plus sub-splits is deeper than the measured agent
  behaviour — and at 94 notes it is also deeper than the vault. Same study: growing 32k→128k, the agent went from *three folders
  of twelve files* to *a single folder with two files*, relocating its
  hierarchy **into headings** — "the store does not shard with scale; it
  consolidates."
- **The cheapest structured store won.** Files moved intact, zero content
  edits, LLM-designed taxonomy — most consistent leader across benchmarks. The
  fully agent-curated store was **weakest of all** on one tier (37.5 vs 78.1
  for a plain verbatim dump).
- **P5 of their taxonomy contract** — *"structure serves the search, not
  itself; a level that does not help routing is overhead."* By that standard,
  most of 00→90 is overhead for any single query.

**Verdict: as many buckets as you have content for — which is 8, not 13.**
Which, note, is close to what you already have.

### 9. Numeric prefixes — my judgement, not a finding

No research on numeric ordering and agent retrieval; none found either way. The
prefixes are redundant with the label, and their own P1 principle requires
siblings be distinguishable "by labels alone."

For a machine the digits are close to pure cost: they appear in every path, in
every listing, in every citation, and carry no routing semantics. **If you want
them for your own muscle memory, that's a legitimate human preference — but say
so plainly rather than inheriting it as a design decision.** The one directly
relevant practitioner report is negative, and about this exact combination:
"PARA and alphanumeric naming schemes conflict with one another, creating a lot
of unnecessary friction."

### 10. The routing decision tree — the most under-evidenced element

**Direct evidence: none.** Searches returned AI content farms, not analysis.

The nearest real evidence points the *other* way: filesystem memory
consolidates upward into headings as it grows, and "the folder and file layers
thin" — a rigid top-level contract runs against what the one relevant study
observed agents actually doing.

And arXiv:2606.24775 (12 systems, 11 datasets) is directly relevant to
re-filing: **"localized maintenance is more cost-efficient than global
reorganization."** That argues against periodic whole-vault restructuring
specifically.

One genuinely good rule in it, which I'd keep: *"Still unsure → 01_Raw/ and let
curation decide. Never force a guess into a compiled folder."* That's
uncertainty-preserving, and it's the opposite of what the folders are for.

---

## What I'd actually do — active-wiki only, 94 notes

The scale finding changes the recommendation. At 94 notes:

- 13 folders = **7.2 notes each**, and **6 folders would start empty**
  (`02_Log`, `20_Areas`, `70_Questions`, `85_Procedures`, `90_Archive`, and
  `10_Self` has an existing but empty `personal/`).
- arXiv:2607.26637's P5: *"structure serves the search, not itself; a level
  that does not help routing is overhead."* Empty folders are the definition
  of overhead.
- The same study measured agents converging at **depth 4–5** and *consolidating
  upward into headings* as stores grow — the opposite of a 13-way top level.

A right-sized version that keeps everything good in the proposal:

| Keep | Fold into | Notes |
|---|---|---|
| `00_System/` | `system/` | 13 |
| `01_Raw/` | `raw/` | 1 (already built + drift-tested today) |
| `10_Self/` | new | 0 → start empty on purpose |
| `30_Projects/` | `projects/` | 2 |
| `40_Entities/` | `entities/` | 13 |
| `50_Beliefs/` | `beliefs/` | 1 |
| `60_Decisions/` | `decisions/` | 33 |
| `80_Models/` | `concepts/` | 28 |

**That's 8, of which 4 are pure renames of folders that already exist.** Drop
`02_Log`, `20_Areas`, `70_Questions`, `85_Procedures`, `90_Archive` until they
have content — or keep them as documented-but-empty intent in `00_System/`
rather than as directories. A taxonomy that admits it has empty buckets is
honest; a taxonomy that pretends otherwise rots.

Then the parts that earn their cost regardless of folder count:

1. **Nothing to do here** — the folder→type mapping uses only existing
   schema types. No enum change, no aliases, no Oracle impact.
2. **`epistemic:` as a field, not four folders** — you already have the field.
   arXiv:2604.11364 supports differentiated *persistence*; it does not support
   four destinations. And no experiment anywhere shows the split reduces
   confabulation.
3. **Resolve contradictions deterministically** — `max(serial)`, not the word
   "contradicted" (arXiv:2606.01435: 78.0% vs Mem0's 18%).
4. **Do not create `brain-hygiene`** — `Wiki Lint Daily` and
   `Wiki Lint Weekly Deep` already run it, contradictions included.
5. **Do create `brain-capture`**, but have it stop at `01_Raw/`. The routing
   tree is best used to *stop* routing, not to classify into 13 buckets — an
   LLM router on the write path is a lossy transform, and 2605.12978 is the
   paper showing that step degrade memory.
6. **No new cron job for hygiene.** At most, adjust the two existing ones.

### The one-line version

The schema objection is withdrawn entirely — no change is needed, because
existing types already cover all 13 folders. What remains is scale: 13 folders
is a structure for a vault of several hundred notes, and this one has 94, with
six that would be empty on day one. Take the 8-folder version, keep the raw
layer, carry the belief split in `epistemic:`, and leave the hygiene jobs
alone.

