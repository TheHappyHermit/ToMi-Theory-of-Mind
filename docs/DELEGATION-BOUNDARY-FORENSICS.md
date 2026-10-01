# Delegation Boundary Forensics — children were writing, not just researching

**Date:** 2026-09-26
**Question the operator asked:** are the Online Lanes dispatching sub-agents instead of
doing the work themselves, and is that why the file system is in a mess?
**Answer:** yes to both. 452 child tasks were dispatched; 414 of them (91.6%)
received no constraint of any kind; the children made 1,074 write/patch calls
across 533 distinct paths. Root cause is not the children. It is that **no cron
prompt anywhere in this system ever told a parent it had to pass its own
constraints down.**

---

## 1. Measured, not inferred

Every number here comes from `~/.hermes/state.db`, reading the actual tool-call
arguments that were sent. Nothing is inferred from a lane's self-report.

| Measure | Value |
|---|---|
| Cron jobs that have ever dispatched a child | **3 of 50** |
| `delegate_task` calls, Online Lane A | 178 |
| `delegate_task` calls, Online Lane B | 116 |
| `delegate_task` calls, Oracle Night Research | 1 |
| Child tasks dispatched (total) | **452** |
| Child tasks that received **any** write restriction | **38 (8.4%)** |
| Child tasks that received **none** | **414 (91.6%)** |
| Dispatches that restricted `toolsets` | **0 of 297** |
| Child sessions created | 484 |

The only three jobs that hand off work are:

| Job | ID | Schedule |
|---|---|---|
| Online Lane A | `c7342bb30048` | `0 */1 * * *` |
| Online Lane B | `36d0ff501181` | `30 * * * *` |
| Oracle Night Research | `50bf431feaea` | `30 3 * * *` |

**The other 47 jobs do not delegate**, so they cannot have this defect. One of
them, `wiki-cognition` (`49280b099b12`), goes further and explicitly forbids it:
*"no `execute_code`, no script, no subagent — not for any reason."* That job is
correct as written and needs no change.

---

## 2. The root cause, stated precisely

**The parent prompt had a detailed, well-written write boundary. The child
prompt had nothing.**

The Online Lane prompt spends ~2,000 characters on a WRITE BOUNDARY: two
permitted paths, an explicit never-touch list, a backup-naming rule, an off-ramp
for findings that belong elsewhere. It is good work.

**It never mentions the word `delegate_task`, "subagent", "child", or
"dispatch" — not once.** Verified by regex over the full prompt.

That omission is the entire bug. `delegate_task` spawns a fresh session with a
fresh context. Per the tool's own contract: *"Children know nothing of this
conversation: pass everything needed via `context`."* So a child receives the
`context` string and nothing else. Every rule, boundary, off-ramp, and
verification discipline in the parent prompt was **structurally incapable of
reaching the child.**

The one dispatch that did carry a boundary down did so because that parent had
already been burned — its context field opens with:

> "CRITICAL WRITE BOUNDARY: You must NOT write, create, or modify ANY file
> anywhere... A previous researcher in this project wrote a file outside its
> boundary and it caused a real incident."

That parent learned the rule from an incident and wrote it into its own brief.
The system did not do it for it. **That is the definition of a missing
mechanism rather than a missing rule.**

---

## 3. What the children actually did

Tool usage across all 484 child sessions:

| Calls | Tool |
|---|---|
| 4,610 | `web_search` |
| 3,321 | `terminal` |
| 1,179 | `web_extract` |
| **668** | **`write_file`** |
| 549 | `read_file` |
| **406** | **`patch`** |
| 357 | `search_files` |

Write destinations, from the real call arguments:

| Destination | Writes | Status |
|---|---|---|
| `~/.hermes/cache/scratch/` | 734 | throwaway, but never cleaned |
| `~/.hermes/oracle/brain/research/` | 20 | on the allowlist |
| `research-agenda-brain-architecture.md` | 10 | on the allowlist |
| **`/home/operator/` (home root)** | **196** | **outside the boundary** |
| **`~/.hermes/active-wiki/`** | **21** | **outside the boundary** |

**208 stray `.md`/`.json` files** now sit in the user's home directory. Two
confirmed instances, both self-reported by the lanes that spawned them:

- `dense-retrieval-score-comparability-VERIFIED.md` — 31 KB, 11:02
- `negative-priming-agent-memory-SOURCES.md` — 22.5 KB, 11:40, described in
  Lane B's own report as *"written by Batch 145's **child**"*

And a Python verifier plus its transcript left **inside the vault research
directory** (`b134verify.py`, 05:59) — a child writing *code* into the wiki,
which is the exact tripwire the parent prompt forbids.

---

## 4. What was NOT damaged

Stating this precisely matters, because the failure was loud and the instinct
is to assume the worst.

- **The agenda is clean.** 10,673 lines, verified: zero narrative contamination.
  Every batch checked its append by prefix-checksum and byte-delta.
- **`SCRATCHPAD.md` untouched** by these children.
- **`git status` shows only `cognition-arena/*` modified** — that is the
  `wiki-cognition` job's own territory, working as designed. **No repo
  boundary violation.**
- **No forbidden zone was hit by a child**: zero writes to `ARENA*`, zero to
  `SCRATCHPAD.md`, zero to `PROPOSED-BRAIN-ARCHITECTURE.md`, zero to
  `.hermes/` runtime.

The blast radius is real but bounded: litter in the home directory and two
stray files in the vault. The **research output itself is high quality** — the
batches contain genuine, self-correcting scholarship.

---

## 5. The second failure: unverified numbers from children

Independent of the file writes, the children produced plausible numbers the
parents had to catch. This is recorded in the batches themselves:

- **Batch 143** — child reported "MaxScore AUROC is at or below chance for 5 of
  11 retrievers." The paper's own Table C.1 says **three**. The parent pulled
  the table and corrected it.
- **Batch 145** — child misattributed authorship of `2601.03543` to "Li, Y.;
  Li, Y."; that is the authorship of a different paper (`2609.10263`).
- **Batch 133** — seven child claims rejected, including one study count that
  contradicts its own abstract.
- **Batch 130** — a child's reported regime table for `2608.01619` was absent
  from the fetched abstract; numbers excluded.

The parents *are* catching this, and they document it well. But note the
ordering: **the child had already written its files by the time the parent
checked the claims.** Constraint-inheritance was the defect that made both
failures possible.

---

## 6. The fix applied

Three edits, all prompt-level, no core changes:

1. **Online Lane A** and **Online Lane B** — added a `WHEN YOU DISPATCH A
   CHILD` section mandating that every child `context` opens with a verbatim
   boundary block, that `toolsets` be set rather than passed as `null`, and
   that every run report its dispatch count.

2. **Oracle Night Research** — same treatment, plus an evidence-discipline
   clause, because its one recorded dispatch had neither a boundary nor a
   source-verification requirement.

3. **`oracle-wiki-research` skill** — this was the worst offender. It
   instructed children to **write `temp-Subject-R1.md` files and then
   `rm -f temp-*.md`**. That is a direct instruction to violate the boundary,
   a grant of write authority no research child should hold, and a use of
   `rm -f` on unattributable files that the project's own rules forbid. Now:
   children return text, the parent holds the rounds and writes the merged
   file. Also corrected a stale `~/.hermes-cortex/` path to the live
   `~/.hermes/`.

**Rule 18 of `SYSTEM-RULES.md` now covers this.** It previously required
sanitizing *data* before delegating but said nothing about *authority*.

### Known limitation — stated, not hidden

This is **advisory, not structural**. A sufficiently determined child that
receives the boundary as prose can still ignore it. The structural fix is to
restrict `toolsets` on dispatch so write tools are simply absent; the new
prompts *mandate* that but cannot *enforce* it from a prompt. Both fixes
together are materially better than either alone; the toolsets fix is the one
that actually removes the capability.

---

## 7. The general lesson

> **A rule that is not transmitted to the agent that must follow it is not a
> rule. It is a note.**

Every finding in this repo's history has the same shape: a check that passes
because nobody looked (BUG 3), a claim that is true-but-unreachable (Batch
142), a metric that measures the wrong axis (A-01 through A-04). Delegation
adds one more: **a constraint that stops at the parent is a constraint on
nobody**, because the parent was never the one writing.

The generalisable fix is not "add a reminder." It is: *when a system spawns a
worker, the parent's authority must be re-asserted in the worker's own
context, because the worker starts from zero.* That is a design rule, not a
prompt patch, and it should be applied to any future job that dispatches.
