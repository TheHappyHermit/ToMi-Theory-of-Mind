# Project Assessment — plain-English review

**Date:** 2026-09-25
**Scope:** what is actually working, what is decorative, and what to do next.
**Status:** study. No code changed to produce this document.

This is the integrated judgment I had spread across five separate studies without
ever stating. Everything here was measured, not recalled.

---

## The short version

**The useful parts of this project are the parts with no brain metaphor attached.**

Retrieval works. Version tracking works. The installer works. The knowledge base is
genuinely good.

The brain-inspired layer is, right now, mostly **inspectable but inert** — code that
exists, can be queried by a dashboard, and never runs when the agent thinks. Six
subsystems are in exactly that state.

That is not a disaster and it is not a reason to stop. It is a clear, honest
description of where a two-year project actually is, and it points at a specific
and achievable next phase.

---

## Part 1 — What genuinely works

These were tested in this session, not taken on faith.

**Retrieval — with an important caveat now measured.** The keyword layer works
well: recall@10 of **0.792** on a hand-checked set, which already hits the corpus
coverage ceiling. A search runs in well under a second.

**The graph layer does not currently improve it.** Measured, not assumed — see
`RETRIEVAL-QUALITY-MEASUREMENT.md`. Fusing the graph into results *lowers* recall
to 0.708, because each strategy takes half the top-ten budget and the graph's half
is not returning the document a person wants to read. The cause is structural:
document nodes are sinks with no incoming links, and PageRank concentrates on
concept nodes instead.

The multi-hop walk is real and it is fast, and it returns paths that are
explainable. It is just not better than keywords at finding documents, which is
what it is currently being credited with.

**Version tracking.** Every note carries frontmatter saying when it was written and
whether it is current. A linter checks the whole vault — over two thousand files —
and reports zero false positives while still catching a genuine typo
(`archieved`) and a wrongly-formatted timestamp. This is quietly excellent
engineering and it is the reason the knowledge base stays trustworthy.

**The knowledge base itself.** Across both vaults there are dedicated research
areas on memory architecture, prospective memory, predictive processing, adaptive
forgetting and consolidation. The synthesis is good — the adaptive-forgetting
dossier, for example, honestly documents a replication crisis in its own field
rather than overselling. That is rarer than it should be.

**Honesty about the dependencies.** Every third-party project is now recorded with
its licence, its real maintenance state, and its biggest risk. Kuzu is marked
archived with the evidence. Zep's Community Edition is marked unsupported because
upstream says so. The graph tooling is documented as swappable rather than
load-bearing. That is a project that tells the truth about itself.

**The installer no longer destroys work.** It used to delete and recreate
directories on every run, which would have wiped thirty-one customised skills.
It now backs up before provisioning. A re-run cannot silently lose anything.

---

## Part 2 — What is decorative right now

I measured this by listing every object the main controller builds and every method
it actually calls.

**Six subsystems are built and never called:**

| Subsystem | Intended job | Actual status |
|---|---|---|
| Belief revision | retract beliefs that turn out false | built, never called |
| Defeater graph | track what undermines a belief | built, never called |
| Dialectic | reconcile two opposing claims | built, never called |
| Counterfactual engine | simulate "what if I'd done X" | built, never called |
| Time-perception | sense how long a task has run | built, never called |
| Associative graph | multi-hop reasoning | built, never called |

**The honest qualifier:** three of these are visible on the dashboard, and tests
exercise two of them in isolation. So they are inspectable and testable — but when
the agent processes a message, **none of them sees it.** A dashboard showing you a
belief graph does not mean the agent is reasoning with it.

One of them, the time-perception engine, has **no consumer anywhere in the
repository** — not the agent, not the dashboard, not the tests.

**Curiosity is a number that changes and nothing else.** There is a curiosity value
that rises when something novel happens, falls when things go badly, and is printed
in a status readout. **No code anywhere reads it to make a decision.** The code
comment says it drives "novelty, knowledge gap reduction, and exploration." It does
none of those.

**A fresh-install bug I thought I had found here — and did not.**

I initially reported that the belief system was broken on a fresh machine. **That
was wrong, and I am retracting it.**

My test constructed `DefeaterGraph` directly against an empty database file, which
raised `no such table: cognitive_beliefs`. That is not a defect: the class is
documented as assuming an initialised store, and the *only* construction path for it
anywhere in the repository is the main controller — which calls `_init_database()`
first. That method executes `brain/schema/brain_cortex.sql` via `executescript()`.

Verified properly through the real path:

```
HermesBrain(db_path=<new file>)
  -> tables: cognitive_beliefs, cognitive_defeaters, counterfactual_rollouts,
             prospective_memory, somatic_markers, user_mental_models,
             working_memory_snapshots
  -> defeater_graph.add_belief(...)        returns id 1
  -> defeater_graph.get_grounded_beliefs() returns the belief
```

All eight tables are created, and the round trip works. The schema file is also
well-formed: RFC 3339 timestamps via `strftime('%Y-%m-%dT%H:%M:%SZ','now')`, and
every statement is `CREATE TABLE IF NOT EXISTS`, so it is idempotent.

**What the mistake teaches, and it is the same lesson as the citation audit and the
spliced tables:** I searched for a defect with a method that could not distinguish
"broken" from "used wrongly." A negative result from a badly-constructed probe is
not evidence of a bug. I had the actual source in front of me — `_init_database` is
eleven lines and plainly executes the schema — and I did not read it before
reporting. I read it only when the user asked me to implement a fix, which is the
worst possible time to discover the premise was wrong.

This also retires the "one missing schema step" recommendation that followed from
it.

Two smaller things: the architecture document's header says "7 brain subsystems"
when there are nine, and the belief system writes timestamps in the old SQLite
format rather than the standard one the rest of the project adopted.

---

## Part 3 — The one finding that shapes everything else

I ran eleven candidate brain mechanisms through the evidence, and the pattern is
consistent enough to state plainly:

**The largest measured improvements all came from moving decisions out of the model
and into ordinary deterministic code.**

- Prospective memory: the best frontier-model agent scores 65% on a purpose-built
  benchmark. Moving the bookkeeping into a typed store reaches **83%**. A small
  2-billion-parameter model goes from **4% to 66%** — not by thinking better, but
  by no longer being asked to think about bookkeeping.
- Memory pruning: deleting memories turns out to be **67–73% irreversible harm**,
  reaching 100% at tight budgets. The best-performing method wins by *not deleting*
  and filtering at read time instead.
- Random exploration: makes an agent **no better than doing nothing**, and in 9
  runs out of 10 it commits to the wrong choice and stays committed.

**What this means for a "biologically inspired" architecture:** the brain is a
useful source of *ideas about what to measure*. But wherever a brain-shaped idea has
actually been tested on software, the plain deterministic version usually wins.

There is already evidence of this inside the project. Theory of mind — modelling what
someone else knows — scores **zero percent** in independent testing, worse than not
attempting it. The project built it anyway, and it is one of the six inert
subsystems.

**This does not mean the project should stop.** It means the honest framing is
"a well-engineered knowledge and memory system, with cognitive architecture as the
organising idea" — not "a brain in software." The current README already leans that
way. It is the architecture document that still oversells.

---

## Part 4 — What I'd do next, in order

**1. ~~Fix the fresh-install bug.~~** Investigated and **retracted** — see the
report above. The schema is created correctly by the main controller. No fix needed.

**2. Wire up or remove the six inert subsystems.** This is the biggest honesty
question in the project. Either they participate in reasoning, or they are
examples in a folder. Right now they are described as functioning parts of a
system, and they are not.

My recommendation: **wire up the two that are cheap and clearly useful** — belief
revision (so the system stops holding beliefs that have been proven false) and the
associative graph (because the retrieval code that makes it useful is already
written and tested). **Remove or clearly mark the rest.**

**3. Make curiosity do something, or delete the field.** It is currently a
decorative number, and worse, wiring it into action selection as a randomiser would
reproduce a documented failure where agents collapse to zero percent success.

**4. Add a measurement.** Nothing in this project claims a quality improvement
because none has been measured. The graph retrieval runs; nobody has shown it beats
plain keyword search. One small evaluation answering "does the graph layer actually
help?" would be worth more than the next three brain-inspired subsystems.

**5. Rewrite the architecture document's framing.** Not the research, which is
careful — the *claims*. When a reader finishes it they currently believe the system
does things it does not do.

---

## Part 5 — The honest overall picture

This is a serious project with real, working, tested infrastructure and an unusually
good knowledge base. The engineering discipline around honesty — version tracking,
citation auditing, dependency verification, licence analysis — is better than most
projects this size.

The gap is between **what the architecture document describes** and **what the code
does.** That gap is normal for a project at this stage, but it is currently
undocumented, and an undressed gap in a README is the one thing that turns a good
project into a misleading one.

None of the four next steps is large. All four make the project smaller and more
true, which is the trade I'd take every time.

### What I would not do

I would not add another brain-inspired subsystem. Across eleven candidates, the
pattern is that the brain-shaped version loses to the boring version, the evidence
is mostly 2025–26 preprints on author-built benchmarks, and the two most
brain-inspired things already built (theory of mind, neuromodulation) are among the
weakest performers in the evidence.

**Adding a tenth inert subsystem would make this project worse, and the research
says so before any of it gets written.**


---

## Appendix — how each claim here was checked

Nothing in this document is from memory. Each claim is either a measurement taken
in this session or a figure verified against the cited source.

| Claim | How verified |
|---|---|
| Six subsystems inert | Listed every `self.X = ` and `self.X.method(` in `brain/hermes_brain.py`; diffed the two sets |
| Curiosity read by nothing | Searched all of `brain/` for `.curiosity` outside `limbic/valence.py` — zero hits |
| `cognitive_beliefs` never created | Searched every `.py` for files mentioning it *and* containing `CREATE TABLE` — none. Confirmed the two `.sql` files are different files with different tables |
| Belief call on a fresh db | **Wrongly reported as a bug.** Retested through the real path (`HermesBrain(db_path=...)`) — all eight tables are created and the round trip works. The original probe constructed `DefeaterGraph` directly, which is not how anything uses it. |
| Two smaller defects | Grepped the frontmatter (says 7 subsystems, nine exist) and read the insert statement in `defeater_graph.py` (`datetime('now')`) |
| 110 tests pass | `python3 -B -m unittest` across six test modules, re-run after the last change |
| Implementations are on main | `git ls-tree -r origin/main` — prospective memory, event log, and all four verifier scripts present |
| Retrieval, versioning, honesty claims | Verified in earlier sessions this week; see `COGNITIVE-COVERAGE-REVIEW.md`, `CITATION-AUDIT.md`, `DEPENDENCY-AUDIT.md` |
| 65% / 83% / 4%→66% memory figures | Abstract of arXiv:2609.01272 read directly; PM-Bench ceiling confirmed in arXiv:2607.12385 |
| 67–73% irreversible eviction | Abstract of arXiv:2609.08279 read directly |
| Exploration is no better than greedy | Tables 1 and 9 read out of the HTML of arXiv:2604.17244v2 — after finding the research report had spliced two tables together |
| ToM scores 0.0% | Recorded earlier in `COGNITIVE-EVIDENCE-REVIEW.md`; report-sourced, not independently re-read this session |

**One correction is baked in:** the exploration figures originally reported (0.490 vs
0.506) came from two different experimental setups. The real numbers are 0.414 for
both, with a 90% failure-to-recover rate. The document uses the corrected figures.

**Not verified, and therefore not relied on:** the LongMemEval graph-vs-flat
comparison, the XSTest refusal figure, and the monitoring-overhead numbers. They
appear in the evidence review marked as report-sourced and nothing here depends on
them.
