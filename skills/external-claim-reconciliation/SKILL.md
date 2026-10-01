---
name: external-claim-reconciliation
description: Use when acting on an external audit or review report.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [audit, review, verification, code-review, research-integrity, reporting]
    related_skills: [verifier-integrity, systematic-debugging, code-review, requesting-code-review]
---

# External Claim Reconciliation

Processing an audit, review, or research report produced by something else —
another AI, a consultant, a linter, a prior session — and acting on it.

## When to Use

- The user supplies an external review and says "fix what you agree with."
- A design doc or architecture claim is being checked against the real system.
- Any situation where you are being told a defect exists and have not yet
  reproduced it.

## The core principle

**The report is a hypothesis, not a fact.** Every claim must be verified
against actual source or actual execution before you act on it.

A report's line numbers may be stale, its snippets may be paraphrased, and its
interpretation may be wrong. It is also a *claim about a codebase you have not
opened yet*, which means it is exactly as fallible as any other unverified
assertion — including the ones you are about to make.

## Workflow

### 1. Parse and number the claims

Extract every discrete assertion. Group by the report's own severity if it
provides one, but treat each claim independently — a correct claim next to a
wrong one does not lend it credibility.

### 2. Verify each against source or execution

For each claim, read the actual code. Do not trust:

- the claimed line numbers,
- the quoted snippet,
- the file existing at the stated path,
- the interpretation of what the code does.

**Reading source tells you what the author intended. Running the code tells
you what it does.** They diverge constantly, and the gap is where the findings
are.

Never report a defect you have not reproduced with executed code. A grep hit is
a hypothesis; a traceback, a printed value, or a database row is evidence.

### 3. Classify each claim

| Verdict | Meaning | Action |
|---|---|---|
| **confirmed** | Reproduced with executed code | Fix it |
| **partly right** | Real defect, wrong mechanism or location | Fix the real defect; say what was wrong |
| **already fixed** | No longer present | No action; say so |
| **not reproducible** | Cannot be made to occur | No action; say so plainly |
| **false** | Demonstrably wrong | No action; say why, with evidence |

### 4. Fix, then report FIXED vs DISAGREED

Present the two lists explicitly. A report that only lists what you fixed reads
as agreement and hides the judgement calls — and the disagreements are the
valuable part for the user.

When your own reproduction contradicts your reading, trust the execution and
retract the earlier claim. Do not quietly drop it.

## The asymmetry worth remembering

A verifier emits two kinds of error and they are not symmetric:

| Error | What it costs | Who notices |
| :--- | :--- | :--- |
| False accusation | Wrongly blames a file for a real defect | Loudly, immediately |
| False exoneration | Silently inflates confidence in a wrong claim | Only if you go looking |

False exoneration is the more dangerous one precisely because it is quiet. So
tighten until the false-accusation classes are gone, then **stop** — do not
keep loosening a check to make the numbers look better.

## Pitfalls

- **Fixing the report's location instead of the real defect.** The report
  points at line 40; the bug is in the caller at line 12.
- **Accepting a claim because it is specific.** Detail is not evidence.
- **Reporting only confirmations**, which reads as capitulation and discards
  the analysis.
- **Bulk-applying a report's recommendations** without checking whether the
  codebase moved since it was written.
- **Treating "no longer reproducible" as "fixed."** Those are different claims
  and the difference matters.
- **Skipping verification because the report agrees with what you already
  suspected.** Suspicion is not reproduction, and acting on it is how a wrong
  belief gets hardened into a "confirmed" finding.
