# Wiki Standards Remediation — plan for a fresh session

Written 2026-09-28. **Nothing in this plan has been executed.** Every number
below was measured read-only with the existing checkers; no file was written,
repaired, moved, or deleted to produce it.

This document is meant to be read in a **new Hermes chat** by an agent that
has none of the history. It carries the measurements, the schema, the
history of what went wrong before, and the explicit answer to the question
asked: sequential-by-me, or a script, or subagents.

---

## 1. The question that was asked

> Is the absolute best course of action to have you go through all of these
> one by one and fix each one? And it may be that there's a child's agent
> that springs up, but it certainly has to have all of the context, all the
> schema and everything as per current cron jobs and best schema practices.

**Short answer: no, and no.** Neither "me one at a time" nor "a bulk script"
is right, and "a subagent springs up" is the specific failure mode to avoid.
The right shape is **a bulk script for the mechanical classes, and an agent
for the semantic ones — and never both over the same file class.**

The reasoning is in §7. It matters more than the plan.

---

## 2. Current measured state

Baseline, 2026-09-28, from the checkers that already exist:

```
okf_lint.py      scanned=2713  findings=6736  auto-fixable=2332  report-only=4404
verify_okf_index.py
  active_wiki    551 md files   418 issues   (all missing-link)
  oracle_brain  2008 md files   944 issues   (784 missing-link, 157 missing-title, 1 missing, 1 no-frontmatter, 1 missing-type)
```

Findings by class:

| Count | Class | Auto-fixable? | What it is |
|------:|-------|---------------|------------|
| 3480 | `link_unresolvable` | **no** | `[[target]]` that resolves to no page |
| 1633 | `type_not_canonical` | yes | `type:` is not in the allowed list |
| 689 | `numeric_citation_marker` | **no** | numeric reference markers |
| 225 | `invalid_confidence` | **no** | `confidence:` not high/medium/low |
| 197 | `bad_okf_version` | yes | wrong `okf_version:` |
| 190 | `missing_required` | yes | a required key absent |
| 151 | `status_not_canonical` | yes | `status:` not in the allowed list |
| 143 | `missing_front_matter` | yes | no YAML block at all |
| 10 | `link_index_suffix` | yes | `[[foo/index]]` should be `[[foo]]` |
| 8 | `link_case_wrong` | yes | case mismatch |
| 8 | `invalid_type` | **no** | type is not a plausible type |
| 2 | `invalid_status` | **no** | status is not a plausible status |

**2,332 auto-fixable, 4,404 report-only.** That split is the whole plan.

### 2.1 The 3,480 unresolvable links are not all broken links

This is the single most important finding, and it is why "fix all 3,480"
would be destructive. Classified by what the target actually is:

| Count | Target shape | Reality |
|------:|--------------|---------|
| 3314 | `other_page_ref` | plausibly a genuinely missing page |
| 68 | `§N` | a section reference, not a page |
| 45 | `arXiv 2609.00177` | **a citation written in wikilink syntax** |
| 31 | `wiki`, `wikilinks`, `links`, `index` | **documentation words, not links** |
| 12 | `graphify`, `honcho`, `brain`, `ollama` | tool names, not pages |
| 10 | `http://...` | a URL in wikilink syntax |

So at least **166 are syntax mistakes or non-links**, not missing pages, and
they are concentrated in a handful of generated files
(`frontier-research-ontology-roundNN-*.md` contribute ~20-28 each).

The 3,314 "other_page_ref" are **not all broken either**. A large share are
pages that exist under a different path — the same path-reorganisation
problem that produced the 419 orphans and the 633 unindexed files. Before
treating any of them as broken, the resolution rule has to try alias, `id:`
frontmatter, basename-anywhere, and slug-normalised forms. `okf_lint` has a
resolver (line 127 notes an earlier relative-path resolver was replaced); its
current rules must be read before trusting a count.

---

## 3. The schema — the single source of truth

`schemas/SCHEMA.md`, which is the narrative companion to
`schemas/okf-schema.yaml` (the machine authority).
Verified: no corruption, no doubled-pipe damage. The two schema files have
identical field sets.

**Required on every page:**

```yaml
---
okf_version: "0.2"
id: stable-id              # unique, stable, kebab-case
description: "Human readable description"
type: <page-type>
status: <lifecycle-status>
generated:
  by: "agent:researcher"
  at: "2026-09-07T10:00:00Z"    # RFC 3339 UTC
---
```

**Recommended:** `verified: []`, `stale_after: "2026-12-07"`, `tags: []`,
`sources: []`, `confidence: high|medium|low`, `epistemic: <label>`,
`wikilinks: []`, `aliases: []`

**Optional:** `review_after`, `related`, `supersedes`, `superseded_by`

**Allowed types:** `profile, person, project, decision, system, asset,
purchase, trip, routine, idea, question, lesson, reference, research_report,
incident, Index`

Canonical type and status lists are at `SCHEMA.md:74` and `SCHEMA.md:107`.
Allowed epistemic labels at `SCHEMA.md:95`.

### 3.1 Timestamps: the rule that was learned the hard way

Every new `generated.at` must be **RFC 3339 UTC, `YYYY-MM-DDTHH:MM:SSZ`**.
Never `datetime('now')` space-separated output. Never mixed within a
column. Mixed formats silently break sorting and indexes. There is already
`scripts/migrate_frontmatter_timestamps.py` — check whether it is correct
before trusting it.

---

## 4. What has already gone wrong — do not repeat these

Every one of these happened in this system, in the last few weeks.

| # | What happened | The lesson |
|---|---------------|------------|
| 1 | 419 "orphans" called stale; 161 were real documents whose only copy was the database | **Never infer deletion from an absence.** Prove it first. |
| 2 | 66 `_archive/` pages looked like duplicates; 51 of them were **different**, the disk copy richer | Hash before calling anything a duplicate. |
| 3 | Deleted test page 7135 did not self-clean; predicted it would | `brain_sync.py` has no `DELETE FROM pages`. Know what your tooling does. |
| 4 | Read-only guard appeared to work; a test `DELETE` succeeded | **A check that can pass via fallback is not verifying.** Test the guard with a write. |
| 5 | `GITHUB_TOKEN` expired, shadowed a working stored credential | Silent auth failure. Check it before blaming the repo. |
| 6 | arXiv links declared 404; a failed fetch is not a refutation | Retry or use an independent extractor before recording a negative. |
| 7 | `sync_state` "had no rows"; queried the wrong column (`last_synced` vs `last_run_at`) | **An empty result is a result about your query.** |
| 8 | `description` and `embedding` columns do not exist | Read the schema before writing a query. |
| 9 | A cron prompt named a retired repository for weeks; the audit said OK | A verifier with no way to fail reports OK. |
| 10 | `.env.honcho.example` documented four variable names Honcho never reads | Documentation can be the bug. Verify names against the code. |
| 11 | Shared `suite.log` gave false `24/27` results | **Concurrent runners overwrite shared state.** Unique output paths. |
| 12 | Staged `SCRATCHPAD.md`, `research-resultideas.md`, `fill_oracle_gaps.py` — files off-limits | Check `git status` before every commit. |

**The common thread: every one of these was an absence of evidence read as
evidence of absence.** That is the failure to design against.

---

## 5. The safety envelope — non-negotiable

- **Never delete a wiki file.** No expiry, no pruning, no "orphaned so
  remove". These are long-term knowledge files. The user has stated this
  explicitly and unprompted.
- **Never rewrite body content to satisfy a linter.** Only frontmatter and
  link syntax are in scope. Prose is knowledge.
- **Every change is reversible.** A manifest of exactly which files change
  and how, plus a full backup, before anything is written.
- **Dry run first, always.** `okf_repair.py --dry-run` and
  `repair_okf_compliance.py` (default is dry-run) both support this.
- **Git is not the rollback.** These files are largely untracked. A
  filesystem backup, not a commit, is the rollback path.
- **One vault at a time.** Active Wiki and Oracle have different schemas and
  different blast radii. Never in the same pass.
- **Verify after every batch**, not once at the end.

---

## 6. The recommended plan

### Phase 0 — Establish the baseline (no writes)

1. Full backup: `tar` the Active Wiki and the Oracle vault, with a
   timestamp, to scratch. **Verify the archive is readable and complete
   before proceeding.** Record file counts.
2. Re-run `okf_lint.py --check --json` and `verify_okf_index.py` and commit
   both reports into the repo. That report is the acceptance criterion for
   every later phase.
3. Snapshot per-file: hash + frontmatter + line count for all 2,559 files.
   This is the "did we change something we should not have" oracle.

**Gate:** a dry-run manifest exists and the backup restores.

### Phase 1 — Fix the checkers before fixing the content

This is the phase people skip, and it is why the count of 3,480 is
untrustworthy today.

4. `link_unresolvable` needs to distinguish:
   - a link to a page that genuinely does not exist → **broken, real**
   - a link to a page that exists under a different path/alias/`id:` →
     **resolver bug, not a content bug**
   - a citation or URL in `[[...]]` → **syntax bug in the source file**
   - a documentation word (`wiki`, `wikilinks`, `index`) → **false positive**
   - a section reference (`§N`) → **false positive**
5. Report each of those as a *different class* with a different severity, so
   that "3,480 broken links" stops meaning one thing.
6. Add a **negative test** for the resolver: known-good links must resolve,
   and the known false positives must not be counted. A checker that cannot
   fail tells you nothing — lesson 9.

**Gate:** the false-positive count is zero and known-good links still pass.

### Phase 2 — The mechanical bulk pass (script, no agent)

Only the classes already marked auto-fixable, and only frontmatter/link
syntax:

- `bad_okf_version` (197) → `okf_version: "0.2"`
- `type_not_canonical` (1633) → map to the allowed list
- `status_not_canonical` (151) → map to the allowed list
- `missing_front_matter` (143) → add the required block, inferring
  `type`/`status` from content, with `generated.by` recorded honestly
- `missing_required` (190) → add the absent key
- `link_index_suffix` (10), `link_case_wrong` (8) → rewrite the link target

Run through `okf_lint.py --fix` and `okf_repair.py --dry-run` first.
Back up before `--apply`.

**Verification after this phase:** findings must drop by ~2,332 and the
file hash snapshot must show **no body-text change on any file**.

### Phase 3 — Citations in wikilink syntax (script, narrow)

The 45 `[[arXiv ...]]` cases and the 10 URL cases are a mechanical
transformation: convert to the correct citation form, preserve the
reference. These are in generated `frontier-research-ontology-roundNN-*.md`
files, and the generator that produced them should be fixed too or the
files will regenerate wrong on the next run.

**Gate:** no `[[arXiv` remains; the underlying references are unchanged.

### Phase 4 — Semantic work (agent, one file at a time, NOT parallel)

Everything the linter refuses to auto-fix:

- `invalid_type` (8), `invalid_status` (2) — the value is wrong, not
  misspelled. A human decides what it *should* be.
- `invalid_confidence` (225) — a confidence value is a claim. Deciding it
  requires reading the page.
- `numeric_citation_marker` (689) — needs the actual reference resolved.
- genuinely broken `[[page]]` links (a subset of the 3,314) — for each,
  decide: does the page exist elsewhere? should the link be created, retargeted
  by path, or removed as meaningless?

**This is the work that must not be parallelised and must not be scripted.**
See §7.

### Phase 5 — Backlinks and index rebuild

`wikilinks: []` in frontmatter exists for graph tooling and backlinks.
Once links are correct, regenerate the index and rebuild graphify for both
vaults. The Oracle side currently has 157 `missing-title` and 233
directories with no index entry.

**Gate:** `verify_okf_index.py` reports zero issues for both vaults.

### Phase 6 — Make it converge

7. Wire `okf_lint.py --check` as a **pre-write gate** and a daily cron, the
   way the staleness watchdog works — empty output when clean, non-zero exit
   when not. A wiki that drifts back to 6,736 findings is not "done", it is
   "done until next week".
8. A **new-page template** so a page is born compliant: required frontmatter
   in the skeleton, lint clean by construction.
9. Record the conventions as one canonical document and link it from both
   vaults' `SCHEMA.md`.

---

## 7. Why not each approach — the direct answer

### "You go through them one by one"

**Rejected as the primary method.** 2,332 of the 6,736 findings are a
mechanical mapping with a deterministic correct answer. Doing those by hand
means ~2,300 opportunities to introduce a typo into a knowledge file, and it
burns the attention that the 4,404 report-only findings actually need.

It is also slow enough that it will not get finished, and a half-finished
remediation across two vaults is worse than a clean plan.

**But** it is exactly right for Phase 4.

### "Write a script and do it in bulk"

**Rejected as the primary method, and this is the one that repeats the
original mistake.** A bulk script that cannot tell a broken link from a
citation in `[[...]]` will "fix" all 3,480. At least 166 of those are
citations and documentation words, and a large part of the remaining 3,314
are pages that exist under a different path. A script that rewrites those
either destroys real references or manufactures links to pages that were
never missing. The measurement in §2.1 is the proof: the number that looks
like the biggest problem is mostly a measurement bug.

The overwrite risk is concrete. The 419-orphan episode happened because a
count was read as a verdict. A bulk fixer repeats that at 6,736 scale.

**But** it is exactly right for Phase 2 and Phase 3, because those classes
are already marked auto-fixable by a tool that distinguishes them from the
rest.

### "Let a subagent spring up"

**Rejected, and it is the most dangerous of the three.** The reason this
must not happen: a subagent will not have the history in §4. It will not
know that 161 "orphans" were real documents, that 51 "duplicates" were
different, that a fetch failure is not a refutation, or that a delete did not
self-clean. Every one of those was a case where the absence of evidence was
read as evidence of absence, and every one is invisible without the history.

Subagents are also how you get two agents writing the same file
concurrently, which is how you get a half-merged frontmatter block.

**The right use of a subagent:** bounded, read-only investigation of a
specific class — "find every `[[arXiv ...]]` and report the file and line,
change nothing". That is a task with a verifiable return and no write risk.

**The wrong use:** "go fix the wiki". No scope, no schema, no history.

### What to actually do

**A script for the mechanical, an agent for the semantic, a gate between
them, and never both touching the same class.** Specifically:

- Phase 1–3: scripts, dry-run first, hash-verified.
- Phase 4: one agent, one file at a time, sequentially, with the schema and
  the §4 history in its context.
- A fresh chat per vault if the work runs long, since this is exactly the
  kind of task that exhausts a context window mid-file.

---

## 8. The context a new agent needs

To do this without repeating the twelve failures:

1. This document.
2. `schemas/SCHEMA.md` and `schemas/okf-schema.yaml`, in full.
3. The two baseline reports committed in Phase 0.
4. §4, the history table. **Non-negotiable — this is the part that prevents
   the repeats.**
5. `docs/ORPHAN-PAGES-TODO.md` — the 161/192/66 breakdown, including that
   51 of the 66 are *not* duplicates and the disk copy is richer.
6. `docs/CITATION-AUDIT.md` — 8 of 8 DOIs broken, 3 resolving to
   completely unrelated papers. The lesson: a DOI that resolves to the wrong
   paper is worse than no DOI.
7. The measured state in §2, re-verified on the day — not trusted from this
   document, because it will drift.

Standing constraints that apply throughout:

- No deletion of wiki content. No expiry.
- No body-text rewrites.
- RFC 3339 UTC timestamps only.
- Check `git status` before every commit; three specific files are off-limits.
- Unique log/output paths — no shared files between concurrent runners.
- Verify by querying the live system, not by reading configuration.

---

## 9. Open questions for the user

1. **Phase 4 scale.** 4,404 report-only findings, of which 689 are citation
   markers. Is the citation work in scope, or is that a separate pass?
2. **Broken links that point at pages that do not exist.** Three legitimate
   outcomes: create the page, retarget the link, or leave it broken and
   recorded. Which does the user prefer as default? My recommendation is
   *record it and leave it* — creating 3,000 stub pages would be a knowledge
   base full of noise.
3. **Confidence and epistemic labels.** 225 `invalid_confidence` values need
   a human claim per page. Does the user want to set these, or should they
   be derived from verification evidence where it exists and left blank
   otherwise?
4. ~~**Should the two vaults converge to one schema, or stay distinct?**~~
   **ANSWERED 2026-09-28: identical.** The owner directed that both vaults use
   the same exact schema, because Active Wiki content flows to Oracle and a
   lower-fidelity version on the way would become the long-term hold. The
   `SCHEMA_ORACLE.md` that implied a deliberate difference was byte-identical
   to `SCHEMA.md` and has been deleted. Remaining work: correct
   `~/.hermes/oracle/brain/SCHEMA.md` in place, since it is the only schema
   that vault has and it currently differs.
