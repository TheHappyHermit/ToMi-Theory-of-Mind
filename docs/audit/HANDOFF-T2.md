# T2 CITATION REPAIR — HANDOFF TO A NEW CHAT

Written at the end of session `20260927_124725_6f428999`. Every fact below was
re-verified against the live filesystem immediately before writing this file,
not recalled from context.

---

## 0. READ THIS FIRST — THE TASK

**Original user request (paraphrased, long since partly fulfilled):**

> Go one by one and get the proper citation for each of the items that have a
> barrier URL with no title so that you can have everything passed properly.
> This is a matter of you doing manual work versus bulk script work in order to
> get the wiki up to our standards rather than skipping out on confidence
> because you don't want to go back and manually do the work that needs to be
> done. Search for the URLs that are the sources of the information and cite
> them appropriately. It's manual and you have to do it file by file... You
> can't be lazy here.

**Where that stands:** the manual, file-by-file work on untitled citations is
essentially done (461 → 1). The remaining 20 rows are a *different* class of
problem — mostly citations to papers that do not exist — and the user has since
authorised a specific remedy (see §6).

**The user's standing rules, from this session:**

- "It's manual and you have to do it file by file" — automation may enumerate,
  query, and apply an *already-reviewed* transformation; it may not make the
  per-file decision about what a source is.
- "If we've got 461 with untitled citations then you've got 461 that you've
  messed up before and you now have to manually go back and fix."
- Don't lower a threshold, count bare URLs as passes, preserve stale verifier
  rows, or write confidence while any T2 source is untitled/mismatched/unresolved.
- Never modify `/home/operator/.hermes/hermes-agent` (Hermes core).

---

## 1. REPO AND STATE (verified)

```
Working dir : /home/operator/hermes-brain
Branch      : main
Local HEAD  : 2440493
Remote HEAD : 2440493  (origin/main)
Ahead/behind: 0 / 0     — fully synced
Remote      : https://github.com/TheHappyHermit/ToMi-Theory-of-Mind.git (PRIVATE)
```

**Uncommitted — LEAVE THESE ALONE, they are the user's WIP:**

```
 M SCRATCHPAD.md                    ← user WIP, do not touch
 M docs/audit/grade-decisions.csv   ← user WIP, do not touch
 M scripts/fill_oracle_gaps.py      ← user WIP, do not touch
?? schemas/okf-queue.jsonl          ← user WIP, do not touch
```

**Tests: 733 passing, OK (skipped=2).** Run them with:
```sh
cd /home/operator/hermes-brain && python3 -m unittest discover -s tests
```

### Current T2 evidence table — `docs/audit/t2-verification.json`

| verdict | count |
|---|---|
| `match` | **938** |
| `mismatch` | **0** |
| `unresolvable` | **19** |
| `untitled_citation` | **1** |
| **total rows** | **958** |

> **STALE — this table predates the repairs below and has not been
> re-derived.** Repairs applied since: the Anderson phantom source and
> reference were replaced with a real paper, the finance DOI was dropped, and
> the McCloskey & Cohen row was titled. Those rows still read
> `unresolvable`/`untitled_citation` here because no invalidation or verifier
> re-run has been run. The vault is ahead of this table.

Progression this session: 453 match / 461 untitled / 40 unresolvable → current.
**Confidence has NOT been written. It must not be written until the gate passes.**

### The T2 promotion gate

`scripts/grade_all.py --with-t2 docs/audit/t2-verification.json` promotes a file
from `confidence: medium` to `high` only when all of its T2 sources resolved with
a matching title. Keys are `path::identifier`. The gate **fails today** because
19 unresolvable + 1 untitled remain.

---

## 2. THE 20 BLOCKING ROWS — exact keys, by file

Verbatim from the live evidence table. This is the work list.

### 1 untitled
```
AI-Architecture/Neuromorphic-Computing.md
  doi:10.1142/10269
```
→ **RESOLVED IN PRINCIPLE, NOT YET APPLIED.** See §4.

### 19 unresolvable
```
Consolidation/Adaptive-Forgetting.md                                    (7)
  doi:10.1017/CBO9780511628136.006
  doi:10.1037/0033-295X.112.4.842
  doi:10.1037/0033-295X.96.2.323     ← NOT fabricated. See §4 item C.
  doi:10.1037/xlm0000908
  doi:10.1038/379232a0              ← RE-ATTRIBUTION ready. See §4 item A.
  doi:10.1177/2515245920933748
  doi:10.3758/s13421-014-0408-9

Learning/Desirable-Difficulties-Bjork.md                                (4)
  doi:10.1016/S0010-0277(85)80010-3
  doi:10.1016/j.memco.2008.10.002
  doi:10.1037/0033-2909.124.4.421
  doi:10.1037/0096-3445.137.4.595

Executive-Control/Habit-Formation.md                                   (2)
  doi:10.1037/a0046060
  doi:10.1146/annurev-psych-010418-103041

Belief-Revision/Belief-Revision-Safe-Belief-Updating.md                 (1)
  doi:10.1016/j.artint.2014.01.1475

Cellular-Neuroscience/Pyramidal-Neuron-Apical-Dendrite-Computations.md   (1)
  doi:10.1038/nn1199_989

Knowledge-Representation/Cognitive-Maps-Beyond-Space.md                 (1)
  doi:10.1177/0956797615621371

Predictive-Processing/predictive-processing-and-active-inference.md      (1)
  doi:10.1093/brain/awag101/8519179

Social-Cognition/Cognitive-Dissonance-and-Self-Justification.md         (1)
  doi:10.1177/1754073917724993

Temporal-Cognition/Encoding-Specificity-Context-Dependent-Memory.md     (1)
  doi:10.1002/(SICI)1099-0720(199812)12:6
```

---

## 3. WHAT THE 19 ACTUALLY ARE — the diagnosis you must not re-derive

Recorded in `docs/audit/t2-unresolved-analysis.json` (keys:
`fabrication_audit_complete`, `fabrication`, `load_bearing_analysis`,
`substitute_research`, `anderson_1996_confirmed_absent`,
`bare_url_matching_risk`, `refuted_normalisation`).

The 19 are **three different defects**. Treating them alike is the trap.

### (a) 9 FABRICATED — the paper does not exist
Independently verified via PubMed (indexes Nature independently of Crossref) with
a positive control (437) before and after every search.

| Work claimed | Identifier | File |
|---|---|---|
| Anderson (1996) *Nature* 379:232–236 | `10.1038/379232a0` | Adaptive-Forgetting |
| Anderson (1998) *Memory and Forgetting* | `10.1037/0033-295X.112.4.842` | Adaptive-Forgetting |
| Anderson (2010) *The encoding and retrieval of memory* | `10.1017/CBO9780511628136.006` | Adaptive-Forgetting |
| Huettl, Hutter & Wozniak (2021) RIF replication | `10.1037/xlm0000908` | Adaptive-Forgetting |
| Basden, Basden & Hatfield (2014) | `10.3758/s13421-014-0408-9` | Adaptive-Forgetting |
| Depret, Erlbaum & Eerland (2020) | `10.1177/2515245920933748` | Adaptive-Forgetting |
| Bjork & Bjork (1992) discard/forgetting | `10.1037/0033-2909.124.4.421` | Desirable-Difficulties-Bjork |
| Bjork (1985) *Cognition* | `10.1016/S0010-0277(85)80010-3` | Desirable-Difficulties-Bjork |
| Friston (2017) *Brain* active inference | `10.1093/brain/awag101/8519179` | predictive-processing-and-active-inference |

**These are LOAD-BEARING, not dangling.** They support specific checkable claims
in the bodies. Recorded per-work in `load_bearing_analysis`. Examples:
`d = 0.31` with publication bias dropping to ~0.20 (Depret); `N = 630`, `d =
0.15–0.20` (Huettl); "the original demonstration" (Anderson 1996).

**CRITICAL CONSEQUENCE:** dropping a citation does NOT withdraw the sentence
citing it. The files would go on asserting those numbers with no source at all,
which is *worse* than a dead DOI — a dead DOI at least shows a reader a check
failed. When dropping, the claim must be withdrawn or marked too.

### (b) 1 DEAD IDENTIFIER, REAL WORK — repairable
> **CORRECTION: the paragraph below misidentifies the dead identifier, and
> following it destroys a real citation.** `10.1037/0033-295X.96.2.323` is
> **not** French's. Stem `0033-295X` is *Psychological Review* (verified via
> `api.crossref.org/journals/0033-295X` → title "Psychological Review"), and
> volume 96 is 1989 — so this DOI points at the slot the file's own reference
> [17] gives to **McCloskey & Cohen (1989)**, which is cited in the body at
> line 347. It fails to resolve because Crossref has not deposited that 1989
> record (all 48 Crossref works for *Psychological Review* 1989 return zero in
> the 32x page range), not because the paper is wrong. The repair is to **title
> the row in place**, not to delete it. Deleting it removes a genuine,
> body-cited source. Already done.

`10.1037/0033-295X.96.2.323` in Adaptive-Forgetting.md ~~is French (1999),
"Catastrophic forgetting in connectionist networks," *TiCS* 3:128–135. The work
is real and the file describes it correctly. Correct identifier:
**`10.1016/S1364-6613(99)01294-2`**~~ — already applied earlier in the session, but
this row still shows unresolvable, so re-verify the source line before touching
it. Possibly needs a re-derivation, not an edit.


### (c) 9 UNATTRIBUTABLE — identifier dead AND file doesn't say what it meant
Including the three SAGE DOIs (`10.1177/1754073917724993`,
`10.1177/0956797615621371`, `10.1177/2515245920933748`), the two
Desirable-Difficulties DOIs not in the fabricated list, and the Belief-Revision /
Pyramidal-Neuron / Habit-Formation rows. These files' reference lists do not
identify the work at the identifier, so there is nothing to search for.

**SAGE digests are DEAD, not mistyped.** 90 digit-variants probed across all
three, every one 404. SAGE uses ISSN stem + bare 10-digit article id, so there is
nothing to complete and one wrong digit anywhere is fatal. Do not retry.

---

## 4. THREE THINGS READY TO APPLY (user has approved #2 and #3)

> **SUPERSEDED IN PART — read `t2-anderson-resolution.json` first.**
> Item A below is **RESOLVED AND APPLIED**, and the answer is not the one this
> document expected. Two shortfalls in the original text, both now corrected
> there: the proposed 1991 JEP:General substitute **does not exist** (its pages
> are occupied by another paper), and item B's row in §3(b) was **misattributed**
> — the dead DOI there belongs to McCloskey & Cohen (1989), not to French.
> Do not re-derive any of this from the paragraphs below; they are kept only
> to show what was originally believed and why it was wrong.

### A. Anderson 1996 re-attribution — RESOLVED AND APPLIED, differently than proposed
**ORIGINAL TEXT — superseded, see the note above.** The file
`Consolidation/Adaptive-Forgetting.md` cites the
real paper at line 22, `10.1038/35066572 (Suppressing unwanted memories by
executive control)`, which is real:

> Anderson MC, Green C (2001) *Nature* 410:366–369. PMID 11268212.

The phantom 1996 entry is at **line 21**: `- "https://doi.org/10.1038/379232a0"`.

The **claim is TRUE** — only the attribution is wrong. Fix = delete line 21, and
re-date the body claim at line 506 from 1996 to 2001. Line 171 and the table at
line 259 also say "Anderson (1996)".

⚠️ **UNRESOLVED SUB-QUESTION — RESOLVED, and the answer is neither option.**
The body at line 171 says "**Anderson (1996), *Journal of Experimental Psychology: General* [1]**" but
reference [1] is *Nature*. The real original RIF paper is likely **Anderson &
Green (1991), "Self-monitoring and suppression of memories," JEP:General 120(3),
3–31** — JEP:General, not Nature. I searched and did NOT confirm it: PubMed's
`Anderson MC[au] AND J Exp Psychol Gen[ta]` returns only 4 records, earliest
2001, so 1991 is outside its coverage; the Crossref bibliographic search
returned unrelated papers. **Verify this independently before choosing between
"re-date to 2001 Nature" and "correct to the real 1991 JEP:General paper."**
This matters: the file may have a *second* journal error, not just a bad year.

> **RESOLUTION:** the 1991 paper is **fabricated** — "3–31" is impossible on its
> face (issue 3 starts at p. 235), and the alternative reading 261–273 is
> occupied by Graesser, Lang & Roberts (1991) at 120:**254–277**. The whole of
> volume 120 tiles with zero page gaps, and no article begins at 261. The file
> does indeed have a *second* error, as suspected. Applied fix: the behavioural
> RIF claim is now attributed to **Anderson, Bjork & Bjork (1994)**,
> `10.1037/0278-7393.20.5.1063` (Crossref + PubMed PMID 7931095) — *not* to
> Anderson & Green 2001, which is an fMRI study and does not contain the
> behavioural effect sizes the sentence reports.


### B. Drop the finance DOI — user approved
**User said:** "correct them to real papers or drop the entries."

`AI-Architecture/Neuromorphic-Computing.md` line 32:
`- "https://doi.org/10.1142/10269"` → resolves to "Real Options in Energy and
Commodity Markets." **Body mentions it ZERO times.** The file is otherwise
excellent (Hodgkin-Huxley 1952, Izhikevich 2003 with correct equations, STDP/Bi &
Poo 1998, Loihi, Intel million-neuron chip, DYNAP-SE2) and its other 12 sources
are all correctly on-topic and titled.

**Action: delete line 32.** Nothing in the file depends on it. Use
`scripts/doi_replace.py`-style boundary-aware editing, and back up first.

### C. The other 8 fabricated claims — user approved
"Correct them to real papers or drop the entries."

**Rules that follow from this, non-negotiable:**
- Correct only where a verified real paper **genuinely supports the claim in
  front of it**. Verify each by resolver status 200 + exact title + first author
  + year + journal. A real paper that doesn't support its sentence is a wrong
  citation with correct metadata — worse than a dead DOI.
- Drop where no real paper does — and withdraw or mark the claim alongside the
  entry, per the (a) consequence above.
- **Do not guess substitutes.** Friston 2017 was investigated and deliberately
  left open: 71 Friston active-inference papers exist, no single 2017 *Brain*
  paper of that name, and the file uses that citation for two different claims.
  Candidate clusters are recorded in `substitute_research`. Any selection is a
  reading of the file, not a lookup.

---

## 5. SCRIPTS (all in /home/operator/hermes-brain/scripts/)

| script | lines | purpose |
|---|---|---|
| `verify_t2_titles.py` | 1680 | The verifier. Writes `docs/audit/t2-verification.json`. **Takes ~3.5 min — run in background.** Crossref + arXiv + DataCite. |
| `invalidate_stale_t2.py` | 75 | Invalidates exact stale untitled/mismatch keys. |
| `invalidate_unresolvable_t2.py` | 48 | Invalidates unresolved rows so they re-derive. |
| `invalidate_repaired_t2.py` | — | Invalidates rows for repaired identifiers. |
| `invalidate_titled_t2.py` | — | Invalidates rows after titling. |
| `doi_replace.py` | 69 | **Boundary-aware** DOI substitution with exact-count enforcement. **Use this, never bare `re.sub`.** |
| `prune_ghost_t2_rows.py` | 249 | Removes evidence rows orphaned by repaired identifiers. Exact-shape matching only. |
| `title_untitled_sources.py` | — | Original 461-row titling pass. |
| `title_bare_url_rows.py` | 176 | Titled the 32 corroborated bare-URL rows. |
| `title_revealed_rows.py` | 254 | Titled 7 rows exposed by re-derivation. |
| `apply_verified_dois.py` | 164 | The 6 batch-2 replacements. |
| `apply_verified_dois_13.py` | 222 | The 10 batch-1/3 mappings (9 applied, SICI skipped). |
| `adjudicate_t2_suspects.py` | — | Ambiguous-band adjudication. |
| `adjudicate_t2_band.py` | — | Band adjudication helper. |
| `grade_all.py` | — | The promotion gate. `--with-t2 docs/audit/t2-verification.json` |

Scratch research scripts (in `/home/operator/.hermes/cache/scratch/`, **not** in
git): `verify_fabrication.py`, `audit_fabrication_all.py`, `fab3.py`,
`find_substitutes.py`, `corroborate_bare.py`, `check_bare_matches.py`,
`load_bearing.py`, `probe_sage.py`, `resolve_by_title.py`, `probe_normalisations.py`.

---

## 6. VAULT LAYOUT

```
/home/operator/.hermes/oracle/brain/<Domain>/<File>.md
```
Domains include `Consolidation/`, `Learning/`, `AI-Architecture/`,
`Executive-Control/`, `Knowledge-Representation/`, `Predictive-Processing/`,
`Social-Cognition/`, `Temporal-Cognition/`, `Cellular-Neuroscience/`,
`Belief-Revision/`, `Attention/`, `Memory-Architecture/`, `research/`.

- The vault is **gitignored / outside the repo** — vault edits are local only.
- Frontmatter is YAML between two `---` lines. `sources:` is a list of
  `"URL (Title)"` strings. `confidence: medium|high`.
- `research/` files use a flush-left list style, NOT indented. Some have nested
  `---` inside the frontmatter — always locate the *first* closing `---`.
- ~2242 parse cleanly; ~91 are pre-existing `{url, desc}` mapping-style files
  that fail ordinary YAML parsing. **None of the 91 are in the T2 table.** Do
  not "fix" them.

---

## 7. THE TRAPS — read before editing anything

Every one of these was hit for real this session. They all share one shape:
**a silent success that lets the next stage believe the work was done.**

1. **Unbounded `re.sub` on a DOI prefix.** `10.1016/0010-0285` matched *inside*
   two complete valid DOIs and produced corrupted concatenations
   (`...74)90009-7(80)90005-5`). Use `scripts/doi_replace.py`.

2. **Stale base for sequential edits.** `title_revealed_rows.py` built each
   candidate from a `text` snapshot read *before* the per-file loop, so in a file
   with several rows **every write after the first discarded the earlier ones.**
   It reported 4 rows written; only the last was on disk. Build against the
   running candidate and assert earlier-accepted titles survive.

3. **Char offset used as line index.** `lines[:end]` where `end` was a character
   offset — grabbed whole documents, all 26 candidates failed, and every row
   still reported "attempted."

4. **`strip()` before rebuilding a line.** Discarded the indent, put entries
   flush-left, ended the `sources:` list. Pass the line **unstripped**.

5. **Wrong key format.** `key.startswith('arxiv:')` when the key is
   `path::arxiv:NNNN.NNNNN` — ran zero times, silently. Split on `::` first.

6. **No-op invalidation.** Computed the correct stale set, then removed a
   *different* set. It must remove `stale`, verify the count, and fail loudly.

7. **Search zeros that are about the query.** Three this session:
   - malformed field tags (`Anderson+MC[au]` instead of `Anderson+MC[au]:`)
     returned `count=0` for an answerable question;
   - requiring two terms *in the title* returned 0 when 71 papers existed;
   - a mistyped SAGE DOI transposed two digits and reported "not in table".
   **Always run a positive control BEFORE treating a zero as absence.** A zero
   from a search API is evidence about the query until a control says otherwise.

8. **PII-style DOIs.** Old Nature DOIs like `10.1038/379232a0` are the class
   Crossref covers *worst*. Use PubMed for those.

9. **Generic pruning heuristics delete live rows.** A 34-char-prefix rule wanted
   to delete 19 valid rows; a sibling-prefix rule deleted a valid one-character
   typo. The pruner now matches only the exact known corruption shape.

10. **Unquoted titles containing `": "`** become YAML mappings. Also, don't
    reorder `batch210` into a different list style.

11. **A DOI that "belongs to paper X" may belong to a different paper
    entirely — check the journal stem, not the topic.** `10.1037/0033-295X.96.2.323`
    was recorded as "French (1999), TiCS". It is not: `0033-295X` is
    *Psychological Review*, and volume 96 is 1989, so it is the DOI slot for
    McCloskey & Cohen (1989) — a real paper the file cites in its body. Acting on
    the recorded attribution deleted a genuine source. Verify the *venue* a
    DOI stem implies (`api.crossref.org/journals/<stem>`) before concluding
    anything about what a dead identifier points at.

12. **A resolver 404 is only evidence of absence if you have measured that
    resolver's coverage for that journal and year.** Crossref holds 37 unique
    DOIs for all of 1991 *JEP:General* and would have "refuted" any 1991 paper
    in it. But its page spans tile the volume with **zero gaps**, so the
    incompleteness is missing DOIs *for articles that exist*, not missing
    articles. The general form: count distinct page spans and check for gaps
    before trusting a negative. A negative you have not calibrated is a guess
    wearing a lab coat.

13. **Verify a delegated researcher's citations before adopting them — two of
    three offered citations were wrong.** One DOI resolved to an unrelated
    paper on a different topic; another 404'd and pointed at different pages
    than claimed. Subagent output is a self-report: exactly as a child cannot
    be trusted to have uploaded a file, it cannot be trusted to have looked up
    a DOI. Re-resolve every identifier it hands you, especially the ones that
    would be easiest to copy.


---

## 8. EXPECTED WORKFLOW FOR THE REMAINING 20

Per file, in this order:

1. Read the file's body and reference list to establish **what it claims**.
2. Back the file up.
3. For each blocking row, decide: real substitute exists / drop the entry.
4. Apply with `scripts/doi_replace.py` (boundary-aware) or a careful scripted
   edit, preserving each file's existing style.
5. **Validate YAML parses** before writing. Check it after.
6. Invalidate the affected keys:
   `python3 scripts/invalidate_stale_t2.py` / `invalidate_unresolvable_t2.py`.
7. Re-run the verifier **in the background** (~3.5 min):
   ```sh
   cd /home/operator/hermes-brain && python3 scripts/verify_t2_titles.py
   ```
8. Run the full test suite — must stay at 733 passing.
9. Commit and push. **Git ops must each be their own terminal call**; bundling
   trips the consent gate. Don't pipe gates through `tail`.

**After all 20:** run the real gate, and only if it passes, write confidence.
Record every decision in `docs/audit/` with its evidence.

---

## 9. COMMITTED HISTORY THIS SESSION (newest first)

```
2440493  research the two fabrications where real literature exists -- one solved
3ae4c81  the fabrication audit is complete -- 9 of 19, not "at least 6"
fe545f3  re-verify the Anderson 1996 claim on a route that trusts Crossref less
09fefc8  the six fabricated citations are load-bearing, not dangling
87f71e1  title 33 more rows; the 32 bare-URL matches were all sound
b22045b  six of the 19 unresolved cite papers that do not exist
d0fcf68  correct two errors in the unresolved analysis; SAGE digits
f07e965  record the refuted normalisation hypothesis for the 19 unresolved
f0708ed  prune ghost rows so a file with perfect citations can promote
befe397  ask DataCite as well as Crossref; repair a DOI I corrupted
1fa1c64  replace 9 more dead DOIs, 928 of 954 citations now title-matched
1faed42  fix six verifier defects that made correct citations look wrong
```

**Ownership:** all commits are TheHappyHermit
(`260156429+TheHappyHermit@users.noreply.github.com`). Verify with
`git log --format='%an %ae' | sort -u` before pushing.

---

## 10. AUDIT EVIDENCE FILES (all in docs/audit/)

Most relevant to this work:
- `t2-verification.json` — the 958-row evidence table
- `t2-unresolved-analysis.json` — **the richest record.** Contains
  `fabrication_audit_complete`, `fabrication`, `load_bearing_analysis`,
  `substitute_research`, `anderson_1996_confirmed_absent`,
  `bare_url_matching_risk`, `refuted_normalisation`
- `t2-doi-replacements.json` — accepted AND rejected replacements
- `t2-fabricated-citations.json` — earlier fabrication corrections
- `t2-adjudication.json` — semantic adjudication evidence
- `t2-source-titling.json`, `t2-citation-corrections.json`,
  `t2-source-exclusions.json`, `t2-abbreviated-labels.json`,
  `t2-abbreviation-mismatches.json`, `t2-rescored.json`, `t2-final-13.json`

`.gitignore` covers timestamped `docs/audit/*.bak.json` safety snapshots.

---

## 11. KNOWN GAP — do not report this as closed

**32 rows are now titled from the resolver, not from anything the file
asserted.** They were bare URLs where the file stated nothing, so `match` meant
only that the resolver returned *some* title. A wrong-but-live paper would score
`match` invisibly. All 32 were cross-checked against their own file's body
(Spelke ×13, Baillargeon ×9, Smith ×6, Howard ×5, Bassett ×4 in
`Developmental-Origins-of-Cognition.md`) — **32/32 supported, 0 contradicted.**
They are almost certainly right, but they are resolver-derived, not
author-asserted. The remaining ~30 of that set are less strongly corroborated
than the sampled ones.

Also: one subagent reported that some *live* identifiers in these files point at
the wrong real paper (e.g. `nature.com/articles/nrn3803` → a GABAergic paper in
`Cognitive-Maps-Beyond-Space.md`; `10.3758/BF03204376` → unrelated 1980 paper in
`Mental-Rotation-and-Imagery.md`). **Not yet investigated.** Worth a pass.

---

## 12. PROCESS NOTES FOR THE NEW AGENT

- **A "BACKGROUND PROCESS COMPLETE" notification is not a user message.** This
  session ended with ~20 such notifications (v15–v33 and research probes) that
  were all stale results from long-finished background runs. The previous agent
  answered each as if it were a fresh turn and produced near-verbatim repeats.
  **Check whether a run is current before acting; batch the rest.**
- Use `session_search` with `session_id='20260927_124725_6f428999'` to recover
  exact earlier reasoning if needed.
- Re-verify anything this document asserts. It was written from live checks, but
  the traps in §7 exist precisely because plausible output wasn't true.
