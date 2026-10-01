---
name: delegated-research-fanout
description: Use when a question needs independent research facets.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, delegation, subagent, fan-out, evidence, verification]
    related_skills: [research-request, oracle-query, multi-round-research, external-claim-reconciliation]
---

# Delegated Research Fan-Out

Researching a question that decomposes into several independent facets, each
needing its own retrieval.

## When to Use

The question splits into N independent parts: "what already exists for each of
these areas", "compare these vendors", "what do the papers say about each
mechanism", "audit each of these subsystems". One serial agent accumulates every
facet's intermediate data and overflows; N parallel subagents each hold one
facet.

Not for single-facet questions. One subagent is overhead; just research it.

## Procedure

① **Enumerate the facets** and give each its own `goal`. Shared state goes in
the `context`, repeated per task, because each child starts with no knowledge
of the conversation.

② **State one evidence bar, repeated in every task's context.** Without it the
results are not comparable and cannot be ranked against each other. The bar
should be concrete and checkable — the fields you require, the provenance you
need, what counts as a dead end versus a finding.

③ **One question per invocation.** A prompt naming nine topics becomes hundreds
of tool calls against one model, and a single dead subprocess hangs the whole
run with nothing written. A prompt naming one topic returns a sourced answer.
Ask in batches of one.

④ **Tell them what an empty result means.** "Could not find it" and "does not
exist" are different claims, and a subagent that cannot tell them apart will
report a registry gap as a finding.

⑤ **Require the negative result to be calibrated.** A subagent must say how it
searched and what a null means, so you can tell a real absence from a broken
instrument.

## Verifying what they report

Child summaries are **self-reports, not verified facts.** A child claiming it
found or wrote something may be wrong.

- Re-resolve every identifier, URL, or record a child hands back. Delegates
  return confident, well-formatted identifiers for papers that do not support
  the claim; one supplied DOI during the T2 audit resolved to an unrelated
  pain-neuroimaging paper.
- Treat "no identifier found" as more trustworthy than a tidy identifier, and
  note that a child discarding its own guess after a failed probe is behaving
  correctly.
- Confirm any side effect yourself. For an external write, require a verifiable
  handle — a URL, an ID, an absolute path — and check it.
- Where a child's account of your own codebase is concerned, read the code.
  A child's description of a file is a paraphrase, not the file.

## Pitfalls

- **Overloading one invocation.** Nine questions in one prompt reliably
  returns nothing.
- **Omitting the evidence bar**, then receiving nine answers at four different
  confidence levels that cannot be compared.
- **Letting "not found" become "does not exist"** without a coverage check.
- **Trusting a child's identifiers because they look authoritative.**
- **A child timing out silently.** An empty output file is a MISS, never a
  pending answer — check for it rather than waiting.
- **Accepting a summary in place of evidence** for anything load-bearing.
