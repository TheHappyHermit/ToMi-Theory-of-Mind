# OKF upstream vs. the local gold standard — and the dead-pointer audit

Written 2026-09-28. **Nothing was changed, deleted, or repointed.** This is
the answer to three questions: what the schema actually is, what should
change in it, and which files that reference a schema should be deleted.

---

## 1. What the schema is, and where it came from

**OKF v0.2 is real and it is Google's.** Verified from the primary source,
not a summary, and by two independent fetches that agree byte-for-byte
(sha256 `26aa5da029278939f914e578107242d9607d4f2dc5fe153272b82f9ed1030101`,
37,748 bytes):

```
CANONICAL  https://github.com/GoogleCloudPlatform/open-knowledge-format
           -> SPEC.md at repo root, "Open Knowledge Format (OKF)", Version 0.2
LEGACY     https://github.com/GoogleCloudPlatform/open-knowledge-format
```

**Use the canonical repository.** The legacy location is frozen — its own
README carries an `[!IMPORTANT]` banner:

> **Stop using the copy under `okf/` in this repository.** It is a frozen
> snapshot, no longer maintained, and anything built against it will drift
> out [of date].

The two SPEC.md files are currently byte-identical, so nothing read from
the legacy path is wrong today. It is a maintenance hazard, not a
correctness problem. Point future citations at the canonical repo.

v0.1 → v0.2 landed 2026-07-24; the canonical repo was created 2026-08-11;
the last SPEC.md edit was 2026-08-21. v0.2 breaking changes: `timestamp` →
`generated.at`, and body `# Citations` → frontmatter `sources`.

So the local schema is genuinely OKF v0.2 with local additions — the
provenance in the skill and the decision doc is correct on that point.

## 2. The finding that matters most: upstream requires ONE field

OKF v0.2 §4.1 states, verbatim:

> `type` is the only always-required key; a concept carrying just `type` is
> fully conformant (§11).

Upstream's own frontmatter block:

```yaml
type: <Type name>                  # REQUIRED
title: <Optional display name>
description: <Optional one-line summary>
resource: <Optional canonical URI for the underlying asset>
tags: [<tag>, <tag>, ...]          # Optional
```

Required: **`type`, and nothing else.** Everything else is recommended or
optional.

Two more upstream positions that the local schema **contradicts**:

| Upstream says | Local schema says |
|---------------|-------------------|
| `type` values are **not** registered centrally. Consumers MUST tolerate unknown types gracefully | 29 closed enum values; unknown type = defect |
| `status`: `draft \| stable \| deprecated`. Absent ⇒ `stable`. Consumers MUST NOT reject a file for missing frontmatter (§11) | 14 statuses, all **required** |
| Trust is **derived** from `verified` actors: no `verified` ⇒ unverified; non-human ⇒ machine-confirmed; `human:<id>` ⇒ human-reviewed | `confidence:` is a **required, hand-set** field |

A fourth contradiction, and the sharpest one: **`okf_version` per-page
contradicts upstream.** §12 permits `okf_version: "0.2"` *only* in a
bundle-root `index.md` frontmatter block — the sole place frontmatter is
allowed in an index. The local schema makes `okf_version` a **required key
on every concept page**, and the daily lint cron counts its absence as a
defect. Under a strict reading of §12, every page in the corpus is carrying
a field upstream scopes to one place. Worth deciding deliberately: keep it
(the value of a per-page version marker is real, and `okf_version: "0.2"`
in `index.md` is still emitted) or drop it to index-only. Do not leave it
decided by accident.

**This is a genuine design disagreement, and it is worth deciding
deliberately rather than by drift.** The local schema is stricter. That is
defensible for a personal knowledge base — stricter provenance is the point
of the whole remediation project, and the owner asked for "a well-educated
broad schema."

But it is important to know that the strictness is a **local decision, not
a Google one**, because the two are currently recorded as if they were the
same thing. The decision doc and the YAML both imply OKF conformance; in
practice the local schema is a *profile* of OKF v0.2 that is deliberately
stricter, and inverts four upstream rules.

The honest description is **"OKF-derived, heavily extended"** rather than
"OKF v0.2".

**Recommendation: keep the strictness, but label it correctly.** Record in
the YAML that this is a local profile of OKF v0.2, and note which fields
are local additions (`id`, `okf_version`, `confidence`, `epistemic`,
`supersedes`/`superseded_by`, `aliases`, `wikilinks`, `review_after`).
Then a future reader knows that deviating from upstream here is a decision
and not an error. This is a documentation change, not a schema change.

**Recommendation on `type`:** keep the enum, but keep upstream's tolerance
principle in `WIKI-STANDARDS.md` — an unknown type should be *reported*,
not auto-normalised into something wrong. The existing `type_map` already
does the safe half of this.

**Recommendation on `status`:** keep 14 values. The 3 upstream values are a
subset (`draft`, `stable`, `deprecated` are all present). The extra 11 are
lifecycle vocabulary this system actually uses. No conflict.

**`confidence` and `epistemic` have no upstream basis at all.** This was
checked directly against the spec text, not inferred: `confidence` appears
**0 times** in the 37,748-byte SPEC.md, and `epistemic` appears **0 times**.
Worse, the spec explicitly discusses rejecting the idea — "credibility"
appears 8 times, and the `sources` section treats `author`, `usage_count`,
and `last_modified` as per-source credibility signals rather than a stored
score. So these two are **local inventions**, and the clearest signal of
where the local profile diverges. They are not wrong; they are ours.

That is worth stating plainly in the YAML, because a reader who assumes
Google specified `confidence: high|medium|low` is wrong, and a reader who
assumes Google forbade it is also wrong.

**Recommendation on `confidence`:** this is the one to reconsider. Upstream
derives trust from `verified` actors and explicitly says consumers MUST NOT
reject a file for lacking it. The local schema makes `confidence`
**required** and hand-asserted. Per the owner's own decision to derive
confidence from evidence, a *derived* field is strictly better than a
self-reported one, and upstream's `verified`-actor model is a better input
than a human typing a string. Consider: keep `confidence` as an output,
computed from `verified` actors plus source quality, rather than a field
an author fills in. This is the one change that would genuinely improve
the schema, and it needs a decision, not an edit.

## 3. The gold standard: complete, and already the strictest

`schemas/okf-schema.yaml` (md5 `6a08c6db`) is the broadest schema found
anywhere on the system. Its required list is already the **stricter** one —
9 keys:

```yaml
required:
  - okf_version
  - id
  - type
  - status
  - description
  - generated
  - tags
  - sources
  - confidence
```

This is the same 9 the generated JSON mirror emits. So the "stricter list"
the owner asked for **is already the live standard** — no schema edit is
needed to get it. What was missing was the certainty, which this document
supplies.

**Two genuine gaps against upstream:**

1. **`resource`** (§4.1, recommended upstream, the canonical URI for the
   underlying asset) is absent from the local required/recommended/optional
   lists. The mirror has `url` and `arxiv_id` as near-duplicates that the
   YAML does not define. **Recommend adopting upstream's `resource` name**
   rather than carrying three names for one idea.
2. **`sources` has no entry shape.** Upstream §5.1 defines it precisely:
   `resource` (required within an entry), plus `id`, `title`, `author`,
   `usage_count`, `last_modified`, and a sibling
   `usage_window: {from, to}`. The local `sources` is a bare list with no
   per-entry structure. This matters directly for the confidence work: a
   source with an `author` and a `usage_count` is exactly the evidence
   input a derived `confidence` would need. **Recommend adopting the
   upstream entry shape** — it is the input the rubric needs.

The whole `Attested Computation` family (`runtime`, `parameters`,
`computation`, `executor`, `attester`) is also absent. For a personal
knowledge base that is very likely correct to skip; noting it only so the
omission is deliberate rather than accidental.

## 4. The generated mirror: keep, do not delete

`schemas/wiki-frontmatter.schema.json` is generated by
`scripts/okf_export_json.py` from the YAML. Verified in sync by
regeneration: md5 `e0374889` unchanged before and after.

It is not a rival schema. Its 23 properties are the YAML's fields plus
`url`/`arxiv_id`/`provenance`, which are mirror-local and **not** in the
YAML — worth noting as a small inconsistency, since a JSON consumer sees
fields the YAML does not define.

**Recommendation: keep the file, keep the generator, and add a CI-style
check that regenerating produces no diff.** The risk was never the file
itself; it was that a reader could mistake it for an independent standard.
A machine check removes that risk permanently.

## 5. The real problem: 12 dead pointers in 8 files

The `standards/` directory **does not exist**. The files live in
`schemas/`. Every pointer below is broken:

| File | Lines | Nature |
|------|------:|--------|
| `~/.hermes/skills/wiki-management/SKILL.md` | 71, 73 | **the skill the agent actually loads** |
| `~/.hermes/skills/wiki-management/references/okf-standard.md` | 9, 68 | live reference |
| `~/.hermes/skills/wiki-ingestion/SKILL.md` | 174, 175 | live skill |
| `/home/operator/scripts/research_quality_check.py` | 38, 39, 44 | **runs daily** |
| `/home/operator/scripts/fill_oracle_gaps.py` | 131 | writes a dead path into a manifest |
| `hermes-brain/scripts/check_cron_drift.py` | 80, 81 | knows the rename, applies it to cron only |

Plus the Oracle decision doc
`decisions/2026-09-25_okf-schema-single-source-of-truth.md` lines 38-39.

### 5.1 The one that is actively broken

`research_quality_check.py` defaults to the dead path, and
`_SCHEMA = _load_schema()` runs at **module level**. Proven by running it
exactly as cron does:

```
FileNotFoundError: [Errno 2] No such file or directory:
  '/home/operator/hermes-brain/standards/okf-schema.yaml'
exit 1
```

With `OKF_SCHEMA` set to the real path it works and reports real findings.

**And the cron job reports `last_status: ok`, `last_run_at: 2026-09-28T10:02`.**
The `|| true` in its prompt swallows the failure. This is the exact failure
class from the history table — a check that cannot fail reports success —
and it means the daily research quality check has been **silently dead**,
reporting nothing, while claiming it ran.

This is the single most important item in this document. It is not a
schema problem at all; it is a broken verifier that looks healthy.

## 6. Files that reference a schema but are NOT duplicates

Correctly configured, no action needed:

- `cron/prompts/okf-lint-daily.prompt.txt` — points at `schemas/`, correct
- `cron/prompts/okf-repair-daily.prompt.txt` — points at `schemas/`, correct
- Cron `Wiki Lint Daily`, `Wiki Lint Weekly Deep`, `Wiki Ingestion Nightly`
  — all name `schemas/okf-schema.yaml` and `schemas/WIKI-STANDARDS.md`
- `Wiki Ingestion Nightly` additionally routes writes through `okf_gate.py`
  and explicitly forbids restating the field list

Note the two daily prompt files say *"This job is PAUSED by default — do not
resume without explicit user approval."* The corresponding live cron jobs
are enabled. **Worth the owner's attention** — the prompts and the jobs
disagree about their own state.

## 7. Genuine duplicates — the deletion list

All verified by md5. **Nothing has been deleted.** These are the candidates,
and the owner decides.

| # | File | Verdict |
|---|------|---------|
| 1 | `hermes-brain/schemas/SCHEMA_ORACLE.md` | **Delete.** Byte-identical to `SCHEMA.md` (md5 `d4435c2c`). The name implies a variant that does not exist. This duplicate is itself a drift hazard. |
| 2 | `hermes-brain/schemas/wiki-schema.md` | **Delete.** Third byte-identical copy (md5 `d4435c2c`). |
| 3 | `~/.hermes/oracle/brain/SCHEMA.md` | **Do not delete — replace.** It is the **only** copy the Oracle vault has (md5 `0ac58058`, differs). Delete it and the vault loses its schema. Correct content into it, or make it a pointer to the repo. |
| 4 | `~/.hermes/skills/wiki-management/references/okf-standard.md` | **Delete after repointing.** Abbreviated 4-field restatement; the live `SKILL.md` explicitly says field lists are "not restated in this skill on purpose." This file violates that. |
| 5 | `~/skills/wiki-management/SKILL.md` | **Delete — it is the worst offender.** Restates the field list inline with a **different, wrong** type enum (11 values, uses `research_report` instead of canonical `research-report`, and names `report` which is not an OKF type at all). The repo copy is the correct one. |
| 6 | `hermes-brain/skills/wiki-management/SKILL.md` | **Keep as canonical**, after adding the `resource` field and the profile note. |
| 7 | `hermes-brain/skills/wiki-management/references/okf-standard.md` | **Same as #4** — byte-identical to the live one (md5 `4b0395b2`). Delete both or neither. |
| 8 | `/home/operator/scripts/fill_oracle_gaps.py` vs `hermes-brain/scripts/fill_oracle_gaps.py` | **Not a schema duplicate.** They differ substantially — the repo copy has 52 extra lines and uses `HERMES_HOME` where the live copy still uses `AUTOGNOSIA_HOME`. This is a retired-name problem, not a schema problem. Note: this file is on the do-not-stage list. |
| 9 | `bak_autognosia/**` (3 files) | **Leave.** Retired filesystem, kept as history. Strict subsets, no improvements. |
| 10 | `hermes-brain/schemas/wiki-frontmatter.schema.json` | **Keep** — generated mirror, in sync. Add a no-diff CI check. |
| 11 | `hermes-brain/schemas/research-request.schema.json` | **Keep.** A different artifact (research requests, not wiki pages). `verify_schema_conformance.py` correctly targets it. |

### 7.1 Also worth deleting, found while auditing

| File | Why |
|------|-----|
| `hermes-brain/schemas/__pycache__/` and `scripts/__pycache__/` (one contains `okf_lint.cpython-311.pyc`) | Compiled bytecode committed alongside source. Regenerable, and a stale `.pyc` is a real hazard when a schema changes. |
| `hermes-brain/cognition-arena/prior-run-*/` (3 directories) | Archived arena runs. Per the standing rule these are *evidence and must not be deleted* — listing them so you can decide, with the rule stated rather than acted on. |

Nothing above was deleted. The `__pycache__` entries are the only ones I
would call safe without discussion; the arena runs are explicitly covered
by your no-deletion rule.

## 8. Summary of what is recommended

**Schema itself:** the required list needs no change — it is already the
strict 9, and it is machine-verified by
`scripts/verify_schema_integrity.py` (new, with negative tests).

Three changes worth considering. All need a decision, not an edit:

1. Adopt upstream's **`resource`** field, replacing the mirror-only `url` /
   `arxiv_id` near-duplicates.
2. Adopt upstream's **`sources[]` entry shape** (`resource`, `id`, `title`,
   `author`, `usage_count`, `last_modified`, `usage_window`). This is the
   evidence input a derived `confidence` would need.
3. Reconsider **`confidence`** as derived from `verified` actors plus source
   quality, rather than hand-asserted. Aligns with the owner's own
   instruction and with upstream's trust model. This is the one change that
   would genuinely improve the schema.

And one to decide *against* changing, but explicitly: **`okf_version`**
per-page contradicts upstream §12, which scopes it to a bundle-root
`index.md`. It is currently load-bearing across the corpus and the lint
cron, so changing it is a Phase 2 decision with real blast radius. The
point is that it should be a decision.

**Schema documentation:** label the local schema as a stricter local profile
of OKF v0.2 ("OKF-derived, heavily extended"), list the local additions,
and state plainly that `confidence` and `epistemic` have no upstream basis
at all. Cheap, and it prevents a future reader assuming Google specified
the strictness — or assuming Google forbade these fields.

**Also fix, and it is a self-contradiction in the gold standard itself:**
the YAML header says "Authority: `SCHEMA.md` … If they disagree, THIS FILE
wins for machines and `SCHEMA.md` must be corrected to match." That
inversion is why three byte-identical copies of `SCHEMA.md` exist and a
fourth drifted. The file that is supposed to be the single source of truth
declares another file to be the authority, with a tie-break rule. Name the
real authority in one place and delete the tie-break.

**The urgent item, which is not a schema item at all:** fix
`research_quality_check.py`. It is crashing daily and reporting `ok`.

**Deletions:** 5 files are safe to delete once their pointers are
repointed (items 1, 2, 4, 5, 7). One must be corrected rather than deleted
(item 3). Two `__pycache__` directories are safe. The rest stay.
