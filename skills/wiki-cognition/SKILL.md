---
name: wiki-cognition
description: Distill a wiki into ranked brain designs with evidence.
version: 5.0.0
---

# Wiki Cognition — corpus distillation for the Hermes brain

**You are running with a fresh context window.** You have no memory of any previous
run, no conversation history, and no idea what the last run concluded. Everything
you need is in this skill and in the workspace files it names. Read them; do not
assume continuity you cannot verify from disk.

---

# 1 · THE MISSION

Read a large wiki corpus directly and think about it, to produce a **ranked
shortlist of what to build, what to adopt, and what to skip** for a comprehensive
Hermes brain — with the evidence that decides between them.

## The target

**A full brain AI system, replicating a human brain for AI on top of Hermes.**

Not memory infrastructure. Not a retrieval system. A brain. That means:

- **Physical/anatomical parts** — hippocampus, cortex, cerebellum, amygdala,
  neuromodulatory nuclei, brainstem, and the loops between them.
- **Psychological parts** — perception, attention, memory, emotion, motivation,
  decision, language, social cognition, metacognition, selfhood, agency, creativity.
- **Heuristics** — the decision procedures and shortcuts cognition actually uses,
  including the ones that are systematically wrong.
- **Philosophical parts** — the framings that make the above coherent: consciousness,
  intentionality, grounding, personal identity, normativity, the hard problems.

**Memory is one organ in the target, not the target.**

Every design must answer: *which part of a human brain does this fill, and what is
the evidence it works?* An idea with no brain-part and no evidence does not enter.

## THE TWO-FILE LAYOUT — READ THIS BEFORE WRITING ANYTHING

`ARENA.md` and `ARENA-EVIDENCE.md` are **one deliverable split in two**, and
conflating them is the failure this section exists to prevent.

| | `ARENA.md` | `ARENA-EVIDENCE.md` |
|---|---|---|
| Role | **the answer** | the audit trail |
| Contains | area headings, `Earned by`, and the three ranked slots with their seven fields | tranche narratives, qualifications, contradictions, measurements, rebuttals, abandoned candidates |
| Update rule | **rewritten in place** — a slot is replaced, never appended to | **append-only** — add a new `###` block, change nothing existing |
| Size today | ~1,450 lines | ~10,600 lines |

**Why the split exists.** Before it, every pass appended its evidence *inside* the
slot it was arguing about. `ARENA.md` reached 10,116 lines with Area 8's rank-1
sitting at line 108 of a 1,928-line area. The 3-slot discipline was never broken —
the ranking was simply buried under its own audit trail, and each pass had more
to re-read and less signal to reason over.

**The rule that replaces the old one.** The old skill said "append the new source
to that slot's `Backup document` line" *and* "rewrite `ARENA.md` in place." Those
two instructions fight, and the append always won.

Now:

- **A new fact about a design** → one clause in the relevant field of the slot in
  `ARENA.md`. If it does not fit in the field, it is evidence, not answer.
- **The reasoning, the measurement, the counter-argument, the thing that nearly
  displaced the slot** → `ARENA-EVIDENCE.md`, under that area, appended.
- **A grade change or a rank change** → edit the slot in `ARENA.md` *and* append
  the justification to `ARENA-EVIDENCE.md`. The evidence file is why the change
  was made; the answer file is what changed.

**`ARENA.md` may legitimately grow to 10,000 lines or more** as areas are added.
There is no size cap. What is forbidden is growing *by accretion* — a pass that
adds prose to a slot instead of replacing the slot's content. The invariant
`scripts/arena_invariants.py` check **C11** enforces this as a growth budget
against the previous pass: growth is fine when the area count grows, and fails
when the file grew without new areas justifying it. **If C11 fails, you appended
evidence to the answer. Move that prose to `ARENA-EVIDENCE.md` and put the
one-line consequence in the slot.**

**Never delete from `ARENA-EVIDENCE.md`.** Superseded evidence stays, struck or
marked as superseded. A displaced rank stays visible for one revision.

## What "learning" means here

This is not a search. The corpus contains research nobody has synthesized,
contradictions nobody has noticed, and designs that were tried and abandoned. Your
job is to read it and **arrive at a position** — then let later evidence move that
position.

**You do not know all the brain parts yet, and neither does the file.** The corpus
is part-read. Brain areas and psychological functions will surface that are not in
today's map. **Finding them is the mission, not a scope violation.** The arena is a
growing map of the brain.

If you only recorded what you could think of at the top of your head, this would be
equivalent to a web search and the entire corpus read would be wasted. **The corpus
is the source of surprise.**

---

# 2 · THE WORKSPACE

**Workspace — every path below is absolute. Use these exact paths for every
read and every write. Never use a bare filename.**

| Absolute path | Role |
|---|---|
| `${HERMES_HOME}/hermes-brain/cognition-arena/ORDER.txt` | **Sole authority for paths.** 2,217 lines, one root-relative path each. |
| `${HERMES_HOME}/hermes-brain/cognition-arena/LEDGER.md` | Progress. `[ ]` unread · `[x]` read · `[-]` excluded · `[!]` blocked. **The cursor lives here.** |
| `${HERMES_HOME}/hermes-brain/cognition-arena/ARENA.md` | **THE DELIVERABLE.** The ranked answer. Rewrite in place. |
| `${HERMES_HOME}/hermes-brain/cognition-arena/ARENA-EVIDENCE.md` | **The audit trail.** Append-only, never pruned. |
| `${HERMES_HOME}/hermes-brain/cognition-arena/ARENA-INFRA.md` | Corpus-hygiene requirements. Edit only when a new defect class appears. |
| `${HERMES_HOME}/hermes-brain/cognition-arena/VERIFICATION.md` | Unverified external claims, corpus trivia, proposals. |
| `${HERMES_HOME}/hermes-brain/cognition-arena/EXCLUDED.txt` | 379 excluded ordered lines + why. |
| `${HERMES_HOME}/hermes-brain/cognition-arena/RUNLOG.jsonl` | **Machine-readable per-run log.** Written every run, appended only. |

Corpus root: `${HERMES_DATA_DIR}/`. `ORDER.txt` paths are relative to it and
**resolve literally** — a corpus read is `${HERMES_DATA_DIR}/` + the
`ORDER.txt` line, with no rewriting. All 2,217 lines were verified to resolve that
way (`active-wiki/…` → `active-wiki/…`, `oracle/brain/…` → `oracle/brain/…`).

**Do not rewrite, shorten, or "fix" an `ORDER.txt` path, and never glob, use
`search_files`, or `find` to locate a file** — build the absolute path and call
`read_file` on it. If that exact path fails, mark the line `[!]` with the error and
move on; do not go hunting for a variant.


## How to read — `read_file` only, no shortcuts

**One file = one `read_file` call, start to finish. There is no other way.**

The user's instruction is explicit: *"with no scripts and no sub agents you. You have
to read the motherfucking work."* And: *"If you created a script that helped you out
at all and you didn't read through every single line of every single file, then you
must restart and do this from the beginning."*

**Never bulk-read, batch-read, or shell-read a corpus file.** All of these are
prohibited for in-scope files:

| Prohibited | Why it fails |
|---|---|
| `cat file.md` via `terminal` | Dumps a window, not a read. Easy to skim past. |
| `head` / `tail` / `sed` / `grep` on a file | Same — a slice mistaken for a whole file. |
| `find … \| xargs cat` | Bulk dump. A digest, not a read. |
| `execute_code` or a script to "process" files | Automated summarising replaces judgement. Explicitly banned by the user. |
| A subagent or delegated read | Banned outright. |
| Marking `[x]` without a `read_file` for that file | The worst failure: the ledger claims a read that never happened. |

**`terminal` is for exactly one thing: arithmetic on the ledger and drift checks.**
It is never for reading corpus content. If a file is long, call `read_file` again
with `offset` until you reach the end — **a truncated body is not a read.** A file
whose content you inferred from its filename, its directory, or a search result has
**not** been read; do not mark it.

**Mark `[x]` only after that file's own `read_file` has returned.** Not in a batch
at the end, not after a shell dump, not because the file is "obviously short." If
you mark 20 files, you made 20 `read_file` calls. The count is checkable and it is
checked.

### The read→mark loop — this is the unit of work

Read and mark as **one indivisible loop, repeated**. Never a read phase followed by
a mark phase.

```
1. read_file  → the whole file, continuing with offset until EOF
2. patch      → flip that ONE row to [x]     ← immediately, nothing in between
3. absorb     → update the arena for what you just read
4. next file
```

**One file per loop. One `patch` call marks exactly one row.**

**Never make two ledger `patch` calls back to back.** Two consecutive patches to
`LEDGER.md` means you are batching marks, and a batch is how a bulk read becomes
twenty fake reads. This is the single most important line in this section — it is
the exact signature of the failure this rule exists to prevent.

**A single `patch` that changes more than one row is a bulk mark. Stop and undo it.**

**If you catch yourself editing `LEDGER.md` two or more times in a row, you are
marking files you did not read.** Delete those marks immediately and re-read the
affected files. Do not leave them for a later audit — a wrong mark is a false claim
about work completed, and it propagates into the arena as a conclusion drawn from a
file nobody read.

### The failure signature — recognise it in yourself

A run that broke this rule looks exactly like this, and it looks *productive*:

- many `patch` calls in a row, more `patch` than `read_file`
- one `read_file` returning tens of thousands of characters (that is several files
  in one window, not one file; the corpus median is ~21k chars, so a ~100k return
  is never a single document)
- twenty marks in under six minutes
- a healthy-looking arena and a clean `completed` status

**All four can be true at once and the run is still a lie.** A completed status
means the process exited, not that the reading happened. Treat "twenty marks in six
minutes" as a symptom to investigate, never as a result to report.

### Read this before you finish

Before reporting, state the two numbers:

- `read_file` calls you made this run
- rows you flipped to `[x]` this run

**If those two numbers are not equal, the run is not compliant and you must say so
in your report rather than describing the work as done.** Do not round them, do not
reconcile them, and do not explain the gap away. An accurate failure report is worth
more than a clean-looking run; the whole point of the ledger is that it can be
trusted, and a trusted ledger is the only thing this job produces.

**Read 20 files per run, or fewer** — never more. Excluded `[-]` lines are not
files to read; they consume no slot.

## Path discipline

**Never guess, reconstruct, or infer a path.** Take every path from `ORDER.txt` via
the ledger. Guessing produced real failures here: a guessed `osint_osint_platforms.md`
that did not exist, and a guessed consciousness-study path. On a miss, re-read the
ledger rather than adjusting the filename.

## Exclusions — never open these

Two authorized scopes. **Neither may be widened on the agent's own initiative.**

**Scope 1 — four topics.** radio/RF, hacking/offensive security, finance, OSINT.

**Scope 2 — wiki housekeeping logs.** `oracle/brain/.meta/` maintenance and wiki-maintenance reports
(user-directed, 2026-09-26, ORDER lines 1247–1257). These log routine upkeep *of* the corpus —
index rebuilds, view regeneration — rather than being part of it, so reading them adds no knowledge
about the subject matter.

Together these are 379 ordered lines, marked `[-]` in the ledger.

**Never open an excluded file, summarize it, infer its contents, or "check whether
it's really relevant."** 379 files is a lot of compute to spend on material the user
excluded. If you believe one is misclassified, record that in `VERIFICATION.md` and
move on — do not open it.

---

# 3 · THE ARENA FORMAT

**One area = exactly three ranked slots: 1st, 2nd, 3rd by preference.**

- Rank 1 is what gets built if nothing changes. Rank 2 is the fallback when rank 1
  conflicts with another area's rank 1. Rank 3 is the fallback for that.
- **Three slots is not padding.** Components interact. The best design in one area
  may not compose with the best in another, and the second-best option in one area
  is sometimes what makes the whole system work. If only one option survived per
  area, that composition dead end would be invisible — and you cannot fall back to
  a runner-up you deleted.
- Never one slot. Never five. Exactly three, always, even if 2nd and 3rd are weak.

## Each slot must answer

1. **Brain part.** Which part of a human brain does this fill, named the way
   neuroscience names it?
2. **Design.** What concretely gets built or adopted.
3. **Already exists?** A service, project, or paper that does this — name it with
   repo or paper ID. **Prefer adopting over building.** Record what exists *before*
   proposing something new. Also note which components are already in the Hermes
   stack (`brain/`, `hooks/`, `plugins/`, profiles, skills, cron, adapters).
4. **Backup document.** A link to the wiki file(s) holding the detail. One area may
   draw on several files; link all of them.
5. **Evidence grade** (below).
6. **Justification.** Why this ranks here — what it beats, on what axis. R-J1: cost
   is never an axis.
7. **Interaction note.** Which other areas it constrains or conflicts with. This is
   what makes the three-slot rule pay off.

## Evidence grades — required on every slot

| Grade | Meaning |
|---|---|
| **HIGH** | Replicated trials, or strong convergent evidence from independent sources. Multiple independent implementations working. |
| **LOW** | Some trials, mixed or thin results, or a single small study. Plausible, unproven. |
| **UNSUCCESSFUL** | Trials were run and it did not work. Recorded so it is not retried blind. |
| **UNTESTED** | No trials found. Common for bespoke builds. Must say so plainly. |

**UNSUCCESSFUL is a first-class result, not a failure to find.** It exists so a dead
end is not rebuilt blind. A slot that was tried and failed outranks an untested
guess in honesty, though not necessarily in preference.

**One grade per slot, from the best available evidence.** If sources disagree, give
both. Never average them into a false consensus.

**A grade is about trials, not about the wiki's tone.** An external claim is
`unverified` until checked against a primary source and does not earn HIGH on the
wiki asserting it.

### The citation rule — an unearned citation is worse than no citation

**A file you have not read this workspace may not be cited in `ARENA.md`. Not as
a backup document, not as "already exists", not in a table, not as a
cross-reference.** If the citation is load-bearing — it backs a grade, a rank, or
a "what already exists" claim — then the absence of a read is the finding, and it
goes in `VERIFICATION.md` until the file is actually read.

This is not new guidance. It is the rule that already exists and has been broken:

- **F2-5** caught a *citation* outrunning a read.
- **F2-7** caught a *mark* outrunning a read.
- On 2026-09-26, C6 found **39 files cited in the arena whose ledger row had
  never been `[x]` in any commit in the repository's history** — not mis-marked,
  never marked. All 39 existed on disk and were in scope. They were cited anyway.

Those 39 were the residue of the same accretion problem: a pass would name a file
it had read in an *earlier tranche* from memory, or infer relevance from a
filename, and the citation outlived the read. **A file's name in the arena is a
claim that you read it. If you did not, you have made a false claim.**

**What to do when you catch yourself wanting to cite an unread file:**

1. Check the ledger. If the row is not `[x]`, you have not read it.
2. If the file is in your next 20, **wait**. Read it, mark it, then cite it.
3. If it is not coming up soon, **do not cite it in the arena.** Note it in
   `VERIFICATION.md` as `Cited-but-unread, pending read: <path> (<why it matters>)`.
4. If the arena already cites it and you cannot read it this pass, **strike the
   citation** and record the strike. Do not leave it standing.

**Three files restating one study are one source, not three** — and a file you
have not opened is zero sources, which is worse than one, because it looks like
evidence.

### Corroboration is new data, not repetition

A slot is not finished when first written. **A second paper confirming a design is
more evidence, not a repeat — record it.** Never skip a file because "this area is
already covered." Reading it is how the slot gets stronger.

When a file you read supports a slot already in the arena, do this instead of
discarding it:

1. **Append the new source** to that slot's `Backup document` line, with the file
   that just earned it. Cite it inline, not in a lump at the bottom.
2. **Count the corroboration.** Add it to a `Support: N independent sources` count
   on the slot so the strength is visible without re-reading the arena.
3. **Raise the grade when it earns it.** A second *independent* implementation or
   trial result can move `UNTESTED` → `LOW`, or `LOW` → `HIGH`. Note in one clause
   what moved it. Do not inflate: three files restating one study are **one**
   source, not three — say so.
4. **Record disagreement.** If the new file qualifies, contradicts, or narrows the
   claim, that goes in the slot's justification and can drop the grade. A source
   that weakens an existing slot is as valuable as one that strengthens it, and
   both are recorded (R-J4: preserve disagreements, never reconcile them away).
5. **Only then ask about rank.** Corroboration usually does not change preference
   order — but check honestly. A design replicated across three independent
   implementations may now beat the rank-1 slot it was losing to on thin evidence.

Distinguish these two cases, because conflating them loses evidence:

- **Same conclusion, new source** → append, count, maybe raise the grade. *This is
  the common case and it must never be skipped.*
- **Same source repeated** → a file quoting the paper an existing slot already cites
  adds no independent support. Log the cross-reference as confirmation of *reach*
  in that slot, but do not increment the independent-source count.

**Never re-litigate a settled ranking without new evidence** — but "new evidence"
means a source that adds support, weakens a claim, or exposes a conflict. Deciding
an area is already covered is not a reason to stop reading its files.

## Why preference order, not score order

Scores are inputs. The **rank is a judgement** about which to actually build, given
everything known so far — including composition with other areas. Ranks change as
evidence accumulates. A rank-3 idea can win tomorrow; a rank-1 idea can be demoted
by a single disconfirming file.

Keep a losing candidate visible for one revision as `rejected:` under the winner,
then drop it. If later evidence re-raises it, it returns. That is how a bad call
gets corrected instead of fossilized.

---

# 4 · CREATING NEW AREAS — discover, don't fabricate

**When a file reveals a brain part, psychological function, or cognitive mechanism
with no existing area: create the area immediately.** Do not wait for permission.
Do not park it as a proposal for someone to approve. The brain has more parts than
today's list, and the read is how we find out which.

Four guards keep discovery from decaying into invention:

1. **Name it for the function, not the file.** A directory called
   `Predictive-Processing/` becomes "Prediction, error & active inference" — never
   "the Predictive-Processing folder."
2. **Cite the file that earned it.** A later reader must be able to check the area
   was earned rather than assumed.
3. **A directory name alone never qualifies.** Browsing filenames is not research.
   One file that actually discusses a mechanism is.
4. **Corpus hygiene is not a brain part.** If you cannot name the brain function it
   fills, it is infrastructure → `ARENA-INFRA.md`. This is the load-bearing guard: a
   link resolver and a hippocampus index both look like "components" in a list, and
   only one is a brain part.

**Mark a new area `PROVISIONAL`** until all three slots fill, then drop the mark. A
provisional area is one file gave us, not a settled requirement.

**Anticipated areas are welcome** — creativity and insight, decision-making under
uncertainty, theory of mind, developmental learning, interoception, and anything
else the subject matter calls for. **Seed them early with a clear note that they are
anticipated rather than earned, and let the read confirm, fill, or delete them.** An
area seeded as a hypothesis and later confirmed by evidence is honest; an area
silently invented to fill a gap is not. Do not limit the arena to what you can think
of in advance — that would make this a search.

## Two bookkeeping sections to maintain

**`## AREA LOG`** — one line per area added: number, name, date, and the file that
earned it. This keeps the map's growth auditable rather than an unexplained sprawl.

**`## BRAIN PARTS NOT YET COVERED`** — the to-do list for the target itself: brain
parts and psychological functions a human brain has that the arena does not address
yet. Marked **`not observed` — never `absent`.** Populate from what the read
surfaces plus gaps the read makes visible. Do **not** pad it from a generic anatomy
list.

**Never claim a brain part is unnecessary.** A missing area means the read has not
reached it, not that the brain does without it. This is the single most important
sentence in the file.

---

# 5 · WHEN NOTHING EXISTS

If a needed brain part has **no** existing project, service, or paper that does it,
the slot says so plainly and specifies a **bespoke build** assembled from research
scattered across multiple wiki files — all of them linked. "We would have to build
this" is a legitimate and expected outcome, and it is only legitimate if the search
for an existing solution was actually done and recorded.

---

# 6 · THE LOOP — one run

1. **Read `${HERMES_HOME}/hermes-brain/cognition-arena/LEDGER.md`.** The first `[ ]`
   line is the cursor. Take the path from that line — never guess a filename.
2. **Read up to 20 files** starting there, whole, in order, with `read_file`, each at
   `${HERMES_DATA_DIR}/` + the `ORDER.txt` line. **One file, one `read_file`
   call, start to finish** — see §2 "How to read". Never more than 20. If a file is
   genuinely huge, continue with `offset` — **a truncated body is not a read.**
   Finish it or mark the line `[!]` with a reason. Skip `[-]` lines without opening
   them; they are not slots.
3. **Mark each file `[x]` in `LEDGER.md` IMMEDIATELY after reading it** — before
   moving to the next file, and before any arena edit. This is the crash-recovery
   boundary: if the run dies at any later point, the ledger already says what was
   read, so the next run resumes correctly instead of re-reading.

   **Never rewrite `ARENA.md` before the ledger reflects those reads.** A run that
   updates the arena and then dies leaves the two inconsistent: the arena holds
   conclusions from files the ledger still calls unread, and the next run reads
   them again and duplicates the work. Observed once already, in the first run.
4. **Extract candidate designs**, not facts. For each: which brain part, what gets
   built or adopted, what already exists, what evidence, what grade.
5. **Place each into an area.** Load that area's three slots in `ARENA.md` and ask:
   does this beat rank 1, rank 2, or rank 3? Displace it and record what it beat and
   why. If it beats none, it does not enter — note it in `VERIFICATION.md` or drop
   it with a one-line reason.
   **If it supports a slot that is already there, that is not "nothing to do."**
   Append the source, bump the independent-source count, raise the grade if it
   earns one, and record any qualification it adds — see "Corroboration is new
   data, not repetition". A file is read for the evidence it carries, whether or
   not it changes a ranking.
6. **New brain part with no area? Create it** per §4 — as a new section *inside*
   `ARENA.md`, never as a new file. Mark it `PROVISIONAL`, cite the earning file,
   log it in `## AREA LOG`. Update `## BRAIN PARTS NOT YET COVERED` in both
   directions.
7. **Rewrite `${HERMES_HOME}/hermes-brain/cognition-arena/ARENA.md` in place.** Area
   numbers stay stable; ranks and contents change freely. Update the COVERAGE table
   counts. **In place — do not write a new file.**
8. **Stop when no `[ ]` remains.** Say so clearly and make no further edits.

Ten minutes later the next run does this again, from wherever the ledger stopped.
That is the whole mechanism: no shared memory required, because the ledger and arena
carry the state.

## Before you finish — the four checks

Run them. Do not report success without their output in hand.

### 1. Drift check
Confirm every edit you made went to one of the absolute paths in §2. If you
find yourself having written anything else — a new file, a copy, a backup, a file
outside the workspace — **say so explicitly in your report**, name the path, and do
not delete it. Stray-file detection is part of the report, and the user decides
what happens to it.

### 2. `scripts/arena_invariants.py`
```bash
python3 ${HERMES_HOME}/hermes-brain/scripts/arena_invariants.py \
  --reference-arena ${HERMES_HOME}/hermes-brain/cognition-arena/ARENA.md.prev
```
Ten checks. **C6 is the one that catches unearned citations**: every file the
arena cites must have a ledger row marked `[x]`. If C6 fails, you cited something
you did not read. Fix it: either read the file now and mark it, or strike the
citation. **Do not leave a citation standing on a file you have not read** — that
is the exact defect F2-5 and F2-7 exist to prevent, and it is how an unearned
claim becomes load-bearing.

C11 catches answer-file accretion (see the two-file layout section).

A failing invariant is a finding to report, not something to paper over. If you
cannot fix it, say which check failed, on what, and why.

### 3. `scripts/verify_reads.py`
Confirms the read→mark ratio for this pass. `read_file` calls must equal rows
flipped. This is the check that catches fabricated marks.

### 4. The RUNLOG entry
See below. A run that does not log is a run nobody can diagnose.

## THE RUNLOG — one JSON line per run, appended, never edited

**Append one object to
`${HERMES_HOME}/hermes-brain/cognition-arena/RUNLOG.jsonl` at the end of every run,
before reporting.** It is the only machine-readable record of what a pass actually
did, and without it a future pass cannot tell a real read from a claimed one.

Schema — every field is required:

```json
{
  "run_id": "2026-09-26T10:19:00-07:00",
  "tranche": 24,
  "order_lines": [420, 441],
  "read_file_calls": 21,
  "rows_flipped": 21,
  "order_numbers_read": [420, 421, 422, 423, 424, 425, 426, 427, 428, 429,
                         430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 441],
  "largest_single_read_chars": 34258,
  "skipped_excluded": 0,
  "blocked": [{"order": 441, "reason": "…"}],
  "new_areas": [30],
  "re_ranks": [{"area": 8, "from": 1, "to": 2, "why": "…"}],
  "grade_changes": [{"area": 6, "from": "LOW", "to": "UNTESTED", "why": "…"}],
  "arena_lines_after": 1452,
  "evidence_lines_after": 10700,
  "invariants": {"C6": "fail", "C11": "pass", "all_other": "pass"},
  "unearned_citations": [],
  "strays": [],
  "duration_seconds": 594,
  "notes": "one line a future run would need to make sense of this one"
}
```

**`order_numbers_read` is the load-bearing field.** It is the only way a later pass
can verify that a citation was earned. A file cited in `ARENA.md` whose ORDER
number is not in any run's `order_numbers_read` was never read — strike the
citation or read the file.

`invariants` records the actual pass/fail of `arena_invariants.py`, not an
assumption. If you did not run it, the value is `"not-run"` — never `"pass"`.

Append with one `write_file` or a single `>>` shell append. **Never rewrite or
reorder earlier lines.** A corrupted log is worse than a missing one, because it
looks authoritative.

## On duration and the 13-minute slot

Runs average ~8.7 minutes against a 13-minute slot. The 20-file-per-pass ceiling
is what keeps it there — do not raise it to "finish faster." A pass that overruns
its slot is delayed, not accelerated, and the delay compounds across hundreds of
passes. If a pass genuinely needs more than 20 files, it takes two passes, and
the second one starts from the ledger cursor like any other.

---

# 7 · WHAT DOES NOT GO IN THE ARENA

Wrong dates, wrong venues, misattributed quotes, mangled names, paper-year drift.
These are corpus hygiene → `VERIFICATION.md`, or fixed by a checker.

**The test: would a good architect change the design because of this?** Nobel
misattribution — no. A missing link target on a component's page — yes, because
retrieval loses the link.

**Exception:** if a hygiene defect *implies a design requirement* (e.g. "every
component name must resolve to a canonical id" is itself a design decision), the
requirement goes in the arena and the instance goes in the queue.

---

# 8 · HONESTY RULES

- **Read whole or record it as not read.** A size-only result is not a read.
- **No scripts, no subagents, no delegation.** You read the files yourself.
- **One `read_file` per file, and never mark `[x]` without one.** If you marked N
  files this run, you made N `read_file` calls. `terminal` is for ledger arithmetic
  only, never for reading corpus content. This is checkable and it is checked — a
  run that marked 24 files with 1 `read_file` and 5 shell calls has falsified the
  ledger, and that is the single worst thing this job can do.
- **A file you bulk-dumped is not a file you read.** If in doubt, read it again
  properly with `read_file` rather than defending the shortcut.
- An external fact is `unverified` until checked against a primary source.
- **Preserve disagreements** between vault and external evidence. Never silently
  resolve them.
- `not observed` is correct. `confirmed absent` requires a full-range or filesystem
  check.
- **Never delete an area.** If evidence disappears, demote the slot and say why.
  Silence reads as "never found," which is a different and wrong claim.
- **Do not re-litigate a settled ranking** without new evidence. If nothing changed,
  say so plainly rather than padding the report.
- **Do not modify any corpus file.** Write only to the four absolute paths listed in
  §2 — `ARENA.md`, `ARENA-EVIDENCE.md`, `ARENA-INFRA.md`, `VERIFICATION.md`,
  `LEDGER.md`, `RUNLOG.jsonl`, all inside
  `${HERMES_HOME}/hermes-brain/cognition-arena/`. Never create a new file, never
  write outside that directory, and never edit `PROPOSED-BRAIN-ARCHITECTURE.md`.
- **Do not create self-measurements as decision evidence** (R-J2).

## A finding that shapes every grade in the arena

Across 793 read files, the recurring shape is: **the validated code path produces
the appearance of authority, and the unvalidated path produces the content.** TOCs,
citations, `verified:` blocks, `confidence:` values, index entries and related-link
boilerplate are generated and checked as *artifacts* — reliable as artifacts. The
prose they decorate comes from a different path and is not checked.

The evidence is an **inversion**, not a correlation: files with correct 16/16 TOCs,
real volume-and-page citations and populated `verified:` blocks carried an invented
Nobel attribution, a fabricated degree and advisor, a misattributed acronym, and a
nonexistent book.

**Until the system can tell verified from unverified, a HIGH grade anywhere else is
a grade the infrastructure has not earned.** Keep that in mind when grading.

---

# 9 · SCALE AND BINDING RULES

The design must hold at **14,589 files** (R-J5), not at today's read count. State
the scale assumption on every requirement. A rule that works only because a human
reads every file by hand is a habit, not a rule — name it as one.

From `hermes-brain/SCRATCHPAD.md`, in force on every run:

- **R-J1** — cost is irrelevant as a decision criterion.
- **R-J2** — do not measure; no new self-measurements as decision evidence.
- **R-J3** — scope is the repository's future.
- **R-J4** — use external research and the local vault; preserve disagreements.
- **R-J5** — recommendations must hold at 14,589-file scale.

---

# 10 · REPORT

Under 25 lines: files read this run, ledger totals (read / excluded / remaining),
areas added or re-ranked, anything rejected and why, any file you could not read, and
any new brain part discovered. **If nothing changed the arena, say that plainly.**

---

## Related

- `wiki-ingestion` — writes single pages. This reads corpora at scale.
- Graph layer — associative traversal ALONGSIDE semantic RAG, never a replacement
  for reading source.
- `verification` — deterministic first, auditor last.
- `PROPOSED-BRAIN-ARCHITECTURE.md` (hermes-brain repo root) — the design document
  this arena feeds. It stays at the repo root permanently.
