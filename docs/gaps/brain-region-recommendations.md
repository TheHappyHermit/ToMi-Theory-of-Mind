# Brain-region recommendations: 1st choice, 2nd choice, why

Date: 2026-09-29. Constraint from the operator: self-host only, no metered API, no
data leaving the house. Licensing is therefore NOT a selection criterion --
AGPL-3.0 is fine for personal self-hosting and only binds on redistribution.

## How the "ours" column was measured

Docstrings are claims, so the baseline was measured from the code: lines,
function count, non-stub functions, presence of an LLM call, presence of
persistence. Measured with `scripts/region_audit.py`.

A NOTE ON WHAT I ALMOST REPORTED: the first audit flagged 5 files as
SUPERSEDED. Four were false positives -- `superseded_by` (a SQL column) and
`epistemic_state` (a data value) are domain vocabulary, not deprecation
notices. Only `thalamus/gate_entropy_superseded.py` is genuinely superseded.
Flagging a live module dead because its column name contains a synonym for
"replaced" is exactly the failure ZenBrain warns about.

## Region by region

| region | ours | verdict | 1st choice | 2nd choice |
|---|---|---|---|---|
| hippocampus | 296 L | extend | call an LLM in replay; add bi-temporal edges | Graphiti for temporal, HippoRAG for PPR eval |
| cortex | 1,615 L | keep ours | add an ablation harness before more code | port MemoBrain's provenance DAG |
| basal ganglia | 128 L | extend | make the gate STATEFUL (Q-values) | port bob's Q+habit pattern |
| thalamus | 446 L | extend | learned threshold; buffer policy | LLMLingua scoring |
| amygdala | BUILT | done | `brain/limbic/amygdala.py` -- 3 pathways, extinction as inhibition | mood-axis deferred; not needed |
| DMN | 178 L | keep ours | leave counterfactual.py alone | -- |
| social | 203 L | fix | tom.py has no recursion; add level-2 | SynchToM for measurement |
| epistemology | REWRITTEN | done | `agm.py` -- real closure, remainders, partial order; Levi identity fixed | Atlas read; arg2p-kt still deferred |plementation |

## The reasoning that matters

**Zero of the 21 modules calls an LLM.** Every one is deterministic. That is
correct for a cost model, a gate, or a buffer -- and wrong for consolidation.
`replay.py:run_consolidation_replay` builds a dict with an f-string
"consolidated_insight" and never asks a model anything. It simulates
consolidation. That is the single highest-value fix in the codebase, and it
is ~50 lines.

**Our hippocampus is ahead of the ecosystem.** Of 35 surveyed projects, the
licensed tier is extract-and-store vector memory; the "sleep/consolidation"
projects are prompt collections. Six of 35 are unlicensed. Nobody in the
licensed tier implements real offline replay.

**Two regions are not what their docstrings say.**
- `epistemology/dialectic.py` is 36 lines returning one fixed sentence.
  **STILL TRUE.** Not yet addressed.
- ~~`epistemology/agm.py` is 82 lines with no closure, no remainders, no
  partial ordering. It is named after AGM theory and does not implement it.~~
  **FIXED** (`1c7979f`). It now has support-edge closure, remainders, a
  real partial order, and a working Levi identity. The production bug
  was worse than the audit recorded: `conflicts_with` was compared
  against corpus keys while the only caller passes propositions, so
  revision silently expanded instead of revising.
- `social/tom.py` claims "Level 2 ToM" in its docstring and has 5 methods
  with no nesting. **STILL TRUE.** Not yet addressed.

**Arg2P-kt is the one genuine dependency.** MIT, 137 Kotlin files, 960
commits, a full ASPIC+ implementation. Our Pollock defeater graph is an older
formalism that ASPIC+ subsumes. It needs no LLM, so it costs nothing to run.
**DEFERRED, not adopted** -- see docs/gaps/arg2p-evaluation.md. The
official npm package is defective, and adopting a dependency is worth
doing once, not on a first attempt.

## Still to confirm against the LLM wiki

Oracle was queried for vault evidence on seven specific claims (bi-temporal
facts, Hebbian reinforcement, offline vs inline consolidation, pattern
separation vs hashing, hyperdirect pathway, fear conditioning as a learning
rule, learned thresholds). Neither query had produced output at the time of
writing. The recommendations above rest on measured code and the GitHub
survey; the seven claims are the part that wants wiki confirmation.

Re-run with: `oracle -z "$(cat ~/.hermes/cache/scratch/oracle_q2.txt)"`
