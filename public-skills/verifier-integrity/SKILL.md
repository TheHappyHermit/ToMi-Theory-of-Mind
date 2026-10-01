---
name: verifier-integrity
description: Use when a check, gate, or verifier must be trusted.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [verification, testing, vacuity, sabotage, audit, gates, root-cause]
    related_skills: [test-driven-development, systematic-debugging, verifying-scholarly-citations]
---

# Verifier Integrity

A **verifier** is any script or harness whose purpose is to check other code,
claims, or artifacts: a spec harness, a validator, a citation checker, a
confidence grader, a schema-compliance runner, a lint gate. A feature test
fails loudly when it is wrong. A verifier fails *silently* — it reports PASS
while detecting nothing, and the damage is negative assurance rather than a
visible error.

## When to Use

Build, harden, or trust any check, gate, validator, grader, or audit script.
Also use it when a verifier's verdicts cause files to be changed, flagged, or
trusted at scale, and when a fix stops moving the failure count.

Governs the class of work, not one tool. For tests of ordinary features, use
`test-driven-development`; for root-cause investigation,
`systematic-debugging`.

## The Iron Law

```
A check that cannot fail is a defect, not a weak test.
```

The cause is almost always the same: **the assertion was written after the
result was read.** The expected value gets copied off whatever the code just
produced, so the check confirms the run rather than the behaviour. A verifier
that has never been red has never been tested, no matter how many assertions
it contains.

**Order matters.** Specify the expected value from the *requirement*. When you
do not know a function's real return shape, inspect it with a stubbed call —
guessing field names produces an assertion against a shape that does not
exist, which either errors loudly or gets loosened into a tautology.

## The sabotage test

1. Copy the code under test into a throwaway clone or temp dir. Never sabotage
   the live artifact.
2. Inject the specific defect class the check claims to catch — drop an area,
   truncate an output, swap an identifier key, revert a mark.
3. Run the check. It MUST fail, and the message should point at the defect.
4. Only then does the check earn the right to be reported as passing.

A suite run against un-sabotaged code proves the code is in the state you
already believed it was in. It proves nothing about whether the test works.

Report **caught/total** ("24/24 caught" is the claim; "the tests pass" is not).

## Five shapes that ship unable to fail

**1. `or True` at the end of a condition.** A check named for a real property
ends in a clause that makes it unconditional. Grep new checks for `or True`,
`or []`, and for expected values computed from the thing under test.

**2. Identifier mismatch yielding a confident zero.** Two components keyed one
on the filename *with* extension and one on the stem *without* it never match.
The lookup returns nothing, the branch never executes, and the code prints "0
problems" while real cases exist. Especially dangerous because the zero reads
as a clean bill of health. Assert that every identifier in the manifest
actually reaches the resolver.

**3. Subset where equality is required.** `set(a) <= set(b)` passes on a
superset, so deleted entries are invisible — exactly the sabotage under test.

**4. A floor where a count is required.** A check-count manifest using `>=`
cannot detect deleted checks. Use `==` against a count derived from the source.

**5. Testing a copy, a temp file, or a monkeypatched wrapper.** Asserting on a
reimplementation tests something that can drift green independently of the code
that actually runs. Monkeypatching the HTTP wrapper bypasses the very error
handler under test — green coverage you do not have.

A fixture that only uses the form the router already handles leaves the
unhandled form untested. And a check that cannot fail *in principle* — no
input distinguishes pass from fail — is not a check at all.

## Hardening a verifier

1. Split the real module into resolvers (comparison, routing, network) plus a
   thin CLI. Tests import the real resolvers. Never give tests a private
   helper "for speed" — that is a reimplementation.
2. Run the sabotage battery against the *real* files. The suite must go red for
   each injected defect.
3. Report caught/total.
4. Run offline *and* live; report both counts separately.
5. Record at least one limitation in the file rather than letting an absence
   read as a pass.

Expect the battery to expose holes in your own harness. Each was invisible
while green.

## Verdicts must distinguish failure from absence

Define the verdict vocabulary so that *the absence of a check* is distinct from
*a failed check*. A citation with no stated title is `untitled`, never
`mismatch` — it is not a bad citation, it is an unexamined one. Collapsing "no
evidence" into "failed" makes the population look worse than it is and buries
the real failures in noise.

## Two errors, not symmetric

A verifier emits two kinds of mistake, and they cost very differently.

| Error | What it costs | Who notices |
| :--- | :--- | :--- |
| False accusation | Wrongly blames a file for a real defect | Loudly, immediately |
| False exoneration | Silently inflates confidence in a wrong claim | Only if you go looking |

False exoneration is the more dangerous defect precisely because it is quiet:
the row scores clean, the gate passes, and the underlying problem ships.
So tighten until the false-accusation classes are gone, then **stop** — do not
keep loosening a check to make the numbers look better. Loosening trades a
loud error for a silent one, which is a bad trade at any ratio.

## A count that barely moves means the wrong layer

The count measures your fix's **reach**, not progress. If N successive
corrections move a failure class by less than its own magnitude, the patches
are not on the path that computes the value. Treat near-zero movement as a
diagnostic about the mechanism, not a partial win — re-derive where the value is
actually produced before writing the next patch. Usually it is not the function
being fixed, but a caller that never invoked it, or a stage whose output is
compared raw instead of normalized.

The tell: the fix is correct, the targeted cases pass, and the population is
unmoved. Verify the fixed function is actually *called* with the values being
compared.

## Non-emptiness is not a passing assertion

A value can be non-empty and still be destroyed downstream. A normalizer that
strips punctuation reduces `"(Qwen3 Technical Report)"` to `""`; the comparator
sees an empty string and every upstream check passes while the verdict is
useless. Assert on the *normalized* value, not the raw one.

## Caching hides fixes

After fixing a value computation, invalidate every verdict the changed stage
wrote. A cache keyed by a string that no longer exists will silently keep
serving the old row, and a clean re-run then proves nothing. When a count
refuses to change, suspect a stale cache entry before you suspect the fix.

## Discipline before running at scale

- Test the checker both ways: inputs that must be dropped AND inputs that must
  survive, plus a near-miss negative where a correct value differs by one
  token. A guard proven only to reject non-targets also passes when it rejects
  everything.
- If the check can pass with the feature switched off, it is not a check.
- Sample the reported failures before believing the count. Two fields
  disagreeing on one row — zero candidates and a non-zero score — is proof of
  a bug regardless of the total.
- A count is a claim about a population; the population is where the error
  lives.
- Silence during a long bulk job is not a hang. Report progress at intervals
  and state what is verified so far.

## Anti-patterns to grep for

```
or True | or \[\] | >= *N *# *count
```

A script whose exit code nobody reads is not a check. The branch installer's
component checklist collected every answer and discarded it; the health
checker printed `[skip]` for a missing verifier and kept success. Verify that
a check can actually fail, and that its verdict changes a decision.
