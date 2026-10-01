---
name: phased-spec-execution
description: Use when executing a numbered multi-phase plan.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Phased Spec Execution

## When to Use

- A numbered phase/phase-step document exists and the user says "do phase N"
  or "do all of them except X"
- A plan has prerequisites that order the work ("do not decide this before
  phase 3 lands")
- Work spans multiple subsystems and each phase should be independently
  revertible

## Core Rule: Read the Spec Before Touching Code

The spec is the source of truth, and its order is an argument, not a
suggestion. Before implementing anything:

1. Locate the *actual* spec file. Do not assume the architecture doc holds the
   phase definitions — plans often live in a separate results/ideas file with
   prose "PART N — PHASE M" headers. Grep for `PHASE 1`, `Phase 1:`, `PART 5`
   across the repo before concluding anything.
2. For each phase you are about to do, quote the spec's own text back to yourself.
   Several phases in practice turned out to hinge on a clause that changed the
   implementation entirely (e.g. a resume note must lower one cost component and
   explicitly NOT another, because the source finding says the opposite of the
   intuitive reading).
3. Check for **deferral clauses**. A phase that says "deferred on purpose, do not
   decide this before phase N lands" is blocked, and the right move is to do the
   blocking phase instead. Verify the blocker is genuinely incomplete — grep for
   its deliverables — rather than assuming the ordering.

## Scope Control

- Implement exactly the phases authorized. If the user skips some, do not
  "helpfully" implement them later, and do not let a later phase silently depend
  on skipped work.
- Put deliberately-deferred phases somewhere durable and retrievable (a task
  database) with **what it is, what it does, and why it is not functioning** —
  not just a phase number. The user reads these weeks later with no context.
- Never expand scope from a single authorized change into adjacent systems.
  Changing the repo is not the same as changing the live environment, and the
  user draws that line hard.

## Per-Phase Procedure

```
1. git checkout -b feat/<phase>-<slug>          # never commit phases to main directly
2. Write the test that asserts the POLICY, not the current behavior.
3. Run it. Watch it fail for the expected reason.
4. Implement minimally.
5. Run the phase's tests, then the full suite for regressions.
6. Commit ONE phase, with a message that states the defect being fixed,
   the rule being enforced, and any secondary defects found on the way.
7. Push the branch. Merge to main only at an authorized checkpoint.
```

### A test must assert policy, not behavior

A test written against whatever the code currently does keeps passing after
the policy changes, and proves nothing. Each test name should read as a
statement about the design ("a required field rejects placeholders", "an urgent
signal survives suppression") so a failure is legible as a design claim.

**Weight tests toward refusals when the module's value is what it prevents.**
For a confidence/validation layer the meaningful assertions are the ones that
prove the bad path is closed.

**Every gate needs a positive test.** "It doesn't crash" is not proof of wiring.
A gate that never fires is a defect, not a safety property — assert that it
fires on realistic input AND does not fire on the near-miss case.

## Verify by Running, Never by Reading

Run the thing. This is the single most repeated lesson:

- A hand-rolled regex refactor of three files broke all three, and `py_compile`
  passed on the broken versions at an intermediate step. **Never rewrite code
  with regex/sed across files** — patch exact strings with the patch tool, and
  `git checkout --` the moment a batch edit produces a syntax error.
- SQL placeholder counts that don't match the parameter tuple compile fine and
  fail only at execute. Read the value back out of the database.
- A docstring claiming a capability the code doesn't have is invisible to every
  test. Check claims against implementations.
- A defaulting method never called leaves everything unmigrated while looking
  complete. Confirm the call site runs before the first consumer.

When a test fails, decide **which side is wrong** before editing. Several times
the *fixture* was wrong (a document about retrieval-induced forgetting used to
test a thalamus query) and the code was right. Never "fix" working code to
satisfy a bad test.

## Reporting Style for This User

- **Short.** Long explanations were explicitly objected to. Lead with the
  result and the evidence; keep reasoning to a line or two.
- **Plain English for decisions, before acting.** When asked what a change will
  do, answer in layman's terms: what changes, what it affects, and **whether it
  deletes anything** — call out deletion explicitly and separately.
- **Tables for before/after evidence.** One row per claim.
- **Report what you found, including that earlier claims were wrong.** Correct
  your own prior statements plainly rather than quietly.
- Distinguish a real regression from a concurrently-running writer's output
  before calling anything broken, and say which it is.
- Do not report success for anything unverified. "Implemented and pushed" needs a
  fresh read/curl/git to back it.

## Git Discipline

- One commit per phase; message states the defect, the rule, and secondary finds.
- Never `git add -A` over a working tree that a scheduled job also writes to —
  stage explicit paths so job output stays unstaged.
- Before claiming done: `git log -1 --oneline`, `git branch --show-current`,
  `git ls-remote origin refs/heads/main`, and a status check.
- Verify a pushed branch materializes correctly in a **fresh clone**; ignored
  parent directories can make a tracked file silently absent.
