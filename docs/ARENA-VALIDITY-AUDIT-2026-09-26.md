# Arena Validity Audit — read-only, 2026-09-26

**Question:** are the online lanes' writes to `SCRATCHPAD.md` invalidating the arena?
**Answer: no. The arena is structurally sound and the lanes never touched it.** But a
*separate*, older integrity gap exists in the arena's own accounting, and it is worth
more than the lane question.

Nothing in this audit was written to `cognition-arena/`. All four arena files were
md5-fingerprinted before and after; only `LEDGER.md` moved, at 09:33:48, by the
15-minute job's own scheduled run (375 → 397 read, forward progress).

## 1. Structural integrity — passes

| Check | Result |
|---|---|
| `LEDGER.md` rows | 2,217 |
| `ORDER.txt` lines | 2,217 |
| Row numbers contiguous 1..N | yes |
| Duplicate paths in `ORDER.txt` | 0 |
| Path mismatches ledger ↔ `ORDER.txt` | 0 |
| Row census vs the ledger's own summary table | exact match, delta 0 on every class |
| `[x]` → `[ ]` regressions since the pre-run backup | **0** |
| `ORDER.txt` mtime | 09-25 18:52 — untouched by every actor |

`LEDGER.md` is **not** git-tracked (only `cognition-arena/templates/` is), so the ledger's
history exists only in the running file. The scratch backup
`~/.hermes/cache/scratch/LEDGER.bak.1790400872` (19 `[x]`) is the only pre-tranche
snapshot on disk, and it shows strictly forward progress to today's 397.

Progress is monotonic across the last 19 runs: 101 → 118 → 134 → 144 → 160 → 171 → 191 →
211 → 241 → 261 → 280 → 300 → 320 → 335 → 355 → 375 → 397.

## 2. The lane question — cleanly negative

Zero writes to `ARENA.md`, `ARENA-INFRA.md`, `VERIFICATION.md`, `LEDGER.md`, or
`PROPOSED-BRAIN-ARCHITECTURE.md` from Online Lane A or B. The lanes' 2,118
`SCRATCHPAD.md` lines are appends to a *different* file and have no path into the arena.
The 15-minute job explicitly disclaimed the scratchpad files in two separate runs,
unprompted, and kept working.

## 3. Finding A — the 9 phantom marks (pre-existing, disclosed, harmless)

`VERIFICATION.md` finding **F2-7** records that `LEDGER.md` rows 21–29 became `[x]`
during a pass that made exactly 20 `read_file` calls and issued no patch naming them.

Verified independently: **all 9 are still `[x]`, and none of the 9 is cited anywhere in
`ARENA.md`** (zero citations in `.md`-or-path form, not just zero substring hits). They
inflate the read count by 9 and support no conclusion, grade, or rank. The job's own
verdict — "left in place and declared, not reverted" — is the right call, and it is
correctly disclosed.

## 4. Finding B — 173 unread-marked files cited as evidence (new, not previously disclosed)

This is the real issue, and it is **not** the lane problem.

`ARENA.md` cites **173 files whose `LEDGER.md` row is still `[ ]`**. Not reversals — the
pre-run backup shows all 14 spot-checked were `[ ]` then and `[ ]` now, so this is
long-standing, not something a recent pass blanked. `ORDER.txt` has zero duplicate
paths, so this is not a benign double-listing.

How the 173 are used:

| Use | Count |
|---|---|
| Table row | 105 |
| Prose mention | 58 |
| **`**Earned by:**` — cited as the evidence backing a claim** | **7** |
| Cross-ref / "backup document" | 2 |
| "CORRECTED DOWNWARD" re-rank | 1 |

**Severity is low, and the direction of the error matters.** Every grade I could trace
that rests on one of the 7 is *conservative*:

- `belief-revision-ai-agent-memory.md` → design `UNTESTED`, Support: 1 source
- `multi-objective-bandit-drift-tuning.md` → design `UNTESTED`, Support: 1 source
- `2026-09-13_to-do-capture-hook.md` → design `UNTESTED`, deployment `LOW`, Support: 2

`UNTESTED` and `LOW` are the arena's *weakest* verdicts. So the unearned citations are not
inflating confidence — the affected claims are already graded as weakly as the evidence
allows. That is the opposite of the F2-5/F2-7 failure mode the job correctly flagged
("a conclusion outran its evidence").

**The arena's own load-bearing claim is now false.** `VERIFICATION.md` F2-7 states
"every grade in `ARENA.md` rests on lines 1–20 only, and the arena states that no file
outside lines 1–20 is cited anywhere in it." That was true when written, at 29 reads.
At 397 reads it is false: 173 citations land outside the read set. The claim has not
been re-tested or retracted as the arena grew. It is stale, not dishonest — but a reader
trusting it today would be misled.

## 5. Method notes — two of my own checks were wrong first

Recorded because they are the same class of error the audit is about.

- **A substring-match citation scan reported 437 unread files cited.** 235 of those
  were the stem `index` matching the English word "index". A bare `stem in text` test
  cannot distinguish a citation from a word. Requiring `.md`-or-path form cut it to 173.
- **A ledger row regex matched 0 of 2,217 rows** because the format is `- [x] NNN path`,
  not a table row. Zero rows parsed is a broken parser, not an empty ledger.

Both were caught only by sanity-checking the result against a known quantity
(2,217 `ORDER.txt` lines, and the ledger's own published summary counts).

## 6. Recommended, not done

These are changes to a document the operator owns, so none were made.

1. **Re-test the "lines 1–20 only" claim** and restate it as a live invariant: *"every
   `ARENA.md` citation resolves to a `[x]` row"*, enforced by a check that fails when the
   count is non-zero. Today it would fail on 173.
2. **Decide the 173's provenance** — either the read happened and was never marked
   (ledger under-reports), or the citation is unearned (arena over-claims). The two have
   opposite fixes and the files cannot distinguish them. The `Earned by … (tranche 1)`
   phrasing points at the first, since tranche 1 was 20 files and these are not among
   the 20 `[x]` of that era.
3. **Give `LEDGER.md` a git history**, or a dated snapshot per tranche. It is the arena's
   only source of truth and it is untracked; the single scratch backup is the sole
   pre-tranche record, and it will be pruned at 24h.
