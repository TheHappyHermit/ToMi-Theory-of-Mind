# Suite state

27 test files. **26 pass. 1 fails.**

Measured by capturing each test's exit code directly, not by reading a shared
log — see the note at the bottom, because the first attempt got this wrong.

## The one failure, and why it is not mine

`tests/test_arena_invariants_nonvacuity.py` — **34 passed, 2 failed**

Proven pre-existing: checked out `3e81f21` (the arena-completion commit, where
the corpus ran to 0 remaining) and it reports the identical 34/2. It predates
the Decisions work.

Both failing cases need an unread ledger row to build a fixture against, and
there are none, because the corpus is finished:

```
t_c7 RAISED
  AssertionError: no unread row available to build a synthetic claim from
C9 respects the ceiling argument (maxrun=1 forces red when marked)
  mean 0.0 marked files per tranche across 0 tranches
```

The suite assumes the arena is still running. **Left alone deliberately.**
"Fixing" it would mean either inventing unread rows or deleting the assertions,
and both are worse than a visible, explained failure. It belongs with whoever
owns the arena harness.

## Decision tests

| File | Result |
|---|---|
| `tests/test_decisions.py` | 50/50 |
| `tests/test_decisions_integration.py` | 16/16 |

Both are mutation-tested — see the commit message for `8a08825`. Reverting the
C7 resolver to return the first record produces 4 failures; emptying the
authority guard produces 2. A suite that cannot go red is not evidence.

## A measurement I got wrong

The first suite runner appended verdicts to a shared log file, and I started
several runs before earlier ones had finished. Each run truncates the log on
start, so a slow earlier run overwrote a faster later run's results. I read the
stale log, which reported **three** failures. Two of the three were not real:

- `test_arena_invariants_nonvacuity` — real
- `test_brain_integration` — exit 0 when measured directly
- `test_brain_timestamps` — exit 0 when measured directly

The mistake was trusting a shared mutable file as the record of a run I had not
confirmed had finished. Confidently wrong in a way that looked like three broken
tests.

This is the same failure class as the arena read-verifier work: **a verdict read
from something other than the thing it was supposed to measure.** When a check
reports a surprising result, confirm the check is reading the live thing before
believing the number.
