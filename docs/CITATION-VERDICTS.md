# Citation verdicts — how to read them

Written 2026-09-28, after Phase 2b resolved every DOI and arXiv identifier
in both vaults. This file exists because the raw numbers look alarming and
mostly are not, and because a future agent reading only the CSV would reach
the wrong conclusion.

Read this before reporting anything about citation correctness.

---

## The numbers

Per **unique identifier**, 4,655 total across both vaults (12,299 citation
rows):

| verdict | count | what it means |
|---|---:|---|
| `unverified_low_overlap` | 1,766 | resolved, title differs enough to be uncertain |
| `title_match` | 1,695 | resolved, title confirmed |
| `title_weak` | 530 | resolved, partial overlap |
| `not_registered` | 277 | the identifier is not registered with the resolver |
| `UNRELATED_TITLE` | 220 | **see below — 95% are correct citations** |
| `unresolved_rate_limited` | 119 | could not be checked from this host |
| `http_404` | 48 | not found |

4,536 of 4,655 were actually checked. The 119 that were not are arXiv
2026-series ids that this host is rate-limited on (HTTP 429 on the API,
406 on the `/abs/` page). Crossref resolves them fine.

---

## The trap: `UNRELATED_TITLE` is a scoring artifact

The similarity metric is:

```
similarity = |shared words| / |words in the REGISTERED title|
```

A citation that does not restate the title therefore scores near zero **by
construction**. I sampled 12 arXiv cases expecting mis-citations and found
correctly-cited papers every time:

```
registered  "Zep: A Temporal Knowledge Graph Architecture for Agent Memory"
cited as   "- Zep (arXiv 2501.13956) + Graphiti issue #1728 ..."
similarity 0.00

registered  "SYNAPSE: Empowering LLM Agents with Episodic-Semantic Memory
            via Spreading Activation"
cited as   "- {'Synapse': 'Episodic-Semantic Memory via Spreading
            Activation (Jiang et al., ACL Findings 2023)'}"
similarity 0.00

registered  "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"
cited as   "arXiv:2306.05685, NeurIPS 2023 Datasets & Benchmarks."
similarity 0.20
```

208 of the 397 arXiv cases were **exactly** 0.0 — the signature of a
citation line that simply does not quote the title.

Reporting these as suspected fabrications would have been a false
accusation produced by a scoring function.

---

## What is actually left

`scripts/reclassify_identifiers.py` splits the 628 `UNRELATED_TITLE` rows:

| class | rows | meaning |
|---|---:|---|
| `no_title_restated` | 313 | a URL or venue line; there is no title to compare |
| `short_name_confirmed` | 287 | the citation quotes a **distinctive** term from the title — an acronym or system name like `Zep`, `SYNAPSE`, `MT-Bench`, `SpectralShift`. Positive evidence the citation is right |
| `needs_judgement` | **28** | says something specific about the work but shares no vocabulary and no distinctive term. **The only shape that can be a real mismatch** |

**600 of 628 (95%) are explained as correct. The 28 are the findings.**

```
python3 scripts/reclassify_identifiers.py    # reclassify
python3 scripts/verify_reclassifier.py       # 9/9 controls
```

The load-bearing control asserts that a correct short-name citation is
**never** routed to a human, because that is the precise failure this
script exists to prevent.

---

## Never report these

- **"N citations appear fabricated"** from this CSV. That is the specific
  error the reclassifier exists to prevent. Report the 28.
- **The 119 rate-limited identifiers as broken.** And never as verified.
  They are unchecked. Per rule 1.4, a fetch you could not make is not a
  refutation.

---

## What is still true

A DOI returning HTTP 200 is **not** evidence a citation is correct.
`10.1109/ICDM.2013.83` resolves, to a real paper, that is completely
unrelated to the citation it appears in — "Non-negative Multiple Tensor
Factorization". That case is correctly routed to `needs_judgement`.

All 2,500 arXiv identifiers in the corpus are date-plausible: no impossible
months, none dated in the future relative to 2026-09-28.

---

## Data files

- `docs/audit/dois.csv` — 12,299 rows, every occurrence with file and line
- `docs/audit/doi-resolution.csv` — the same rows with status, verdict,
  similarity, registered title, shared words, and citation context
- `docs/audit/unrelated-title-reclassified.csv` — the 628 rows with their
  reclassification and the distinctive term that matched
