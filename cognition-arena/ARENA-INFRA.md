# ARENA-INFRA — corpus-hygiene requirements

Separate from `ARENA.md` **by design, and the separation is load-bearing.**
`ARENA.md` is a brain design; this file is a defect taxonomy. A link resolver and a
hippocampus index both look like "components" in a list and only one is a brain
part — the same reasoning that keeps ontology-engineering papers out of the arena
keeps link-case defects in here.

**This file is not reset when the arena is.** The distillation is re-derived from
scratch every run; the corpus-hygiene requirements are not rewritten each time. A
new class enters **only** when a file read in a live pass earns it, and a class is
never deleted — evidence disappears, the class is demoted, and the demotion says
why. Tranche 3 added **C-017**; it is the first class earned by a file in the
current pass rather than a prior one. **Tranche 4 added C-018**, earned by a
collision found while reading `round49-2026-09-20.md` — and it is the first class
earned by a defect the corpus *cannot* mark, because the corrupted field is the
citation itself.

Each class states a **requirement**, three **ranked candidates** scored on
generality / verifiability / evidence / consequence / novelty, the **rejected
variants** with the reason, the **evidence**, and what is **open**. A class with no
open question and no measurement is a wish.

**Class list is stable; rankings are not.** Evidence appears continuously. A rank-3
candidate can win tomorrow.

---

## C-001 · Provenance is not authority

**Requirement.** A claim records where it came from and how much weight it carries as
two separate fields. `source` never implies `trusted`.

**Ranked candidates.**

1. **Split `provenance` from `authority` in the schema, enforce at write time** —
   score 9/10. Generality 2 · Verifiability 2 (a validator reads two distinct fields) ·
   Evidence 2 (CP-034 registry-enforced publishing, CP-035 CBOR profile semantics,
   CP-052 provenance/authority defects, CP-061 index set as an authority claim) ·
   Consequence 2 · Novelty 2.
   *Beats:* #2 because a single `confidence:` field provably conflates the two — see
   837, which has 13 citation markers, no reference list, and `confidence: high`.
   *Costs:* one more required field; migration of existing rows.
   *Superseded:* 2026-09-25, replaced "raise the confidence vocabulary."

2. **Rich `confidence` enum (low/medium/high/critical)** — score 5/10.
   Rejected: an enum adds resolution without adding the missing axis. `high` on an
   unreferenced file (837) is not a confidence problem, it is a category error — the
   field measures the writer's mood, not the claim's standing.

3. **Trust-quarantine table with promotion workflow** — score 7/10.
   Retained as a *mechanism* for #1, not an alternative to it. But the SQL had real
   bugs when last seen (CP-038). Do not build before those are fixed.

**Rejected variants.** Salience scoring (retrieval-priority, not authority — conflates
"useful now" with "true"). `verified:` with by/at (only 1 file of 793 populates it, so
it is a wish, not a mechanism).

**Evidence.** CP-034, CP-035, CP-052, CP-061 §837, CP-062 §856, CP-063 §10.
**New instance 2026-09-26 (tranche 5) — the axis is proliferating, and it is
load-bearing.** The arena now names **four** unreconciled confidence vocabularies:
the `confidence:` frontmatter field, the synthesis passes' `severity:
high/medium/low`, Area 2 Slot 1's per-signal ρᵢ(t) ∈ [0,1], and — new — the
architecture's own stated principle in `entities/autognosia.md`: "Evidence and
belief are different — **the system tracks confidence levels**." The fourth is the
most dangerous because it is written as a *design commitment* rather than as a
field: someone decided the system tracks confidence, and four different mechanisms
now track it four different ways with no shared scale and no statement of which one
retrieval reads. The consequence is concrete, not aesthetic — a consolidation pass
(Area 4 Slot 1) writing deductions into a store whose confidence field is not the
axis the retrieval layer filters on produces output invisible to a
confidence-filtering reader. **This is the first C-001 instance that would change a
build order**, which is why it is filed as a design question and not trivia (§7
exception).
**Open.** Does anything currently *enforce* authority at read time, or is it advisory?

---

## C-002 · Apparatus quality is uncorrelated with claim correctness

**Requirement.** A file's self-reported quality signals must never be used as an
evidence weight. They are outputs of the validated code path; correctness lives in the
unvalidated one.

**Ranked candidates.**

1. **Never derive trust from frontmatter; derive it from executed checks** — score
   10/10. Generality 2 · Verifiability 2 · Evidence 2 · Consequence 2 · Novelty 2.
   *The evidence is unusually strong because the correlation was observed to run
   backwards.* Files with correct 16/16 TOCs, real volume-and-page citations, and
   populated `verified:` blocks (869, 874, 880, 881) are the files carrying an
   invented Nobel attribution (869), a fabricated degree and advisor (878), a
   misattributed acronym (880), and a nonexistent book (879). Meanwhile 875 — the
   *only* file of 793 with a populated `verified:` block — is a cron-status file with
   correct `status: paused`.
   *Beats:* every alternative because it is the only candidate supported by a
   measured inversion rather than an inference.

2. **Score files by citation count** — score 3/10. Rejected: 842 has ~150 numbered
   entries across **six separate reference lists**, each restarting at `[1]`, so
   citation count is uncorrelated with resolvability. A file can have more citations
   than any other and still resolve none of them.

3. **Confidence-weighted retrieval ranking** — score 4/10. Rejected as a direct
   consequence of #1: it would rank the most confidently-wrong files highest.

**Rejected variants.** Human review of flagged files (does not scale; and the files
with the best apparatus are not the ones a reviewer samples).

**Evidence.** CP-060 (best bibliography, most fabricated radio measurements), CP-061
§842, CP-062 (14 of 110 `Entities/` files share one boilerplate link block),
CP-063 §§1, 5, 7, 11, 13, 15 and the seven positive controls.
**Open.** Is the boilerplate link block a *generator* default? If so the fix is at the
generator and no amount of downstream checking helps.

---

## C-003 · Referential integrity of internal links

**Requirement.** Every internal link resolves to an existing file, case-exactly.

**Ranked candidates.**

1. **Post-write link resolver over the whole tree, fail-closed** — score 10/10.
   Generality 2 · Verifiability 2 (`find` + existence test; no judgment) · Evidence 2
   (16 broken links in 20 files: 869 §2, 870 §2, 885 §3, 886 §4) · Consequence 2 ·
   Novelty 2.
   *Beats:* #2 because it needs no per-file discipline — a broken target is caught in
   files nobody ever opens, and the files with the most links are not the files being
   read (CP-063).
   *Costs:* one filesystem walk per regeneration. R-J1: cost is not a decision factor.
   *Superseded:* 2026-09-25, replaced "check links in the files we read."

2. **Per-file link check at authoring** — score 6/10. Rejected: covers only files
   someone opens, which is demonstrably not the files with link defects.

3. **Directory-case canonicalization pass** — score 7/10. Retained as a *sub-fix* for
   #1: 9 of the 11 breaks in 869/870 were `entities/` vs `Entities/` alone. One
   character each. Fixing case without fixing existence still leaves `Franklin-Crick`
   and `Tomaso-Poggio`, which match no file at all.

**Rejected variants.** Symbol-level link checking (misses file-level case errors).
`/index`-suffix inference (the generator appends `/index` to sibling *files* — caught
885 §3; needs filesystem resolution, not a naming convention).

**Evidence.** 869 §2, 870 §2, 885 §3, 886 §4, CP-053 (case-colliding directories
`Decision-Making/` vs `decision-making/`), CP-062 (`Entities/` 110 files vs
`entities/` 14, neither with an index).
**Open.** Does the graph builder create edges for unresolvable links, or drop them?
This determines whether a broken link is a cosmetic defect or silent graph corruption.

---

## C-004 · Index completeness is machine-checkable

**Requirement.** Every directory containing Markdown has an index listing **all** of
its files, and the index's file set equals the directory's actual file set.

**Ranked candidates.**

1. **Bidirectional set-equality check, index ↔ directory, run on every regeneration** —
   score 10/10. Generality 2 · Verifiability 2 (two sorted lists, `comm`) · Evidence 2
   (841 lists 1 of 7; 843's related-links sit outside its `## Contents` so machine and
   human read different file sets; `concepts/index.md` omits 12 of 19) · Consequence 2
   · Novelty 2.
   *Beats:* #2 because it catches a *stale* index, which a "does an index exist" check
   cannot.

2. **Require an index to exist per directory** — score 4/10. Rejected: the corpus
   *has* indexes. They are wrong. Existence is not the failure mode.

3. **Freshness compare: index `generated.at` vs max content `generated.at`** — score
   8/10. Retained as a *complement* to #1: catches the 17-day regeneration gap
   (CP-060) where a set-equality check would pass because the sets happen to match.

**Rejected variants.** Manual index review (does not scale; and index files are among
the most formulaic in the corpus, so the check is cheap to automate).

**Evidence.** 841, 843, CP-060 §802, CP-061 §841, CP-053 (`concepts/index.md` omits
576, 579, 580, 588, 591), CP-062 (neither `Entities/` nor `entities/` has an index).
**New instance 2026-09-26 (tranche 2):** `active-wiki/decisions/index.md` carries
**15 index rows for 14 decision files, with `2026-09-16_honcho-dreaming-surprisal`
listed twice** (byte-identical duplicate row). Verified: all 14 files appear — no
omissions; all 15 link targets resolve — no dead links. So this is **not** an
omission defect and **not** a link defect. It is a set-equality violation of the
opposite kind: **index cardinality > directory cardinality.**
**This is a real limit on candidate #1 as written:** "two sorted lists, `comm`"
passes on this file, because `comm` on sorted *unique* lines finds no difference.
**The check must compare row count against file count, not set against set.** The
requirement line stays as written but the mechanism needs the multiset comparison,
or the check reports clean on a file that is provably wrong.
`entities/index.md` is clean by the same test (8 rows, 8 files).
**New instance 2026-09-26 (tranche 5):** `active-wiki/entities/index.md` is clean
(8 rows, 8 files) and `active-wiki/index.md`'s Stats table claims
`decisions 15 · concepts 15 · entities 8 · total 358` — **where the 15 is the
duplicated row, not a 15th file.** So the same stale apparatus propagates one level
up: the parent index agrees with the child's wrong cardinality rather than
catching it. Two indexes that share a defect are not two witnesses. And the
2026-09-20 activity entry in that same file records a different total
(~342), so the parent disagrees with itself. This strengthens the multiset
requirement above rather than adding to it.
**Open.** Does the graph builder index rows or files? If rows, the duplicate is
also a duplicate graph node.
**Open.** Are index omissions correlated with file size? The omitted files in 841 were
the substantive ones.

---

## C-005 · Deterministic corpus checks must exist as executable code

**Requirement.** Every defect class found by reading is encoded as a check that
returns pass/fail without judgment. Otherwise the same class is rediscovered per file
forever.

**Ranked candidates.**

1. **A checked corpus-linter suite, run in CI, one check per defect class, each with a
   named failure message** — score 10/10. Generality 2 · Verifiability 2 · Evidence 2
   (27 checks now identified across CP-053..CP-063; checks 19 and 26 alone found 16
   defects in 20 files) · Consequence 2 · Novelty 2.
   *Beats:* #2 because a checklist executed by a model is not a check — it is a
   suggestion, and 697 demonstrates the failure mode: a "frontmatter verifier" that
   greps one literal string and reports success while 798 files still need frontmatter.
   *Note:* 697 is the single most instructive artifact in the corpus. It is a
   self-comparing validator that reports 0 failures and 876 files while active Oracle
   holds 1,781.

2. **A documented checklist of known defect classes** — score 5/10. Rejected: recorded
   but unenforced; the corpus already contains checklists that nothing reads.

3. **Spot-check high-traffic files only** — score 2/10. Rejected: evidence shows the
   best-trafficked files carry the most apparatus and are not the most broken.

**Rejected variants.** "Confidence" self-reporting (C-002 forbids it). Sampling.

**Evidence.** CP-037 (self-comparing validator), CP-055 (file 697 literal-string
`grep`), CP-060 (constant `stale_after` from a generator constant, not policy),
CP-063 checks 19-27.
**Open.** None — this is directly implementable and needs no further evidence.

---

## C-006 · Generator validation must be structural, not semantic

**Requirement.** The generator proves TOC/body agreement, anchor resolution, fence
balance, link-set equality, and EOF integrity — deterministically, before a file is
considered written.

**Ranked candidates.**

1. **Post-generation structural validator, fail-closed, blocks the write** — score
   10/10. Generality 2 · Verifiability 2 · Evidence 2 · Consequence 2 · Novelty 2.
   *Evidence includes positive controls, which is what makes this safe to assert:*
   848 (12/12 anchors correct) and 869 (16/16 correct) prove the checks are
   achievable, so 861 (10/10 broken, capital `I` in `fmrI`) and CP-060 (TOC/body
   mismatch at 812) are **generator bugs, not format limits**.
   *Beats:* #2 because a warning that does not block the write is the same as no
   check — 697 shipped.

2. **Warn-and-report structural validator** — score 5/10. Rejected on the 697
   evidence: warnings were emitted and ignored.

3. **Human review of generated files** — score 2/10. Rejected: the corruption is
   mechanical (literal `\n` in table cells at 809, `\nabla` newline at 871, mangled
   names at 860/863/878) and invisible to a reader who trusts the page renders.

**Rejected variants.** Checking only that the file is non-empty (697's mistake).
Checking only headings exist (861's headings exist; the anchors are wrong).

**Evidence.** 809, 812, 848, 861, 871, 878, CP-045 (citation-offset corruption),
CP-047/CP-048 (repeated header corruption at 520:29, 621:1, 664:38, 703:35).
**Open.** The source EOF cuts (635, 636, 734, 775, 778, 808, 814) all report
`truncated: false`, which means the corruption is upstream of the reader. Generator
truncation, deliberate excision, and source construction are all still possible and
cannot be distinguished from the read side.

---

## C-007 · Escape-sequence corruption in generated math and tables

**Requirement.** Literal `\n` and swallowed `\r` in generated output are impossible.

**Ranked candidates.**

1. **Escape-aware emitter: never round-trip a string through a layer that
   interprets escapes** — score 9/10. Generality 2 · Verifiability 1 (needs a LaTeX
   parse, not a one-liner) · Evidence 2 (four distinct instances, two of them
   LaTeX) · Consequence 2 · Novelty 2.
   *Beats:* #2 because the two LaTeX cases are unrenderable — 871 lost `\right]` into
   a literal newline, so the file's single worked derivation does not display at all.
   *Note this is a distinct class from C-006:* a structural validator can *detect* the
   damage, but only the emitter prevents it.

2. **Post-hoc LaTeX delimiter and fragment check** — score 7/10. Retained as
   *detection*; the fragment pattern (`ight]`, bare `left(`) is a cheap regex.

3. **Markdown table cell-count check** — score 6/10. Retained as detection for the
   literal-`\n` cell corruption (809, CP-060).

**Rejected variants.** Rendering the corpus and diffing (expensive, and a broken
render can look intentional).

**Evidence.** 809 (literal `\n` in cells), 871 (`\nabla` → newline + `ight]`),
860 (`Ned erg`), 863 (`Seth` as a book title), 878 (`KravchIOff`), 852 (`Humerus`).
**Open.** The name-corruption instances (860/863/878) are 4 of 4 — is there a
truncation bug in the name-emitter specifically?

---

## C-008 · Content type must be machine-enforced

**Requirement.** `type` is drawn from a declared enum and validated against the file's
actual subject.

**Ranked candidates.**

1. **Enum + per-type required-field schema, validated at write** — score 9/10.
   Generality 2 · Verifiability 2 (`in` against a declared set) · Evidence 2 (six
   distinct wrong values observed: `person` on a dashboard at 867 and on a Postgres
   database at 859, `reference` on portraits, `entity`, `Index`, `research_report`) ·
   Consequence 1 · Novelty 2.
   *Beats:* #2 because the field currently carries **no information at all** — a
   retriever branching on `type` misclassifies a web dashboard as a person.

2. **Documented type list** — score 3/10. Rejected: 697's pattern. A documented list
   that nothing validates is a comment.

**Rejected variants.** Inferring type from directory (defeats the purpose; the corpus
already has `Entities/` and `entities/` disagreeing).

**Evidence.** 859, 867, 875, 856, CP-061 §845, CP-062.
**New instance 2026-09-26 (tranche 5):** one directory, three frontmatter
dialects. In `active-wiki/decisions/`: six pages carry `type: "decision"` with
`created_by`/`created_at`/`status`/`topic`; two carry `type: "temporal"` with
`description:`/`created:`/`updated:` and no `status`; one carries unquoted
`type: temporal` with `id: auto` and a nested `salience:` block. The directory name,
`decisions/index.md`, and the `type` field give three different answers to "what
is this file". This is the exact failure C-008 exists to prevent, and it is *not*
a wrong value in a field nobody reads — `decisions/index.md` reads the directory,
Graphify reads frontmatter, and the two disagree.
**Open.** Is `type` consumed anywhere? If nothing reads it, this is hygiene, not
architecture — but it becomes architecture the moment a router branches on it.
**And the answer is now yes:** `decisions/index.md` branches on the directory while
Graphify branches on frontmatter, so a router branching on `type` is already
built and already disagrees with another router over the same seven files.

---

## C-009 · Live state must not be frozen into static prose

**Requirement.** Point-in-time assertions ("Running, accessible", sync cadences,
container counts) live in dated fields, never in prose under `confidence: high`.

**Ranked candidates.**

1. **Separate `observed_at` from content; prohibit transient assertions in the body** —
   score 8/10. Generality 2 · Verifiability 1 (needs judgment about what is
   transient) · Evidence 2 · Consequence 2 · Novelty 2.

2. **Freeze all live state into a generated snapshot file that is regenerated, never
   hand-written** — score 7/10. Retained as the concrete mechanism for #1; 867's
   "Running, accessible" and 859's 1,470/283 counts are exactly this shape.

**Evidence.** 859 (Oracle brain syncs monthly, active-wiki hourly — the semantic index
of the largest store is a month stale by design, stated without flagging; counts
already stale against 1,781/436), 867 (liveness asserted as permanent prose),
CP-062 §5.
**Open.** Does the sync cadence mismatch mean Graphify's Oracle index is a month
behind by design? That is a standing architectural fact, not a file defect.

---

## C-010 · Scale: rules that only work because a human reads every file

**Requirement.** Any rule that depends on a human having read a file is a habit, not a
rule, and must be stated as such.

**Ranked candidates.**

1. **Tag every requirement with the scale assumption it makes; reject any that
   presupposes exhaustive manual reading** — score 9/10. Generality 2 · Verifiability 1
   · Evidence 2 · Consequence 2 · Novelty 1.
   *This class is not a check. It is the discipline the audit itself is subject to* —
   R-J5 requires the result to hold at 14,589 files, and the read itself is a manual
   process that will not scale to the corpus.

2. **Automate the audit** (the `wiki-cognition` skill + `ARENA.md`) — score 8/10.
   Retained as the mechanism for #1. This is the current work.

**Evidence.** 802's index correct on first inspection but regenerated 17 days later
(CP-060) — a manual pass found a stale artifact that automation would have caught.
**Open.** None.

---

## C-011 · Configured is not running (mechanism status must be an observed postcondition)

**Requirement.** A mechanism's status is its last **observed postcondition**
(process alive, query returned rows, endpoint answered), never the presence of an
enabling config value. `ENABLED = true` in a file the system wrote is evidence that
someone wrote a file.

**Ranked candidates.**

1. **Status is a probe result with a timestamp and the probe's own failure output;
   config state is a separate, differently-named field** — score 9/10. Generality 2
   · Verifiability 2 (the probe either returns or it does not — no judgment) ·
   Evidence 2 · Consequence 2 · Novelty 1.
   *Evidence, tranche 2:* `active-wiki/decisions/2026-09-16_honcho-dreaming-surprisal.md`
   carries **all three states in one table** — Honcho API "✅ Running", dream "⚠️
   Likely inactive — Workspace returned 404", surprisal "❌ Disabled (default
   `false`, needs explicit opt-in)" — while the same file prints a full `config.toml`
   with `ENABLED = true`, `TOP_PERCENT_SURPRISAL = 0.1`, `TREE_K = 10`. **The
   configuration is complete, plausible and correct, and the mechanism it enables is
   probably not running.** This is the *strongest available form* of the C-002
   inversion: the artifact is machine-generated and validated, the behaviour is
   absent, and nothing in the schema distinguishes them.
   *Consequence for the arena:* a brain design graded on its config is graded on
   nothing. This class is why Area 6 holds UNTESTED and not LOW.

2. **Startup self-report: every subsystem prints a probe result on boot** — score 7/10.
   Retained as the mechanism for #1, cheaper and catches a dead-on-arrival component
   but not a slow decay.

3. **Health-check cron asserting each component answers** — score 8/10. Retained as a
   *complement*: catches a component that dies after boot, which #2 cannot. Note the
   corpus already runs two (`2026-09-20_cron-job-errors.md` records "Daily Health
   Check" and "Autognosia Health Check", both failing the same `Directories` check) —
   so the mechanism exists and is not yet trusted with the question.

**Rejected variants.** Reading `ENABLED` (the defect itself). A single boolean
`active: true/false` — recreates the conflation at smaller scale; a component can be
*configured*, *running*, and *effective*, and those are three different facts.

**Evidence.** 2026-09-16 (three states in one table + a complete config),
2026-09-20 (two health checks, one shared failure).
**Open.** Does any probe in the current stack assert *effectiveness* (the dream
actually produced output) rather than *liveness* (the deriver is up)? A deriver
that is up and producing nothing passes every check above.

---

## C-012 · A citation must be checked against the string it cites

**Requirement.** Every quoted claim carries a locator that a mechanical check can
confirm: the cited file exists **and** contains the quoted string. Existence alone
is not verification.

**Ranked candidates.**

1. **Extract each `file:line` or quoted-span citation and grep it; fail on miss** —
   score 10/10. Generality 2 · Verifiability 2 (`grep -F` on a literal string; no
   judgment, no model) · Evidence 2 (measured this run, below) · Consequence 2 ·
   Novelty 1.
   *Evidence:* `ARENA.md` Area 5 Slot 1 asserted the corpus records *"a second
   simultaneous call returns 503"* and cited
   `active-wiki/concepts/speech-to-speech-pipeline.md`. **That file contains no
   `503` at all.** The claim is true and lives in
   `concepts/webrtc-realtime-voice.md:29` and, independently,
   `decisions/2026-09-22_dashboard-voice-integration.md:46`. A true claim with a
   false citation survived a full arena rewrite.
   *Why it survived:* the only automated check in play was *does the target file
   exist* — and it did. **A resolvable path is not a verified citation.** This is
   C-001 ("provenance is not authority") applied to the arena's own output, which
   makes it a self-inflicted instance and therefore hard to dismiss as a corpus
   problem.

2. **Spot-check a sample of citations per run** — score 7/10. Retained as the
   fallback where full extraction is impractical. Weakness: sampling cannot
   distinguish a 5% and a 50% miss rate, which is exactly the distinction that
   matters for trusting a file.

3. **Cite by immutable content hash, not filename** — score 6/10. Retained as an
   *addition*: survives the file being rewritten, which filename citations do not —
   a file can be edited to remove the line after the claim was made.

**Rejected variants.** Trusting the reading agent's recall (it is the thing that
errored). `okf_gate.py` as currently written (frontmatter/structure validity — it
cannot know what a downstream file claims about an upstream one).

**Evidence.** Measured 2026-09-26 in `ARENA.md` Area 5 Slot 1 (see above);
`VERIFICATION.md` §A carries the corrected citation and the three unre-checked ones.
**Open.** Three further `ARENA.md` citations are unverified against their quoted
strings and are queued. Until they are checked, the arena's citation *count* is not
evidence of anything except that the arena cites a lot.

---

## C-013 · Auditable state must be append-only and reconcilable

**Requirement.** A state file that records *what has been done* may only be
updated by appending, and any external rewrite must be detectable by a check
that needs no model. A progress ledger that can silently lose marks is worse than
no ledger: it is authoritative-looking and wrong.

**Ranked candidates.**

1. **Append-only progress log plus a derived counter; a reconciliation check
   runs every run and fails loudly on mismatch** — score 10/10. Generality 2 ·
   Verifiability 2 (`grep -c` on marks, compared against the recorded count — no
   judgment) · Evidence 2 (**three observed mark-count drops**, now explained —
   see the correction below) · Consequence 2 · Novelty 1.
   *The check itself is sound and was the only thing that noticed:* each of the
   three events was invisible to the summary table and visible to `grep -c`. A
   reader trusting the file's own summary would have believed 20 files read when
   41 had. **Keep the check.**
   *But the evidence for this requirement was wrong, and the correction matters
   more than the requirement.* Tranches 1–3 recorded these as reversals by "an
   unidentified writer" acting ~2 minutes after arena writes, and this class was
   scored partly on that. **The writer was this job's own operator: the arena was
   deliberately restarted at 2026-09-26T05:49Z on explicit user instruction.**
   The full 736-line arena, the 30 KB infra file, the 166 KB ledger and the 14 KB
   verification file were archived intact at `prior-run-20260926T054909Z/`, with
   `.prior-run-latest` pointing at them. **No data was lost.** The mark counts
   looked like data loss and were an intentional, fully-preserved reset.
   *What actually failed:* three tranches spent effort hunting a phantom adversary
   and, worse, wrote "treat any unexpected drop in the read count as this until
   proven otherwise" into `VERIFICATION.md` as standing guidance. That converted
   an unexplained observation into a durable false claim, and the archive
   directory that would have answered the question in one `ls` was sitting in the
   workspace the entire time.
   *The correct rule, replacing the one just retracted:* **an unexpected state is
   evidence, not a diagnosis. Check the archive and the pointer before naming a
   cause.** A count-check tells you *that* something changed; it never tells you
   *who*.

2. **Content-hash each marked file into the ledger, so a reverted mark is
   detectable as a hash mismatch rather than a missing character** — score 7/10.
   Retained as the mechanism that survives a *partial* rewrite, which a count
   cannot distinguish from a deliberate edit.

3. **Timestamp and PID-stamp each ledger write; refuse writes from an unexpected
   writer** — score 5/10. Rejected as detection: the writer is unidentified, so
   a stamp records the anomaly without preventing it, and a lock that fails
   closed would block a legitimate repair.

**Rejected variants.** Version-controlling the ledger (already in git, and the
reversal is not being reverted *from* git — a `git checkout` would show in the
reflog). Relying on the job scheduler to own the file exclusively (the scheduler
is the thing that observed the damage).

**Evidence.** Three mark-count drops at tranches 1–3, **all now attributed to the
deliberate arena restart of 2026-09-26T05:49Z** (see `VERIFICATION.md` E-1). The
drop is real and the check that caught it is real; the adversarial reading was not.
**Open.** ~~The writer is unidentified.~~ **Closed 2026-09-26: the writer was the
operator, acting on an explicit user instruction, and the state was archived rather
than lost.** The residual question is narrower and worth keeping: *should a
destructive-looking reset of a progress ledger require an in-band marker, so the
next run can distinguish "operator reset me" from "something broke me" in one
read?* `prior-run-*.md` directories plus `.prior-run-latest` answer that only if
the reader knows to look — which is the actual defect, and it cost three tranches.

---

## C-014 · A citation without a resolvable identifier is decoration

**Requirement.** A source line either carries an identifier a machine can resolve
(arXiv id, DOI, ISBN, ACL anthology id, or a real URL) or it does not claim to be
a citation. Bare venue names, bare `arXiv`, and empty `sources:` lists presented
in a `sources:` field are the same defect at three severities.

**Ranked candidates.**

1. **Validate every `sources:` entry against a declared identifier grammar;
   a source line with no identifier is a lint failure, not a warning** — score
   9/10. Generality 2 · Verifiability 2 (regex for the id forms; no judgment) ·
   Evidence 2 (below) · Consequence 2 · Novelty 1.
   *Evidence, tranche 3, across 20 research reports:*
   - `round36-2026-09-06.md` §4 cites ODL-TempLLM as **"ACL 2026, Long Paper"**
     with `(arXiv)` and **no identifier at all**; the file's own numbered
     `Sources` list ends at an entry with the same defect.
   - `round36` §§6, 7, 10 (TUNSR, ORT, EvolveMem) carry a bare `(arXiv)` and
     nothing else; Context Cartography (§9) carries `(arXiv)` with no id.
   - `round35-2026-09-06.md` has **`sources: []` and `tags: []`** in frontmatter
     while its body lists ten works with identifiers in §Key Works Cited — the
     structured field is empty while the prose field is populated. `round36`
     repeats it.
   - `round34-2026-09-05.md` uses YAML flow-mapping `sources:` (`{'GrOIL': '...'}`)
     where most files in the corpus use a YAML sequence. A parser written for
     the common shape silently gets a dict instead of a list.
   *Why this is a design defect and not trivia:* every grade in `ARENA.md` is
   currently `unverified` because nothing can check a citation. The blocker is
   not the checking step — C-012 supplies it — it is that **half the citations
   have nothing to check against.**

2. **Normalise the `sources:` shape to a sequence of `{id, kind, locator}`
   objects at the generator** — score 8/10. Retained as the *mechanism* for #1;
   also fixes the flow-mapping divergence on its own, since a dict cannot be
   validated as a list of sources.

3. **Permit a bare venue string but mark it `unresolved: true`** — score 6/10.
   Retained as a *migration path* so the check can be introduced without failing
   every existing file at once. Honest cost: a permanent exemption is where
   unresolvable citations go to be forgotten.

**Rejected variants.** Counting citations (C-002 candidate #2 already rejects
this: 842 has six reference lists and resolves nothing). Requiring a URL (some
legitimate sources are print-only, and this would push authors to invent one).

**Evidence.** `round34` frontmatter `sources:` shape; `round35` and `round36`
empty `sources:`/`tags:` against populated bodies; `round36` §4 "ACL 2026, Long
Paper" and §§6, 7, 9, 10 bare `(arXiv)`.
**Open.** None — directly implementable against
`/home/operator/hermes-brain/standards/okf-schema.yaml`. Whether the bare-venue
exemption should exist is the only judgement call.

---

## C-015 · A design claim may cite nothing, and nothing flags it

**Requirement.** Every claim in the corpus that a design *depends on* must name
the file or paper it rests on, or be marked `UNTESTED — uncited`. A page may not
carry a load-bearing design assertion with no source field and no review flag.
Scale note (R-J5): at 14,589 files, "some human noticed this page has no
citation" is a habit, not a rule, so the check must be executable.

**Distinct from C-014, and the distinction is the whole point.** C-014 says a
*citation* must carry a resolvable identifier. C-015 says **a design claim must
have a citation slot at all.** A page with `sources: []` and a design assertion in
prose passes C-014's grammar check — there is no malformed identifier to reject —
and still carries an unsourced claim. The prior 14 classes all assume a citation
exists and ask whether it can be trusted. This one asks whether there is one.

**Evidence, tranche 5 (ORDER lines 1–20, 2026-09-26, all fifteen
`active-wiki/concepts/` files read whole).** Every one carries
`source: "session:<id>"` or `source: "cron:online-lane-b:<ts>"` and **no
`verified:` block, no `confidence:` field, and no citation of any kind** — while
carrying design assertions of very different strength:

- `signal-reliability-fusion.md`: "RC-AD demonstrates 3.25× improvement with
  reliability gating (Recall@FAR=0.05: 0.335 vs 0.103)" — a quantified result with
  no dataset, no detector, no N, and nothing to check it against.
- `multi-objective-bandit-drift-tuning.md`: three named algorithms with venues and
  years ("MOL-TS, NeurIPS 2025"; "CSTS, ICPR 2026") and a regret bound, cited
  nowhere on the page.
- `speech-to-speech-pipeline.md`: 28 tools, a full component list, a rejected
  alternative (REST audio) — all asserted, none cited.
- `decision-logger.md`: a SQL schema and three synthesis passes, none cited.

**Why this is a design defect and not trivia.** The arena's grades rest on this
distinction. Three of the five areas earned in this tranche grade `UNTESTED` on
design **because the corpus supplies no source to check** — that is F2-1 in
`VERIFICATION.md` made load-bearing. A schema that permits an uncited design claim
cannot be distinguished from a schema that permits a cited one, so no grade in the
arena can ever be raised from LOW to HIGH on corpus evidence alone. The check is
cheap and the absence of it is the constraint on the whole grading system.

**Ranked candidates.**

1. **Require an explicit `evidence:` field — `cited` | `uncited` | `tested` — on
   every page carrying a design assertion; a page with neither the field nor a
   resolvable source is a lint failure.** Score 9/10. Generality 2 ·
   Verifiability 2 (presence check, no judgment) · Evidence 2 (above) ·
   Consequence 2 · Novelty 1.
2. **Extend the C-014 identifier grammar to treat a missing `sources:` on a
   design-bearing page as a failure rather than an exemption.** Score 8/10 —
   subsumed by #1, kept because it is the same change in the same validator.
3. **Emit `evidence: uncited` automatically at the generator for every new page
   and require a human to clear it.** Score 6/10. A migration path; honest cost
   is that "auto-filled" becomes permanent, which is where C-003's unresolvable
   links go to be forgotten.

**Rejected variants.** Requiring citations on *every* page (configuration records
cite nothing and should not; `nohup-disown-pattern.md` documents a shell pattern
and needs no reference). Counting cited pages as a quality score — the corpus-wide
citation density is already high and already meaningless, which is C-002.

**Open.** Whether `evidence:` is a new field or an inference from the presence of
`sources:` + `verified:`. A new field is explicit and costs a schema change; an
inference is free and is exactly the kind of check that C-002 warns cannot be
trusted. **Recommend the explicit field**, on the grounds that a rule which cannot
fail silently is worth more than one that is cheap.

---

## C-016 · A derived document must declare what it derives from

**Requirement.** A file that summarises, indexes, mirrors or re-states another
artifact carries a machine-readable `derives_from:` naming the source (or the
`source:` session it came from), so a reader can tell an independent
observation from a second reading of the same one. **Two documents with the same
`derives_from` are one source, always, no matter how many files they are.**

**Distinct from C-014 and C-015, and the distinction is the whole point.** C-014
asks whether a citation carries a resolvable identifier. C-015 asks whether a
design claim has a citation slot at all. **Both presuppose one source and ask
whether it can be traced. This class is about the second problem: the corpus
contains multiple files that are the same source, and nothing marks them.** The
consequence is not hygiene — it is that an evidence count is wrong.

**Evidence, tranche 2 (ORDER lines 30–49, all read whole this pass).** Measured,
not inferred:

1. **Two entity pages, one session.** `entities/speech-to-speech-server.md` and
   `entities/gods-eye-view.md` both carry **`source:
   "session:20260921_213949_16a2fbde"`** and both describe the same build: the
   same 28 tools, the same WebRTC protocol, the same `10.0.0.10:8765` server, with
   `created`/`updated` both 2026-09-22. **They are one observation written down
   twice on two different pages of the wiki.** Tranche 1 recorded the
   server-plus-consumer architecture from the concept pages and correctly declined
   to claim two implementations; this pass read the entity pages and found the
   reason it *could not* claim two. The count is 1, and the `source:` field would
   have said so in one read had anyone asked.
2. **The same shape at report scale.** Six research reports in lines 41–45 are
   comprehensive "Frontier Research Comprehensive Update" documents dated
   2026-09-01, 2026-09-10, 2026-09-10, 2026-09-11 and 2026-11-15. **They cite
   the same ~50 primary papers, several of them repeatedly across all of them**
   (OaK 2608.22974 in three of the six; structural hallucination 2603.01341 in
   five). A reader counting "files that mention X" gets a support count of five
   for a single study. The arena is written explicitly against this — the skill's
   "three files restating one study are one source" rule — **and the rule had to
   be enforced by hand, per slot, because the corpus marks nothing.**
3. **A derived file that outruns its own source.** `…-comprehensive-update-2026-
   september.md` (dated `2026-09-10`) opens its `Relation` field claiming to
   "extend the **November 2026** comprehensive update." Its `verified:` block
   reads `by: "Hermes Agent (cron)" at "2026-09-10T22:00:00Z"` and
   `confidence: high`. **A file generated on 10 September cannot have read a
   document generated on 15 November.** The derivation points forward in time.
   See `VERIFICATION.md` §B-11.

**Why this is a design defect and not trivia.** The arena's entire evidentiary
apparatus — grades, support counts, the LOW/HIGH boundary, corroboration — rests
on counting *independent* sources. **A corpus that cannot distinguish a second
source from a second copy will inflate every count in it, and an inflated count
raises a grade.** This is the direct cause of one correction made this pass: Area
5's rank-1 support count was implicitly 2 and is now recorded as 1. That
correction was found by reading two frontmatter fields, not by a check. Under
R-J5 — 14,589 files — no run will catch this by reading.

**Ranked candidates.**

1. **Require `derives_from:` on any file that is not a primary observation;
   make the support count a `uniq(derives_from)` rather than a row count.** Score
   9/10. Generality 2 · Verifiability 2 (a set-unique over one field; no
   judgment) · Evidence 2 (above, three independent instances) · Consequence 2 ·
   Novelty 1.
   *Beats:* #2 because the failure is not "the field is missing" — `source:
   "session:<id>"` **already exists and is already correct on both entity pages.**
   Nothing is wrong with the corpus's data; the wrong thing is that nothing reads
   it for this purpose. No migration is needed.
2. **A provenance check that fails when two files share a `source:` id and are
   not marked as mirrors of each other.** Score 8/10. Retained as the
   *mechanism* for #1, and the one that runs without a schema change.
3. **Strip the `verified:` block from derived files at the generator** — Score 5/10.
   Rejected as a fix: it removes the misleading signal without adding the true
   one, and `verified:` is load-bearing for other checks. Instance 3 above shows
   the block is *not* the bug; the missing derivation is.

**Rejected variants.** Counting unique paper titles across the corpus (works
today by hand, does not survive a reworded title, and is not expressible as a
rule). Deprecating `source:` in favour of a richer provenance model (C-001
already requires the split; this class is a consumer of it, not a replacement).
Deduplicating the reports (deletion — the golden rule, and the duplication may be
intentional round-keeping).

**Open.** Does the graph builder treat a derived file as a node distinct from its
source? If it does, every derived document is a second witness to its source in
the graph, and the contamination is in the retrieval substrate rather than only in
the prose. This is the same question C-003 leaves open, and the answer is one
query away.

---

## C-017 · The same identifier may back two incompatible summaries `NEW — tranche 3`

**Requirement.** When two files cite the same resolvable identifier, their
substantive claims about that source must be **comparable**. Where they are not,
the corpus must mark which one is a primary reading and which is a restatement, and
a design that consumes the contested claim must cite the *contested* field, not the
identifier.

**Distinct from C-014, C-015 and C-016, and the distinction is the whole point.**
C-014 asks whether a citation carries an identifier. C-015 asks whether a design
claim has a citation slot. C-016 asks whether a derived document declares what it
derives from, so a second copy is not counted as a second source. **All three are
about the presence and multiplicity of citations. This class is about their
*content* disagreeing while every check above passes cleanly.**

**Evidence, tranche 3 (ORDER lines 50–69, twenty ontology rounds read whole this
pass) — one paper, two four-layer taxonomies, both in files that pass C-014.**

CMA / Animesis (arXiv 2603.04740) is described in two rounds with **different
layer names and different layer semantics**:

| Source file | Four layers as named |
|---|---|
| `round35-2026-09-06.md` §2.2 | **Constitution** / **Identity** / **Operational** / **Session** |
| `round44-2026-09-10.md` §5.2 | **Governance** / **Epistemic** / **Experiential** / **Procedural** |

**These are not one taxonomy under two vocabularies.** *Identity* ("what the agent
is") and *Core memory* ("inalienable facts") are not *Epistemic* ("what it knows"),
and *Session* (an ephemeral buffer) is not *Experiential* (the accumulated
engram). Round 44 goes further and rests an argument on the difference — the claim
that **"no prior AI memory system places governance before functionality"** is a
different claim from round 35's, and it is only true of the Governance/Epistemic
reading. One of the two files has the taxonomy wrong.

**What makes this a design defect and not trivia, and why it is filed under §7's
exception.** `ARENA.md` Area 11 Rank 1 is *built on this taxonomy* — the
constitution/immutable → core/inalienable → operational/audited → ephemeral/TTL
layering is the design, and the arena inherited whichever reading the earlier
tranche copied. **An architect would change the design because of this**: the two
taxonomies imply different mutation authority, different persistence, and a
different answer to "can the system delete this?" So the instance is queued
(`VERIFICATION.md` §H-2) *and* the requirement is a design requirement.

**Why none of the existing checks catch it.** The identifier is present and
resolvable in both files (C-014 clean). Both files cite a source (C-015 clean).
Neither declares `derives_from:` relative to the other, so C-016 cannot collapse
them — **and note that C-016's remedy would make this *worse* if applied naively**:
marking round 44 as a restatement of round 35 would assert that one is correct, and
the evidence says one is wrong.

**Ranked candidates.**

1. **A `claim:` field: every substantive statement a derived document makes about
   a cited source carries a stable id, so two documents' claims about one paper can
   be diffed.** Score 9/10. Generality 2 · Verifiability 2 (two sorted claim-id
   lists, `comm`; no judgment) · Evidence 2 (measured this pass) · Consequence 2 ·
   Novelty 1.
   *Beats:* #2 because the taxonomy names are free text, but a *claim id* is
   authored once and reused, so divergence becomes a set difference rather than a
   reading judgement.
2. **A two-file claim-comparison pass over files sharing an identifier, flagging
   any where the same source is described with different entity names.** Score 7/10.
   Retained as the *detector* for #1 and the only one that works on the corpus as
   it stands today (no schema change). Weaker than #1 for the reason C-004
   documents: a name-set comparison cannot tell a synonym from a contradiction
   ("Constitution" vs "Governance" might be either), so it flags rather than
   proves — **which is the correct behaviour for a linter and the wrong behaviour
   for a decision.**
3. **Require that any design slot citing a contested source records the contention
   in its own text.** Score 8/10. Retained as a *consumer* rule and the cheapest
   thing to do today; it is a discipline on `ARENA.md`, not a fix to the corpus.

**Rejected variants.** Verifying the paper against the actual arXiv PDF inside the
read (out of scope for a read pass, and it would resolve the question rather than
record it). Trusting the later file because it is more recent — the two files are
nine days apart and the divergence is not drift, it is one of them being wrong,
and recency is not a tiebreaker for a taxonomy. **Marking one file wrong in the
corpus** — corpus files are not modified by this work, and the choice between them
is a primary-source question.

**Evidence.** `round35-2026-09-06.md` §2.2 and `round44-2026-09-10.md` §5.2, both
read whole this pass; both citing arXiv 2603.04740.

**THIRD READING, found three tranches later — and this changes the class.**
`round54-2026-10-12.md` §1.2 describes the same paper (arXiv 2603.04740, now
attributed to **"Zhenghui Li," RVHE Group / Animesis Memory Project**, with three
named axioms — Memory Inalienability, Model Substitutability, Governance Precedes
Function) as organising memory around a **four-layer governance hierarchy of
Constitution / Charter / Law / Regulation**.

**So the CMA taxonomy now has three readings, and no two of them agree:**

| Reading | Layers | File |
|---|---|---|
| 1 | Constitution / **Identity** / Operational / **Session** | `round35` §2.2 |
| 2 | **Governance** / **Epistemic** / **Experiential** / **Procedural** | `round44` §5.2 |
| 3 | Constitution / **Charter** / **Law** / **Regulation** | `round54` §1.2 |

Reading 3 shares exactly one layer name with reading 1 and none with reading 2.
**"Charter," "Law," "Regulation" is a legislative vocabulary; "Identity" and
"Session" are a cognitive one. They are not translations of each other — they
describe different things.** The C-017 remedy assumed two readings and a
majority to break. **Three readings and no majority: 1–1–1, with reading 1 also
being the only one whose first layer repeats reading 3's.** The class therefore
needs the *primary source* more urgently than it did two tranches ago, not less,
and the arena's Area 11 rank-1 design — which is built on a four-layer hierarchy
with a governance ordering — should be understood as resting on **a design
principle the three readings agree on (governance before function) and a specific
taxonomy none of them can confirm.** That separation is the honest form of the
slot, and it is recorded in `ARENA.md` Area 11 Rank 1 this pass.

**Open, and it is the more important half of this class.** C-017 proves the corpus
can disagree with itself about a source. **It does not yet prove the corpus
disagrees with the source.** The counter-instance runs the other way: round 35
carries the sharper, more checkable claim (the "hourly `brain_sync` that appends
without conflict adjudication" is a real observation about *this* system, and it is
the version the arena's rank 1 rests on), while round 44's version carries the
sharper *argument*. Both read as confident, and neither marks the other. **Which
is closer to the paper is unknown and is queued as §H-2 rather than guessed.**

**FIFTH INSTANCE — RE-READ AT SOURCE 2026-09-26 (ORDER line 81,
`round59-2026-09-06.md`). The previous run recorded this as a one-line claim carried
from a transcript; it is now a re-read instance, and it is much larger than the
claim.** The file's own `id:` field reads **`frontier-research-ontology-round56-2026-09-05`**
— the identifier of ORDER line 78 — while its filename, title and H1 all say
**round 59 / Round 56**. It is a duplicate of `round56-2026-09-05.md` under a
different round filename. **But the duplication is not a copy: it is a rewrite with
four different arXiv bindings for the same eight papers.** Read at source:

| Paper named in both files | `round56` (line 78) | `round59` (line 81) |
|---|---|---|
| OntoURL | **2505.11031** | **2505.11031** ✓ agrees |
| Stable Matching Alignment | *(folded into Open Ontologies)* | **2604.02847**, "Game-Theoretic Convergence" |
| Open Ontologies | **2605.09184** (Rovai) | **2605.07984** |
| Neuro-Symbolic Consistency | **2504.07640** (Magana, Monti) | **2603.15293** |
| LLM-KG survey (Bian) | **2510.20345** | **2510.20345** ✓ agrees |
| OG-RAG | **2412.15235** | **2412.09615** |
| FOIS 2025 | IOS Press FAIA Vol 409 | "15th Intl **Workshop**" |

**Five identifiers disagree, two agree, on the same eight papers.** And the
*measurements* disagree too, which is the part that damages the arena rather than
the index: `round56/59` reports OntoURL at **35–55% on symbolic reasoning vs 85–95%
natural language** and describes the paper as **12 task types**; `round57` reports
**understanding 80–92%, reasoning 3–4 pp lower, best model 68.8% on R5, class
hierarchy construction at 0.1–2.0% BERTScore, across 15 tasks and 57,303
questions**. **Same benchmark, same identifier, two different result sets — and I
absorbed the `round57` numbers into Area 8 Rank 1 earlier in this very pass before
reading this file.** Under C-017 that is two incompatible summaries; under C-018 it
is worse, because the two summaries are carried by two *different* bindings of four
*different* identifiers.

**Consequence for the check in candidate #1, and it is a design requirement now.**
`uniq(identifier → title)` still cannot see this: both files bind identifiers to
plausible, differently-titled papers. **The check that catches it is
`uniq(benchmark-name → reported metric)`, or more practically a *content* hash
keyed on round-filename** — and neither is derivable from the citation fields that
C-017 and C-018 already police. **The honest generalisation: identifier uniqueness
is necessary and not sufficient; a corpus that re-derives claims from papers under
an automated programme will produce two internally-consistent, mutually-incompatible
accounts of the same paper, and no field-level lint on citations will ever see it.**
That is recorded here as the *open* half of the class, and it is the strongest
corpus-hygiene finding this workspace has produced — because it is C-002 stated
from the other side: **the validated path (a clean citation block, a real
`confidence: high`) produced two incompatible accounts of the same evidence, and
`verified: []` was empty in both.**

**Also newly visible at source, and it is a genuine `UNSUCCESSFUL` the corpus never
marked:** `round59` §1.1 claims OntoURL shows models "at or near chance," §1.2
gives 35–55%, and §1.1's own framing is a **grounding gap** — while `round57` §1.3
gives 80–92% on understanding. **The corpus contains both "at or near chance" and
"80–92%" for the same benchmark, and the file that says "at or near chance" is the
one carrying the wrong identifiers.**

---

## C-018 · One identifier may name two different papers `NEW — tranche 4`

**Requirement.** Every resolvable identifier in `sources:` must map to **exactly one
(title, author-set) pair** across the whole corpus. An arXiv id, DOI or ISBN that
appears against two incompatible titles is a **hard lint failure**, and any
`ARENA.md` slot resting on it must cite the *contested identifier*, not a paper.

**Distinct from C-017, and the distinction is what earns this class.** C-017 says
one identifier, two **incompatible summaries** — the corpus disagrees with itself
about what a paper said, and either reading could be right. **C-018 says one
identifier, two different papers** — at most one binding can be right, no reading
resolves it, and the *identity* of the source is in doubt. C-017's remedy (mark
the restatement, cite the primary) is unusable here, because it presupposes we know
which file names the real paper.

**Evidence, tranche 4 (ORDER lines 70–71, read whole this pass) — one arXiv id,
two papers, and the collision lands on an arena rank-1.**

`round49-2026-09-20.md` §6 sources **"Structural Hallucination in LLMs: Network-Based
Evaluation of Knowledge Organization"** to **Huang et al., arXiv 2602.05636**.

That identifier is already bound, in the arena, to a different paper:

| Binding | Source | Where it entered the arena |
|---|---|---|
| **arXiv 2602.05636** = *Generative Ontology* (Cheung) | `round38-2026-09-07.md` §5 | **Area 14 Rank 2** |
| **arXiv 2602.05636** = *Structural Hallucination in LLMs* (Huang et al.) | `round49-2026-09-20.md` §6 | this pass |

So **one id carries a creativity paper and a hallucination-evaluation paper**, with
no author in common, in files that pass C-014 cleanly. Compounding it: the
*title* "Structural Hallucination in LLMs" is itself bound twice elsewhere —
`round49` gives it **2602.05636 / Huang et al.**, while **Area 8 Rank 1** gives the
same experiment (Roget's node-set Jaccard 0.028, >94% source mismatch) to
**arXiv 2603.01341 / Boudourides**. Same findings, different id *and* different
author. **One of the two id bindings is wrong and the corpus does not know which.**

**Why this is a design defect and not trivia.** Area 14 Rank 2 is the arena's
**entire constrained-creativity design** — executable Pydantic schemas, enums
forcing the ontological vocabulary, the 5.03 → 0.10 → 0 error result — and it is
graded `LOW` on a single paper whose identifier is contested. **An architect would
change the design**: if the underlying paper is the hallucination-evaluation work,
Area 14 Rank 2's evidence base is wrong, not merely unverified.

**Ranked candidates.**
1. **A corpus-wide identifier-uniqueness check: `uniq(identifier → title)` over all
   `sources:`; fail on any mapping to two titles.** Score 10/10. Generality 2 ·
   Verifiability 2 (a set-unique over two fields, no judgment) · Evidence 2 (measured
   this pass) · Consequence 2 · Novelty 1. *Beats* #2 because the defect is a
   data collision, not a missing field, and a resolver cannot see it.
2. **Require `title:` alongside every identifier in `sources:`.** Score 8/10 —
   retained as the *enabling* change; without the title there is nothing to compare,
   which is exactly why this went unnoticed across 70 files.
3. **Downgrade every slot citing a collided identifier to `UNTESTED` automatically.**
   Score 7/10 — retained as the *consumer* rule and the cheapest thing to do today.

**Rejected variants.** Resolving against arXiv inside a read pass (out of scope for
a read; and it would *resolve* rather than record). Trusting the more recent file —
C-017 already rejects recency as a tiebreaker. Deleting the duplicate (golden rule;
and one of the two is a legitimate paper).

**Open.** Is this one collision or the visible edge of a class? At 70 files read,
**1 collision involving 1 id and 3 slots** is a rate with no denominator worth
extrapolating from. **The check in candidate #1 is the only way to get the
denominator, and that is the argument for building it before arguing about it.**

**SECOND INSTANCE, found on the next file read (ORDER line 73) — a different
shape, which is what makes the class real.** arXiv **2605.09184**, the stable-matching
alignment paper, is attributed to two different author sets:

| Binding | Source file | Author set |
|---|---|---|
| 2605.09184 = *Stable Matching Alignment* | `round48-2026-09-18.md` §8 | **Beverley, Elkin, Ravenel, Archer, Parente de Oliveira, Lopes** (6 names) |
| 2605.09184 = *Stable Matching Alignment* | `round51-2026-09-20.md` §7.5 | **Rovai et al.** (1 name) |

Same id, same title, **disjoint author sets** — and the first binding has no
"Rovai" in it. So C-018 has now caught **a title collision (§71) and an author
collision (§73)**, on two different identifiers, in two different files, within
three reads. **A class that produces a new shape on its second instance is a class
and not an anecdote.** Note the *damage* differs too: §73's collision is harmless
to the arena (nothing ranks on it), which is precisely why it survived unnoticed
while §71's collision silently demoted a rank-2 slot.

**THIRD BINDING, one file later (§75) — and it tips the balance without settling
it.** `round53-2026-10-05.md` §3 binds **2602.05636 → Generative Ontology (Cheung,
Benny)**, adding a venue (*"published in Open MIND"*) and a full author name. The
identifier is now bound **2-to-1 for Cheung** (rounds 38 and 53) against **1 for
Structural Hallucination** (round 49). **A count is not a resolution** and the
arena has explicitly declined to restore a grade on one (Area 14 Rank 2, same pass)
— the reason is the same in both places: a majority among three generated files is
inference, and C-018's whole point is that the check, not the vote, is the
mechanism. **The denominator is now three files and two shapes; that is enough to
say this is a class, and not enough to say which binding is true.**

**A separate finding this class produced for free, and it is the cleanest
instance of C-002 in the corpus because the corpus reports it against itself.**
`round53-2026-10-05.md` §2.3 records DaoQL's headline — **94% composable
counterfactual decomposability versus 45% for GPT-4o alone**, a 49-point gap,
backed by latency figures (graph BFS 1.20 ms, HNSW 83.1 μs), a hybrid-query
benchmark, and **LDBC SNB SF1 34/34 query coverage** — and then reports, in the
same paragraph, that **its own peer reviewer found Theorem 1 "closer to
definitional than architectural" and the 94% headline "not auditable from the
submitted text."**
**That is the arena's governing inversion, arrived at by a human reviewer rather
than by this audit: the apparatus around the claim is impeccable and auditable —
every microsecond, every query covered — and the claim itself is not auditable at
all.** No linter in C-001 through C-017 can detect this, because the defect is not
a malformed field; it is a *well-formed, correctly-measured environment wrapped
around an unmeasurable assertion*. **It is also the strongest available argument
for a requirement nobody has written yet: a headline result must carry its own
auditing procedure, or the numbers that describe its environment do not count on
its behalf.** The corpus's own instinct — recording the reviewer's caveat in the
same file as the claim, under `confidence: high` — is the behaviour this class
exists to make systematic.

**AND A NEW REQUIREMENT this class forced into existence, which no linter in
C-001–C-017 can check.** The DaoQL instance is a claim whose *environment* is
fully measured and whose *content* is not measurable at all. A field-level check
cannot see it, because every field is well-formed. **The requirement: a headline
quantitative claim carries its own auditing procedure, or the numbers describing
its environment do not count on its behalf.** Concretely — a claim of the form
"X% improvement" must name the population, the baseline definition, and the
procedure a third party would run to reproduce it; a claim missing any of the
three is `unverified` regardless of how many benchmarks surround it.
*Rejected:* requiring an actual reproduction (out of scope for a read, and R-J1
makes cost irrelevant but not effort impossible); requiring a confidence interval
(a statistical bar, not an epistemic one — several legitimate corpus claims are
qualitative and would be excluded by the wrong filter).
**Open.** Does the corpus contain claims that would fail this and are currently
graded *above* `UNTESTED`? **Area 8 Rank 1's 98% clinical accuracy on 60
questions is the obvious candidate and has not been tested against it.** Recorded
as work, not as a finding.

**FOURTH INSTANCE, and this one is detectable inside a single file — which
materially lowers the cost of candidate #1.** `round55-2026-10-13.md` cites
**arXiv 2510.08966 twice, ninety lines apart, for two different papers**:

| Line in file | Paper bound to 2510.08966 |
|---|---|
| §3 | "Beyond Prefixes: Graph-as-Memory Cross-Attention..." — Liu, Ruitong; Lin, Boxu; Li, Peize; Li, Siyuan; Wu, Yunjia; Sun, Te; Wu, Chaohan (GMT) |
| §6 | "Semantic-Condition Tuning: Fusing Graph Context with LLMs..." — no authors given (SCT) |

Different titles, different methods, different author sets, **same identifier, same
document.** A per-file `uniq(identifier → title)` check finds this without touching
a second file at all, which means the expensive-looking corpus-wide check in
candidate #1 has a cheap per-file core that catches the clearest cases first.
**Four instances, three shapes (title collision, author collision, same-file double
binding), in eight files.** *A note on why that rate should not be over-read: the
`.meta/archive/ontology-rounds/` block is one automated programme restating itself,
so collisions concentrate here by construction and this is not a corpus-wide rate.
It is, however, an unambiguous rate for the densest part of the corpus, which is
where an architect reading for design would look first.*

**FIFTH INSTANCE, and the first one at *document* granularity rather than
identifier granularity — `round59-2026-09-06.md` is a whole-file instance.**
This file **duplicates `round56-2026-09-05.md` under a round59 filename, carrying
incompatible identifiers and numbers.** Every previous instance was one field or
one `sources:` line disagreeing with another; this one is an entire document
reappearing under a second round number, with the two copies reporting
*different* identifiers for the same material.

**Why the escalation matters, and it is not simply "more of the same."** A
collided identifier is a bad citation. A collided *document* is two nodes in the
evidence graph that the arena will read as two independent sources, and every
slot that cites one of them has an inflated support count. **The per-file
`uniq(identifier → title)` check in candidate #1 cannot see this at all** — the
collision is between two well-formed files, each internally consistent. It
requires `uniq(round-filename → content hash)` or an equivalent
near-duplicate detection over the archive directory, which is a different and
cheaper check against a different key.

**Provenance caveat, stated because the honesty rules require it and this one
matters.** This instance is recorded from a run in which the file was read and
marked in full, but the **file body did not survive the context compaction that
ended that run** — the finding is carried forward from the run's own verbatim
transcript record, not re-read from the document in the window that writes it
here. It is therefore a **one-line claim, not a verified instance**: the
duplicate relationship is asserted, the specific disagreeing identifiers and
numbers are not itemised, and the next pass that reaches this file should
expand this entry with them or withdraw it. Recorded at the strength it is
actually held at rather than padded out to match the other four.

**A consequence worth recording here because it is the arena's own most-cited
warning, now with numbers.** §73 §7.5 adds that on the same benchmark **an LLM
reading a raw OWL file scores F1 = 0.323 — worse than unaided inference — while
structured tool access reaches F1 = 0.717**, and that *"the matching constraint is
the dominant factor: signal weights are irrelevant when stable matching is
applied."* **The third independent domain in this corpus to report that hand-tuned
or learned feature weights do not matter** (after Area 2's ρ and Area 3's bandit
α). It does not refute them — the domains differ — but three-for-three is no longer
a coincidence, and the check in candidate #1 would cost less than the argument is
worth.

---

## C-019 · A health metric must be computed over the population it claims to describe `NEW — tranche 7`

**Requirement.** Any tier-health, liveness, staleness, or coverage metric must
declare (a) the **population it enumerated** and (b) the **traversal that
enumerated it**, and two runs of the same metric over the same target with
different traversals must not both report a confident verdict. A status column
(`✅ Healthy` / `❌ Stale`) derived from file *existence*, byte size, or a
hand-listed backup filename is a **provenance claim about a filesystem**, and
must be labelled as such rather than as a statement about the system's
functioning.

**Distinct from every prior class, and the distinction is what earns it.** C-009
says live state must not be frozen into static prose. C-002 says apparatus quality
is uncorrelated with claim correctness. **C-019 says a metric can be computed
correctly over the wrong population and therefore report the opposite of the
truth while every one of its component numbers is accurate.** The defect is not a
wrong number; it is a right number about a different set.

**Evidence, tranche 7 (ORDER lines 102–103, two cascade reports read whole this
pass).**

The corpus runs a periodic `cron:memory-cascade` health report over a five-tier
memory stack. Two runs, four days apart, describe the **same** Tier 3
(Oracle Brain) and reach opposite verdicts with no drift in between:

| | `cascade-report-20260916.md` (ORDER 102) | `cascade-report-20260920.md` (ORDER 103) |
|---|---|---|
| Verdict | **❌ Stale** | **✅ Healthy** |
| Files enumerated | **34 root `.md`** (no recursive count given) | **2,013 `.md`** (recursive) |
| Subdirectories | ~183 | 183 |
| Size | 74 MB | 127 MB |
| Modification claim | *"No files modified in 90+ days (all files older than 90 days)"* | *"All 2,013 files modified within last 30 days"*; 236 in last 7; 1,771 in 7–30 |
| Most recent file | not stated | 2026-09-20 04:06 |

**The 09-16 report computed a staleness verdict over 34 root files and stated it
about a 2,013-file corpus.** The 09-20 report enumerated the same 183
subdirectories and found 1,979 files the first report had never looked at. The
first report's own text supplies the refutation it discarded: *"the log showing
activity through September 7 but no filesystem changes since."* **It had
contradicting evidence in hand and preferred the mechanical check.**

That preference then generated a **false recommended action** — *"Investigate
Oracle Brain staleness… determine if this is expected (completed research) or if
ingestion pipeline has broken"* — a four-day investigation of a pipeline that the
next run shows writing 236 files in seven days.

**A confound the second report hands us, which is why this is a defect and not a
scheduling error.** 09-20 records: *"Files from September 9 (13:41 UTC) show batch
git checkout timestamps."* A `git checkout` rewrites mtimes without touching
content. **A staleness detector keyed on mtime is therefore not merely
under-populated; it is actively defeatable by ordinary repository operations.**
This is C-009's failure mode with a *mechanism*: not "state frozen into prose" but
"state inferred from a field that a routine command overwrites."

**The same two files carry two more instances of the class, on the same
production system, and they are the reason this is graded as a design defect
rather than a reporting nit.**

1. **Every plumbing metric green, the function dead.** Honcho Tier 1 on 09-20:
   4/4 containers healthy, 1,431/1,431 queue items processed, 0 pending, 1,380
   messages, 1,380 message embeddings, 8 peers — and **0 documents stored**. The
   report's own words: *"semantic search via documents table is non-functional.
   Only raw message retrieval works."* Plus **1,360 stale queue errors**, all on
   already-processed items, therefore invisible to a pending-count check. **The
   queue drains to zero because the errors are attached to items that already
   completed.** This is the arena's §8 inversion in production, and it is the
   fourth independent instance: validated path (containers, queue, embeddings)
   produces the appearance of health; unvalidated path (can it retrieve?)
   produces nothing.
2. **"Backups current" counted by filename.** 09-16 records *"Backups | 7 tarballs
   (latest: 2026-09-16_030016)"* and grades the tier **✅ Healthy — 13K operations,
   backups current**. 09-20 records the database at **0 bytes** and *"No recent
   .db backups found in the usual backup locations."* **The backup claim was a
   filename listing that was never restored from.** A backup that has not been
   restored is a hypothesis about a backup.

**Why a good architect changes the design because of this.** The arena's
memory designs (Areas 4, 6, 7, 8, 11) all specify *what* is stored and *when* it
is consolidated. None of them specify **how the system's own health is
established.** Under C-019, a brain design that ships with tier-health reporting
must specify: metric population, traversal, and a **restore test**, not a
file count. Without it, a green dashboard is compatible with a dead retrieval
path and a destroyed database — which is precisely the state 09-20 documents.

**Scale note (R-J5).** The 2,013-file figure is the denominator C-019 protects.
At the 14,589-file target, an under-populated traversal does not degrade
gracefully: it reports a *confident* verdict over a sample, and confidence is
what downstream automation acts on. The defect grows with the corpus, not with
the number of checks.

**The corollary, and it is the sharpest thing in this class: the checker exists
and is switched off.** `ingestion-log.md` (ORDER line 104, read whole this pass)
closes with an operational note, not a research note:

> *"pre-existing, NOT changed this run: cron jobs **6537c4376a9c** (OKF Schema
> Lint, read-only) and **3e9f2a2053d9** (OKF Schema Repair, WRITES wiki) are
> both **disabled**, so the schema lint/repair pair built to converge the wiki is
> not currently running."*

**C-005 has ranked "deterministic corpus checks must exist as executable code"
first in its class for several tranches. This is the counter-instance, and it is
not a missing checker — it is a working, paired, read-only-plus-writer
implementation that is not scheduled.** The same log records the gate *did* run
on the day of that entry: *"Gate: 11/11 GATE PASS via `scripts/okf_gate.py
--fix`. One page was rewritten after the gate caught an unresolvable
`[[wikilink]]` in its frontmatter."* **So the checker works, catches real
defects, and is disabled anyway** — which means every C-002 through C-019
instance catalogued in this file is being detected by nothing at
present, and the *only* reason the arena knows about them is that a human-shaped
read happened to walk past them.

**This converts C-005 from a design requirement into a deployment blocker, and
the requirement it implies is new:** *a convergence loop that depends on a
scheduled job is a design with an availability assumption, and the assumption
must be stated and monitored like any other.* Cost is not the axis (R-J1) and is
not the reason; the reason is that **an unenforced invariant is indistinguishable
from an invariant that does not hold**, and the arena's entire corpus-hygiene
apparatus is currently in exactly that state. Recorded as **Open, this pass**, and
it is the highest-value open item in this file.

**The second, independent C-019 instance in this same tranche, and it is the
pure form: a metrics table reporting a green cell for a quantity the same
document says it could not measure.** `maintenance-report-2026-09-18.md` (ORDER
line 106, read whole):

| Section | What the body says | What the Summary table reports |
|---|---|---|
| §1 Orphans | *"**Unable to determine with current structure**"* … *"No obvious orphaned pages detected in the **sampled** content"* | **Orphans \| ~0 \| ✅** |
| §3 Stale pages | Ages given for **5 files**; *"All pages appear to be recent"* | **Stale Pages \| 0 \| ✅** |
| §4 Contradictions | *"analyzed **10 files**"* of 375 | **Contradictions \| 0 \| ✅** |
| §6 Hit counts | Top 10 by hits, **every value 0**; *"the hit counter database may need to be populated or synced"* | *(not in the table at all)* |

**The orphan row is the one worth naming precisely, because the report performs
the C-002 inversion on itself in a single table.** Its body says the metric is
**undeterminable**; its summary reports **~0 with a ✅**; the tilde is the only
honest character in the row, and it is a quantifier over a guess, not over a
count. A downstream reader — a human scanning for the one red cell, or a script
parsing the table — receives `✅`. **An unknown and a zero are not the same
value, and only one of them is a defect the reader can act on.** The other three
green cells share the shape: a *sample* of 5 or 10 files reported as a verdict on
375, in a corpus whose target size is 14,589.

**This is why C-019 is stated as it is.** The requirement is not "check more
files." It is that **a metric whose population is a sample must not emit a
status glyph at all** — it must emit `n/a` with the sample size attached. The
alternative is worse than having no check, because `~0 ✅` actively teaches the
reader that the check passed.

**Three sub-populations reported as corpus-wide verdicts in one document, and a
fourth metric silently dropped from the table when it came back all-zero** — the
hit counter, whose top-10 table is entirely `0` and whose explanation
(*"may need to be populated or synced"*) is the most likely true statement in the
file. **A hit counter reading zero on the wiki's ten most-linked pages is not a
popularity measurement; it is a broken instrument being reported as a
measurement.** This is also, precisely, the failure the arena's own R-J2 exists to
prevent — a number that cannot be believed because the system producing it is
broken — arriving as a *published table row* rather than as a decision.

**Third instance, one day later, and it introduces the failure mode the other two
share: a check whose result is discarded and then restated as the opposite.**
`maintenance-report-2026-09-19.md` (ORDER line 107, read whole) §3:

> *"**Pages without Source: field: 378 of 378 (100%)** — All pages are
> technically orphans per the Source: field check. **This is structural** — the
> wiki is primarily research papers and system logs that don't use cross-linking.
> **Not actionable.**"*

**The check ran, returned 100%, and the finding was reclassified from "every page
is an orphan" to "this is structural, not actionable" inside the same
paragraph** — with no change to the corpus between the measurement and the
reclassification. A 100% failure rate is not a structural property to be noted
and dismissed; it is a check that has just told you it matches nothing, and the
only question worth asking is whether the field name it greps for is the field
the corpus writes. **Two days earlier, in the same tranche, the ingestion log
records ingestion runs that *do* write `Source:`** — `| Source: session:… | Mode:
standard` on multiple entries — **and a later log entry records
`20260924-120400` counting `Pages with no Source: 363/435 (83.4%)`, not 100%.**
Three reports, three values for one property of one corpus, and the 100% reading
is the one that got a verdict.

**The same file also contradicts the ingestion log's own archive record, and this
one is checkable without any judgment at all.** 09-19 §2 reports
**"Archive Directory: Empty (0 pages archived)"** and §7 reports
**"No pages archived (none stale)."** The ingestion log (ORDER 104) carries, at
`20260919-120000` — **eight hours after this report was generated at 04:00** —
*"Wiki maintenance — archived **53** frontier-research-ontology-round files and
8 superseded comprehensive/addenda files to `.meta/archive/`."* **53 + 8 = 61
files archived, after a report that closed by certifying the archive empty.**

**This is C-019 at its most easily caught and therefore most damning: two
reports, eight hours apart, about a directory, disagreeing about whether it
contains 0 or 61 files, and neither is marked uncertain.** The second is not
marked wrong either. Both are trusted, by the same reader, on the same day.
The reconciliation is almost certainly benign — the archive happened later — but
**"almost certainly" is doing the work that a timestamp comparison would have
done exactly, and the check is one `ls | wc -l`.**

**Fourth instance, and this one is the C-003 answer, so it is the load-bearing
entry in this class.** `maintenance-report-2026-09-22.md` (ORDER line 108, read
whole) records **493 broken links** in a 422-page wiki, and resolves them in a
single paragraph:

> *"**493 simple-file broken links** detected (genuinely broken `[[file-name]]`
> references to non-existent pages)"* … *"Many broken links are anchor-based
> (`[[file#heading]]`) or contain commas/special chars — **these are false
> positives from the simple regex check**"* … *"**No action taken** on broken
> links — **they're cosmetic issues** in research pages."*

And then closes the section in the Actions table as:

> *"4. ✅ **Broken link scan — 493 noted (cosmetic in research category)**"*

**Read precisely, this is three separate defects stacked, and the third is the
one C-005 exists to prevent.**

1. **The check's own words — "genuinely broken" — are contradicted by its own
   words nine lines later, "false positives from the simple regex check."** The
   report does not know which of its two characterizations is true, and reports
   **493** as the number either way. **A metric that cannot distinguish its true
   positives from its false positives is not a measurement, and printing the
   unseparated total is worse than printing nothing** — 493 is a number that
   looks like a defect count and is actually an artefact count.
2. **A known false-positive mechanism — anchors and special characters — was
   identified and not fixed.** This is C-006 exactly: the validator's grammar is
   weaker than the corpus's syntax. **The corpus *uses* `[[file#heading]]`; the
   checker does not parse it.** One grammar extension separates the two
   populations, and until it is extended the number cannot be interpreted.
3. **The disposition is recorded as a success.** ✅ is the glyph for "done
   correctly." The scan *was* done correctly; the finding *was* discarded. **A
   check whose output is discarded and whose row is marked ✅ is
   indistinguishable, to every downstream reader and to every dashboard, from a
   check that passed.** This is why C-005 requires a checker whose failure
   *blocks* — the entire corpus-hygiene apparatus in this file is currently in
   the state where **493 acknowledged broken links and a disabled lint cron
   (see C-019's corollary) coexist, and the system's own summary of that
   situation is a column of green ticks.**

**Scale consequence, stated per R-J5 because it inverts the usual intuition.**
At 14,589 files, a regex check that cannot parse anchors does not produce a
proportionally larger false-positive rate — **it produces a number nobody can
act on at all**, because the false-positive fraction grows with the number of
distinct link syntaxes while the true defects stay roughly constant. A check
whose output is uninterpretable at 422 files is not a check that can be trusted
at 14,589, and **the fix is a grammar, not a bigger sample.**

**Fifth instance, next day, and it names the false-positive syntaxes explicitly —
so the corpus has now diagnosed C-006 correctly, in writing, and still shipped no
grammar.** `maintenance-report-2026-09-23.md` (ORDER line 109, read whole):

> *"Found broken internal links in research pages — mostly **`[[§N]]` and
> `[[#section]]` anchor references** in the frontier-research-ontology pages.
> These are intra-page anchors used as shorthand for cross-round references.
> **Not actual broken links, just the grep heuristic matching section reference
> syntax.**"*

**This is the correct diagnosis, stated exactly, one day after 493 links were
dismissed as "cosmetic" and marked ✅.** The report identifies the two literal
tokens the regex must not treat as filenames — `[[§N]]` and `[[#section]]` — and
correctly says the defect is in the *heuristic*, not the corpus. **A fix is now
fully specified: two prefix rules, and the 493 number becomes separable into
signal and artefact.** It has not been written, and §2 of the same report notes
the graphify index was last rebuilt **Sep 15** — eight days stale, reported
without a verdict, in a document whose entire purpose is reporting staleness.

**The same file's orphan count is the fourth value in four days for one
property**, and the sequence is worth preserving because it is a clean
demonstration that the number is a function of the *traversal*, not the corpus:

| Date | "Pages without `Source:`" | Corpus size | Ratio |
|---|---|---|---|
| 09-19 | 378 | 378 | **100%** |
| 09-22 | 300 | 422 | 71% |
| 09-23 | 245 | 429 | 57% |
| 09-24 | 363 | 435 | 83% |

**A property of a corpus that is monotonically growing (378 → 435 pages) moved
100% → 71% → 57% → 83%.** Growing corpora do not produce oscillating coverage
rates. **Four runs, four populations, four verdicts — and 09-19 is the one that
declared itself "not actionable."** This is the C-019 requirement stated as a
single testable claim: *the same metric on the same corpus must be
monotone in the corpus direction, or the traversal is wrong.*

**One thing in this report is a clean positive and is recorded as such, because
a class that only ever finds defects will eventually be ignored.** Its
consolidation section reports `MEMORY.md` **2,178 → 1,238 bytes (99% → 56%)**,
and — this is the part that matters — describes the operation as *"**Merged**
'don't manage graphify' rule **into existing** graphify note; **compressed**
Smart Speaker Project bullet list; compressed brain_sync path description."*
**That is rule-relocation, not rule-deletion: a standing instruction was folded
into the note it duplicated instead of being dropped to make room.** It is the
exact operation the arena's memory-hygiene discipline requires, executed
routinely by a cron job, and it is the one piece of corpus self-governance in
this tranche that worked as designed.

---

## Cross-class observation (not yet a requirement)

Across all 793 files, the recurring shape is: **the validated code path produces the
appearance of authority, and the unvalidated path produces the content.** TOCs,
citations, `verified:` blocks, `confidence:` values, index entries, related-link
boilerplate — all generated, all checked at some point, all reliable as *artifacts*.
The prose those artifacts decorate is generated by a different path and is not.

This is why C-002 ranks at 10/10 and why C-005 and C-006 outrank the semantic
alternatives. It is a claim about the generator, not about the corpus content, and it
should be tested directly: **does the generator that emits frontmatter also emit the
body prose, and are they different code paths?** One grep answers this. Until it is
answered, C-002 rests on a measured inversion across 7 positive controls and 6 defect
clusters, which is strong but circumstantial.

---

## C-020 · A field whose serialization drifts across the corpus is a schema with no fixed type `NEW — tranche 8`

**Requirement.** Any field that carries a **version**, a **confidence**, or a
**status** must have one canonical serialization across every file that uses it,
and the checker must assert on the serialization and not merely on the field's
presence. A corpus in which `okf_version` is `1` in one file and `1.0.0` in the
next, or in which `confidence` is the boolean `false` in one file and the float
`0.95` in the next, **has no schema for those fields** — it has a naming
convention. The two forms both parse, so no validator that checks types or
presence will ever report the drift.

**Relation to C-008, stated so this is not double-counted.** C-008 says a field
holds a value outside its declared type. **C-020 is the case where every value is
individually well-formed and the *set* of well-formed values differs between
files.** That is a different failure: a type error is caught by a schema
validator on sight, a serialization drift is not caught at all, because each file
passes alone. C-008 is a loud defect; C-020 is a silent one.

**Evidence, tranche 8 (ORDER lines 134–135, two adjacent corpus files read whole
this pass).** Both are `active-wiki/research/`, both generated 2026-09-15, both
research type, both describing the same subject (CBOR tag 6):

| Field | `cbor-tag-6-dependent-type-formalization.md` (134) | `cbor-tag-6-evolution-semantics-drift.md` (135) |
|---|---|---|
| `okf_version` | **`1`** | **`1.0.0`** |
| `status` | `complete` | `verified` |
| `verified` | **`false`** (boolean) | **`"2026-09-15T03:15:00Z"`** (timestamp) |
| `confidence` | **`high`** (string) | **`0.95`** (float) |

**Four of the five corpus-convention fields serialize differently in two adjacent
files on the same day.** `verified` is the sharpest: it is the field the whole
trust model rests on, and in 134 it is a **boolean** while in 135 it is a
**timestamp** — so a checker cannot ask "is this verified?" without first knowing
which corpus it is in. **A trust field that is sometimes a boolean and sometimes a
timestamp cannot be queried, and an unqueryable trust field is decoration.** This
is C-002's inversion with a specific new mechanism: the validated path (the field
exists, the key is present, the linter is satisfied) produces the appearance of a
trust model; the unvalidated path (can anything *read* the value?) produces
nothing at all.

**And file 135 is the inversion in miniature, in the corpus's own voice.** It
carries `status: verified`, a populated `verified:` timestamp, **ten** enumerated
`sources:` including six distinct IETF draft URLs and the WG repository, and
`confidence: 0.95` justified as *"Based on direct reading of all 19+ draft
versions."* Every apparatus check passes. **The content of the same file then
states that the specification it describes has no version field in its payload,
that three semantic shifts have occurred across those drafts, and that *"No
automatic negotiation mechanism exists in any current draft."*** The most
thoroughly-attested file in the tranche is about data that cannot say what it
means — and the file's own apparatus is the demonstration, because `okf_version`
in it cannot say what version it is either.

**Why it belongs in the corpus and not only in CBOR.** The mechanism is general
and it is the one the arena's own ledger is exposed to: **`ORDER.txt` carries
paths, `LEDGER.md` carries marks, and neither carries the regime under which
those marks were written.** A `[x]` written under the pre-tranche-5 reading of the
skill and a `[x]` written under the post-tranche-5 reading are the same character
in the same column and mean different things. See `VERIFICATION.md` §I-7.4 for the
instance this class produced in *this* tranche — a run in which the read marks
were truthful and the absorption they stood for did not happen.

**TRANCHE 9 — THE DRIFT IS NOT TWO FORMS, IT IS FIVE, AND IT NOW SPANS
`type`, `verified`, `confidence` AND `epistemic` IN FILES THAT ARE NOT ADJACENT
IN THE CORPUS.** Four further instances, all read whole this pass, all in
`active-wiki/research/`:

| File | ORDER | `okf_version` | `type` | `verified` | `confidence` |
|---|---|---|---|---|---|
| `ce-qe-query-expansion-longmemeval.md` | 136 | **`1.0`** | `research` | **`"2026-09-15T03:45:00Z"`** | **`0.95`** |
| `clvr-aware-layer-type-attribution.md` | 137 | **`"0.2"`** | **`research_report`** | **`[]`** (empty list) | **`high`** |
| `coap-content-format-registration-for-packed-cbor.md` | 138 | **`0.3.0`** | `research` | **`false`** | **`0.9`** |
| `context-dependent-head-type-saturation-override.md` | 143 | **`"0.2"`** | **`research_report`** | **`[]`** | **`medium`** |

**`okf_version` now has five serializations across eight files: `1`, `1.0`,
`1.0.0`, `"0.2"`, `0.3.0` — and the version number is *itself* drifting
downward** (`1.0.0` in tranche 8, `0.2` and `0.3.0` here), so the field
intended to declare schema compatibility is not comparable across the corpus
it describes. **`verified` has four: boolean, timestamp, and empty list.** A
checker cannot ask "is this verified?" without knowing which corpus convention
is in force, and **an empty list is the dangerous one: it is truthy in some
languages and falsy in others, so a file asserting nothing about its own
verification can be read as asserting either.**

**`type` has two (`research`, `research_report`) and this one is a taxonomy
error rather than a spelling variant** — both are *research*, so a consumer
filtering on `type == "research"` silently loses files 137 and 143, and those two
are precisely the files carrying this tranche's most falsifiable claims
(`epistemic: hypothesis` and a pre-registered kill criterion). **A schema variant
that partitions a corpus by prose genre rather than by content type will drop
exactly the files that are most careful about their own limits**, which is the
worst possible direction for the error to point.

**And `epistemic` appears in 137 (`hypothesis`) with no counterpart in the other
seven** — a field present in one convention and absent in six, carrying the
distinction between "this was tried" and "this was proposed" that this entire
arena grades slots on. **Under the skill's own evidence vocabulary, a corpus
that does not record `epistemic` cannot be graded, and the field that would
make grading automatic exists in 1 file of 8.**

**This closes the loop the class predicted.** C-020's requirement was written in
tranche 8 from two adjacent files and asserted the mechanism was general. **Four
files later, in a different directory range, the drift is worse and now touches
the field the arena's own grading depends on.** The class does not need
strengthening; it needs a checker, and the checker has a name: *every field in
this table must have exactly one serialization and one presence rule across the
corpus, asserted in CI, with the four `verified` forms and the five `okf_version`
forms as the test cases.*

---

## C-021 · A link block generated at scale is a count, not a graph — and the count is uncorrelated with resolution `NEW — tranche 9`

**Requirement.** A generated backlink block must be **resolved against the corpus
before it is written**, and a file's link count must never be usable as a
quality signal. A backlink list that exceeds the prose it annotates, contains
its own duplicates, and names targets that no ordered path resolves, **is not a
graph — it is a log of what the generator intended to have read.**

**Relation to C-003 and C-004, so this is not a re-skin.** C-003 records 16
broken links in 20 files and C-004 records an index that omits 1 of 7 entries:
both are **small, countable, and fixable by editing the links.** C-021 is a
different failure at a different scale: **the link block is larger than the
document**, its targets are *asserted* rather than looked up, and its size is
therefore a function of generation volume rather than of anything about the
corpus. A defect count over such a block measures the generator's throughput.

**Evidence, tranche 9 (ORDER line 140, `conservation-normalized-cross-layer-
attribution.md`, read whole — 587 lines).**

| Measure | Value |
|---|---|
| Prose (problem, background, related work, method, proof, open questions) | **212 lines** |
| `## Connections to Other Research` link block | **350 lines** |
| Share of the file that is link targets | **60%** |
| Link targets named | **~350** |
| Targets appearing **more than once** in the same block | **≥5** (`cross-encoder-token-attribution-local-models`, `attention-entropy-saturation-diagnostic-profiling`, `influence-score-gated-deltanet-validation`, `gate-saturation-influence-score-interaction`, `eap-gp-for-matching-heads-saturation-avoidance`) |
| Near-duplicate slugs for what is evidently one target | **`eap-gp-for-matching-heads-saturation-avoidance` *and* `eap-gp-cross-encoder-attribution-saturation-avoidance`** |

**The duplicates are the strongest evidence, because they are checkable without
the corpus at all.** Two slugs for one target means the block cannot even be
used to count distinct neighbours, let alone resolve them. **A relation set with
internal duplicates has no cardinality, and a graph metric computed over it is
uninterpretable.**

**On resolution, the claim is deliberately weaker than it could be, and the
weakening is the point.** This pass read `LEDGER.md` through ORDER line 1,140,
which covers the **entire** `active-wiki/` tree. The overwhelming majority of the
350 targets do not appear in those lines — including the tool and vendor
entries (`microsoft-graphrag`, `lightrag-hkuds`, `hipporag`, `nano-graphrag`,
`openspg-kag-ant-group`, `kuzu`, `falkordb`, `pgvector-postgresql-extension`) and
the ~180 `graphrag-extraction-*` slugs. **ORDER lines 1,141–2,217 were not read
this pass, so this class asserts a measured *rate of unresolvable targets in the
readable range*, not a corpus-wide absence claim.** `not observed` is the correct
epistemic state and `confirmed absent` is not available here. The distinction is
recorded because getting it backwards is the error this whole workspace exists to
avoid.

**Why it is a design requirement and not trivia — the §7 test.** *Would a good
architect change the design because of this?* Yes, in two specific ways. (1) **A
knowledge graph built by ingesting these blocks has a degree distribution
determined by the generator's topic model rather than by the corpus**, so any
retrieval or centrality metric computed over it — including the graphify
index this workspace depends on — is measuring the generator. (2) **A backlink
count is the cheapest possible quality signal and the arena has already been
burned by it once**: the corpus's own `wiki_hit_counter.py` returns `0` for all
ten of its most-linked pages (Area 1, `maintenance-report-2026-09-18.md` §6), so
popularity is not merely unmeasured here, it is **inverted**. **The generator
writes more links; the counter reads zero.** A system that cannot distinguish
those two states has no popularity signal at all.

**What is open.** Whether the targets are *generated* (hallucinated filenames,
which would be a C-002 instance at scale) or merely *stale* (real files from an
earlier corpus revision, which would be C-010). **The file does not distinguish
them and neither can this pass**, because distinguishing them requires resolving
the targets, which is what the class is about. Resolving a sample of twenty
targets against ORDER 1,140 and recording the ratio is the open measurement.

---

## C-022 · An apparatus token that survives scrubbing into a copy-pasteable code block `NEW — tranche 10`

**Requirement.** Any token that is **redacted, masked, or templated** must be
replaced with something that **fails loudly** — `REDACTED_JOB_REF`, a `TODO`, a
failing assertion — never with a placeholder that still *parses*. A scrubbed
token inside a shell command, a YAML job graph, or a URL that a reader is told
they can run is a defect the reader cannot see and cannot execute around.

**Evidence, tranche 10 (ORDER line 152, `cross-registry-monorepo-release-
orchestration.md`, read whole).** §4.2 presents a split-workflow architecture as
the solution to a real, correctly-diagnosed problem (PyPI's Trusted Publisher
filters OIDC tokens by `repository_owner` before checking `job_workflow_ref`, so
a reusable workflow cannot publish to the caller's package). The fix is
right — **putitoutthere does exactly this.** And the YAML that implements it
contains, at line 223:

```yaml
  pypi-tag:
    needs: «redacted:pypi-…»|    uses: thekevinscott/putitoutthere/.github/workflows/pypi-tag.yml@v0
```

**The redaction has eaten the `needs:` value *and the newline*, leaving a
pipe character in the middle of a key line.** The block is presented as
copy-pasteable — it is the file's recommended architecture, in a block with no
"adapt this" caveat — and it does not parse. A reader who copies it gets a
YAML error at `needs:`, which is at least loud. **A reader who copies only the
surrounding jobs gets a silently different DAG**, because the job they needed to
order against is gone and the pipeline still runs.

**Relation to C-007 (name corruptions) and C-002 (apparatus/content
inversion), so this is not a re-skin.** C-007 is a *name* corrupted in
transcription. C-002 is content that is wrong while its apparatus is right.
**C-022 is the scrubbing layer itself: a redaction that was applied for a good
reason and left a syntactically-plausible hole where a load-bearing value was.**
The distinguishing property is that the redaction is *not* the bug — the file
had no reason to contain a PyPI job reference at all, and something upstream
replaced it. **The check belongs at the point of redaction, not at the point of
publication**, and it is one grep: any `«redacted:` or `[REDACTED` or
`<redacted>` token inside a fenced code block is an error.

**Why it is a design requirement and not trivia — the §7 test.** *Would a good
architect change the design because of this?* Yes: **the corpus's redaction
passes are untracked relative to its code blocks, so any generated document
containing a command cannot be executed without re-deriving the redacted
values.** At 14,589 files that is every operational file in the corpus. The
companion requirement is that a scrubbed *identifier* (a job name, a package
name, a registry name) must be replaced by an equivalent that is **still
resolvable**, or the surrounding instructions are void.

**Adjacent instance, same tranche, same class, different severity.** ORDER line
153 (`cross-registry-provenance-verification.md`) contains **eight** occurrences
of the same `«redacted:pypi-…»` token, and here they are worse: the file's
central recommendation is *"use `«redacted:pypi-…» verify pypi` in CI"* and its
library table lists *"[«redacted:pypi-…»](https://pypi.org/project/«redacted:pypi-…»/)"*
as an official PyPI package. **The tool the file recommends cannot be named
from the file.** The surrounding finding — that valid attestations can describe
malware — survives intact and is recorded in `ARENA.md` Area 8; the *actionable
half* of the file is unusable. **A finding that cannot be acted on is a finding
that will not be acted on**, and the arena grades the finding while the corpus
loses the fix.

---

## C-023 · One source identifier presented under several titles inflates the support count `NEW — tranche 10`

**Requirement.** A source list must be **keyed by identifier**, and the
independent-source count any consumer computes must be taken over *distinct
identifiers*, never over list entries. A bibliography that repeats one
identifier under different titles is not a longer evidence base; it is one source
listed three times.

**Evidence, tranche 10 (ORDER line 155, `cusum-gradual-drift-detection-
preferences.md`, read whole).** The file's source list, lines 293–295:

```
- [A Framework for Evaluating and Benchmarking Concept Drift Detection Methods (arXiv:2606.07789)]
- [Monitoring calibration with CUSUM for concept drift detection (arXiv:2510.25573)]
- [Online Meta-Recommendation of CUSUM Hyperparameters (arXiv:2510.25573)]
```

**`arXiv:2510.25573` appears twice, under two different titles**, and the file's
body cites the same identifier for *two* distinct claims in §4.3 (*"Online
Meta-Learning for CUSUM Hyperparameters (arXiv:2510.25573)"*) and §4.4. The
frontmatter `sources:` block also lists it once. **Three list entries, one
identifier.**

**This is the arena's own independent-source rule, violated by the corpus, in
the corpus.** The rule exists because three files restating one study are one
source; here one study is restated three times *inside one file*, and the
inflation is invisible to every existing check — a link checker resolves all
three to the same arXiv abstract and reports success. **The file also carries
`confidence: 0.82` and rates its own sources**, so the apparatus is present and
correct while the count it feeds is wrong. That is the §8 inversion in
miniature: the apparatus produced a clean-looking bibliography and the content
under-reports its own evidence base by 2×.

**Relation to C-017 and C-018, stated so this is not a re-skin.** C-017 is one
identifier, two *taxonomies* in two different files. C-018 is one identifier, two
different *papers*. **C-023 is one identifier, two titles, in one file's own
source list** — a bibliographic defect rather than a citation defect, and the
cheapest of the three to detect.

**Why it is a design requirement and not trivia — the §7 test.** *Would a good
architect change the design because of this?* Yes, immediately, because **the
arena's grading rests on independent-source counts.** A count computed over list
entries rather than identifiers inflates every grade in this file. A file that
reports 11 sources and has 8 identifiers is graded on 11. **Support counts must
be computed by deduplicating on identifier, and the arena's own counts should be
re-derived that way** — which is recorded as an open action in
`VERIFICATION.md` §I-10.1, not silently applied, because retroactively lowering
counts across ten tranches is a larger claim than this pass has verified.

**One more instance in the same file, which is C-023 in miniature and worth
naming because the file presents it as a strength.** §4.4 credits *"1-second
temporal windowing eliminates 60/61 false positives"* to the Driftage framework
(PMC:8168350) and immediately proposes the same mechanism for a **session-scale**
system where windows are measured in sessions, not seconds. **A result about
one-second windows is being used to justify a design whose window is days.** The
principle (require multi-signal agreement within a window) is portable; the
number is not, and the file does not mark the difference. Queued in
`VERIFICATION.md` §I-10.2.

---

## C-024 · A risk raised in the analysis, denied in the conclusion, and then re-asserted in the recommendation — with no trace left that it was ever live `NEW — tranche 11`

**First evidence:** ORDER line 163, `active-wiki/research/dns-cbor-media-type-provisional-vs-standards-track.md`, read whole. Three mentions of one mechanism inside one 254-line file, holding two incompatible positions, with no reconciliation anywhere.

| § | What it says | Position |
|---|---|---|
| **4.2** | Quotes RFC 6838 §4.3 — parameters *"may be automatically made available to the media type by virtue of being a subtype"*. `application/dns+cbor` carries `+cbor`, so `packed` registered for `application/cbor` **"may automatically apply"** to it, *"creating direct conflict with DNS-CBOR's divergent semantics."* | **RISK IS REAL** |
| **4.4** | *"**No automatic inheritance**: DNS-CBOR must register its own `packed` parameter with its own semantics."* — stated as a conclusion, with no argument between it and §4.2 | **RISK IS DENIED** |
| **5.2 (rec. 5)** | *"Monitor draft-ietf-cbor-packed … if they register `packed` for `application/cbor`, DNS-CBOR must **ensure no inheritance conflict via RFC 6838 §4.3**."* | **RISK IS REAL** |

**Why this is a distinct class and not an instance of C-019, C-020 or C-023.**
C-019 is a metric computed over the wrong population. C-020 is a field whose
serialization drifts. C-023 is one identifier counted several times. **In C-024
every individual statement in the file is accurate and correctly sourced, and
every citation resolves.** The quoted RFC text is right in all three places. What
is missing is not information — it is the *link between the analysis and the
conclusion*, and the file is internally inconsistent about whether a mechanism it
correctly identified is in play.

**Why it matters more than a normal inconsistency, and it is the reason this is
a class rather than a note.** The three positions are not equally visible:

- A reader who reads **§4** and stops at the conclusion (§7, which is emphatic
  and unconditional) concludes there is **no inheritance risk** and ships without
  a check.
- A reader who reads **only the recommendation list** (§5.2) correctly concludes
  the risk is live and adds the check.

**The defect is invisible to every check that validates statements**, because
each statement is true. It is invisible to every check that counts sections,
because all three exist. The only thing that catches it is reading the document
as an argument rather than as a set of claims — which is exactly the check this
distillation performs and exactly the check no linter performs.

**The design requirement it earns, and it is a requirement about documents, not
about code:** *a risk named in an analysis section may not be silently resolved
in the conclusion without an argument; if the resolution is "the risk does not
apply", that argument must appear adjacent to the conclusion, and if a
recommendation contradicts the conclusion then the contradiction is the finding.*
At 14,589 files with a corpus regenerated on a cadence, an analysis section is
re-read and a conclusion is copied — so this is precisely the asymmetry that
makes the class recur.

**Second instance, same shape, different surface, and it is the arena's own.**
ARENA.md's tenth domain records three independent arrivals at the rule *a static
label must be a prior with a runtime validity check, never a fact* — MEMTIER's
zero-variance auxiliary signals, CLVR's absent layer boundary, RouteHead's
dataset-specific head selection. ORDER 168 supplies the fourth arrival **and the
implementation the other three lacked**, a five-feature domain classifier. The
arena therefore cites 168 for the *shape of the repair* while grading the
direction of its effect `UNTESTED`, because the file's own §Open Questions 1
states *"No existing study measures attention entropy of BGE-reranker-v2-m3 on
matched MS MARCO / LongMemEval-S query pairs."* **Keeping a file's reusable
mechanism while refusing its unmeasured conclusion is the discipline C-024
exists to make routine, and this workspace now has one worked instance of it.**

---

## C-039 · A threshold update clipped against the wrong end of its own variable's declared domain — the demotion becomes a no-op and, below full scale, a silent promotion `NEW — tranche 23`

**Instance: `trust-quarantine-cascade-provenance-graph.md` (ORDER 419) §5.1.**
The file ships its containment cascade as runnable Postgres. One line reads:

```sql
trust_alpha = GREATEST(1.0, m.trust_alpha * 0.5),   -- depth-1 demotion
```

`trust_alpha` is a **Beta distribution parameter, declared in [0,1] by the file
itself.** The update is `trust_alpha × 0.5`, which for any admissible value
satisfies `trust_alpha * 0.5 ≤ trust_alpha ≤ 1`. So `GREATEST(1.0, …)` **returns
1.0 for every row**, without exception and without a type or domain error to
signal it. **The depth-1 demotion never fires.** Worse, it is not merely inert:
for any entry with `trust_alpha < 1.0`, the row is *raised to full trust* on every
cascade pass. **The containment mechanism promotes exactly the entries it was
written to demote.**

The same file's Neo4j implementation of the same cascade gets it right
(`d.trust * 0.5`, plus `min(length(p))` for true depth), so the defect is
localised to the Postgres path — and it is in the one query a reader would copy.

**Why this is a new class and not C-037.** C-037 (tranche 22) is *a rule stated in
prose and inverted by the file's own worked numbers* — the prose and the numbers
disagree, and a reader can find the disagreement. **C-039 is worse on three
counts:**

1. **It is not a disagreement — it is a well-formed expression.** The line parses,
   type-checks, and looks like a standard numeric floor. C-037 is visible;
   C-039 executes.
2. **The failure is silent and direction-inverted.** A no-op gate looks like a
   gate. A demotion that silently *promotes* is worse than a missing demotion,
   because the operator's logs, counts and dashboards all show the containment
   path running.
3. **It is provable without executing anything, from the variable's own declared
   domain** — the cheapest possible defect check in the corpus, and it is the
   kind that scales: at 14,589 files the containment cascade is the one path that
   runs unattended over the whole store.

**The generalisation, and it is the rule the arena adopts.** *Any severity,
threshold, weight or confidence update in a governance or containment path must be
checked by substituting its own declared domain bounds and confirming the update
can actually move the variable within them.* A "floor" expression over a variable
bounded above by that same floor is a no-op by construction; a "ceiling"
expression over a variable bounded below by it is a no-op in the other direction.
**This is C-025 (a threshold branch mapped onto the wrong end of its quantity's
range) with the decisive extra step: not merely mapped to the wrong end, but
mapped to an end that makes the update unreachable — provable arithmetically from
the declaration, with no test data and no execution.**

Note the arena-wide shape this belongs to: the corpus's *validated* path
(structures, citations, TOCs) is clean here, and the defect sits in the *shipped
code* the file offers as the thing to copy. Same inversion as §8, one level down.

---

## Provenance of the post-split arena

`ARENA.md` and `ARENA-EVIDENCE.md` were separated by an external process on
2026-09-26 10:03:28 (see `VERIFICATION.md` V-23.3). **`ARENA-EVIDENCE.md` is not
one of this skill's four permitted paths and this distillation does not write to
it.** Two consequences recorded here because they bear on corpus hygiene rather
than on any single area:

- **C11 (`arena_invariants.py`, "an append is a bug") now needs a stated
  relationship to the split.** The pre-split file was 10,116 lines; the
  post-split `ARENA.md` is 1,429. A pass that appends two areas is now
  indistinguishable, to a line-count check, from a pass that failed to rewrite in
  place. **The invariant's premise ("this file is rewritten in place and meant to
  be short enough to reason over") is only true of the post-split file, and only
  while the arena grows by less than the split removed.** Recorded, not repaired.
- **Mid-sentence truncation survived the split** (V-23.3.2). A structural check
  that confirms "every line of the pre-split file is in exactly one of the two
  files" **cannot detect a line that was cut at a character boundary** — the line
  still exists in the other file, so the conservation property holds while the
  rendered sentence does not. This is the §8 inversion in its purest form: **the
  artifact that is validated (line conservation) is not the property a reader
  needs (a complete sentence), and passing the first says nothing about the
  second.**

| Class | Seeded from | First evidence |
|---|---|---|
| C-001 | CP-034, CP-035, CP-052, CP-061, CP-062 | registry-enforced publishing |
| C-002 | CP-060, CP-061, CP-062, CP-063 | apparatus/correctness inversion |
| C-003 | CP-053, CP-062, CP-063 §2-4 | 16 broken links in 20 files |
| C-004 | CP-053, CP-060, CP-061, CP-062 | index omits 1 of 7 |
| C-005 | CP-037, CP-055, CP-060, CP-063 | file 697 self-comparing validator |
| C-006 | 848, 809, 812, 861, 871, 878 | anchors correct in 2 files, broken in 1 |
| C-007 | 809, 860, 863, 871, 878 | 4 of 4 name corruptions |
| C-008 | 859, 867, 875, CP-062 | 6 wrong `type` values |
| C-009 | 859, 867 | monthly vs hourly sync |
| C-010 | 802, CP-060 | 17-day regeneration gap |
| C-011 | C-011 reversion record | configured ≠ running |
| C-012 | citation-vs-string check | citation does not match quoted text |
| C-013 | ledger reversion record | state not reconcilable |
| C-014 | round34–round36 | bare venue, no identifier |
| C-015 | ORDER lines 1–20, tranche 1 | design assertion with no source field |
| C-016 | ORDER lines 30–49, tranche 2 | two files, one `source:` session id; six reports, one paper set |
| C-017 | ORDER lines 50–69, tranche 3 | one id, two four-layer taxonomies (CMA / arXiv 2603.04740) |
| C-018 | ORDER lines 70–71, tranche 4 | one id, two papers (arXiv 2602.05636) |
| C-019 | ORDER lines 102-103, tranche 7 | staleness verdict over 34 files, stated about 2,013 |
| C-020 | ORDER lines 134-135, tranche 8 | `okf_version` `1` vs `1.0.0`; `verified` boolean vs timestamp |
| C-021 | ORDER line 140, tranche 9 | 350-line backlink block, ≥5 self-duplicated targets |
| C-022 | ORDER lines 152-153, tranche 10 | `«redacted:…»` inside copy-pasteable YAML; 8 in one file's recommended tool |
| C-023 | ORDER line 155, tranche 10 | arXiv 2510.25573 listed 3× under 2 titles |
| C-024 | ORDER line 163, tranche 11 | inheritance risk raised §4.2, denied §4.4, re-asserted §5.2 |

---

## C-025 · A threshold branch mapped onto the wrong end of its own quantity's range — provable from the stated weights, no execution required `NEW — tranche 11`

**First evidence:** ORDER line 171, `active-wiki/research/drift-strength-adaptive-suppression-policy.md`, read whole, against the weights it inherits from ORDER line 170.

**The defect.** 171 §2 maps a fused *drift strength* `s ∈ [0,1]` to a required
count of corroborating signals:

| `s` | Suppression | Required signals |
|---|---|---|
| `s > 0.8` | Relaxed | **≥1 of 4** |
| `0.6 < s ≤ 0.8` | Moderate | ≥2 of 4 |
| `0.4 < s ≤ 0.6` | Standard | ≥2 of 4 |
| `0.2 < s ≤ 0.4` | Tight | ≥3 of 4 |
| `s ≤ 0.2` | Maximum | ≥4 of 4 |

**The proof, from the two files' own numbers and no code.** 171 §1 and
recommendation 1 define `s` as a **weighted mean of the four signals**,
`s = Σ(wᵢ·sᵢ)/Σ(wᵢ)`. 170 §3.1 fixes the weights at
`cw_decay 0.30, consolidation 0.25, correction_pressure 0.25,
precision_degradation 0.20`, summing to 1.00. If exactly *k* signals fire at
their maximum of 1.0, the largest attainable `s` is the sum of the *k* largest
weights:

| k signals at 1.0 | max `s` |
|---|---|
| 1 | **0.30** |
| 2 | 0.55 |
| 3 | **0.80** |
| 4 | 1.00 |

**`s = 0.80` is not `s > 0.8`.** The Relaxed branch requires strictly more than
what three saturated signals can produce, and the only way in is four saturated
signals — at which point "≥1 of 4" is a condition already satisfied. **The
Relaxed branch is unreachable, and the one-signal case that relaxation exists
to serve (`s ≤ 0.30`) is routed to Tight → ≥3 of 4.** The policy's stated goal
is inverted by its own table.

A second, smaller defect in the same table: Moderate and Standard both require
≥2 of 4 and differ only in the `s` range, so the `0.4` boundary maps to
identical behaviour — a four-row ladder implementing three distinct policies.

**Why this is a class and not a note.** C-019/113 cover *unreachable* thresholds
(a gate set outside its score's range). **C-025 is the inverse: a gate that is
reachable, whose branch is nonetheless attached to the wrong end of the range,
because the quantity being thresholded is itself a function of the things the
branch counts.** A generic linter that checks "is this threshold inside
[min, max]?" passes this table — every threshold is inside [0,1] — and the
component still does the opposite of what it says. **The check that catches it
is relational: for a branch that maps a value of `f(signals)` to a count of
`signals`, enumerate the attainable `f` at each count and confirm the intervals
are ordered consistently with the policy's stated direction.** That is a finite
computation over the weight table, not a measurement, so it is R-J2-compatible
and belongs in a checker.

**Safe-direction note, recorded because it is easy to overstate the severity.**
The failure is in the conservative direction: a component that suppresses
legitimate drift more often than intended, rather than alerting more often.
The cost is missed drift, not false alerts. This does not make it benign — the
file's own §1 premise is that *both* failure modes matter (false positives
during volatile periods **and** missed subtle drift) — but it is a
`degraded-not-dangerous` finding and is graded as one.

**Second instance, same class, different quantity — and this one is a state
collision rather than a range inversion.** 170 §5.3 sets the CW integration
states: superseded `CW = -0.5`, new entries bootstrap `0.7–0.9`, and
**"Uncertain entries during drift: `CW = 0` (freeze until resolved)"**.
MEMTIER App. E, as recorded in tranche 7, measures MEMTIER's CW as
**approximately 0** — the degenerate value. **The freeze sentinel is set to the
degenerate value, so "held pending resolution" and "never measured" are the same
stored state, and the condition that would release the freeze is the drift
detector that is itself gated on the frozen signal.** Filed as the same class:
a sentinel that is indistinguishable from the failure it is meant to record.

**Design requirement, and it generalises past drift detection:** *every
branch of a threshold ladder must be checked for reachability against the
attainable range of the quantity it gates; where the gated quantity is a
function of the items the branch counts, reachability must be checked per
count, not against the global range. Every reserved sentinel value must be
checked for collision with the quantity's measured degenerate value.*
Cheapest defect class in the workspace: both halves are pure arithmetic over
values the document already states.

---

## C-026 · A calibration map that fails its own stated reference cases

**Found in:** `finite-size-burstiness-correction-sparse-preferences.md` (ORDER
line 180, read whole, tranche 12).

**The defect.** The file presents Kim et al. (2016)'s finite-size-corrected
burstiness statistic as a closed form,

```
B*_n(r) = (√(n+1)·r − √(n−1)) / ((√(n+1)−2)·r + √(n−1))
```

and states its defining property three times: §2.2 tabulates the three reference
cases as mapping to **−1, 0, +1 exactly for any n**; §6 Key Finding 4 says
*"B\* maps regular/Poisson/bursty to −1/0/+1 exactly for any n — no finite-size
artifacts"*; and the Direct Answer repeats it. The file closes `CONFLICTS: None
— the Kim et al. (2016) correction is mathematically exact and uncontroversial`
and grades `SOURCE_QUALITY: High — mathematically proven, not empirically
fitted`.

**Substituting the file's own reference points into the file's own formula:**

| Reference case | Claimed | Actual | |
|---|---|---|---|
| Regular, `r = 0` | −1 | **−1.0000** (n=5…100) | correct |
| Poisson, `r = 1` | 0 exactly | **+1/(2n)**: +0.1835 (n=5), +0.0204 (n=30) | **fails** |
| Extremely bursty, `r → ∞` | 1 | **√(n+1)/(√(n+1)−2)**: **5.4495** (n=5), 1.2485 (n=100) | **fails** |

One of three reference cases is correct. The other two are not approximations
that are slightly loose — at the sparse end the bursty limit is **5.4× outside the
statistic's own stated range of [−1, +1]**.

**Why it matters, and it is not a typo.** The file's model-selection protocol is
*"if B\* > 0.1 → reject Poisson in favour of NB"*, and its own §4.2 concedes the
sparse case is exactly where selection goes wrong. Applying the corrected
statistic to a **perfectly Poisson** process: at **n = 5 it returns +0.1835, at
n = 6 +0.1422, at n = 7 +0.1156 — all above the 0.1 threshold.** The false
positive band is **n ≤ 7**, precisely the sparsest stratum the file exists to
serve, and the correction *creates* the error it was written to remove. The
uncorrected statistic is negative there (−0.20 at n=5), so it would not have
tripped the rule.

**Design requirement.** *A calibration or correction map must be evaluated at
each reference point it claims to hit, and the claim "exact for any n" is a
universal quantifier that a finite set of substitutions cannot establish but a
single counterexample refutes.* The check is one substitution per reference case
and needs no execution, no benchmark, and no dataset — it is R-J2-compatible by
construction. Note what makes this class distinct from C-020 (an artifact
asserting unverified content): here the artifact asserts a **mathematical**
property, and the assertion is checkable against the artifact's own formula.
A formula that fails its own calibration points needs no external source to
refute and no trust decision to make.

---

## C-027 · A verification step with no failure mode

**Found in:** `frontier-research-2026-oct-update-new-papers.md` (ORDER line 184)
and `…-v2.md` (ORDER line 185), read as a pair, tranche 12.

**The defect.** ORDER 184 searches arXiv for October-2026-onward papers on four
topics, finds none, and — correctly — explains why: as of its stated date
(2026-09-11) arXiv only holds 2609.*, so 2610.* onward **has not been submitted
because it has not happened**. That is an honest null result, `verified: []`,
`confidence: high`.

ORDER 185, generated **seven minutes later**, is the same search with a populated
`verified:` block citing *"arXiv.org direct listing checks (cs.AI, cs.CL,
cs.LG)"*. Its one piece of new evidence is a table row reading:

> `https://arxiv.org/list/cs.AI/2026-11` → **"No updates for this time period."**

**That string is what arXiv returns for a month that has not occurred.** The
check confirms a calendar fact, not a literature finding. It could not have
returned anything else, so it cannot fail, and a check that cannot fail is not
evidence — yet the artifact's verification state improved while the epistemic
content stayed identical.

**Why this is its own class and not an instance of C-020.** C-020 is *an
artifact asserting unverified content*. This is the **verification procedure
itself** being degenerate: the question is not "is the claim true" but "does this
check have any outcome under which it reports the opposite." A `verified:`
block whose supporting procedure had a reachable failure branch would be
weak-but-real evidence; one whose procedure had none is indistinguishable from
a block typed by hand.

**Design requirement.** *Every verification step must be able to fail. Before
recording a check as verification, state the observation that would have
reversed the conclusion.* For time-bounded or future-dated claims the reachable
negative is usually available and cheap — here it was `arxiv.org/list/cs.AI/2609`
returning entries, which would have shown the prefix convention was wrong. This
is the cheapest possible instance of the arena's §8 inversion and the sharpest
one yet: **the validated artifact improved, the unvalidated content did not
move, and the file reports higher confidence than the file it corrects.**

---

## C-028 · A self-assessed score re-ingested as evidence by the component that produced it

**Found in:** `frontier-research-dual-memory-dynamic-ontology-experiential-2026-oct-update.md`
(ORDER line 189, read whole, tranche 12), reporting **Memory Reward Inflation**
(arXiv 2608.00017) and the **Echo Gap**.

**The defect.** The mechanism, in the file's words: *"inflated self-assessed
scores written to persistent memory → retrieved, imitated → error compounds
through reuse."* Its own name for this is **memory-specific reward hacking.**

This is the arena's §8 finding — *the validated path produces the appearance of
authority while the unvalidated path produces the content* — with the loop closed.
A wrong claim in a document is a wrong claim. A wrong claim in a document that
later agents retrieve and cite is a **self-amplifying** error, because each
retrieval adds the prior's apparent authority to the successor.

**It applies to this workspace specifically, which is why it is filed rather than
noted.** The corpus writes `confidence: high`, `verified:` blocks and
`SOURCE_QUALITY: High` into hundreds of pages across dozens of research rounds,
and downstream rounds read those pages back as evidence. A grade written by a
file is then a grade *about* that file, cited by the next file, and the
apparatus and the content are the same object.

**Design requirement.** *A self-assessed score must not be retrievable as
evidence by the component that produced it.* Concretely: an assertion may inform
a human reader, and must not be re-ingested as an input to the next inference
about the same subject. This is a **provenance-edge constraint on the memory
substrate** — checkable as a property of the graph (does any retrieval path from
an assertion to a later inference about its own subject exist?), R-J2-compatible
because it is structural rather than a benchmark, and holding at 14,589 files
(R-J5) because the constraint is per-edge and does not degrade with corpus size.

**This is the one requirement in tranche 12 that binds the arena's own outputs**,
and it is recorded in that capacity deliberately. The arena does not claim to be
exempt from its own findings.

---

## C-029 · A well-formed reference list whose body citations are systematically mis-bound

**Found in:** `frontier-research-ontology-2026-09-01-5.md` (ORDER line 204, read
whole, tranche 13).

**The defect, and it is the first one in this file that every existing check
passes.** The file carries a **32-entry source table** with arXiv IDs, venues and
author names. Every entry is present, well-formed, and independently resolvable.
Its body then cites that table **systematically off by two**:

| Body claim | Cited as | Entry actually at that index |
|---|---|---|
| "Verifiable Knowledge Expansion via FCA" (`2607.01773`) | `[30]` | *Align Aspirations Not Flaws* |
| "LMMs4OL 2026 results" (§29) | index-bound to a different entry | the right paper, the wrong slot |
| "The Specification Trap" (§22) | index-bound to a different entry | the right paper, the wrong slot |

**The two papers named in the body are real; the entries they are bound to are
not about them.** That is what makes this a class rather than a typo: a typo
produces one bad citation, and a **systematic** offset produces a file in which
*every* reference resolves and *no* reference is the one the sentence means.

**Why every check the corpus applies to a reference list misses it.** The
validated path in this corpus is the *artifact*: a table exists, has 32 rows,
each row has an arXiv ID and a venue, and the file's TOC and frontmatter are
generated and correct. §8's inversion, in its purest form yet — **the generated
apparatus is perfect and the prose it decorates is bound to the wrong sources.**
A linter checking that the list is well-formed passes this file completely. So
does a link checker, so does a count check, so does a venue-format check.

**Design requirement — and this is the first requirement in this file that is
*relational* rather than local.** *A citation must be verified against the entry
it resolves to, not against the existence of the entry.* The check is: resolve
the cited index, read the entry's title and abstract, and ask whether the entry
is **about the thing the citing sentence asserts**. Every existing check in the
corpus is a property of the list; this one is a property of the *pairing*.

- **R-J2-compatible:** it is a deterministic check over two documents, not a
  benchmark and not a self-measurement.
- **Holds at 14,589 files (R-J5):** the check is per-citation and does not
  degrade with corpus size. It is *more* valuable at scale, because a
  mis-binding compounds: a wrong binding propagates into whichever file cites
  the citing file, and the arena's own `## BRAIN PARTS NOT YET COVERED` shows
  how far a single uncorrected claim travels.
- **It is checkable without an LLM for the mechanical half.** An off-by-N in
  index binding is detectable by comparing the cited index against the position
  of the entry whose title best matches the citing sentence's subject — a
  retrieval problem, not a judgement problem. The residual cases need a reader.

**Precedent for why this is filed as a class and not an instance:** ORDER 209's
`Related` block has the same *family* of defect from a different cause — a
pipe-in-wikilink (`[[Target|alias]]` written where the corpus's own convention
requires `[[alias]]` or `[[Target]]`) across **7 rows**, which breaks the link
and the display text together. Neither defect is visible to a well-formedness
check. Together they say the corpus's validated path covers *shape* and not
*binding*, and that is the general form of §8.

## C-030 · A wikilink substituted for the term it names — the link renders, the sentence stops being English `NEW — tranche 16`

**Found in:** `frontier-research-round6-addendum-sept-2026.md` (ORDER line 280,
read whole) — 3 instances — and `frontier-research-round7-sept-2026.md` (ORDER
line 281, read whole) — 2 instances. Both read whole, tranche 16.

**The defect.** A generator or a scrubber has replaced a bare noun with a
`[[wikilink]]` **inside running prose**, so the sentence retains the link
mechanics and loses the word. The corpus's own convention is a link on a
*descriptor*; the failure is a link on the *referent itself*, which reads as:

> …and [[file formats]].

rather than

> …and YAML, JSON, CSV, and similar file formats.

The three instances in ORDER 280 are worse than the two in ORDER 281 because one
of them sits **inside an enumeration of file formats**, so the list item that
should name a format instead points at the *category* the format belongs to. **A
reader following the link arrives at a page that describes the class and learns
nothing about the member.** The five instances in ORDER 279 (`…-psychological-
ontology-2026-oct-update.md`) are the same family and a different mechanism: five
**literal ellipses** (`[[...]]`) standing where a target should be — a link
target that was never resolved and was emitted as text.

**Why every existing check in this file misses it.** C-003 governs referential
integrity of internal links and C-021 governs link-block counts. **Both inspect
the link. None inspects the sentence the link sits in.** A wikilink is
well-formed, resolvable, correctly cased and correctly spaced in all ten
instances. The defect is invisible to every check in this file because the
corpus's validated path is the *link*, and the prose — which is where the
information was lost — is on the unvalidated path. **§8's inversion again, and
in its most compact form yet: a file whose links are perfect and whose sentences
no longer parse as English.**

**Design requirement.** *A link is a noun phrase the reader can lose. Every
generator that inserts a wikilink into prose must assert that the link's display
text is a **descriptor or a proper name**, and must refuse to emit a link whose
display text is the bare referent of the sentence's own grammar slot — the
object of a preposition, an element of an enumeration, or the sole word of a
clause.* Mechanically checkable with no LLM: parse each linked occurrence's
surrounding sentence; if the link is immediately preceded by a preposition, a
conjunction within an enumeration, or a determiner, and its display text is a
single common noun, flag it. **A literal `[[...]]` is an unresolved target and
must fail the build, not be emitted.**

- **R-J2-compatible:** purely syntactic over existing markdown; no model call.
- **Holds at 14,589 files (R-J5):** this class gets *worse* with scale rather
  than better, because a generator that mangles one noun in prose mangles every
  occurrence of that noun, and at corpus scale the affected noun is almost always
  a hub term. It is the cheapest check in this file and the one with the highest
  expected yield per file scanned.
- **Precedent for filing as a class rather than an instance:** five instances
  across two consecutive files from the same programme, plus five literal-ellipsis
  wikilinks in a third file from the same month. **A defect that appears in every
  file a generator touches is a property of the generator**, and the corpus has
  now produced four such properties (C-007, C-016, C-021, this one).

**RECURRENCE — tranche 17 added five further instances, and one of them is in a
title.** ORDER 282 (`frontier-research-round8-sept-2026.md`) has **four**,
including one in the H1 where a version/format term has been replaced by a
`[[…]]` link. ORDER 293 (`…-taxonomy-late-2026-supplement.md`) has **one**,
where a short method acronym in prose is replaced by a wikilink to a research
file — the sentence keeps the link mechanics and loses the word. ORDER 299
(`…-taxonomy-theory-knowledge-organization-sept-2026.md`) has a **suspected
mislinked label** rather than a substitution: §1.3 renders as
`[[research/frontier-research-fca-semanticweb-evaluation]]` where every other
reference in the corpus uses a longer suffixed path, and the label is the
descriptor that was supposed to survive. Recorded in `VERIFICATION.md`; **not
opened, because the ledger's path is the only authority for paths and this file
is not a ledger line.** **Eight instances in two tranches from the same generator
family is no longer a sample.** The class is confirmed and the yield estimate in
the requirement above — *"the cheapest check in this file and the highest expected
yield per file scanned"* — is now measured, not estimated.

---

## C-031 · A declared negative that no check supports — "CONFLICTS: None found" over 23 papers `NEW — tranche 17`

**Found in:** `frontier-research-taxonomy-2027-supplement.md` (ORDER line 287),
`frontier-research-taxonomy-late-2026-supplement.md` (ORDER line 293), and
`frontier-research-taxonomy-comprehensive-2026-09-10-v2.md` (ORDER line 291) —
all read whole, tranche 17. One earlier instance is on record in
`VERIFICATION.md` from tranche 15.

**The defect.** These files carry a generated summary block asserting:

> **CONFLICTS: None found**

…immediately above or below a `CONFLICTS:` slot that a generator is expected to
populate, and above a body that summarises **23 papers** (ORDER 287), **20
papers** (ORDER 293) and **23 major papers/frameworks** (ORDER 291). The field is
**structurally incapable of being anything but empty**, because the generator has
no procedure that could detect a conflict — and the assertion of a negative is
indistinguishable, to any reader, from a checked result.

**The content of these three files contradicts the assertion, and this run read
the contradiction.** ORDER 287 and ORDER 293 are consecutive supplements to the
same series, and ORDER 293's own TSCG result (**structure dominates content**,
R² 0.88 vs 0.03) directly contradicts the fifteen tranches of *vocabulary*-first
taxonomy work that the series itself contains. ORDER 291's TaxoBench reports
twelve models **all converging on the same wrong answer**. Neither is a
"conflict" in the narrow sense of two papers reporting opposite numbers, which is
perhaps what the field was scoped to — **and that scoping is the deeper defect:
a field named `CONFLICTS` that only catches one shape of disagreement will read
`None found` on a file full of them.**

**Why every existing check in this file misses it.** C-002 governs apparatus
quality versus claim correctness and would flag a `confidence: high` — but these
files carry `confidence: high` *and* the assertion, so C-002's remedy is
"distrust the confidence," not "distrust the negative." C-015 governs a design
claim with no citation; **a declared negative with no procedure behind it has no
citation to be missing.** C-021 governs link-block counts. **None of them asks
whether a field's value could have been produced by a check.**

**Design requirement.** *A field asserting a negative must declare the procedure
that would have detected it, and the procedure must run.* Concretely: every
`CONFLICTS:`-shaped field is either (a) populated by a named, executed procedure
whose output is quoted, or (b) **omitted entirely**. A field whose value is
`None` or `None found` is a claim of exhaustive search, and the corpus is not
exhaustively searched by anything. **Mechanically checkable with no LLM:** a
summary field matching `^(CONFLICTS|ISSUES|OPEN_QUESTIONS|ERRORS):
\s*(none|nil|-)\s*$` fails the build, because the honest encoding of "no
procedure ran" is the field's absence. This is the one class in this file whose
remedy is *deletion*, and that is why it belongs here.

- **R-J2-compatible:** pure syntactic match; no model call, no re-reading.
- **Holds at 14,589 files (R-J5):** the class is **constant per file, not
  per-claim** — one generator writing 14,589 files emits 14,589 false negatives,
  and each is read as a checked result by every downstream consumer including
  graph indices and retrieval. It is the cheapest check in this file and the
  second-highest expected yield after C-030.
- **Precedent for filing as a class rather than an instance:** four instances
  across three files this pass plus one in the previous tranche, **all from the
  same generator family, all in files that pass C-014 and C-015 cleanly.** A
  defect that appears in every file a generator touches is a property of the
  generator — the corpus has now produced five such (C-007, C-016, C-021, C-030,
  this one), which is itself the strongest available evidence for §8's inversion.

---

## C-032 · A conservation claim whose own derivation establishes a strict inequality `NEW — tranche 18`

**Found in:** `gdn-lrp-conservation-validation.md` (ORDER line 302, read whole,
tranche 18). One instance this pass; the class is filed on the strength of the
*shape*, not the count, because the shape is machine-checkable and the arena had
no rule covering it.

**The defect.** §3.2 asserts for the matrix-state right-propagation rule:

> **Conservation error: 0 (exact, no ε needed)**

and §3.3's summary table repeats it as **"Matrix-state (Rule 4) | Exactly
conservative | None | No fix needed."** The supporting argument in the same
section is a **Frobenius-norm** identity, and the file's own premises contradict
the conclusion:

> ‖R(S_{t−1})‖_F = (1/α_t) · ‖R(S_t) · M_t^T‖_F
>
> Since M_t = I − β_t·k_t·k_t^T **is a contraction** when |β_t·k_t^T·k_t| < 1 … the
> propagation is **exactly conservative** in the matrix form.

**A contraction does not preserve a norm.** If M is a contraction then
‖R·M^T‖_F ≤ ‖R‖_F, with strict inequality unless M is orthogonal. The file
identifies the operator as a contraction and then concludes exact preservation
from the same sentence. Worse, the (1/α_t) prefactor is not shown to
compensate: α_t is a decay gate in (0,1), and nothing in the file relates it to
‖M_t‖_F, so the two errors are not shown to cancel.

**There is a second, independent mismatch, and it is the more fundamental one.**
**A norm is not a sum.** LRP's conservation axiom is
**Σᵢ R(xᵢ) = y** — a statement about the *sum* of relevance, which is the
`L¹`/`L^0,1` quantity and is preserved by the sum rule. The Frobenius norm is
`L²`. **An L²-preserving map need not be L¹-preserving**, so even a correct norm
identity would not establish conservation of the quantity the axiom is about. The
file's Rules 1 and 3 use the *sum* correctly (and correctly conclude
"approximately conservative"); Rule 4 silently switches to a *norm* and then
claims the stronger result. Three rules, two different quantities, one table
grading all three on a single "conservation status" column.

**Why this is an infra class and not an arena slot.** Per §7 the test is whether
a good architect would change the design. They would: the file's own §4.4
decision tree routes on this claim — *"Conservation error < 1% for all layers →
GDN-LRP is faithful → use for CE-QE expansion"* — so an unearned "exact" verdict
is load-bearing for an adoption decision. But the *requirement* it implies is
about proof hygiene, not about brains: **a conservation/no-loss/exactness claim
must be stated in the same quantity as the axiom it claims to satisfy, and the
operator's action on that quantity must be shown to be the identity.**

**Design requirement.** *When a claim asserts that some quantity is preserved,
name the quantity, and prove preservation in that quantity. A norm identity does
not establish a sum invariant.* Concretely and checkably with no LLM: a claim of
the form `error: 0` / `exact` / `no ε needed` must be accompanied by an
expression in which the operator appears as **the identity, a permutation, or an
explicitly normalised contraction** (i.e. `M/‖M‖` with the norm factor shown
cancelling). A contraction asserted as a preserver fails. A `L^p` norm in a proof
of a `Σ` invariant fails.

- **R-J2-compatible:** the check is local — regex for `exact|0 \(exact|no ε`,
  then inspect the adjacent expression for a norm (`‖·‖_F`, `L²`, `norm`) or a
  contraction keyword (`contraction`, `isometry`, `≤`) inside a conservation
  argument. No model call.
- **Holds at 14,589 files (R-J5):** the check is **O(1) per claim and needs no
  cross-file context**, which makes it cheaper than C-012 and C-016. At scale
  the higher-yield variant is the *cross-rule* one: a section that grades several
  rules on one column must use one quantity throughout, and that is a per-section
  check, not a per-file one.
- **Distinct from every class above.** C-024 is a risk denied in the conclusion
  and re-asserted in the recommendation — the claim survives, its support does
  not. C-025 is a threshold on the wrong end of a range. C-026 is a calibration
  map that fails its own reference cases. **This is a claimed identity proved in
  the wrong algebraic space**, and no existing class would flag it: the file
  cites a real theorem (MambaLRP's conservation work, arXiv 2406.07592), carries
  `confidence: high`, populates a full source-quality table grading fifteen
  sources as High/Medium, and proposes a five-experiment protocol. **Every
  apparatus in the file is correct; the one sentence that carries the verdict is
  the one that fails.** That is §8's inversion in its purest form and it is why
  this class is worth a rule rather than a line in `VERIFICATION.md`.

- **Instances on record:** 1 (`gdn-lrp-conservation-validation.md`, ORDER 302,
  Rule 4). Preserved unreconciled per R-J4: whether a corrected right-propagation
  can be made exactly `L¹`-conserving is an open question the file itself poses in
  its §7 Q1, and the arena does not resolve it here.

---

## C-033 · A file's own worked example falsifies the file's own thesis, in the file's own numbers `NEW — tranche 19`

**Found in:** `lipschitz-assumption-validation-fedd-reward-surface.md` (ORDER
line 330, read whole, tranche 19). **Three further instances in the same tranche**,
recorded below. The class is filed on the *shape*, which is machine-checkable, and
the shape is new: C-025, C-026 and C-032 are all claims that fail an *external*
test. This is a claim that fails a test the file itself supplies, in the same
section, four lines apart.

**The defect.** §2.2 states a **correct theorem** — that `F1(k, λ)` is piecewise
constant in λ with breakpoints at the unique predicted probabilities — and gives a
**correct proof** by the order-statistic argument. §2.3 then supplies the only
worked example in the file, four samples `(y,p) ∈ {(1,0.7), (1,0.9), (0,0.6),
(0,0.8)}`:

| λ range | TP | FP | F1 | file says |
|---|---|---|---|---|
| (0.9, 1] | 0 | 0 | 0 | ✅ correct |
| [0.7, 0.9) | 1 | 0 | 2/3 | ❌ |
| [0.6, 0.7) | 2 | 0 | 1 | ❌ |
| (0, 0.6) | 2 | 1 | 4/5 | ❌ |

**Every row after the first is wrong, and each is wrong in a way that
*reverses* the file's argument.** Recomputed from the file's own `F1 = 2·TP/(2·TP
+ FP + FN)` and its own definition `TP = Σ_{p≥λ} 1[y=1]`:

- **λ ∈ [0.7, 0.9):** both positives (0.7, 0.9) are ≥ λ, so **TP = 2, not 1**;
  the negative at 0.8 is also ≥ λ, so **FP = 1, not 0**. F1 = 4/(4+1) = **0.8**,
  not 2/3.
- **λ ∈ [0.6, 0.7):** all four samples selected — **TP = 2, FP = 2**, F1 =
  4/(4+2) = **2/3**, not 1. The file reports `F1 = 1` for a selection containing
  two false positives. **`F1 = 1` is unreachable whenever FP > 0**, so this row is
  not a rounding error; it is a value the metric cannot take.
- **λ ∈ (0, 0.6):** all four selected, identical to the row above, so F1 must be
  **2/3**, not 4/5. The file's own table therefore has **two different F1 values
  for the identical confusion matrix**, which is a self-contradiction independent
  of any external check.

**The load-bearing sentence is the one the example supports.** The file's
conclusion — *"A change in λ from 0.70 to 0.69 changes F1 from 2/3 to 1.0 — a
jump of 1/3 over a 0.01 threshold change. The local Lipschitz constant is
effectively infinite at every breakpoint"* — is built on the two wrong rows. The
**qualitative** claim survives: `F1` genuinely is piecewise constant and genuinely
has infinite local Lipschitz constant at breakpoints, and the file's §2.2 proof is
sound. **But the file supplies no correct instance of its own phenomenon**, and it
does so in the one section whose purpose is to make the phenomenon concrete. The
theorem is right; the illustration is invented; the file carries
`verified: ["2026-09-17T12:30:00Z"]`, `confidence: high`, and `status: completed`.

**Why this is a class and not an instance.** The check is trivial and needs no
model: **a worked example is an executable claim.** If a file states both a
formula and a table of values for that formula, the table is checkable by
substitution with the file's own inputs. A file that supplies inputs, a formula,
and outputs has done three quarters of the work of proving itself, and gets the
last quarter wrong in 3 of 4 rows.

**Design requirement.** *When a file states a formula and then a table of values
for that formula, the table is an assertion and is checkable by substitution
using the file's own inputs — a checker must do that substitution, not read the
table as prose.* Concretely: extract the numeric example's inputs and its claimed
outputs, recompute, and report row-level disagreement. This is the cheapest
high-yield check in the whole corpus, because the corpus is **full** of numeric
worked examples and they are, empirically, where the errors are.

- **R-J2-compatible:** fully deterministic. No model, no execution of the
  project's code — pure arithmetic on numbers already in the file.
- **Holds at 14,589 files (R-J5):** **O(1) per table, no cross-file context.**
  At scale this is the highest-throughput check available: the corpus's numeric
  density is the asset. A file with 20 such tables costs 20 substitutions.
- **Distinct from every class above.** C-026 is a *closed-form correction* that
  fails its own reference cases — the formula is the thing under test, and it is
  offered as a general map. C-032 is a conservation claim proved in the wrong
  algebraic space. **C-033 is different from both: the general claim is correct,
  the file says so, and only the illustration is false.** That is the shape the §8
  inversion predicts and no existing class names — a corpus in which the *checked*
  artefact (formula, proof, apparatus) is right and the *unchecked* artefact (the
  example that makes it legible) is invented. A reader who accepts the theorem and
  skips the table is unaffected; a reader who trusts the table is wrong.
  **Corollary worth stating: an error confined to worked examples is the most
  dangerous kind, because it survives a careful reader who checks the argument.**

- **Instances on record:** 4 this tranche, all the same shape, all found by
  substituting a file's own numbers into the file's own formula.
  1. `lipschitz-assumption-validation-fedd-reward-surface.md` (ORDER 330) §2.3 —
     3 of 4 rows wrong; one claimed value (`F1 = 1`) is outside the metric's
     range; two rows assign different F1 to one confusion matrix. **The error
     propagates:** ORDER 331 §Theoretical Background cites this file as its
     warrant for *"the F1 surface is piecewise constant in λ (breakpoints at unique
     predicted probability thresholds)"* and builds a five-layer conformal
     architecture on it. The claim it inherits is true; the warrant it inherits is
     the broken table. **Confirmation of reach, not of correctness.**
  2. `mambalrp-extension-gated-deltanet.md` (ORDER 335) §4.3 — the file derives
     the Kronecker Jacobian three times in the artifact, visibly reversing itself
     in prose (*"Wait, let me reconsider"* … *"No wait — the state multiply is
     S_{t-1} · (I − β_t k_t k_t^T), which is a right-multiply"*), and the
     dimension is wrong at every attempt: `S ∈ R^{d_k×d_v}` right-multiplied by
     `I − β_t k_t k_t^T ∈ R^{d_k×d_k}` is not conformable unless `d_v = d_k`. The
     correct form left-multiplies. **The file's §3.1 step-by-step form is also
     written with `k_t e_t^T` where the read-out `o_t = q_t^T S_t` requires
     `S_t ∈ R^{d_k×d_v}`** — the same slip, stated twice, and §10's summary table
     reports the Kronecker form as a **Key Finding** with evidence "Matrix
     calculus." **A file that argues with itself three times and lands on a
     non-conformable product in all three attempts has not derived anything**, and
     the visible self-correction is retained in the artifact — reasoning left
     mid-stream in a research file.
  3. `latency-accuracy-pareto-reranker-edge.md` (ORDER 327) §5.1 — the Pareto
     table marks **`Ettin-17M, k=100` as "✅ 200ms budget winner" at 374ms**,
     which is 1.87× the stated budget; the same table marks
     **`BGE-reranker-v2-m3, k=50` "Dominated by Ettin-68M (better quality, 5x
     faster)"** when BGE's NanoBEIR (0.6971) **exceeds** Ettin-68M's (0.6915) and
     only MTEB is lower — **domination requires beating on every axis**, and the
     file's own §5.1 note concedes *"NanoBEIR nDCG@10 may not predict LongMemEval
     Recall@10"* two sections later. §5.2's "Optimized two-stage for 200ms" then
     totals **432ms** and concedes *"exceeds 200ms but fits 500ms"* in the same
     breath. **This file is `status: verified`, `confidence: 0.85`** — the
     highest-credentialed artefact in the tranche, and the one whose derived table
     is most wrong. **The inversion is not correlated with credibility; it is
     visible only in the arithmetic.**
  4. `layer-type-aware-hybrid-saturation-routing.md` (ORDER 329) §5.3 — asserts a
     **97% reduction** in detection overhead from `O(384) → O(128)`, and gives
     `O(H) = O(16) per layer`, then totals 384 heads as `128 + 128 + 128` across
     three ranges of a **24-layer × 16-head** model — where `24 × 16 = 384` is
     correct but **the three ranges (1-8, 9-16, 17-24) are asserted by scaling a
     12-layer model's boundaries to 24 layers**, which the file admits is
     unverified (*"hypothesized by scaling"*) and which §6.1 rates **"Probability:
     High"** as a risk. The 97% figure is arithmetic on a partition the file has
     not established.

---

## C-034 · A stated property is not entailed by the stated formula, and the shipped code implements a third rule — so the headline result is not reproducible from the specification that looks authoritative `NEW — tranche 20`

**First evidence:** ORDER line 339, `active-wiki/research/memory-provenance-lineage-memlineage.md`, read whole, tranche 20. **MemLineage** (arXiv 2605.14421, Ouyang & Hou), `verified: []`, `confidence: 0.88`.

**The defect.** The file states the same security rule three times, at three
different strengths, in three registers — and the file's headline result depends
on the strongest while the formal specification offers the weakest.

| § | Register | Rule | Quantifier |
|---|---|---|---|
| **1.3** | **formula** | `trust(e) = max_{P} min_{f∈P} w(f)` | **∃** one good path |
| **1.3** | **prose claim** | *"makes Untrusted-Path Persistence hold: if any ancestor is untrusted, all descendants inherit untrusted status"* | **∀** paths |
| **1.4 (M4)** | **prose** | refuse *"if any entry in the justification set has an external ancestor **along any path**"* | **∀** paths |
| **4.3** | **code** | `for path in walk_lineage_dag(...): if any(edge.weight < tau): continue; if path.source.writer.startswith("external:"): return False` | **∀** paths |

**The formula does not entail the property.** `max`-over-paths-of-`min`-over-edges
is the standard **widest-path / maximum-bottleneck** rule: it returns the *best*
chain of derivation available. Under it, a single untrusted ancestor is simply
*not the max* — it is discarded. **One clean trusted path launders a descendant
that also has a poisoned parent.** "Untrusted-Path Persistence," the property the
file names as the reason to adopt the mechanism at all, requires the opposite
quantifier over paths (min-over-paths, or "every path must be strong"), and that is
not what §1.3 writes.

**Why this is its own class and not an instance of C-033.** C-033 is a *numeric*
contradiction — a worked example falsifying a thesis in the file's own arithmetic,
and the check is substitution. **Nothing here needs a number substituted.** The
defect is a **mismatch of quantifier between a formal definition, the prose that
claims to follow from it, and the code that implements it.** A checker that
verifies arithmetic passes this file completely: every weight, every threshold and
every latency figure in it is internally consistent. A checker that *type-checks the
formula against its own docstring* would catch it, and nothing in the corpus's
validated path does anything of the kind.

**Why it matters more than a normal inconsistency, and it is the reason this is a
class.** The three registers are **not equally likely to be read.** An implementer
reproducing this design will take §1.3's formula, because it is the only one
written in a formal register and it is the one the file's `confidence: 0.88`
frontmatter appears to vouch for. Someone reading §1.4 or running §4.3's code gets
a *stronger, safer* system than the specification describes. **The file's
evaluation result — §1.7, "MemLineage is the only configuration that drives all
three attack-success-rate columns (AgentPoison, MemoryGraft, lineage-stress) to
zero" — cannot be reproduced from §1.3's formula, because §1.3's formula admits
exactly the laundering path that the zero is evidence against.** The security
claim and the spec disagree, and the spec is the part that looks load-bearing.

**The design requirement it earns — a requirement about specifications, not about
code:** *where a security property is claimed in prose and defined in a formula,
the formula must be checked for the quantifier the prose requires; and a security
result must be reported as reproducible from the weakest stated rule, not the
strongest.* A provenance gate whose rule strength is ambiguous is a gate whose
strength is chosen by whoever reads it, and the choice is made silently. At
14,589 files with a corpus regenerated on a cadence, this is O(1) per
`formula → claimed property` pair — pure symbolic inspection, no execution, R-J2
clean — and it is the check most likely to be skipped, because a formula that
parses and a docstring that reads plausibly *look like* verification.

**Second instance, same tranche, and the opposite failure direction — a formula
that is right, in a document whose stated purpose it cannot perform:**

`multi-signal-false-positive-decomposition.md` (ORDER line 351, read whole,
tranche 20), `confidence: 0.85`, builds a pipeline whose entire stated purpose is
to **collect false-positive signatures, cluster them, and design suppression rules
to cut FPR by ≥40%.** §1.2 defines the trigger: *"A false positive occurs when the
weighted sum crosses the trigger threshold (default 0.65)."* The synthetic
generator in §3.2 then draws each signal from a range whose **maximum weighted sum
is below 0.65 in all four scenarios**:

| Scenario | Max signal values | Max weighted sum | vs 0.65 |
|---|---|---|---|
| 1 — new legitimate topic | 0.6 / 0.7 / 0.2 / 0.15 | **0.435** | **cannot trigger** |
| 2 — hedging misclassified | 0.5 / 0.2 / 0.6 / 0.1 | **0.370** | **cannot trigger** |
| 3 — low-exposure pattern | 0.7 / 0.15 / 0.1 / 0.5 | **0.3725** | **cannot trigger** |
| 4 — cyclic preference | 0.3 / 0.6 / 0.1 / 0.4 | **0.345** | **cannot trigger** |

Every one of them is stamped `ground_truth=False` — the dataclass field whose own
docstring reads *"human-labeled: False = false positive."* **A signature that never
crossed the trigger is not a false positive; it is a true negative that never
alerted.** The consequence is arithmetic and total: every synthetic signature
lands in the `tn` bucket of §6.2's own counter, so `fpr = fp/(fp+tn) = 0` **by
construction** — and the file's headline target, *"reduce false positive rate by
≥40%,"* is met perfectly by a generator that cannot emit a single false positive to
suppress. Phases 2–5 (cluster 200+ signatures, design gating rules, A/B test,
production deploy) all operate on an empty phenomenon.

**The same file carries the defect a third time, in §2.1's own table**, which is
headed *"Dominant combinations likely to trigger false positives"* and catalogues
S1+S2 (weight sum 0.55), S1+S3 (0.55), S2+S3 (0.50) and S1+S4 (0.50). **0.55 < 0.65:
saturating every signal in those four combinations still cannot cross the
threshold the file set three sections earlier.** Only S1+S2+S3 (0.80), S1+S2+S4
(0.75) and all-four (1.00) have weight sums that clear 0.65 at all, and each needs
signals near saturation. The table catalogues as the primary false-positive
signatures four combinations that are arithmetically incapable of being any.

**Why this belongs with C-034 rather than under C-033.** ORDER 351 *is* also a
C-033 instance — its §2.1 table falsifies its §1.2 threshold in the file's own
weights, which is substitution, which is C-033. **What earns it the new class is
the direction of the failure in the generator: C-033 finds a wrong number next to a
right claim, and this finds a right number next to a claim the number cannot
support.** The weight table is not wrong. The threshold is not wrong. The bug is
that the *instrument* has no reachable output in the class it is supposed to
generate, so a well-formed pipeline measures nothing and reports success — which
is the same shape as C-027 (a verification step with no failure mode), one level
up: **C-027 is a check that cannot fail; this is a measurement that cannot produce
the thing being measured.** A generator whose output is provably outside the domain
it was built to populate is a stricter failure than a guard that always passes,
because the guard is at least visibly trivial while the generator looks like
substitute data.

**The design requirement it earns:** *for any synthetic/bootstrapped data
generator, substitute the maximum of every sampled range through the file's own
scoring function and check the result can reach the threshold the file's own
decision rule uses. A generator whose maximum output is below the trigger produces
only true negatives, and any metric computed from it is vacuous — including the
metric the file sets as its own success criterion.* O(1) per generator, R-J2 clean
(no measurement, no benchmark, just range endpoints through a stated function),
and it holds at 14,589 files. The companion rule follows from the same check:
**bootstrap data must be validated against the decision rule before it is admitted
as a substitute for the real thing** — the file's own §3.1 already knows the
synthetic path is a fallback (`if len(signatures) < min_fp_samples`), and never
checks whether the fallback is admissible.

*(A fourth instance from the same tranche, `multi-objective-k-lambda-optimization.md`
ORDER line 350, carries two substitution-checkable arithmetic errors in its
posterior-sample derivation and is filed under C-033 in the tranche's verification
queue; it is a numeric contradiction, not a specification mismatch, and is noted
here only so the two tranche-20 files are not confused with each other.)*

---

## C-035 · A measurement protocol that cannot execute, inside a file whose thesis is that measurement must be run — and a rate named for one quantity that is computed as its complement `NEW — tranche 21`

**Earned by:** `online-active-learning-preference-schema-drift.md` (ORDER line 361,
read whole this pass) §4.3 and §2.4.

This is the fourth consecutive tranche whose strongest result is about the evidence
base rather than the brain, and the first about a **protocol that does not run**.

**The evaluator raises `NameError` before it can return.** ORDER 361 §4.3 opens with
a function whose signature is `evaluate_drift_detection(ground_truth_drift_events,
detected_events)`. It computes `tp`, `fp`, `fn`, `precision`, `recall` and `f1` from
set operations on those two arguments. It then computes time-to-detect:

```python
ttd = median([detected_time - truth_time for truth_time, detected_time in matched_pairs])
```

**`matched_pairs` is never defined.** It is not a parameter, it is not computed
earlier in the function body, and it does not appear anywhere else in the file. The
statement raises `NameError` on first execution. **The function therefore never
returns its dictionary** — and `median_time_to_detect_sessions` is one of the six
metrics the file lists in §6.2 as an evaluation target, and one of the two metrics
(§10, "Measure detection latency") it tells the implementer to build a benchmark
for. A protocol that raises before returning has measured nothing, and a table
listing six targets above it presents all six as pending rather than four.

**The same section names a rate for one quantity and computes its complement.**
`false_positive_rate` is returned as `fp / len(detected)`, which is `1 - precision`.
`false_negative_rate` is returned as `fn / len(ground_truth)`, which is `1 - recall`.
Neither denominator contains a true negative, so neither can distinguish *a detector
that fires rarely* from *a detector that is accurate*: a system that never fires
returns `false_positive_rate = 0` and passes the §6.2 target of `≤0.15` trivially.
**FPR requires `fp/(fp+tn)` and FNR requires `fn/(fn+tp)`; the function never computes
a true negative at all.** This is the C-034 shape one level up — a correct-looking
name attached to a quantity that cannot support the claim made of it — and it is the
*second* file in two tranches to make a vacuous-metric argument: ORDER 351's
generator cannot emit a false positive, and ORDER 361's evaluator cannot emit a true
negative. **Both make the same headline claim — a false-positive rate has been
reduced / bounded — and neither instrument can produce the class of error the claim
is about.**

**A third, smaller instance, and this one is a unit error with a stated derivation.**
§2.4 defines the precision-degradation alarm as `drift alert if precision(p, recent)
< precision(p, historical) - δ`, and then writes `where δ = 0.15 (empirical threshold
from DeepParse's 1.5% PA drop)`. The cited effect is **1.5 percentage points = 0.015**
on a quantity the same line defines as a ratio `TP/(TP+FP)`. The file sets the
threshold **ten times** the effect it derives it from. An alarm set an order of
magnitude above the drift it is meant to catch will not fire on that drift.

**Two more in the same file, both C-033-adjacent but neither worth a new class.**
§3.1's trigger is `drift_score = w1*cw_decay + w2*consolidation + w3*correction +
w4*precision`, threshold `> 0.65`. **The four weights are never given anywhere in the
file**, and the four signals are on incommensurable scales (a CW delta, a recurrence
count, a correction count, a ratio), so the aggregate is not computable by anyone
reading it. §2.2 separately defines a *second* quantity also called "drift score" as
`recurrence(new) * (1 - similarity(new, existing))`, which is unbounded above 1 and
would exceed 0.65 on its own at recurrence 3 — so the two definitions of the same
named quantity cannot be composed into the pipeline of §3.1. §3.2's
`select_drift_annotations` is presented as Python but contains `scores = entropy ×
diversity_bonus` (a U+00D7, not `*`), references two names never bound (`entropy`,
`diversity_bonus`), and calls `argmax` on a scalar.

**And the mitigations that would prevent the false positives are catalogued but not
wired in.** §4.1 lists four false-positive sources and a mitigation for each —
sustained decay over ≥3 cycles, seasonal-baseline exclusion, a condition field, a k=3
self-consistency check. **§3.1's scoring function contains none of them.** An
implementer copying the pipeline in §3.1 gets an unprotected trigger; the protections
exist only as prose in a later section, and nothing in the file connects them.

**The design requirement it earns — two, and both are O(1) or a single parse:**

1. *Any code block presented as the evaluation protocol must be executed, or at
   minimum name-resolved, before the file publishes the metrics that block is
   supposed to produce. A function that raises before its `return` invalidates every
   row of the target table above it.* One `compile()` + one `exec()` of the extracted
   block catches this, and it is exactly as mechanical as C-005.
2. *A rate named `false_positive_rate` or `false_negative_rate` must have a true
   negative in its denominator.* If the evaluation set contains no negatives, the
   correct name is `1 - precision` / `1 - recall`, and the correct target is not a
   rate at all. This is a one-line grep for `fp / len(detected)` and friends.

Both hold at 14,589 files, and neither is a self-measurement (R-J2): the first is a
parse of a file that already exists, the second is a pattern match over a name.

**Why this is a new class and not C-027 (a verification step with no failure mode).**
C-027 is a check that always passes. **This is a check that never runs** — the defect
is upstream of the check, in the artifact the check is written in, and the file that
carries it is a *roadmap* whose §7 is four phases of unchecked boxes and whose §6.2
lists six numeric targets. The distinguishing feature: the artefact's own framing is
"measure this, here is how," and the how is inoperative. An arena that grades designs
on whether they have metrics will grade this file as strongly evidenced, because it
has a metrics table, a protocol, and an implementation roadmap. It has none of the
three working.

**Two more instances of the same class, both from tranche 21, and the second is in
the file the arena would most want to trust.**

**ORDER 369 §"Pre-computation Validation Algorithm" — the security control that
does not execute.** The file calls its linear-time validator *"the single most
effective mitigation"* and the basis for rejecting blow-up attacks *before* memory
allocation. Its `walk()` function contains:

```python
case TAG(6): // Reference
    chainLen = state.refChainLengths.get(item.content) + 1
```

`refChainLengths` is declared as a **`Map`**, which is precisely the structure that
returns an absent value for an unseen key. `None + 1` raises `TypeError` on the
**first** reference to any identifier — i.e. on the first reference in any document
that has one. The depth, table, size and chain checks are all downstream of that
line, so the file's headline defence is unreachable from the first input it meets.

**ORDER 361's companion defect in the same shape, and this one is a *derived
constant* that the file's own formula excludes.** ORDER 374 §3 specifies a
seven-term weighted bootstrap whose weights sum to 1.00, then §4.2 tabulates the
bootstrap values the design assumes (0.3, 0.4, **0.5**, **0.8**) and §6.3 reasons
from *"CW ∈ [−0.5, 0.8] typically."* Substituting the maxima of all seven terms into
§3's own formula gives a ceiling of **0.42** — and 0.8 is §2.2's *raw* return value,
not the function's output. The file's headline conclusion ("self-sustaining in 2–5
sessions vs 15+ vanilla") is computed from bootstrap values the recommended formula
cannot produce. **Same class: a downstream claim resting on a value the stated
computation excludes.** C-033 covers the case where the file's own *numbers* are
wrong; this is the case where the numbers are fine and the *function* does not reach
them.

---

## C-036 · A file's summary statistics contradict the table they were computed from, in the same section, in four lines `NEW — tranche 21`

**Earned by:** `packed-cbor-resource-limit-recommendations.md` (ORDER 370, read
whole this pass) §3.1 and §3.3.

This is C-033's most concentrated instance yet, and it earns its own class because
the defect is not in the *claim* — it is in the **aggregation step between a survey
and its summary**. C-033 finds a wrong number beside a right claim. **This finds a
right number beside a table that cannot produce it.**

§3.1 tabulates seven implementations' max-depth defaults:

| Library | Max Depth |
|---|---|
| cbor-rs | 128 |
| cbor-core | 200 |
| fxamacker/cbor | 32 |
| cbor-php | 1,000 |
| Chromium CBOR | 16 |
| cbor2 | Unbounded |
| go-ipld-prime | 1,024 |

§3.3, headed *"A Statistical View,"* then reports over "the 7 implementations
above":

- **"Mode: 32 (Chromium, fxamacker/cbor)"** — the table gives Chromium **16**, and
  every one of the seven values is distinct, so **there is no mode**. The file names
  two libraries attaining a value the table gives to one of them, and the other
  value appears once.
- **"Median: 128 (cbor-rs)"** — excluding `Unbounded` the sorted values are
  16, 32, 128, 200, 1000, 1024 (n=6), median **164**. Including `Unbounded` as
  unbounded (n=7), median **200**. **128 is the third value, not the median**, and it
  is the value of the library the file names. The file attributes the median to the
  library whose number it is.
- **"Mean: 339"** — 339 × 6 = 2034 and 339 × 7 = 2373; the six finite values sum to
  **2400** and no subset of the table averages to 339 under any exclusion.
- **"Range: 16 (Chromium) to 1,024 (go-ipld-prime)"** — **correct**, and in direct
  contradiction of the mode bullet **four lines earlier**, which says Chromium is 32.

**So three of the four summary statistics are wrong, one is right, and the right one
contradicts a wrong one inside the same list.** The file's own §7 recommendations are
anchored to these numbers — §7.3 justifies a browser depth limit of 32 as
*"Consistent with Chromium CBOR (kCBORMaxDepth)"*, a claim that is true of the
**range** bullet and false of the **table** and the **mode** bullet simultaneously.

**The design requirement it earns, and it is the cheapest check in this file:** *any
section presenting summary statistics (mode / median / mean / range) over a table in
the same document must be recomputed from that table mechanically, not restated from
memory.* Mode and median over seven values is a sort and two index operations; the
entire class is catchable by a fifteen-line deterministic function with no model in
the loop, which makes it R-J2 clean and O(1) per table. **The generalisation: a survey
is an artifact and a statistic derived from a survey is content. The corpus validates
the first and inherits the second unchecked — which is the §8 inversion in its purest
form, because the *table* is the part a reader trusts and the *statistic* is the part
that decides.**

*(Two smaller instances in the same tranche, filed under existing classes rather than
given their own: ORDER 375's "cuts average extraction latency by 26%" is computed
from the wrong row of its own table — (420−140)/420 = 66.7% for the row that actually
uses the fast path, 26.2% only for the row that does not; and ORDER 369's proposed
depth defaults of 64/128/256 do not include the surveyed median of 320 and are
offered with no derivation, after a survey spanning a 64× range. Both are C-033.)*

---

Undated classes have no class ID yet. They are held in `VERIFICATION.md` and enter
the arena only when they clear the rubric.

---

## C-037 · A rule stated in prose and inverted by the file's own worked numbers, where the inversion runs in the *permissive* direction `NEW — tranche 22`

**A corpus file defines a semantic predicate, gives a worked example of that
predicate, and the example satisfies a weaker condition than the predicate. The
shipped gate enforces the weaker condition, so it admits a class of inputs the
rule forbids. Nothing crashes; the file is internally coherent as prose.**

**Worked through ORDER 377 (`procedural-tier-integration-cyclic-fps.md`), which is
the cleanest instance the read has found.** The file's §4.1 promotion rule reads:

> **3. Temporal recurrence** (one of):
>    - Same context + same action ≥3 times across **distinct cycles**
>    - Same context + same action ≥2 times within **one session**
>
> `min_cycles = 3`

and its §3.1 detection code computes:

```python
if dominant_freq > 0.25:
    period_sessions = int(1.0 / dominant_freq)   # ≈4
    return True, period_sessions
```

Two things break at once, and they compound rather than each being merely wrong:

1. **The frequency is computed over a session index, and the reciprocal is read as
   a period in sessions.** `dominant_freq` is cycles-per-session, so
   `int(1.0/dominant_freq)` is a session count — this direction happens to be
   right. But the file elsewhere uses the same symbol as *sessions per cycle* when
   justifying the `0.25` threshold, and the threshold is only meaningful in one of
   the two readings. **The parameter is overloaded across the file's own two
   sections**, which is Area 26's failure appearing in the file that was written to
   prevent it.
2. **The gate cannot distinguish the two bullets of rule 3.** `min_cycles = 3` is
   enforced downstream as `len(cw_history) >= 6` — six *observations*. A preference
   tracked in six consecutive sessions produces a decaying cyclic signature with
   the same dominant frequency as a preference recurring across three weekly
   cycles, and both pass. **The check that looks like the semantic gate is a
   sample-size check.**

**Why this is its own class and not C-034.** C-034 is a stated property not
entailed by the stated formula. This is the inverse: the formula is fine, the
*predicate* is stated in words, and the words are the thing the code fails to
implement. C-034's remedy is a formula audit; this one's remedy is a
**prose-to-code predicate audit** — every natural-language qualifier in a design
document ("across distinct cycles", "at the point of interpretation", "with no
intervening update") must be traced to the line that enforces it, and if no line
does, the qualifier is decoration. At 14,589 files (R-J5) the prose is the
specification: it is the only layer a human reads, and the code is the only layer
that runs.

**Second instance, same class, and it is a *threshold contradiction*:** ORDER 379
(`proxy-label-quality-validation.md`) states two different agreement targets for
what it calls the same thing — §3.1 sets *"Inter-Annotator Agreement: Target
≥0.80"* while §3.3's acceptance table sets *"Cohen's κ (proxy vs human) ≥0.70"*.
**These are different quantities** (three-way agreement versus two-rater
agreement), the file uses the name "agreement" for both, and it never says which
governs acceptance. The sampling plan that would produce them (§3.2, 130 samples
across 6 strata) also cannot support a κ per stratum: stratum E carries n=30
across three distinct sub-strata, i.e. **n=10 per sub-stratum**, which is below the
point where a κ is stable. So the protocol is *underpowered for its own
acceptance criterion*, not merely ambiguous about it.

**Third instance, and this one is a metric that cannot be computed as stated:**
ORDER 398 (`self-reinforcement-bias-preference-llm-annotation.md`) reports
specificity/TNR **below 25%** across 14 judges and pairs that with *"errors at
>0.90 stated confidence of 52–69% for LLM annotators vs 10–38% for human"* — the
implied comparison is sound only if the two annotator classes saw the same items
at the same difficulty, which the file's own §"Limitations" concedes it did not
control. A rate reported across unmatched item pools is not a rate; it is two
rates subtracted. Recorded as a class instance because the failure is *reporting a
comparison statistic whose denominator was not held constant*, which recurs
throughout the arena's evidence base and is the reason no slot here holds HIGH.

**Deterministic check (O(1) per document, no execution, R-J2 clean):** for each
prose qualifier in a design document, grep the shipped code for a token that could
enforce it. Unmatched qualifiers are the defect queue.

---

## C-038 · A component declared unchanged while a second component in the same file is declared changed, and the two declarations are load-bearing for the same result `NEW — tranche 22`

**ORDER 381 (`query-time-vs-ingest-time-synthetic-generation.md`) evaluates two
synthesis strategies and reports their gains against the same baseline, but the
two strategies sit at different points in the pipeline — one synthesises at
**ingest**, the other at **query time** — and the file never states that the
comparison is therefore not a comparison of strategies but a comparison of
*trigger positions*.** The ingested form is built once and amortised over
thousands of reads; the query-time form is built fresh on every read and paid
every time. A reader of the gain table sees two numbers for the same quantity and
cannot tell that one of them is amortised and the other is not.

This is a distinct failure from C-033 (a file's own numbers falsify its own thesis)
because **the numbers are each correct and the thesis is not wrong — the
comparison is simply not the one the table's column headers claim.** It is the
same shape as the arena's own §8 finding, one level down: the validated artefact
(the gain table, with its arithmetic intact) is trustworthy, and the
*interpretable claim* layered on top of it is not, because the axis label is
missing rather than the value.

**Why it matters at scale (R-J5):** the entire query-time-versus-ingest-time
question in the arena resolves on this distinction, and at 14,589 files the
amortisation gap is not a rounding error — it is the difference between a
strategy that is free per query and one that is not. **A comparison that omits the
amortisation basis cannot decide it.**

**Deterministic check:** any results table whose rows differ in *when* a
component was built, rather than in *what* it does, must carry the trigger position
in a column and state the amortisation. Otherwise the table's rows are not
comparable and the delta is not a result.

---

## C-019 · A verifier that resolves a bare name cannot distinguish a citation from a collision `NEW — remediation pass 2026-09-26`

**The defect.** `scripts/citation_remediation.py` reported **39 MUST RE-READ** as
unearned citations. Reading the twenty I was allocated found that **four of them
were not unearned at all** — they were *name collisions*. The corpus contains the
same document at two paths:

- `active-wiki/research/enforcement-layer-supersede-prevention.md` — ORDER 177, `[x]`
- `oracle/brain/research/enforcement-layer-supersede-prevention.md` — ORDER 1693
- `active-wiki/research/graphiti-temporal-knowledge-graph.md` — ORDER 309, `[x]`
- `oracle/brain/research/graphiti-temporal-knowledge-graph.md` — ORDER 1887

The arena cites these as bare filenames (`enforcement-layer-supersede-prevention.md`),
with no directory prefix. The matcher resolves a bare name to *a* ledger row, got
the `oracle/brain/` copy, found it unmarked, and reported an unearned citation
against a file that had in fact been read at its twin three tranches earlier. The
same pattern holds for the eight `concepts/` and `decisions/` files in the list:
`active-wiki/concepts/belief-revision-ai-agent-memory.md` is ORDER **2** and marked
`[x]`; `oracle/brain/concepts/belief-revision-ai-agent-memory.md` is ORDER **575**.

**Why this is a corpus-hygiene class and not a tooling bug.** C-012 requires a
citation to be checked against the string it cites. C-014 requires a resolvable
identifier. Both assume the string is *specific*. This class is the case where it
is not: **the corpus itself publishes the same document under two roots**, so a
filename is not a unique identifier, and any verifier that treats it as one will
manufacture findings. That is the arena's own §8 inversion one level down — the
validated artefact (the checker's verdict line, its arithmetic intact) is
trustworthy, and the *interpretation* layered on it is not, because the key is not
unique.

**Why it matters more than a wrong count.** A remediation pass reads files *to
legitimise citations*, and this pass was explicitly told to read the 39 first. Four
of those 39 slots were spent on documents already in hand. Had the arena been
faithful to the instruction and read 39 files, roughly a tenth of the pass budget
would have gone to re-reading. Worse: the finding points the wrong way. "Cited but
unread" invites *striking a legitimate citation*, which would have removed a
correctly-earned reference from the answer file. **A verifier that produces false
positives is not a safe-to-fail verifier**, and the remediation rule that follows
from it must be the conservative one: on an ambiguous citation, **read, do not
strike**.

**Ranked candidates.**

1. **Require directory-qualified paths in arena citations — recommended.** Make
   `ARENA.md` cite `active-wiki/research/X.md`, never `X.md`. Cost: one edit per
   existing citation. General: forces the whole file to the rule at once.
   Verifiable: the matcher's ambiguity disappears by construction. Evidence: this
   pass, four instances. Consequence: removes both false positives and the
   false-strike hazard. Novelty: none, and none needed.
2. **Match on basename, then require *every* colliding row to be `[x]`.** Treat a
   multi-row match as satisfied only if all rows are marked. Cheaper, but it
   accepts a genuine gap: one twin read, one twin unread, citation declared sound.
   Rejected — it trades a false positive for a false negative, which is worse,
   because a false negative is invisible.
3. **Report collisions separately from unearned citations** and never count them
   in the same number. Honest reporting, no fix to the underlying key. Rejected as
   a sole remedy; worth doing *alongside* candidate 1.

**Deterministic check:** for every basename the arena cites, `grep` the ledger for
all rows with that basename. If the count exceeds 1, the citation is ambiguous and
must be directory-qualified. This is one pass over the ledger and it is the check
that would have caught all four instances before any file was opened.

---

Undated classes have no class ID yet. They are held in `VERIFICATION.md` and enter
the arena only when they clear the rubric.

**`ARENA-INFRA.md` is not reset with the arena.** It was carried forward
deliberately through the 06:53Z restart: the distillation is re-derived from
scratch, the corpus-hygiene requirements are not rewritten each time. C-015 is the
first class earned by a file read in the *current* pass rather than a prior one;
**C-016 is the first class earned by a *measurement* in the current pass** — three
instances, each found by reading a field and comparing two files, none of which a
linter would have been written to look for. **C-019 is the first class earned by a
file that was opened only to check whether it needed opening** — four of the
twenty files this pass read were found already read, under a second path.

---

## C-020 — The answer file's seven-field slots are truncated mid-sentence, and no invariant tests whether prose ends

**Class:** answer-file integrity. **Instances: 257 field lines.** **Earned:** 2026-09-26,
remediation pass, by reading `mambalrp-extension-gated-deltanet.md` (ORDER 1914) to
check Area 24's own earning file and noticing the arena's rendering of it.

**The defect.** A slot field that ends without terminal punctuation, at the seven
positions the format defines:

```
- **Brain part:** belief revision in the prefrontal cortex; epistemic entrenchment
- **Design:** implement `expand` / `contract` / `revise` as real operations with an
- **Already exists:** AGM is a 1970s framework, not a package. Nothing in the twenty
- **Grade:** design `UNTESTED` · Support: **1 source**. The literature's *implemented*
- **Interaction:** constrains Rank 2. If the chain is the only thing that will ever be
```

Five consecutive fields, four cut mid-sentence, at consecutive lines.

**Extent and boundary.** Areas 1–27 are affected (13/19, 7/8, 15/22, 13/18, 16/22,
13/19, 10/13, 13/20, 10/16, 11/14, 9/14, 13/21, 7/11, 4/6, 8/12, 14/18, 10/16,
16/18, 15/18, 11/18, 12/15, 13/15, 8/15, 12/15). **Areas 28 and 29 are 0/21 each.**
**257 total.**

**Provenance — this is one event, not a decay.** Measured across the last four
commits: `4d04ac5` 284, `0849d56` 257, `a352015` 257, `fc7b398` 257. **It has not
grown since the two-file split** and is not an accretion failure. The boundary is
the cause: the split commit `0849d56` rewrote Areas 1–27 and cut each field at a
character budget; Areas 28–29 were authored after the split and are intact. **C11
— the accretion check — reported `pass` on this file.** Accretion is not what
happened here, so C11 was right and the file is still broken.

**Why no checker sees it.** Every invariant tests structure: row counts,
contiguity, path match, citation resolution, growth budget. **None tests whether a
field's prose ends.** A line cut at 85 characters is a structurally valid line. A
checker looking for this must inspect the *last token* of a field, not its shape.

**Consequence for the deliverable.** The **ranking survives** — headings, grades,
support counts, interaction notes, and the whole evidence file are intact, and the
order is still legible. **The slots do not.** An architect reading Area 21's Rank 1
receives `Design:` and half a clause. The arena currently looks finished and is
not usable as a ranked answer without repair.

**Why it was not repaired alongside the defect that prompted this pass.** Repair
means reconstructing 257 truncated sentences across 27 areas, from the evidence
file and the corpus. That exceeds a 12-minute slot, and the honest inputs are not
the arena's own cut text. **A guessed reconstruction is worse than a visible
truncation**, because a truncation announces itself as damage and a guess reads as
finished work — which is precisely the failure mode this workspace keeps finding
in the corpus. **The repair is a dedicated pass and the decision to spend it is
the user's.**

**Deterministic check, for whoever runs it:**
```bash
awk '/^### Area [0-9]+/ {match($0,/Area [0-9]+/); a=substr($0,RSTART+5,RLENGTH-5)}
     /^- \*\*(Brain part|Design|Already exists|Backup doc|Grade|Interaction|Justification)/ {
       t[a]++; if ($0 !~ /[.:;,)`*—]$/) b[a]++ }
     END {for (k in t) printf "Area %s: %d/%d\n", k, b[k], t[k]}' ARENA.md | sort
```
A field is truncated when it ends without terminal punctuation. **This belongs in
`arena_invariants.py` as a twelfth check** — it is cheap, deterministic, and it
catches a defect class that has survived eleven checks and at least three passes
of self-audit.

**The general form, which is the reason this is filed as an infra class and not a
one-off.** This is the skill's own inversion finding, located inside the workspace
rather than the corpus. The validated path — invariants, citations, growth budget,
`[x]` ledger rows, frontmatter — produces the appearance of authority. The
unvalidated path produces the content. Here the authoritative-looking artifact is
the deliverable itself, and what it fails to carry is the seven fields the format
exists to deliver. **Every check this workspace runs is a check on the apparatus.
Not one, before this, checked the prose.**

---

## C-034 — A corpus file may carry a complete validated apparatus and no body at all `NEW — tranche 27`

**Two instances in one tranche, and they are different severities of the same
defect.**

**ORDER 529, `Attention/Value-Driven-Attentional-Capture.md`.** 52 lines.
Frontmatter: `type: reference`, `status: active`, `confidence: high`. The body
consists of a `## Related Pages` block and a `## Sources` heading followed by
**25 numbered references** — every one carrying a DOI or a PMID, correctly
formatted, internally consistent. **There is no prose at all.** No overview, no
mechanism, no evidence section. The page's own `description` is the two-word title.

**ORDER 525, `Attention/Load-Theory-Attention.md`.** 62 lines, and the same
metadata profile: `type: research_report`, `status: active`, `confidence: high`,
**twelve URLs in `sources:`**. The body stops mid-document after §Core Mechanisms,
with two dangling `[[wikilinks]]` and no §Methodological Notes, no §Sources, no
§Open Questions — while its own Overview promises *"core mechanisms, key empirical
findings, neural evidence, computer parallels, major criticisms, and open
questions"* and delivers the first of six.

**Why this is a new class and not an instance of C-002.** C-002 is *"apparatus
quality is uncorrelated with claim correctness"* — the apparatus is good and the
prose is wrong. **This is the degenerate case: the apparatus is good and the prose
is absent.** A reader checking the apparatus finds twelve or twenty-five
verifiable, correctly-formatted sources. A reader checking the content finds
nothing. The two checks are maximally *misleading in the same direction*, which is
worse than C-002's ordinary case, where a careful reader would at least be misled
by a claim rather than by an absence.

**Why it is dangerous specifically for this arena.** Four sibling attention files
(ORDER 519, 521, 523, 526) cross-reference `Load-Theory-Attention.md` as though it
were a full treatment, and ORDER 521 §"Overlaps & Tensions" argues a substantive
dispute against it — *"Load Theory emphasizes perceptual capacity rather than
binding as the bottleneck, creating a tension about whether the limit is at feature
detection or feature integration"* — **on the authority of a page that contains no
argument.** The citation is unearned in the strongest sense available: the file
cited makes no claim to have been misread. This is a step past the citation rule
in the skill, which requires a file to have been read before it is cited; here
**the file was read, and the correct action is to strike the citation**, not to
re-read it.

**The check that catches it, which is cheap and deterministic.**
A `research_report` or `reference` file whose prose body (content outside
frontmatter, headings, link blocks, and reference lists) is shorter than some
floor — 500 characters is generous — is a stub. Both files here fail it by one to
two orders of magnitude. This belongs in `arena_invariants.py` as a thirteenth
check, and it is the corpus-side twin of C-020: C-020 catches a field that drifts
across the corpus, and this catches a document that never had the content its type
declares.

**The rule it produces, and it is the arena's own rule restated:**
*`confidence: high` describes the apparatus. It does not describe the content, and
a file with no content has no grade at all.*

---

## C-035 — A basename collision can destroy evidence, not merely create it `NEW — tranche 27`

The remediation pass (2026-09-26) filed **C-019**: *"a verifier that resolves a
bare name cannot distinguish a citation from a collision,"* and produced the rule
*on an ambiguous citation, read, do not strike*. 446 basenames in the corpus appear
at more than one ORDER row. That pass then verified 19 apparent duplicates as
**byte-identical** twins (`active-wiki/` and `oracle/brain/` publishing the same
document twice), and correctly concluded that the "19 unearned citations" were 19
name collisions.

**ORDER 508 is the counterexample, and it inverts the direction of the risk.**

- `oracle/brain/AI-Reasoning/Reasoning-Models-and-Test-Time-Compute.md` — ORDER 508, **17,483 bytes**
- `oracle/brain/AI-Reasoning-and-Chain-of-Thought/Reasoning-Models-and-Test-Time-Compute.md` — ORDER 506, **12,524 bytes**
- `cmp`: **DIFFERENT**

These are **two different documents sharing one basename**, not a duplicated
record. Every pass so far treated twin-hood as the default explanation for a
basename collision, on the evidence of 19 identical pairs. That evidence does not
generalise, and the failure it invites is the mirror of the one C-019 was filed
for: **C-019's risk is a phantom source inflating a support count; this is a real
source being silently merged into another and erased.**

**What it would have cost here, concretely.** C-026-4 is a live three-way dispute
about the shape of test-time-compute scaling. ORDER 504 says logarithmic; ORDER 506
says a power law with α≈0.1–0.3; **ORDER 508 §2.3 says power-law-*like* and adds
that *"the shape is domain-dependent"* — the only one of the three that carries a
domain-dependence term.** Had 506 and 508 been deduplicated on basename, the
dispute would have collapsed to two positions and the most design-relevant claim in
it would have been lost. **Area 3's effort allocation differs under each shape.**

**The rule, which amends C-019's rule rather than replacing it:**

> On a basename collision, **read both.** Do not strike, and **do not merge.** Two
> rows with one basename are two sources until proven identical, and proof is
> `cmp` reporting zero difference — never a size match, never a shared directory
> prefix, never a matching title in the frontmatter.

**The check that catches it, and it is one line.**
`arena_invariants.py` should report, for every basename with more than one `[x]`
row, whether the files are byte-identical. The corpus currently has **446**
colliding basenames and the tool reports `PROVEN read: 0` — **which is exactly the
signature of a tool that has never run this comparison and is reporting an empty
branch as a result.** C-019 diagnosed the ambiguity; this files the missing
measurement, and notes that the remediation pass's clean result did not clear it.

---

## C-036 — The bodyless index shell: a validated apparatus with a file listing and no prose

**First observed tranche 28 (2026-09-26), reading ORDER 515, 517, 518, 527, 533, 535,
538, 540, 543, 544 — ten index files in one tranche, all bodyless.**

C-034 (tranche 27) recorded a file with complete validated apparatus and no body. This
class is worse, and it is worth separating because it is *systematic* rather than
incidental: **nine of the twenty files read in tranche 28 were index shells.**

The template is identical every time and is machine-generated, not authored:

```
## Overview
Knowledge domain: <Pascal-Case-Of-The-Directory-Name>

## Contents
### Files
- [<Sibling>.md](<Sibling>.md)

### Subdomains
No subdomains.
```

with frontmatter `type: Index`, `verified: []`, `stale_after: 2026-12-08`, and —
this is the part that matters — **`confidence: high`**. ORDER 518 (the `archive`
index) carries **`confidence: medium`** and `"No files yet."` The other nine carry
**`confidence: high`** on a file that asserts nothing about the world.

**Why this is a defect class and not a curiosity.** The skill's own closing finding
applies with unusual force here: *the validated code path produces the appearance of
authority, and the unvalidated path produces the content.* An index shell has the
**entire validated path** — frontmatter parses, `id` is well-formed, `stale_after` is
set, `confidence: high` — and **none of the content path**. It is the purest instance
of the inversion the arena has found, because there is no content to be wrong about.
A corpus-health dashboard that counts files, checks frontmatter validity, and
tracks `stale_after` will report these as the *healthiest* files in the corpus.

**Three consequences, each of which costs something real.**

1. **A read slot can be consumed by nothing.** Ten of twenty slots in one tranche
   yielded no candidate design, no corroboration, and no area. At 1,268 rows
   remaining, index shells at this density are a material fraction of the remaining
   corpus and therefore of the remaining *schedule*. This is an R-J5 statement: a
   rule that assumes every row is a document is a rule that only holds because a
   human reading by hand would notice.

2. **The index can be a *wrong* inventory, not just an empty one.** ORDER 524
   (`Attention/index.md`) is the first shell found that is not merely bodyless but
   **incomplete**: it lists exactly three entries — `[[Attentional-Residue]]`,
   `[[Inattentional-Blindness-Change-Blindness]]`,
   `[[Vigilance-Decrement-Sustained-Attention]]` — in a directory that
   `LEDGER.md` shows contains at least **ten** read or pending pages
   (ORDER 519–531, including `Attention-Networks.md`, `Feature-Integration-Theory.md`,
   `Frontoparietal-Attention-Networks.md`, `Load-Theory-Attention.md`,
   `Negative-Priming.md`, `Value-Driven-Attentional-Capture.md`,
   `Working-Memory-Limits.md`). **Seven of the domain's pages are unreachable from
   the domain's own index.** The directory was renamed (it holds `Attention/` and
   `Attention-Mechanisms/` entries) without the index being regenerated — the
   generated at-timestamps differ (`2026-08-23T05:49:58Z` for ORDER 524 versus
   `2026-09-08T00:00:00Z` for the September shells), which is consistent with the
   index having been written once in August and never revisited.

   **This is a retrieval defect, so per §7 it is a design requirement and not just
   hygiene:** *every content page must be reachable from its domain index by a
   resolvable link, and a page with no inbound link from its own index is
   invisible to index-mediated traversal even when it is fully indexed elsewhere.*
   The instance goes in the queue; the requirement goes in the arena.

3. **It is a live false-positive generator for any completeness check.** A checker
   asking "does every domain directory have an index?" passes on all ten. A checker
   asking "do all index entries resolve?" passes on all ten. Both would have passed
   on ORDER 524 while seven pages were unlinked. **Per the skill's own rule — a
   check that can pass via a fallback is not verifying** — an index-presence check
   is exactly that shape, and should be treated as an `UNTESTED` instrument until
   it has been shown to fail on a case it should catch.

**The check that catches it.** `arena_invariants.py` should flag any `[x]` row whose
file is under 1,000 bytes *and* contains no `##` section heading beyond the
template, and separately should compare each `index.md`'s link list against its own
directory listing and report the difference. **Both are deterministic and neither
requires a judgement call.** The arena has no such check today, and until one
exists, `PROVEN read: 446` colliding basenames and ten bodyless shells are both
being absorbed silently into the corpus-health picture.

## C-040 — An index that links a subset of its own directory, where the omission is the highest-value file `NEW — tranche 29`

**First instance: ORDER 555, `Cognitive-Architecture/index.md`.** The index lists
**two** files — `Cognitive-Architecture-Models.md` and `Hierarchical-Temporal-Memory.md`
— in a directory that contains **three**. The omitted file is
`Dual-Process-Cognitive-Memory.md` (ORDER 553), which is the **most
measurement-dense document in its tranche**: three benchmarks, a full ablation
decomposition with per-component point costs, a scale analysis with named complexity
bounds, and an explicit falsifiable prediction. It is also `status: stable`, the only
such status in its directory.

**Why this is worse than a broken link, and why it belongs here rather than in
hygiene.** A missing link target loses a reader the page. An index that *looks
complete* — valid frontmatter, `confidence: high`, a `### Files` section, a `### Tags`
section, a `### Status` section — while silently omitting one entry in three is the
arena's inversion in its purest infrastructural form. **The apparatus is validated and
the content is wrong.** Every check the file passes is a check on its shape. Nothing
checks whether the list is the list.

**Second instance, same tranche, same shape: ORDER 549** (`Circadian-Rhythms/index.md`)
and **ORDER 547** (`Chinese-AI-Research/index.md`) and **ORDER 551**
(`Cognitive-Aging/index.md`) — all three link their single file correctly. So the
defect is **not systematic**, which is what makes it dangerous: the same generator
produced correct indexes in the same run. **A reviewer sampling indexes would find
three correct ones and conclude the corpus is fine.**

**Design requirement this implies (§7 exception).** Per the skill, a hygiene defect
that implies a design requirement goes in the arena, and this one does:

> **Every index must resolve to a mechanically-derived file list, and the derivation
> must be checkable.** A hand-maintained or LLM-maintained `### Files` section is a
> claim about a directory that no artefact in the corpus can verify. The check is
> trivial and deterministic — enumerate the directory, compare to the linked set —
> and its absence is the defect. **The same requirement applies to every generated
> manifest in this workspace**, and it is the same shape as Area 26: a bare name that
> does not carry which thing it names is a name that can be wrong without detection.

**Not repaired here.** These are corpus files and the skill forbids modifying them.
Recorded for the corpus owner.

**Relationship to C-036.** C-036 (tranche 27) is the *bodyless* index shell — a
validated apparatus with a file listing and no prose. C-040 is the inverse: a
substantial body with a **listing that is silently incomplete**. Both are the same
underlying failure — **the listing is generated and checked as an artefact while the
thing it claims to enumerate is not** — and they are recorded as a pair because a
checker written against C-036 alone would pass all four of these files.

### C-041 — Frontmatter `id:` collision between a directory index and its own content file

**First instance: ORDER 564 and ORDER 565** (`Computational-Neuroscience-Methods.md`
and `Computational-Neuroscience-Methods/index.md`), both declaring
`id: computational-neuroscience-methods`.

**The class, stated so a checker can be written against it.** A wiki page's
canonical identity is its frontmatter `id`, and a `[[wikilink]]` resolves through
it. When an index and a content file in the same directory share one `id`, **the
link target is not determined by the link** — resolution depends on load order,
index precedence, or filename fallback, and the corpus contains nothing that
records which rule applies. This is a **different defect from C-040**: C-040 is a
*listing that omits an entry* (a coverage failure), C-041 is *two objects claiming
one identity* (a resolution failure). A checker written against C-040 counts links
and would pass both files cleanly.

**Why it is not systematic, and the control condition that proves it.** Every
neighbouring index/content pair in the same tranche uses distinct ids — ORDER
558/559 (`functional-fixation-duncker` / `cognitive-science`), ORDER 560/561
(`bayesian-cognitive-science` / `cognitive-science-methods`). The generator
produced correct ids immediately before and after the collision. **A sampled
reviewer would find the neighbours correct and conclude ids are unique.**

**Design requirement this implies (§7 exception).** This one *is* a design
requirement, and it is a stronger one than C-040's:

> **A canonical id must be unique across the corpus, and uniqueness must be checked
> by construction rather than by convention.** The id is the primary key every
> retrieval layer joins on. Two pages sharing one is not a broken link — it is two
> rows in a table whose primary key is not unique, which means every query against
> it returns a non-deterministic answer. This is the same requirement as Area 26
> (a name must carry which thing it names), and it is the schema discipline the
> workspace's own conventions already state: **uniqueness is an invariant, not a
> default.**

**Detection is trivial and deterministic:** group all pages by frontmatter `id`;
any group with cardinality > 1 is a collision. Cheaper than C-040's directory
enumeration and strictly more load-bearing, because a collided id silently
corrupts lookups rather than merely hiding a file.

**Not repaired here.** Corpus files are read-only to this job. Recorded for the
corpus owner.

---

## C-042 · Stub file whose overview promises sections the body does not contain

**Found:** 2026-09-26, tranche 37, ORDER 715
(`oracle/brain/Distributed-Cognition/Extended-Mind-Theories.md`, 47 lines).

**Shape.** The file is structurally valid, has complete OKF v0.2 frontmatter
including `confidence: high` and ten `sources:` URLs, and a `Related Pages`
block. Its Overview enumerates what the report *"synthesizes … landmark
empirical evidence, the major criticisms and ongoing disputes, computational
parallels, and tensions with existing brain concepts."* **The body contains
none of the four.** It stops after two paragraphs of philosophical framing.

**Why this is a new class and not C-041.** C-041 is a frontmatter `id:`
collision between an index and its own content file. C-042 is the opposite
failure: the file is *uniquely identified and well-formed* while being a
promise rather than a document. It also differs from the empty-directory-index
stub (`*No files in this directory.*`), where the emptiness is declared.

**Retrieval consequence — this is the load-bearing part.** A link to this page
resolves, the page passes every artifact check the corpus tooling performs, and
a reader following the citation receives 47 lines that do not answer the
question. **This is the arena's §8 finding in its purest form: the validated
code path produces the appearance of authority and the unvalidated path
produces the content.** Here the validated path is *structural validity* and
the content path is *absent*.

**Detection.** Not currently automated. A candidate check: an OKF file whose
`description` or opening Overview contains an enumeration of promised sections
(count the comma-separated or colon-introduced list items) while the body
contains **zero** matching `##` headings. Filed as a proposal, not implemented
— `ARENA-INFRA.md` records requirements, and this job does not add checkers.

**Corpus instances so far:** 1 (ORDER 715). A directory-wide sweep has not
been run, and per the arena's rule that would be `not observed` → pending, not
`confirmed absent`.

---

## C-043 · Two files in one directory covering the same question, index listing one

**Found:** 2026-09-26, tranche 37, ORDER 710 + 711 + 712
(`oracle/brain/Developmental-Cognition/`).

**Shape.** `Developmental-Origins-of-Cognition.md` (368 lines, `id:
developmental-origins-of-cognition`, generated 2026-09-07) and
`Developmental-Origins-of-Cognitive-Architecture.md` (339 lines, `id:
developmental-origins-of-cognitive-architecture`, generated 2026-09-02) answer
the **same question** — core knowledge versus emergent mechanisms as the origin
of cognitive architecture — with different frontmatter ids, different
generation timestamps, and no index entry for the first. `index.md` (ORDER 712)
lists only the second. ORDER 710's `See Also` block links forward to 711, so
the corpus knows about the relationship from inside the file, but the index
does not express it.

**Why it matters for retrieval.** ORDER 711 is the better file — it carries the
Bramley et al. (2024) bootstrapping result (44.7% construct vs 22.6% deconstruct
generalization, t = 8.13), the neuroconstructivist synthesis, Karmiloff-Smith's
four representational-redescription levels, and the Oudeyer & Kaplan IAC
self-organisation account, none of which appear in 710. **The index points at
the right one, so this is not currently a retrieval failure — it is a
near-miss that will become one the moment the two files diverge further, or
the moment ORDER.txt order changes which is read first.**

**Related but distinct from C-041.** C-041 is a collision on a single `id:`.
C-043 is two validly-distinct files covering one question with an index that
sees only one. **Both are the same underlying disease: the index is a
generated artifact that is checked as an artifact, and the corpus is free to
grow underneath it.** A deduplication or merge decision belongs to the corpus
owner, not to this job — recorded, not repaired.

**Corpus instances so far:** 1. Not swept.

---

## C-045 · Append-only logs must never be corrected by rewrite

**Found:** 2026-09-26 19:59, tranche 37 — self-inflicted, 14 lines of
`RUNLOG.jsonl` destroyed. Full incident in `VERIFICATION.md` under *C-044*.

**The rule.** `RUNLOG.jsonl` is append-only. A wrong field in the last record
is corrected by **appending a correction record that supersedes it**, never by
reading the file, mutating an object, and writing it back. This is not a
stylistic preference: the rewrite destroyed 14 uncommitted records because the
run assumed they were recoverable from `git HEAD`, and they were not.

**Why it is a corpus-hygiene class and not a one-off.** The same failure mode
is available in every append-only artifact this workspace keeps —
`ARENA-EVIDENCE.md` (14,535 lines), the cron `usage_audit.jsonl`, the
`persisted_error_recoveries.jsonl`. Each is a file whose value is that it
accumulates, and each is one careless `write_file` away from losing its
history. `ARENA-EVIDENCE.md` survived this pass only because the correct
operation (`cat >>`) was used.

**Preconditions that made it possible — all three are checkable next time:**
1. The file was **dirty in git** (uncommitted lines), so `git show HEAD:` was
   not a valid recovery source. **Check `git log --oneline -- <file>` and
   `git status --porcelain <file>` before treating git as a backup.**
2. The writer used Python `open(path,'w')` after reading, which silently
   truncates. **`>>` and append-mode writes are the only sanctioned write for
   these files.**
3. No pre-write size assertion existed. **A cheap guard: record `wc -l` before
   the write and assert `after >= before`.** Any shrink on an append-only file
   is a bug, and the assertion is one line.

**Standing requirement.** Any future run that appends to an append-only log
must verify the line count did not decrease, and must not use a
read-modify-write cycle on it under any circumstances.

---

## C-046 · A generated directory index that asserts content it does not have

**First seen:** tranche 38, ORDER 751–760 and ORDER 823. **Instances in this
pass: 8**, of which two are structurally worse than a bare stub.

`oracle/brain/domains/local-ai/` contains seven sibling index files plus a
parent. Six of the seven are 27-line files whose entire Contents section reads:

    *No files in this directory.*

Each carries the full OKF v0.2 frontmatter block: `okf_version: "0.2"`,
`status: active`, `verified: []`, `stale_after: 2026-12-08`, and
**`confidence: high`**. A file that contains no content certifies high
confidence in the absence of content.

**The worse variant is ORDER 754 (`local-ai/index.md`).** It is not empty — it
is *populated-shaped*. It carries **eight empty section headings** (`## Models`,
`## Hardware`, `## Inference`, `## Quantization`, `## Deployment`,
`## Comparisons`, `## Queries`, `## Disputed`), each with no body; a blockquote
reading `> Status: Knowledge not yet installed`; and a `## Contents` list
containing exactly one entry, `[[DOMAIN]]`. **The file describes a populated
domain and states in passing that it is not populated.** Both facts are in the
file, and neither cancels the other for a reader or a retriever that keys on
structure.

**Why this is a class and not an instance.** A retriever that traverses by
heading structure, or an index-regeneration check that asserts *"every domain
index has a Contents section"*, receives a **pass** from all eight files. The
generator produced valid frontmatter, valid headings and valid cross-links; what
it did not produce is the thing the headings promise. This is the §8 inversion
in its purest and most mechanical form — **the validated code path produced the
appearance of a populated domain, and the unvalidated path (the content) is
absent** — and it is distinct from C-042 (a stub whose overview promises
sections the body lacks) because here the *generator itself* emitted the
promise, at scale, from a template.

**Check, O(1) per file, holds at 14,589 files:** an index file is
content-free if its `## Contents` section is `*No files in this directory.*`, or
if it has ≥3 consecutive headings with no body text between them, or if it
asserts a section count it does not satisfy. None of the three requires parsing
the prose.

**Standing requirement.** `confidence:` must not be emitted for a file with no
body content. A `confidence` field on an empty file is not a weak claim; it is a
false one, and it is the same shape as the arena's own `verified:` block — an
artefact that is reliably present and whose presence is not evidence.

---

## C-047 · Two files on one topic count as one source — the arena applied its own rule and declined a slot

**First seen as an explicit decision:** tranche 38, ORDER 831 vs ORDER 833.
Recorded because the arena had been *near* violating this and did not.

ORDER 831 (`Embodied-Cognition/Embodied-Cognition-and-Situated-Action.md`,
290 lines, 67 numbered sources) and ORDER 833
(`Embodiment-and-Robotics/Embodiment-and-Robotics-Cognition.md`, 161 lines) are
**the same subject from the same field**: Brooks's subsumption, the enactivist
programme, the free-energy principle, the symbol grounding problem, Moravec's
paradox. ORDER 831 is the deeper treatment; ORDER 833 is the summary with its
own key-papers lists. **A pass could have read both and reported two
independent confirmations of an embodied-cognition area.**

It did not, and the reason is general. The skill's rule — *three files restating
one study are one source, not three* — is a rule about **independence of
evidence**, and independence is a property of the **underlying work**, not of
the file count. Two files that both cite Brooks (1986, 1990, 1991) and Friston
(2010) have one source in the relevant claim regardless of how many headings
they divide it into. **An `Already exists?` line listing four Brooks papers
across two files is one line, and must be graded as one.**

**Corollary that costs the arena something.** The rule suppresses corroboration
counts, so applying it honestly makes areas look thinner than a file count would
suggest. That is the correct direction of error: an inflated support count is a
claim the arena cannot cash, and a deflated one is merely conservative.

---

## C-048 · Encyclopaedic entity pages are secondary literature and must never increment a support count

**The class.** `Entities/*.md` and `entities/**` — biographical or
organisational profiles, each internally well-formed, densely cited, carrying
`confidence: high` or `confidence: medium` frontmatter, and containing no claim
of its own that is not traceable to a primary source the arena may already hold
at a higher grade. Eight such files were read in tranche 39 (ORDER 847–854) and
**none was admitted as corroboration.**

**Why it is a class and not an instance.** The two most dangerous members were
ORDER 847 and ORDER 854, and both were dangerous for the same reason: **each is
about a subject the arena already holds an area for, and each restates a result
the arena already holds with better evidence.** ORDER 847 (Baddeley) restates
Miller's 7±2 and Cowan's ~4, which Area 38 carries *with the controls that make
the capacity claim causal* and with the dispute held open rather than averaged.
ORDER 854 (Damasio) restates the Iowa Gambling Task dissociation that ORDER 843
was read and **deliberately declined to slot** last pass because the load-bearing
result is contested inside the file — so an entity page about the same person
could have been used to launder a declined slot into an admitted one. **It is
the mechanism by which a declined decision gets reversed by an authority the
declining pass never saw.**

**The rule.** A file in `Entities/` may **be read** and may supply:

1. **new vocabulary or a decomposition** for an area the arena already holds
   (Miyake's shifting/updating/inhibition split of the central executive is the
   example that earned its place in tranche 39 — it is a *decomposition*, not a
   restatement);
2. **a constraint on wording** (ORDER 853's insistence that self-monitoring of
   resource usage is *not* interoception, because it lacks the affective
   dimension — binding on every affect slot in the arena);
3. **corroboration of reach** — logged in the slot as confirmation that the
   subject is discussed, never as an increment to the independent-source count.

It may **not** increment `Support: N independent sources` for any claim, and it
may **not** be used as the second source that would move `UNTESTED` → `LOW` or
`LOW` → `HIGH`. The test: **would the claim survive the deletion of this file
and every other file about the same subject?** If yes, the file is a
restatement and its content is already counted once, elsewhere.

**Why this belongs in the infra file rather than in a slot.** It is a property
of the *corpus's shape*, not of any finding, and the arena's guard-4 rule
already says corpus hygiene is not a brain part. Left unstated, the failure
presents as *progress*: a pass that admits four entity pages as corroborations
reports four increments, and a later pass cannot tell those increments from the
independently-measured ones. The arena's whole method is counting sources
honestly, and this is the class of file most likely to inflate that count while
looking like evidence. **Third consecutive barren tranche in `Entities/`; expect
this to recur until the walk leaves the directory at ORDER 856+.**

### C-049 — a knowledge-graph key that contradicts its own article (tranche 40)

`oracle/brain/Entities/Christof-Koch.md` (ORDER 863) carries a machine-readable
knowledge-graph block listing **`"IIT": "N"`** — a negative flag — on the page
whose entire subject is Koch's defence of Integrated Information Theory as the
mechanism of consciousness. The prose and the flag disagree, and **nothing in
the corpus's validation path checks the direction of the disagreement.**

This is the **inverse** of the §8 inversion. The §8 pattern is a *valid*
artefact decorating *unvalidated* prose: the metadata looks right and the content
does not deserve it. C-049 is a metadata field that says *no* to its own article,
and the failure is different: a reader trusting the flag would discard a claim
the page argues for, and a reader trusting the prose would ignore a field the
corpus emitted about itself. Both are reasonable and they disagree.

**Why the existing checks miss it.** The corpus validates that a knowledge-graph
key *resolves* and that a flag is *well-formed* — an `N` is a perfectly valid
value. What no check does is ask **whether the flag agrees with the article it
is attached to.** That is a semantic check on a semantic relation, and the corpus
has no semantic validation layer at all. Expected to recur: any page with a
`Y`/`N` polarity field in its metadata block.

**The design requirement the defect implies** (§7's exception clause — a
hygiene defect that implies a design requirement goes in the arena queue):
**a knowledge-graph polarity key that contradicts its own page needs an explicit
resolution marker** — `N-disputed` / `N-per-file` — rather than a bare `N`, so
that a negation and a non-assertion are distinguishable. A bare `N` cannot
express *the corpus does not assert this*, *the corpus asserts the opposite*, or
*the corpus flags this as debated*, and those are three different states with
three different consequences for a consumer. Filed to the queue; not minted as
an area, because corpus hygiene is not a brain part (§4 guard 4).

### C-050 — `Entities/` and `entities/` both exist, and ORDER spans both (tranche 40)

Two directories with different capitalisation for the same subject matter exist
side by side under `oracle/brain/`. ORDER 859, 867 and 875 (this pass) are in
the **lowercase** `entities/`; their alphabetical neighbours on both sides are in
the **uppercase** `Entities/`. A case-insensitive reader and a case-sensitive one
disagree about how many files exist, which files have been read, and what the
total is — and on a filesystem that folds case, a merge or a move can silently
collapse one into the other, **changing a path a ledger row has already earned**.

**Mitigated in practice by the arena's own path discipline.** The rule "build the
literal path, never rewrite it" is what prevented this from becoming a data
loss: all three lowercase files were read at their literal paths and marked at
their literal rows. The hazard is recorded because a future pass that *helpfully*
normalises a path — the single most natural mistake to make here — would break a
row silently, and the invariant that would catch it (C6) checks the path against
the ledger, not the ledger against the filesystem.

**Expected to recur until the walk leaves `Entities/`.** Not fixable from the
four write paths.

---

## C-052 · `Entities/` holds two grades of page under identical metadata, and nothing in the frontmatter distinguishes them

**Found in tranche 43** (ORDER 915–934), the first tranche to cross from
encyclopaedia pages in `Entities/` to operational stubs in lowercase
`entities/`. Both directories' files carry **the same OKF v0.2 frontmatter
block, the same `type` field, and in several cases the same
`confidence: high`.**

**The two grades, as measured this pass:**

| | Encyclopaedia page | Operational stub |
|---|---|---|
| Example | `Entities/Karl-Friston.md` | `entities/n8n-mcp.md` |
| Lines | 624 | 49 |
| Structure | 16-section TOC, per-section citations, `confidence`, `sources` | prose, one tool count, no TOC |
| Brain part? | usually yes | never |
| Yield | 20 pages → 3 areas, 5 corroborations | 2 pages → 0 areas, 0 corroborations, 55 lines total |

**The discriminator is line count and section depth, which is a heuristic and
not a rule.** There is no metadata field that says which grade a page is, and
`confidence: high` appears on both — the stub's `confidence: high` is
self-evidently about the MCP endpoint's reliability, and the
encyclopaedia's is about notability (see `VERIFICATION.md` V-43.3, where a
`confidence: 0.95` in a file's closing block turns out to describe the file
rather than its weakest claim).

**Why this is a hygiene class and not a one-off.** The walk crosses a
directory boundary roughly every tranche. A pass that budgets its time by
directory — "`Entities/` yields about one area per seven pages" — will
mis-budget the moment it enters a region of stubs, and will mis-budget
silently, because a stub produces no area and no complaint. The yield figure
this pass established is only valid for the encyclopaedia grade.

**Requirement for future passes, pending a checkable fix:** before treating a
page as encyclopaedic, check the **directory casing** (`Entities/` vs
`entities/`) and the **line count**. A file under 100 lines in the lowercase
directory should be assumed to be a product/service page until read, and a
file in `Entities/` below roughly 200 lines should be assumed to be a stub or
a stub-like index until read. **This is a rule of thumb, not a guarantee, and
it is recorded as a rule of thumb** — the arena's own standard forbids a
heuristic from being cited as if it were measured.

**Not fixable from the four write paths.** The fix belongs to the ingestion
layer that writes the frontmatter, which is a different job; what is
recorded here is the failure mode and the workaround. The lowercase
`entities/` directory has now produced two operational stubs and zero brain
parts across the whole walk.

### C-053 — A duplicate entity page is a contradiction with no canonical
copy, and the arena's citation rule has no way to express it

**Found in tranche 44.** The `Entities/` stratum contains **two pairs of
pages describing the same person**, with **contradictory bibliographies**
(Sutton at ORDER 942/943, Penrose at ORDER 940/945). Both members of each
pair carry `verified: []`, neither is marked canonical, and neither
redirects to the other.

**Why this is a corpus-hygiene class and not a one-off.** The existing
rule — C-052 — covers *one page graded two ways*. This is a different
shape: **two pages, both live, disagreeing, with nothing in the corpus
naming either as canonical.** A reader resolving a wikilink gets whichever
page the link points at, and has no signal that the other exists.

**The rule this forces.** A duplicate entity pair is **one source, not
two**, and a *contradictory* duplicate is **one source of unknown
reliability**. Neither member may be cited as independent support for a
slot, and **an increment that would otherwise come from "two sources" is
void if the two are a duplicate pair.** This is the same counting rule the
skill states for "three files restating one study," extended to the case
where the restatement is not faithful.

**Detection, for a future pass.** Adjacent or near-adjacent ORDER lines
whose paths resolve to the same person by any of: same surname, same
surname with a different first-name prefix (`Richard-` / `Rich-`), or one
path being a two-hyphen compound of the other's subject. A path-based
check alone is insufficient — `Richard-Sutton` and `Rich-Sutton` differ by
two characters — so the detection has to be semantic, and **it is filed
here as a requirement rather than implemented, because implementing it
would be a script reading corpus filenames, which this workspace's own
rules forbid.**

**Not fixable from the four write paths.** The fix is a canonical-id
resolution step in the ingestion layer — the same class of fix as the
`confidence:` field problem already on record. What belongs here is the
failure mode and the counting rule, both of which the arena must honour
while the fix is pending.

### C-054 — A read can be legitimate and its *extraction* still
provisional, and the ledger cannot tell the difference

**Found in tranche 44, and this is the first defect class that points at
the ledger rather than at the corpus.** ORDER 952's `read_file` returned,
the row was marked `[x]` immediately and correctly, and the read→mark
totals are equal. **The provenance problem is downstream of the mark:** the
*specific claims* attributed to that file were retained across a context
boundary as candidate labels rather than as read text, so the citation is
in the arena and the evidence for it is thinner than the mark implies.

**Why the existing rules do not catch this.** The skill's citation rule
is binary: a file whose row is not `[x]` may not be cited, and a file
whose row is `[x]` may be. **That rule is sound and this is not a counterexample
to it** — the row is `[x]`, the read happened, the citation is earned in
the sense the rule means. What is missing is a second, finer distinction:
*the read happened* and *the extraction survived*.

**The rule this forces.** A citation whose supporting detail was not
carried in the same context as the read is marked
**`re-read before load-bearing`**, and any Support increment resting on it
is **provisional** until re-read. Provisional increments are filed in
`VERIFICATION.md` as a first-class result — the strike, when it comes, is
recorded there rather than applied silently. **Filed this pass as
V-44.4.**

**The generalisable form, which is the uncomfortable half.** This defect is
invisible to every checker in the stack, because every checker reads the
*artifact* and the artifact is correct. `verify_reads.py` passes.
`arena_invariants.py` passes. `citation_remediation.py` passes. **The
failure is real, the ledger is accurate, and the claim is still thinner
than it looks** — which is the §8 inversion one level up, and the reason
Area 76's second-order protocol is a design requirement rather than a
nice-to-have.

---

## C-052 · A coverage claim with no date and no method is a coverage claim by
assertion

**Filed tranche 47, from ORDER 1008–1011 (the four `GAP-ANALYSIS-*` files).**

**The defect class.** A corpus self-audit states what the corpus does *not*
contain, without recording the date the audit was taken, the method that
produced the count, or the denominator it counted over. The claims are
therefore unfalsifiable and — as read — false. Concretely, across four audit
files:

- Two files dated the **same day** report **44 entity profiles** and **29
  entity profiles** respectively. One of those numbers is wrong; neither file
  says which, when it was counted, or over what population.
- Coverage claims are stated for the corpus as a whole while the counts that
  would support them are scoped to one directory.
- The topic-level findings (zero-mention claims) are the load-bearing part,
  and they are exactly the part with no stated method — a zero-mention finding
  is only as good as the search that produced it, and the search is not
  recorded.

**Why this is a corpus-hygiene requirement and not a slot.** Per the skill's
guard-4, a file that cannot name a brain function it fills is infrastructure.
None of these four files names one. But per §7's exception, the defect implies
a design requirement, and that requirement is a real one: **a coverage claim
must be re-derivable, not asserted.** The corpus's answer to that requirement
is to make the claim machine-checkable — and it already has the mechanism. A
`grep -rE` over the corpus root returns the count in milliseconds. The four
files did not run it, or ran it, and did not record the result.

**The uncomfortable connection, recorded because it is load-bearing.** This is
**the arena's own `BRAIN PARTS NOT YET COVERED` discipline, failing inside the
corpus it audits.** That section exists to stop a missing area from reading as
an unnecessary brain part. Its stated protection is the word `not observed`
rather than `absent` — a *scoping* discipline, not a counting one. Four audit
files that report absences without a date or a method demonstrate that the
distinction between "we looked and did not find it" and "we did not look" is
one the corpus can write down without honouring it. **A file in this corpus
claiming a coverage fact now needs the same `verified: []` discipline the
arena applies to its own claims** — an audit with no `audited:` date and no
command is `verified: []` regardless of its citation apparatus.

**Not counted as a defect in any area, and no grade moved on it.** Recorded
here and in `VERIFICATION.md` (V-47.1) so a future pass does not re-derive it.

### C-053 — Frontmatter closed early leaves every subsequent key unvalidated, and a content-address field is the worst possible place to carry an unvalidated key

**Instance: `oracle/brain/grpo-note-2026-08-03.md` (ORDER 1023), read whole.**
A valid OKF v0.2 block runs lines 1–15 (`okf_version`, `id`, `description`,
`type`, `status`, `generated`, `verified`, `stale_after`, `tags`, `sources`,
`confidence`) and closes with `---`. **Then lines 23–25 carry three more
YAML-shaped lines in the body:**

```
ource_url: ""
ingested: 2026-08-03
sha256: placeholder
```

Three defects in three lines, and they compound:

1. **Outside the block.** A frontmatter parser stops at the closing `---`. These
   keys are read as body text, so a linter sees a valid document with three
   stray colon-bearing lines and no provenance schema violation to report.
2. **`ource_url`, not `source_url`.** The leading `s` is missing, so even a
   tolerant reader that scans the body for the key finds nothing that binds to
   a schema. **A misspelled key is worse than an absent one** — absent is
   missing data, misspelled is data that will never be read.
3. **`sha256: placeholder`.** A content-address field exists to make a stored
   artefact verifiable. **A literal placeholder in that field is worse than
   leaving it empty**, because empty reads as *not yet computed* and
   `placeholder` reads as *computed, and the value is this*. Nothing downstream
   can tell the two apart, and a deduplicator or cache keyed on it will treat
   every file as sharing one hash.

**The generalisable form, and the check.** *A content-address field must never
carry a non-computed value.* `verified: []` is honest because the array is
empty and reads as empty. `sha256: placeholder` is a **non-empty assertion of
a fact that was not established**, which is the §8 inversion in its purest
one-field form: the field's whole purpose is to certify identity, and it is
certifying a literal.

**Checkable at R-J5 scale, O(1) per file, no execution required:** for every
file in the corpus, any key matching `(sha|hash|checksum|digest)\w*` must hold
either a value of the declared algorithm's shape or be **empty**. A non-empty
value failing its own shape test is a defect. This holds at 14,589 files because
it is per-file and does not require a corpus-wide view.

**Not counted as a defect in any area, and no grade moved on it.** The file is a
28-line test note whose one sentence is a correct definition of GRPO; there was
no arena claim resting on it. Recorded here and in `VERIFICATION.md` (V-48.4).

### C-054 — Two indexes for one directory, sharing one `id`, each authoritative for a different file list

**Instances: `oracle/brain/Hermes-Stack/_index.md` (ORDER 1038) and
`oracle/brain/Hermes-Stack/index.md` (ORDER 1039), both read whole.** Both
declare **`id: hermes-stack-index`** and both claim to index the same
directory. They are not copies and they do not agree:

- `index.md` is **machine-generated** (`generated: by: hermes-agent`,
  `at: 2026-09-08T00:00:00Z`, `confidence: medium`) and carries a `## Contents`
  block listing **eight files**, starting with `GBrain.md`.
- `_index.md` is **hand-written** (`generated: by: "unknown"`, `at: 2026-08-25`,
  `confidence: high`) and carries **prose tables** organised by role — *The
  Agent*, *Memory and Knowledge*, *Web and Inference* — plus a *Reading Order*
  section and seven *Cross-Cutting Lessons*. It never presents itself as a
  file list at all, and it describes **GBrain as a live component** in a
  dedicated table row.

**Why a shared `id` is a defect and not a naming preference.** Every id-keyed
consumer — the link resolver, the graph extractor, `okf_gate.py`, any
frontmatter-indexed lookup — resolves the id to **one** of the two, and which
one depends on traversal order. The loser's entire content is then invisible
while remaining present on disk. Here the loser is not redundant: it is the
**only** file carrying the seven cross-cutting operational lessons, and those
are among the most expensive-won lines in the corpus (a container serving the
wrong config for 42 hours; a 200-for-HTML / 403-for-JSON service that passed
healthchecks for weeks; a retry loop that turned latency into outage at 80
sockets).

**The generalisable form.** *A directory may have one index. If a second file
claims the same role, it must carry a distinct `id` and a distinct title, or
the directory has two claims on the same address.* The existing frontmatter-`id`
collision class (an index colliding with its own content file) is the same
defect one level in; this instance is **within one directory**, which is why
`ORDER.txt`-level dedup and filename-level checks both miss it — the two files
have different names and different titles, and only the `id` field ties them.

**Compounded, and recorded at `VERIFICATION.md` V-48.3:** both indexes describe
as current a component (`GBrain`) that the operating rules record as removed.
So the collision is not merely a lost-content risk here — **whichever index
loses the id lookup, the arena silently loses part of its picture of its own
stack, and the picture is already stale about a component that no longer
exists.** No area cites either file as a brain part and no grade moved; recorded
because the next pass will read one of them and believe it is the index.

**Not counted as a defect in any area, and no grade moved on it.** `Hermes-Stack`
is substrate and operating reference, not a brain part, and no arena claim
depends on either file's completeness. Recorded here and in
`VERIFICATION.md` (V-48.3).

### C-055 — A removed component keeps its citations (class: stale live-fact)

**Recorded 2026-09-27, tranche 49.** A component removed from the stack does
not retract the files that describe it as live, and **a reader arriving fresh
has no signal the referent is gone.** Observed on **GBrain** — removed, with no
process, container, or shim, and must not be routed to — which is still cited as
**current architecture** by four files read this pass (V-49.4), one of them
resting a *design argument* on it, and two more listing `gbrain` entity
profiles as live sources.

**Why this is a class and not an instance.** The second occurrence in the
corpus of a claim resting on absent infrastructure, and the failure is
structural: removing a subsystem does not touch prose. **Every hygiene checker
in this stack validates that a citation resolves to a file — none validates
that the file's referent still exists.** A resolution check would pass all
four.

**Requirement.** A component page carries a lifecycle field
(`active` / `deprecated` / `removed`) and a checker resolves every
"X uses/implements Y" assertion in prose against it. **At 14,589-file scale
this cannot be a per-claim review** — it is a term-level scan for component
names, with the names themselves as the checkable artifact, which is the same
shape as C-050's case-variant directories. Not yet implemented.

### C-056 — Two corpus files, one `id`, case-variant directories

**Recorded 2026-09-27, tranche 49.** ORDER 1110
(`knowledge-representation/symbol-grounding.md`, 250 lines) and ORDER 1111
(`Knowledge-Representation/Symbol-Grounding.md`, 310 lines) both declare
`id: "symbol-grounding"`, open with the same paragraph, and cite the same
Harnad 1990 / Searle 1980 / Cangelosi & Harnad 2001 sources. ORDER 1111 is a
superset (18 annotated sources, a `Related` block pointing at four
GAP-ANALYSIS files), so it carries the load and the pair is counted as **one
source** in Area 85.

**Related:** the same directory exists twice, differing only in case. **This is
the third case-variant directory split** after ORDER 1101/1102's two
`knowledge-representation/index.md` files with **disjoint contents** and
different ids.

### C-057 — Case-variant directories are now a class, not a third instance

**Recorded 2026-09-27, tranche 49.** Three independent case-variant directory
splits have now been read (C-050, C-056, and the ORDER 1101/1102 index pair).
The consequence is the same in all three and it is a **silent** one: **on a
case-insensitive index, or on any consumer that resolves by directory name, each
pair collapses to a single node and one of the two files becomes invisible to
retrieval while remaining fully readable on disk.** The ledger keeps them
separate because it is keyed on ORDER line; a graph or index keyed on path will
not.

**Requirement at 14,589-file scale.** A one-time path-normalisation check that
folds case-variant directories into one canonical key and reports the shadowed
files for adjudication. **A human reading every file will not catch this** — it
is exactly the class of rule the R-J5 scale test excludes, because correctness
depends on a property of the *path* rather than of the *content*.

**Not counted as a defect in any area, and no grade moved on it.** These are
index and identity problems. They are corpus hygiene, and guard 4 sends them
here rather than to a slot.

### C-058 — The corpus root in the skill is wrong, and it composed with the error rule into 20 false ledger marks

**Recorded 2026-09-27, tranche 53.** **This is NOT a new defect.** It is the
**fourth recorded occurrence**: `VERIFICATION.md` `V-38.1` (second), `V-45.1`
(third), and `ARENA.md` status blocks for tranches 39/44/45 all record it, and
tranches 44 and 45 explicitly noted that they avoided it by building paths from
`~/.hermes/`. **The defect is old. What is new is that this pass converted it
into 20 false ledger marks**, which none of the three prior passes did. Read
this entry as a consequence record, not a discovery.

**The defect itself.** The `wiki-cognition` skill's §2 workspace table states
the corpus root is `/home/operator/.autognosia/`, and §2's "How to read" says a
corpus read is that prefix plus the `ORDER.txt` line. That directory does not
exist. The corpus is at `/home/operator/.hermes/`, which is what the cron job
prompt says and what every prior tranche used in practice.

**Why it kept recurring.** Each pass begins with a fresh context window. The
skill is the authoritative-looking document in front of it, the prompt is a
paragraph below it, and nothing in either reconciles them. The workspace
already knew the answer in three places and no pass read those places *before*
issuing the first `read_file`. **The knowledge was in the repository the whole
time; only the reading order was wrong.**

**What it cost this time.** Tranche 53 issued 20 `read_file` calls against
`~/.autognosia/` + path. All 20 returned `File not found`. Following the skill's
own instruction — "if that exact path fails, mark the line `[!]` with the error
and move on" — the pass marked **20 rows `[!]` blocked**, a false claim that 20
corpus files are unreadable. The files exist and are 27–33 KB each. The marks
were detected only because the pass `ls`'d the parent directory after the third
consecutive miss, and **all 20 were reverted** before the run ended. The ledger
census after the revert is `1067 [x] / 421 [-] / 1 [!] / 728 [ ]`, identical to
arrival.

**The failure mode, stated precisely.** The skill's path rule and the skill's
error-handling rule *compose into a mark-falsification factory*. A wrong prefix
produces a miss; the miss-handling rule converts a miss into a permanent ledger
claim; and `[!]` reads as "this file was examined and could not be read," which
is exactly what a reader would believe. Nothing in the loop distinguishes "the
file is not there" from "I looked in the wrong place." A pass that had not
spot-checked the root would have left 20 permanent false blocks in a ledger whose
entire value is that it can be trusted — and the 728-row countdown would have
been quietly wrong by 20. Prior passes each burned one failed call; this one
would have burned the ledger.

**Three requirements, all at 14,589-file scale. None is catchable by a human
reading every file, which is why they are infra rather than a habit:**

1. **The path prefix must be resolved from the filesystem, never copied from
   prose — and resolved before the first read, not after the third miss.** The
   pass asserts the root exists; on a miss it aborts rather than marking `[!]`.
   The abort must be *loud* and must not write to the ledger.
2. **A `[!]` mark must be earned by a positive existence check, not inferred
   from a read error.** `read_file` returning `File not found` is evidence about
   *one path attempt*, not about the file. A `[!]` requires the parent directory
   to have been confirmed present.
3. **An all-miss tranche is a control-plane failure and must not be recorded as
   corpus state.** N consecutive `File not found` on paths sharing a directory
   prefix means the prefix is wrong, not that N files vanished. Stop at the
   second and verify the root.

**No area moved and no grade moved on this.** It is not a brain part and it is
not evidence about the subject matter — it is a broken instrument. Per guard 4
it is corpus hygiene and it belongs here.

**Not fixed here.** `wiki-cognition/SKILL.md` is not one of this job's four
writable paths, and a skill is exactly the artifact a pass must not edit while
running under it. **The user owns this fix**, and it is now four passes old.
Until it is made, every pass should build corpus paths from `~/.hermes/`, which
the cron prompt states correctly.

---

## C-057 — The H1 title line is clipped mid-word above an intact copy

**Found:** tranche 59, ORDER 1282–1301. Four instances in twenty files.

**The defect.** A generated research report carries a duplicated title line
immediately above its `#` H1, and that duplicate is **truncated partway through a
word** while the H1 below it is intact. Observed:

| ORDER | Line | Clipped duplicate begins | Intact H1 at |
|---|---|---|---|
| 1289 | 41 | `rgic Signaling of Expected Uncertainty and Precision"` | 43 |
| 1292 | 49 | `us-Norepinephrine System: Network Reset and Unexpected Uncertainty"` | 51 |
| 1298 | 34 | `c Spikes and Plateau Potentials in Cortical Computation` | 36 |
| 1300 | 32 | `e: Hebbian Learning and Synaptic Weight Update Rules` | 35 |

The clip point is not random: in 1289 and 1292 it falls inside the *second* word
after dropping the leading `# `, and in 1298 and 1300 it leaves only a trailing
single character. Consistent with a **fixed-width header line being re-emitted
after its leading characters have already been consumed** — the same
frontmatter-adjacent region that produces the `e: concept` fragment in the
20-line stub at ORDER 1299 line 16.

**Why it is a defect class and not four typos.** It is systematic (four of four
generated reports examined for it), it is **invisible to a reader who does not
look**, and it is **actively misleading to a reader who does** — because a
mid-word fragment reads as *file corruption*, which invites discarding a file
whose content is complete and correct.

**Why it belongs here and not in a slot.** §7's test: would a good architect
change the design because of this? No. The prose is intact, the citations are
intact, the claims are intact. It is a broken artifact around sound content.

**And why it is nonetheless the most important hygiene finding recorded so far.**
§8's finding is that *the validated code path produces the appearance of
authority, and the unvalidated path produces the content.* Every prior instance
had the artifact looking **sound** while the prose was unchecked — the artifact
endorsed unchecked content. This class is the **same inversion with the signs
reversed**: the artifact is **reliably damaged** while the prose is sound, so a
validator that checks the artifact sees a defect and a reader who checks neither
sees a clean document. The pattern is therefore confirmed to be a property of
**the validation path itself**, not of either component — which strengthens §8
rather than qualifying it. A system that trusted artifacts to the point of
rejecting files on artifact damage would discard the soundest content in the
corpus.

**Handling.** Do not treat a clipped title line as evidence that the file is
truncated, empty, or unread. Confirm by locating the `#` H1 a few lines below
before drawing any conclusion about the file's extent. `Neuroimaging-Methods-Complete.md`
(ORDER 1286), by contrast, **is** genuinely truncated — it ends mid-sentence at
line 217 with no closing content — and the two conditions must not be confused.

### C-058 — a directory index advertises a file no ORDER line resolves to

**Class.** A directory `index.md` links or names a corpus document that the
ordered walk cannot reach: the name appears in the index and nowhere in
`ORDER.txt`, so no ledger row exists and no pass can ever read it.

**Instance.** `Neuroplasticity/index.md` (ORDER 1302) lists
`Dendritic-Spike-Plateau-Potential-Computation.md`, which is not in the ordered
set.

**Why this is worse than a broken link.** §7's test — *would a good architect
change the design because of this?* — passes for a different reason than usual.
A broken link loses the *reader*. This loses the *walk*: the index advertises
material the distillation process structurally cannot reach, so the corpus's own
table of contents overstates its coverage. A reader who trusts the index believes
the walk has covered a document it has not, and no invariant in this workspace
detects it, because the missing thing is a file rather than a citation.

**Handling.** Do **not** go looking for the file — path discipline forbids
inferring a path, and the index's spelling of a name is not an ORDER line. Log
the discrepancy in `VERIFICATION.md` and move on. When an index is read, its
link list is data about the *index*, not a manifest to be followed.

### C-059 — a body truncated mid-sentence inside an otherwise complete document

**Class.** A file's prose ends mid-word, mid-clause, with no closing content,
while the file's structure (frontmatter, index, citations) is otherwise intact.
Distinct from **C-057** (clipped *title* line) in kind, not just degree.

**Instance.** `Corollary-Discharge-Efference-Copy-Agency.md` (ORDER 1310) line
140 ends `...normal passive-conditio`. This is the largest file of tranche 60 at
48,675 chars and the truncation is at the tail, not the head.

**Handling.** A tail truncation does not invalidate a read of the body that
preceded it, and it does not license marking the file `!` — the file was read and
it earned its slot. But it **must** be logged, because the missing tail is
exactly the region a later pass would want for a detail it cannot now find. Note
the contrast the corpus supplies: `Neuroimaging-Methods-Complete.md` (ORDER
1286) ends mid-sentence at line 217 **and has no intact structure around the
cut**, which is a different condition and a different handling. Confirm which of
the two you have before deciding.

## C-034 — A threshold branch that is provably unreachable

**Class:** arithmetic inconsistency between a stated score's range and a threshold
applied to it. **A C-025 instance with a strictly stronger shape** — C-025 records
a branch mapped onto the wrong *end* of a quantity's range; this is a branch that
**can never fire at all**.

**Instance (tranche 67, ORDER 1607, `absence-of-evidence-monitoring-sparse-corrections.md`,
§"Recommended Thresholds").** The file defines
`drift_risk = α·(1−RRD) + β·(1−TSMD) + γ·IGS + δ·AES + ε·(4-signal score)` and states
**"Where α+β+γ+δ+ε = 1 and each component is normalized to [0,1]."** Every term is
therefore in [0,1] and the sum is in [0,1]. The threshold table then reads:

| Level | Threshold | Action |
|---|---|---|
| Watch | drift_risk > 0.3 | Log for monitoring |
| **Warning** | **drift_risk > 4** | Increase consolidation scrutiny |
| Supersedure | drift_risk > 0.7 | Trigger re-annotation |

Watch (0.3) and Supersedure (0.7) are in range. **Warning at > 4 is not reachable
by any assignment of the weights**, including degenerate ones (all mass on one
component still yields ≤ 1). The Warning row is dead code, and the ordering
Watch < Warning < Supersedure is false.

**Why this is a hard version rather than a soft one.** A mis-scaled threshold is a
tuning error: the branch fires, at the wrong time, and the damage is
over-triggering or under-triggering. A **provably dead** branch is worse in one
specific way — it is **invisible to every test that only exercises reachable
states**, so a system can pass a full validation sweep with the Warning path
never once executed. The report of a run that "works" is therefore not evidence
that Warning works.

**Detection rule for the checker (deterministic, no execution of the model
required).** When a file states both (a) a weighted sum of components with weights
summing to 1 and each component normalised to [0,1], and (b) a threshold constant
outside [0,1] applied to that sum, the threshold is dead. This is decidable by
reading the two declarations and comparing ranges — it needs no run.

**Second, related instance in the same file, for the rule's boundary.** The
`Deprecation` row is not a threshold on `drift_risk` at all — it reads *"sustained
MW < 0.40 for >30 days"* — so the table silently mixes **two different quantities
in one column**. A reader scanning the "Threshold" column sees three rows and
reasonably infers one quantity. **Range-checking the column catches the dead row
and would raise a false positive on the third**, so the rule must be applied per
row against the quantity that row actually names.

## C-035 — Frontmatter that is not frontmatter, and a standard that is not enforced by anything

**Class:** schema non-conformance, with the specific and previously-unrecorded
sub-case that the frontmatter block is **syntactically inert** — the keys are
present and human-readable but cannot be parsed, so every tool that reads
frontmatter sees an empty document.

**Instance (tranche 67, ORDER 1611, `adaptive-fusion-with-suppression.md`, lines
3–12).** The block is written as

```
**okf_version:** 0.1
**id:** adaptive-fusion-with-suppression
**status:** draft
**verified:** false
```

`**: key**` is Markdown bold, not YAML. A YAML frontmatter parser reads this as
either nothing or a malformed scalar; the keys are **unreachable to `yaml.safe_load`
and to every downstream consumer** that relies on them. Note that this file also
uses `**verified:** false` where the OKF schema requires a `verified:` **list**.

**The part that makes this class worth recording rather than the instance.** In the
**same 20-file window**, ORDER 1602
(`reference/wiki-frontmatter-standards.md`) was read and *specifies* the standard
these keys violate:

- `okf_version: "0.2"` is **mandatory** — ORDER 1611 declares `0.1`, two majors behind;
- `verified: []` is **required and must be a list** — ORDER 1611 declares `false`;
- the type enum **must be lowercase**, with `Index` → `index` mapping — ORDER 1611
  declares `type: research`, which is not in the enum at all.

**The standard and its violation arrived in the same pass.** That is the finding:
the corpus contains a *written* standard, a file that *states* the standard is
mandatory, and a violating file, with nothing connecting them. **A documented
convention that is not checked by a checker is a convention, not a schema** — and
this is the same shape as the arena's own §8 inversion and as the SOUL rule about
*a check that can pass via fallback is not verifying*: **a standard no tool reads
provides no guarantee, only an intention.**

**Note the asymmetry with a merely *stale* frontmatter.** A file declaring
`okf_version: "0.1"` with valid YAML is a **version-lag** problem and is handled by
migration. A file whose frontmatter **cannot be parsed at all** is invisible to the
migration — the tool that would fix it never sees the field. So the inert form is
strictly worse than the stale form, and a checker that treats "old version" and
"unparseable" as the same severity will under-prioritise.


---

## C-036 — a "priority" produced by a keyword sweep over a backlog is not a ranking, and it is formatted exactly like one

*Found tranche 68, ORDER 1622 and ORDER 1623 (`agenda-update-2026-09-21-round9.md`,
`agenda-update-2026-09-22.md`). Instance of the class **"assertion formatting as
authority", a sibling of C-035's inert frontmatter. Not the same defect: C-035 is
a field that cannot be parsed; this is a field that parses perfectly and carries
no evidence.*

The `agenda-update-*` sweep ends each file with an **Implementation Priority**
table whose rows are `Immediate / Short-term / Medium-term`. In ORDER 1622 three
items are **"Immediate"**; in ORDER 1623 three are **"Immediate"**. The mechanism
behind them is a **Relevance Gate**: keywords absent from a 5,760-line agenda are
*zero-coverage gaps*, and the table is those gaps sorted by how confidently the
sweep asserted them. The external numbers behind the immediate items
(arXiv:2607.22962, 2608.03372, 2609.22043, 2606.25161, 2511.03506, 2608.01679,
2605.12978) are **not quoted with results in these files and were not reproduced
by any of them**.

**The defect class, stated generally: a table that assigns an urgency to a claim,
in a document whose other sections are machine-generated boilerplate, inherits
the boilerplate's authority without the boilerplate's auditability.** A reader
skimming for the decision finds a confident three-column table. There is no
column a reader can check.

**Why it is a corpus-hygiene requirement and not an arena slot** (§4 guard 4):
naming the brain function it fills is impossible, and it is the arena's sharpest
counterexample to "a link resolver and a hippocampus index both look like
components in a list" — a priority table looks *more* like a component than a
link resolver does, and it is less.

**Required of any sweeper that writes one: an `evidence` column, populated with
a trial result, a named adopter, or the literal string `none`.** A row that
cannot fill that column must read `deferred — no evidence`, never `Immediate`.
The empty column is the whole point; a populated-looking table is the failure.

---

## C-037 — a confidence field certifies the artefact, and the recommendation in the same file is not in the artefact

*Found tranche 68, ORDER 1637 (`bm25-normalization-failure-analysis.md`). The
sharpest instance yet of §8's inversion, because here the inversion appears
*inside a single well-reasoned file* rather than across a corpus.*

The file carries `status: verified`, `confidence: 0.95`, a correctly stated
theorem, and a five-variant experiment that **confirms** the theorem (all five
normalisations return identical Acc=0.320). Then its §"Practical Implications"
recommends *"Stage-1 retrieval: Migrate to dense (bge-small) + RRF"* — an action
the file has not run, and its own §5 records that the hybrid leg costs **3.7×
latency for +0.030 accuracy**. The proof is sound, the experiment is sound, the
migration is `UNTESTED`.

**This is C-035's cousin and it is worse than an inert field, because an inert
field is at least inert.** `confidence: 0.95` here is *earned* — the file earns
it on the theorem — and it then sits 400 lines above a recommendation that
nothing in the file supports. A reader who trusts the field extends that trust to
the action. The validated path produced the authority; the unvalidated path
produced the content. §8 states this as a corpus-wide finding; **C-037 is the
first case where the two paths are adjacent inside one file and the field is
correct**, which makes it the cleanest demonstration available: correct metadata
does not license the prose beneath it.

**Required:** any recommendation that would change a design must carry its own
evidence marker, and a `confidence` value must not be inherited across a section
boundary. Concretely — the recommendation needs `UNTESTED` printed on it, the way
the arena's own slots do, and at 14,589-file scale a reader has no way to learn
that `0.95` stopped at line 400.

### C-038 — A metric can be high while the quantity it decomposes is zero

**Observed 2026-09-27, tranche 69, ORDER 1654.** HiLRP (arXiv 2609.01282), as
reported in that file, shows relevance conservation ratios of **0.00, 0.00,
0.00, 0.16, 0.35, 0.38, 0.77** across five hierarchical ViT backbones — in four
of them relevance is *reduced to exactly zero at depth* and in one it is
*inflated threefold* — while **localization still scores 0.80–0.98 Pointing**.
The same file reports hand-derived GDN-LRP introducing 2–5% conservation error
per layer, compounding to **40–70% across 36 layers**.

This is §8 with a number attached, and it is the sharpest form yet. §8 says
correct metadata sits over unverified prose. C-038 says something stronger and
worse: **the measurement that would detect the failure is itself uncorrelated
with the failure.** A relevance map that sums to zero at the input can still
point at the right tokens, because localization only asks *which* tokens rank
highest and conservation asks *whether the ranking accounts for the output*.
Ranking survives the loss of magnitude; decomposition does not.

**Why this is a corpus-hygiene requirement, not an area.** §4 guard 4: a metric
is not a brain part. The design requirement it implies *is* load-bearing —
**every aggregate the arena proposes must declare whether it is a ranking or a
decomposition, and a checker that validates the ranking does not validate the
decomposition.** A coverage score, a cognitive-weight sum, a consolidation
recall figure: each is either an ordering or a partition of a stated total, and
the two fail differently. The arena has been quoting these numbers without
saying which kind they are.

**Required:** the arena's own evidence-grade discipline extends to metric
*kind*. Where a number is a ranking, a second check of the sum is required
before the number is used to constrain a design — and that check must not be the
ranking metric itself. Bounded by R-J2: this is a requirement on what may be
cited, not a new measurement to run.

### I-19 — Never append free text to a `LEDGER.md` row

**Discovered 2026-09-27 (tranche 74), by a checker, not by a read.**

`scripts/verify_reads.py` parses each ledger row with `LEDGER_RE` and takes
capture group 2 as the **path**, stripped of a leading number and nothing else
(`verify_reads.py:79`). Any annotation after the filename is therefore swallowed
into the path string. Tranche 73 marked 21 rows with
`-- READ 2026-09-27 at relocated root …, NNN lines, not truncated`, and the
verifier reported all 21 as **both "not in ORDER.txt" and "does not exist on
disk"** — on files that are plainly present and plainly read.

**Why this is a defect class and not a one-off typo.** The failure is
*silent and total*: the row still reads as read to a human, the mark is still
`[x]`, `grep` still finds it, and the only signal is a checker reporting 21
files missing that are not. A future pass auditing trust in the ledger would see
"the ledger is claiming reads that the log does not support" and would be
entitled to **reset those marks and re-read** — which is the correct
conservative response to a bad row and pure waste when the read was real. Worse,
the read detail is redundant by construction: it already lives in
`ARENA-EVIDENCE.md`, which is where the skill says reasoning and measurement
belong.

**Required:** a `LEDGER.md` row carries the mark, the ORDER number, and the
path — **exactly three fields, nothing else.** Per-file read detail (line count,
truncation status, relocated-root note) goes in the tranche narrative in
`ARENA-EVIDENCE.md` and, where it changes an answer, in the slot in `ARENA.md`.
The census table at the head of the ledger is prose-labelled and *is* matched by
`arena_invariants.py` C4, so that is the place for a per-pass count — which is
how tranches 66–74 have recorded theirs.

**Remediation applied this pass:** the 21 annotations were stripped to bare
paths after a `diff` of the annotation-stripped backup against the live file
proved **every mark and every row identical**, so no read was lost. The read
detail is preserved in `ARENA-EVIDENCE.md` tranche 74. `verify_reads.py` now
reports zero path errors. Recorded here because **the next pass will want to
annotate its rows too**, and the pull to write "read whole, untruncated" next to
the mark is strong and has now cost one verifier run.

---

## C-057 · The corpus republishes one document at several ORDER rows, and `[ ]` overstates the remaining work by ~2.2×

**Defect class:** duplicate publication across `ORDER.txt` rows. Distinct from
the twin-basename hazard already recorded (C-056 and the remediation pass): that
one is about *citing* an ambiguous name, this one is about *budgeting* a pass.

**Evidence (tranche 80, ORDER 1847–1867).** All twenty files in the window were
verified byte-identical by `cmp` to documents already read at ORDER 269–289 —
`active-wiki/research/X.md` and `oracle/brain/research/X.md` are the same bytes.
Four (ORDER 1852, 1858, 1859, 1861) are triple-published, with a third copy at
`oracle/brain/X.md` (ORDER 1004–1007) that is a *near*-duplicate revision
(20,048 vs 20,343 bytes for ORDER 1859/1858's sibling) rather than a clean match.

**Measured scale.** Of the **208** unread rows at the start of tranche 80, **143
(69%)** are duplicates of already-read documents. **65** carry a basename with no
read twin. The real remaining corpus is roughly **31%** of what the cursor count
says.

**Why this is a defect and not an observation.** A pass sizes itself from the
`[ ]` count, budgets 20 files, and expects the frontier to move. On a 143/208
duplicate run the frontier does not move, and the pass reports honestly — but it
has spent 20 whole reads, 20 marks, and a full 13-minute slot to learn that the
ordinal structure of the corpus does not correspond to its informational
structure. The cursor is a position in a list, not a measure of unread knowledge.
This is the same shape as the benchmark-saturation finding: **the number that
looks like the workload is not the workload.**

**Requirement for future passes.** Before spending a full tranche on a window,
check how many of its rows are duplicate publications. One `grep` of the window's
basenames against the `[x]` rows costs a second and can redirect a 20-file slot at
the 65 genuinely-unread rows instead. **The check is bookkeeping, not reading** —
it reads no corpus content and is permitted under §2, which restricts `terminal`
to ledger arithmetic and drift checks.

**What is NOT proposed.** No row is un-marked and no file is deleted or excluded.
The user decides on the corpus's duplicate publication; this entry only records
that the duplication exists, is measured, and will mislead a pass that trusts the
count. The 65 twin-free rows are contiguous enough (from ORDER 1918, with
interleaved duplicates) to be worked in order without abandoning the cursor.

## C-057 · Addendum (tranche 82) — the duplicate block has a hard end, and it has been reached

Tranche 80 measured 143 of 208 unread rows as duplicate publications and predicted
that the twin-free rows begin at **ORDER 1918**, contiguous enough to be worked in
order. **Tranche 82 read ORDER 1889–1917 and the prediction was exact: the pass ended
one line before the predicted frontier.** Eighteen of its twenty files are
byte-identical (`cmp`) republications of ORDERS 311–338, across four whole lanes
(hybrid-attention attribution, FEDD/Lipschitz drift, preference-annotation routing,
IANA/Packed CBOR) plus the Neo4j GraphRAG MCP survey. Only the two navigation
indexes carried twin-free content.

**What this adds to C-057, and it is a stronger claim than tranche 80's.** The
defect is not a scattering of coincidental double-publication. It is a
**contiguous, bounded block that terminates**, which means the corpus's ordinal
structure and its informational structure diverge over a *known interval* rather
than indefinitely, and the interval is now closed. A future pass can therefore
budget against the real frontier — the ~65 twin-free rows from ORDER 1918 — instead
of the cursor's `[ ]` count, which overstates remaining knowledge by roughly 2.6×.

**Concretely for the remaining passes:** the ledger's `Remaining to read ([ ])`
figure is a count of *rows*, and rows are not knowledge. The final report's
"remaining" number should carry the twin-free figure alongside it, because a
statement like "170 files remain" is true about the ledger and false about the
work, and this job's whole value is that the ledger can be trusted.

**Still not proposed.** No row is un-marked, no file is deleted, no row is excluded.
The user decides on the corpus's duplication.

---

## C-058 · A populated index stub passes every structural check while containing no knowledge — tranche 91

**Class:** false authority from a valid artifact. **Instance count:** 5 files,
all in the final tranche, all at the alphabetical tail of `oracle/brain/`.

`Tool-Use-and-Extended-Mind/index.md` (36 lines), `Training-Dynamics/index.md`
(25), `Visual-Autognosia-Hierarchy/index.md` (37),
`Working-Memory-and-Executive-Function/index.md` (37), `World-Models/index.md`
(33). Every one carries a complete `okf_version: "0.2"` frontmatter block, a
`## Contents` → `### Files` → `### Subdomains` section, a `## Tags` section and
a `## Status` block. **Every one passes schema lint. None of them names a brain
function, a mechanism, or a claim.**

**Why this is a new class and not C-046.** C-046 (tranche 38) was six 27-line
files whose `## Contents` section read `*No files in this directory.*` — **the
stub declared its own emptiness in prose, and a reader who opened the body
learned it was empty.** These five do not. They are *populated* indexes: they
list real sibling files, they carry generated timestamps, they have
`stale_after` dates, and **three of the five have `tags:` values that are a
directory name mechanically split on hyphens** (`tool, use, and, extended,
mind`) — the signature of a generator, not an author. **A consumer asking
"does this domain have content?" gets the wrong answer from all five**, and a
consumer asking "is this file well-formed?" gets the right answer from all five.

**The self-referential link, which makes it checkable.** ORDER 2210's line 37
is `- [[Visual-Autognosia-Hierarchy]] — Visual Autognosia Hierarchy`, appearing
*after* the file's `status: active` line and its own content have ended. **The
link's target is the file itself.** A wiki-link checker that resolves it will
find ORDER 2210, find it already visited, and record a pass — **a self-link is
the cheapest possible positive for a link checker and it carries zero
information.**

**The requirement this implies** (§7's exception clause — a hygiene defect that
implies a design requirement puts the requirement in the arena and the instance
in the queue). For any index or generated page:

1. **`description` must not restate the type.** `description: "Index"` over a
   body that is an index asserts nothing; `description: "Index — stub, 1 file"`
   asserts something checkable. **This is the same defect as `confidence: high`
   over `*Nothing archived yet.*` (V-90.1) with the field name changed.**
2. **A `tags:` value produced by splitting a directory name on hyphens is a
   generator artefact and must not be counted as a curation signal.** A tag that
   appears in every file of a directory distinguishes nothing between them.
3. **A self-referential wikilink must be a checker failure, not a pass.** The
   existing link checkers resolve and report "reachable"; none asks whether the
   target is the source. **A self-link is a reachable link that carries no
   information, and reachability is not the property being checked.**
4. **A domain index whose file list has one entry and whose single file is the
   domain's only content should be typed as a heading, not as an `Index`.** Four
   of the five stubs here describe a domain with exactly one substantive page.

**Not applied to the corpus.** Writing to corpus files is outside this job's four
write paths. The requirement is recorded here; the five instances stay in the
corpus and are filed at `VERIFICATION.md` V-91.1.

**Why this class matters more than its five instances suggest.** The arena has
now recorded, across 91 tranches, that **the validated code path produces the
appearance of authority and the unvalidated path produces the content** (§8).
C-058 is that finding at its most economical: **a 25-line file with valid
frontmatter, a generated timestamp, a contents section and a status block is
indistinguishable from a real page to every automated check in this
workspace — and contains no claims at all.** The corpus's own repair rate for
this is what it is; the check that would catch it is a *body-length floor for
`type: Index`*, which is a one-line change to a linter and is **not proposed
here** because it is a change to the corpus tooling, not to the corpus.

---

## C-059 · Two corpus files give one 1984 paper two venues and two titles — tranche 91

**Class:** cross-file bibliographic conflict. **Instance count:** 1 paper, 2
files, 2 incompatible bibliographic identities.

`Predictive-Timing-Internal-Clocks-Interval-Timing.md` (ORDER 2203) footnote
`[^5]` gives **Gibbon, J., & Church, R. M. (1984). *Sources of variance in an
information processing model of animal timing. JEP: Animal Behavior Processes*,
10(4), 433–455.** `Temporal-Cognition-and-Time-Perception.md` (ORDER 2204) gives
the same authors and year as **"Scalar expectancy theory and Weber's law in
animal timing. *Psychological Review*, 91(2), 130–152."**

**Why the arena needs this as a class rather than an instance.** Every checker in
this workspace validates a *file's* citations: the format is well-formed, the
volume is a number, the pages are a range. **No checker compares a citation
across files, and a per-file validator is structurally incapable of detecting
this** — each file is internally consistent and they are mutually contradictory.
**A source count that de-duplicates by author-year-string would treat these as
two independent sources**, which is precisely the overcounting error the
independent-source rule exists to prevent, arriving through the citation
path rather than the republication path.

**The related instance in the same file, filed as the same class.** ORDER 2203's
footnotes `[^3]` and `[^7]` are **the same reference** (Gibbon 1977, *Psychological
Review* 84(3):279–325) attached to two different claims. That is legal citation
practice and is not a defect; it is recorded because **a pass counting footnotes
rather than papers double-counts**, and this corpus publishes 46 footnotes
across the three temporal files.

**The requirement this implies.** Any independent-source count in this arena that
involves a corpus citation must de-duplicate on **(author-set, year, title)**
across files, not on the string as printed in one file. **The arena already
knows this is needed** — `VERIFICATION.md` I-10.1 has carried "re-derive every
`Support: N` by arXiv ID" as an open action since tranche 10 and it is **still
not done**, and this class is a second, independent demonstration that the
de-duplication key is wrong: **arXiv ID would not have caught either instance
here, because neither is an arXiv paper.** The correct key is
**(DOI ∨ arXiv ID ∨ normalized author-year-title)**, and the third disjunct is
the one no current tooling implements.

**Not applied.** The arena's `Support: N` values are unchanged by this pass, and
lowering counts across 150 areas on the strength of one discovered conflict
would be a larger claim than one pass has verified. **The class is filed so the
next pass that touches a support count knows the key is three-way or it is
wrong.**
