---
name: wiki-ingestion
version: 3.0.0
description: >
  Ingest raw content into Active Wiki with dedup, formatting, and source tracking.
  Supports quick-insert (minimal), standard (auto-suggested), and full schema modes.
  Use when processing captured content, research results, or user-provided material.
---

# Wiki Ingestion Skill

## Purpose

Process raw content and ingest it into the Active Wiki with proper formatting, deduplication, and source references.

## Wiki Location

- **Active Wiki**: `~/.hermes/active-wiki/`
- **Categories**: `projects/`, `reference/`, `system/`, `personal/`
- **Metadata**: `.meta/` directory for ingestion logs and content hashes

## Workflow

### 1. Receive Raw Content

Content can come from:
- User-provided URLs or text
- Researcher profile results
- Web clippings
- Documents

### 2. Compute Content Hash

Use SHA-256 to hash the content and check against existing wiki pages for duplicates.

### 3. Choose Schema Mode

**Quick-Insert Mode (default):**
Use when user wants fast entry with minimal friction. Only `title` required.

```markdown
---
id: auto
title: Descriptive Title
created: auto
updated: auto
---

# Title

Content here...

Source: session:YYYYMMDD_HHMMSS / url:https://... / user-provided
```

**Standard Mode (auto-suggested):**
Use when user wants structured metadata. Auto-suggest fields from content analysis.

```markdown
---
id: auto
title: Descriptive Title
created: auto
updated: auto
type: evergreen | temporal | historical
tags: [auto-suggested]
source: session:YYYYMMDD_HHMMSS
---

# Title

Content here...

Source: session:YYYYMMDD_HHMMSS
```

**Full Mode (power user):**
Use when user wants complete metadata control.

```markdown
---
id: auto
title: Descriptive Title
created: auto
updated: auto
type: evergreen | temporal | historical
status: recent | active | pinned | archived
knowledge_type: evergreen | temporal | historical
researched_at: YYYY-MM-DD
valid_as_of: YYYY-MM-DD
review_after: YYYY-MM-DD
project_ids: []
tags: []
salience:
  user_importance: low | medium | high | critical
  unresolved: false
  conflict: false
  novelty: low | medium | high
  active_project: false
  risk: low | medium | high
future_cues:
  - alternate search terms for this content
future_scenarios:
  - situations where this content would be relevant
---

# Title

Content here...

Source: session:YYYYMMDD_HHMMSS / url:https://... / user-provided
```

### Auto-Suggest Logic

When using Standard or Full mode, auto-suggest these fields from content analysis:

- **`type`**: 
  - "evergreen" if no dates mentioned
  - "temporal" if dates in past and present
  - "historical" if all dates in past
- **`tags`**: Extract noun phrases, project names, key concepts
- **`project_ids`**: Inherit from folder path if page is in `projects/X/`
- **`knowledge_type`**: Same as `type` if not explicitly set

### 4. Determine Category

Route content to the appropriate wiki category:
- `system/` — System configuration and memory
- `personal/` — Personal knowledge and decisions
- `projects/` — Project documentation
- `reference/` — Reference material

### 5. Write to Wiki

Create the formatted page in the appropriate category under `~/.hermes/active-wiki/`.

### 6. Log the Ingestion

Record the ingestion in the wiki log:
```markdown
YYYYMMDD-HHMMSS: Ingested [title] into [category]/[slug].md | Source: [source] | Mode: quick|standard|full
```

Update `~/.hermes/active-wiki/.meta/ingestion-log.md`.

## Source Reference Standards

Every ingested page must include a `Source:` field:
- `session:YYYYMMDD_HHMMSS` — Session where content was created
- `url:https://...` — URL where content was found
- `user-provided` — User provided the content directly
- `researcher:package-id` — From a researcher package
- `oracle:vault-page-id` — From Oracle vault

### A `sources:` entry with an identifier also needs a TITLE

Distinct from the `Source:` field above, and the thing the T2 verifier reads.
When a `sources:` entry carries a DOI or an arXiv id, it must also carry the
paper's title:

```yaml
sources:
  - arXiv:2509.20021 (Embodied AI Survey)              # GOOD
  - doi:10.1109/PROC.1975.9939 (The protection of information in computer systems)
  - https://arxiv.org/abs/2607.18704                    # BAD — no title
```

The verifier resolves each identifier, fetches the real document, and
compares the real title against the title recorded here. With no title to
compare, the row becomes `untitled_citation` and the page is capped at
`medium` permanently — and **nothing reports it**. The write succeeds; the
failure surfaces months later in a grading run.

A title that *differs* from the real one is worse than none: it is treated as
a fabrication and capped at `low`.

- **Fetch the title from the source** — the arXiv abstract page, the DOI
  landing page, the PDF. Never from memory, never from a search snippet,
  never paraphrased.
- **Never invent one.** If it cannot be retrieved, write the identifier alone
  and set `status: unverified`. An honest gap is fixable; a fabricated title
  is a permanent defect.
- Checked mechanically: `okf_gate.py` fails on an identifier-bearing source
  with no title. Rationale:
  `/home/{USER}/hermes-brain/docs/CITATION-WRITING.md`

## `raw/` — the immutable layer

The active wiki has a `raw/` folder for verbatim source material. **Never
edit a file in it.** The agent reads raw files and cites them; corrections
belong in the page that cites the raw file, not in the raw file.

Capture a source there before summarising it anywhere else:

| Source | Goes to |
|--------|---------|
| Web article, blog post, news | `raw/articles/` |
| PDF, arXiv paper, preprint | `raw/papers/` |
| Meeting notes, interview, call | `raw/transcripts/` |
| Image or diagram referenced by a source | `raw/assets/` |

Frontmatter is **not** the standard wiki block. A raw file records where
content came from, not how confident we are in it — it makes no claim of its
own, so it has no `confidence` to declare:

```yaml
---
source_url: https://example.com/article   # or the local path for a paste
ingested: 2026-09-30
sha256: <hex digest of the body below this block>
---
```

The `sha256` covers the body only — everything after the closing `---` — and
never the frontmatter, which would make the value self-referential and
permanently mismatched. Compute it on ingest:

```bash
python3 -c "import hashlib,sys; \
  t=open(sys.argv[1]).read(); \
  b=t.split('---',2)[2].lstrip('\n'); \
  print(hashlib.sha256(b.encode()).hexdigest())" <file>
```

On re-ingest of a URL already in `raw/`: recompute and compare. Same hash →
skip, the source has not moved. Different hash → the source changed upstream;
flag it and update deliberately.

Check drift across the whole folder at any time:

```bash
python3 /home/{USER}/hermes-brain/scripts/check_raw_drift.py
python3 /home/{USER}/hermes-brain/scripts/check_raw_drift.py --strict   # exit 1 on drift
```

**Never auto-repair a stored hash.** The hash is the only evidence that a raw
file changed; rewriting it destroys the finding. `--write` exists only to add
a *missing* hash on first ingest.

## Deduplication

- Hash new content and compare against existing pages
- If duplicate found, log it and skip ingestion
- If similar but not identical, create a new page with a cross-reference link

## Before writing: pass the schema gate

Never hand-write frontmatter from memory. After creating or updating a page:

```bash
python3 /home/{USER}/hermes-brain/scripts/okf_gate.py <file> --fix
```

It applies the canonical fields and enum values, and fails on defects a rule
cannot fix (broken link, invalid confidence). Fix those by hand or skip the
page — never force a write through.

- format authority: `/home/{USER}/hermes-brain/schemas/okf-schema.yaml`
- rules: `/home/{USER}/hermes-brain/schemas/WIKI-STANDARDS.md`

Do not restate the field list or the enums here. They are read from the schema at
runtime precisely so they cannot drift.

## Prospective Retrieval Indexing

When an important knowledge page is created or materially updated, add **retrieval cues**:
```yaml
future_cues:
  - alternate search term 1
  - alternate search term 2
future_scenarios:
  - situation where this would be relevant
```

These cues are not new facts — they are alternate ways future queries may refer to the same knowledge. Store them in the page's frontmatter.

## Salience Controls

Salience controls retrieval priority and hotness:
- `user_importance` — How important is this to the user?
- `unresolved` — Is there an open question here?
- `conflict` — Does this conflict with other knowledge?
- `novelty` — How new is this information?
- `active_project` — Is this tied to an active project?
- `risk` — What's the risk if this is wrong or missing?

Salience does NOT authorize deletion — only prioritization.

## Related Bundled Skills

- **`llm-wiki`** — For advanced wiki architecture (schema, index, log, provenance markers). Use when setting up a new wiki or restructuring an existing one. This skill provides the three-layer pattern (raw sources → wiki pages → schema) that makes wikis useful long-term.
- **`grounded-citations`** — For citation-backed research integrity. Use when ingesting sources that need verifiable provenance.
