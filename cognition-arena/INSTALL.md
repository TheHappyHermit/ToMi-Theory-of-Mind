# Corpus distillation workspace — install guide

This directory holds the **corpus distillation job**: a cron-driven read that walks an
ordered file list one document at a time and distils what it finds into ranked,
evidence-backed designs.

## The two files that matter

| File | Role | Update rule |
|---|---|---|
| `ARENA.md` | **the answer** — ranked slots, rewritten each pass | rewritten in place; a slot is replaced, never appended to |
| `ARENA-EVIDENCE.md` | **the audit trail** — reasoning, measurements, rebuttals | **append-only**, never pruned |

Before the split these were one file and the answer was buried: `ARENA.md` reached
10,116 lines with Area 8's rank-1 at line 108 of a 1,928-line area. The three-slot
discipline was never broken — the ranking was buried under its own evidence.

`ARENA.md` may legitimately reach 10,000+ lines as areas are added. There is no
size cap. What is forbidden is growing *by accretion*. If a pass finds itself
appending prose between two slots, that prose belongs in `ARENA-EVIDENCE.md` and
the slot should carry a one-line consequence instead.

## What is tracked in git

**Everything, including the runtime files.** The corpus content is machine-specific
and enormous, but `ARENA.md`, `ARENA-EVIDENCE.md`, `LEDGER.md`, `ORDER.txt`,
`RUNLOG.jsonl`, `EXCLUDED.txt`, `VERIFICATION.md` and `ARENA-INFRA.md` are all
tracked. They are the accumulated work, and an untracked arena is an unrecoverable
one. `templates/` carries the blank scaffolds for a fresh install.

---

## Install

### 1. Generate `ORDER.txt`

The job reads paths only from `ORDER.txt`. It must contain **one root-relative
corpus path per line, in navigation order**, and the order is the whole point: it is
what makes the read resumable and auditable.

Never let a job guess a filename. Never reorder the list mid-run.

### 2. Copy the templates into place

```bash
cd cognition-arena
for t in templates/*.template; do
    cp "$t" "${t%.template}"
done
```

That creates `ARENA.md`, `ARENA-EVIDENCE.md`, `ARENA-INFRA.md`, `VERIFICATION.md`,
`LEDGER.md`, `EXCLUDED.txt` and `RUNLOG.jsonl`. **The evidence file and the runlog
are not optional** — without them a pass has nowhere to put its reasoning and no way
to prove a later citation was earned.

Then populate `LEDGER.md` with one row per `ORDER.txt` line, all `[ ]`, and set the
cursor to the first row. Populate `EXCLUDED.txt` with the user's exclusion rule and
its line ranges, marking those rows `[-]`.

**A blank ledger is a valid starting state.** The first run creates the first areas
from the first files it reads.

### 3. Fix the absolute paths

`SKILL-wiki-cognition.md` and `cron-prompt.txt` both name **absolute paths**, on
purpose: a bare filename can be redirected by a `cd` into either corpus and write to
the wrong place. On install, rewrite every path to the new location. There are
exactly four writable paths, and they must all be changed together:

- `ARENA.md`
- `ARENA-INFRA.md`
- `VERIFICATION.md`
- `LEDGER.md`

Search the skill for the old prefix and confirm no bare filenames remain. There
are now **seven** writable paths, and they change together:

- `ARENA.md`
- `ARENA-EVIDENCE.md`
- `ARENA-INFRA.md`
- `VERIFICATION.md`
- `LEDGER.md`
- `RUNLOG.jsonl`
- `ORDER.txt` (read-only in practice, but named absolutely so a `cd` cannot redirect it)

### 4. Install the skill and the job prompt

**Both arrive with the main install.** `install.py` symlinks every
`skills/*/SKILL.md` into `~/.hermes/skills/`, and seeds the cron job from
`cron/jobs.template.json`, which already contains this job's prompt. There is no
separate step and no separate script to run.

The skill states the rules; the prompt tells the job to enforce them. Both are in
the repo, so a fresh install gets a matched pair — one without the other is the
case the template already prevents.

To check an **existing** install for drift against the template:

```bash
python3 scripts/check_cron_drift.py            # report, write nothing
python3 scripts/check_cron_drift.py --verbose  # show the differing lines
```

It compares the template against the live `~/.hermes/cron/jobs.json` after
expanding the template's `${...}` variables, so a prompt that is identical apart
from resolved paths is not reported as different.

Manually: copy `skills/wiki-cognition/SKILL.md` to
`~/.hermes/skills/research/wiki-cognition/SKILL.md`.

The description must be **≤ 60 characters** — the system prompt budget — and the
index truncates at 57, so keep it comfortably short. A longer description is
rejected on approval with an explicit budget error.

### 5. Create the cron job

Read `installers/arena-prompt.md` and use it as the job prompt. The job needs:

- **skills:** `wiki-cognition` — injected on every run
- **workdir:** this directory
- **schedule:** an interval long enough for a run to finish. A run that reads N
  whole files and arbitrates them takes minutes, not seconds. An interval shorter
  than a run guarantees overlap.
- **model:** leave unpinned so it inherits the configured default, unless you want a
  specific model. If you do pin one, verify that model is actually available — a
  retired model id fails at request time and looks like a hang.
- **fallback:** consider whether a fallback chain helps. A chain that points at an
  unreachable endpoint turns a fast failure into a long hang.
- **retry:** raise per-call retries and recovery cycles if the provider rate-limits.
  A model that is rate-limited should wait and retry, not silently switch.

### 6. Verify before trusting it

Do not infer progress from a success message. After the first run completes:

1. **Check the ledger moved.** Count `[x]` marks directly.
2. **Check the marks are contiguous and in `ORDER.txt` order.** A run that marks
   files it did not read produces gaps and out-of-order rows.
3. **Check the marks resolve to real files.**
4. **Check the read-to-mark ratio.** One `read_file` per file marked. A run with far
   fewer reads than marks used a shortcut, and the ledger is now claiming reads that
   did not happen — reset those marks.

---

## The rules that matter most

**Read whole files.** One file, one `read_file` call, start to finish. A truncated
body is not a read; continue with `offset`. No `cat`, `head`, `grep`, bulk dumps, no
scripts, no subagents. `terminal` is for ledger arithmetic and drift checks only.

**Mark `[x]` immediately after reading that file**, before any other edit. This is
the crash-recovery boundary: if the run dies later, the ledger already says what was
read, so the next run resumes instead of repeating.

**Never cite a file you have not read.** A name in the arena is a claim that you
read it. 39 files were once cited in `ARENA.md` whose ledger row had never been
`[x]` in any commit — not mis-marked, never marked. When a citation is load-bearing,
the absence of a read is the finding: note it in `VERIFICATION.md` until the file is
actually read, or strike the citation and record the strike.

**A bare filename does not identify a file.** 446 of 1,445 basenames in `ORDER.txt`
appear at more than one row, because the corpus publishes most documents twice —
under `active-wiki/` and `oracle/brain/`. Cite the full relative path. Resolving a
citation to a single ORDER row by name is a coin flip, and it has already produced
one false alarm in both directions.

**Corroboration is data, not repetition.** A second source supporting an existing
slot is additional evidence — append it, raise the independent-source count, and
raise the grade if it earns one. Never skip a file because the area looks covered.
Distinguish a *new* source (counts) from a file restating an already-cited source
(does not), so counts cannot inflate.

**Discovery over search.** New brain parts and cognitive functions are found by
reading, not by recalling what was anticipated. An area earned by a file that
discusses a mechanism; never by a directory or product name. Missing coverage means
"not observed yet" — never "absent" or "unnecessary."

**Three ranked slots per area, always.** Rank 1 is what gets built, 2 and 3 are the
fallbacks that let components compose. A runner-up you deleted is a fallback you
cannot use.

**Keep design-evidence and deployment-evidence separate.** A design with six papers
behind it and a local instance that returns 404 is a `LOW` design and an `UNTESTED`
deployment. A reader who sees only one draws the wrong conclusion in one direction or
the other, so both gradings belong in the file permanently.

---

## Failure modes seen in practice

Recorded because each cost real time and none is obvious from the code.

- **A retired model id looks like a hang.** A provider dropped a free tier; every
  request 404s, retries exhaust, and the run parks on a dead socket. The error was in
  the log the whole time. **Read the log before theorising about the network.**
- **`CLOSE-WAIT` with no read timeout is an infinite hang.** The process shows as
  running, uses almost no CPU, and never writes anything. Check CPU time and socket
  state before assuming slow work.
- **A heartbeat is not progress.** A file count that never moves while a process is
  "running" is a hang, not a slow read.
- **Interval shorter than a run guarantees overlap.** Runs queue behind each other and
  pile up.
- **An identifier mismatch yields a confident zero.** Two components keyed one on the
  filename and one on the stem-without-extension never match, the branch never runs,
  and it reports "0 problems" while real cases exist. Assert that every identifier
  one side produces is resolvable by the other. This has now happened four times in
  this project, always the same shape: the assertion written after the result.
- **A ledger that silently reverts is worse than no ledger.** It has been observed
  more than once here. Any unexpected drop in the read count should be treated as
  that until proven otherwise, and reported rather than quietly re-marked.
- **Never overwrite a state file before reading it.** The write guard will block you,
  and that is the guard working.
