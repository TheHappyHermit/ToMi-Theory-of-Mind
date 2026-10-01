# Wiki Quality Gates — operator's guide

**Read this if:** you are setting up a new Hermes and want the wikis to
come up correct, you are about to change anything under `scripts/` that
touches the vaults, or something reported "green" and you do not believe
it.

If you only read one thing in this repo about the wikis, read
[WIKI-GOLD-STANDARD-STATE.md](WIKI-GOLD-STANDARD-STATE.md). It is the
running state of every phase, including what is NOT done. This file is
the how.

---

## The one-paragraph version

Two markdown vaults (`~/.hermes/active-wiki/` and
`~/.hermes/oracle/brain/`) are the knowledge base. Every file carries
YAML frontmatter conforming to `schemas/okf-schema.yaml`. Fourteen gate
scripts check that, and they are run before every commit. **Thirteen
pass. One is supposed to fail** — see the table below. If you find
yourself "fixing" a gate to make it green, you have broken the gate.

---

## Run everything

```bash
cd ~/hermes-brain
for s in verify_schema_integrity verify_schema_negative verify_schema_mirror \
         verify_citation_parser verify_body_gate verify_reclassifier \
         verify_frontmatter_fix verify_glued_delimiter \
         verify_frontmatter_gen verify_frontmatter_last \
         verify_state_file verify_embedding_probe verify_oversized_chunk; do
  printf '%-30s ' "$s"
  python3 scripts/$s.py >/dev/null 2>&1 && echo PASS || echo "exit=$?"
done
python3 scripts/verify_frontmatter_parses.py; echo "exit=$?  (1 is CORRECT)"
```

`precommit_guard.py` runs automatically on commit. It checks staging
area safety, not the vaults — the vaults are not in this repo.

---

## What each gate is for

Every one of these exists because a real defect got through at least
one other check. That is the only justification for a gate here.

| Script | What it proves | Why it exists |
|---|---|---|
| `verify_schema_integrity.py` | `okf-schema.yaml` is internally consistent (29 enums, 14 rules, 9 sections) | Schema was hand-edited and drifted |
| `verify_schema_negative.py` | Deliberately corrupt the schema, and the check **catches it** (8/8) | A check that cannot fail is not a check. This one proves the others can |
| `verify_schema_mirror.py` | The generated JSON mirror matches the YAML | The mirror was stale; two sources of truth disagreed |
| `verify_state_file.py` | The state file is valid YAML, 41 keys | The state file was **never** valid YAML, for its entire life |
| `verify_frontmatter_parses.py` | Every article's frontmatter is parseable YAML | `okf_lint.py` never called a YAML parser, so **391 broken files** passed as healthy for the whole project |
| `verify_frontmatter_fix.py` | The unquoted-colon repair preserved values (10/10) | Repair scripts can silently corrupt |
| `verify_glued_delimiter.py` | The glued-`---` repair moves only the delimiter (12/12) | That repair rewrote 207 files |
| `verify_frontmatter_gen.py` | Generated frontmatter asserts nothing it cannot derive (13/13) | Adding frontmatter to 134 files risks inventing values |
| `verify_frontmatter_last.py` | The six-rule repair preserves every value (22/22) | Three of those six rules were wrong on first write |
| `verify_citation_parser.py` | Citation parsing handles every syntax present (15/15) | Four syntaxes had never been seen; numbered *content* lists were parsed as footnotes |
| `verify_reclassifier.py` | DOI/arXiv classification is reversible (9/9) | An 8-worker rate-limit bug turned 4,145 results into "unrelated" |
| `verify_body_gate.py` | Content guards do not alter bodies (12/12) | Guards that "fix" a file by rewriting its prose |
| `verify_embedding_probe.py` | The embedding endpoint is reachable in all three API modes (5/5) | A bare run exited 1 claiming an unreachable host |
| `verify_oversized_chunk.py` | Oversized chunks truncate instead of failing forever (10/10) | A deterministic HTTP 400 was retried 5× and always failed |

### The one that must fail

```
verify_frontmatter_parses.py   ->  exit 1, lists 15 files
```

All 15 are `.meta/` maintenance logs (`ingestion-log.md`,
`maintenance-report-*.md`). Schema frontmatter on an ingestion log is
exactly the noise this project exists to remove, and `okf-schema.yaml`
already skips `.meta/`. **Do not add frontmatter to a log. Do not "fix"
the gate.**

---

## Setup prerequisites that are easy to miss

### The search index needs two env vars

```bash
export BRAIN_API_MODE=openai
export BRAIN_OLLAMA_URL=http://<host>:<port>
```

Without `BRAIN_API_MODE` the sync now tries `/v1/models` then
`/api/tags` and only fails if neither works. But the **cron job must
set it**, or it silently uses the wrong path. See `INSTALL.md` for the
full source-path table.

### The embedding server's context window is 2048 tokens

Anything longer gets a deterministic `HTTP 400`. `brain_sync.py` caps a
single chunk at 7,500 characters and logs:

```
[trunc] chunk of 41230 chars exceeds the embedding window;
        embedding the first 7500. Tail not indexed.
```

**If you see `[trunc]`, content is not searchable past the cut.** That
is a real loss of recall, not a cosmetic warning. Raise the cap only if
you have also raised the server's context window.

### The embedding dimension is deliberately 2000, not 2560

The server returns its native 2560 and **ignores** the `dimensions`
request parameter. `brain_sync.py` truncates to 2000 client-side,
because 2000 is the pgvector HNSW maximum. If you see a dimension
mismatch in the logs, that is this, and it is not a bug.

### `schemas/okf-queue.jsonl` is ignored but must stay on disk

`okf_repair.py` reads it at a fixed path, and a paused cron job reads
the same path. It is regenerated by the linter, so it is not in git —
but **do not move it.** It is not a stray file.

---

## Checking the index is actually current

The sync does not fail loudly. To prove a write end to end rather than
inferring it:

```bash
python3 scripts/brain_sync.py --source active-wiki     # single source
python3 scripts/brain_sync.py --report-orphans         # read-only
```

Then confirm in the database:

```sql
select source, count(*) as pages, sum(chunk_count) as chunks
from pages group by source order by 2 desc;
```

A large "never indexed" count in `--report-orphans` means content is
**missing from search** — a worse problem than duplicates.

**The sync never deletes pages.** There is no `DELETE FROM pages`. If a
file is moved, its page stays and stays searchable, indefinitely. This
is deliberate: pages are sometimes the only surviving copy. Decide what
to do about orphans yourself. There is intentionally no `--purge`. See
`docs/ORPHAN-PAGES-TODO.md`.

---

## Rules for writing a repair script here

These are not preferences. Each one exists because the alternative
shipped a bug.

1. **Parse the frontmatter with a real YAML parser.** `okf_lint.py`
   walks it with a regex and checks enum values, which is why 391
   syntactically broken files looked healthy. Never extend that pattern.
2. **Back up before every write**, and verify the body is byte-identical
   afterwards. Not "equivalent" — byte-identical, compared from the
   first heading.
3. **Never invent a value.** If a value is gone, drop the line and print
   the loss loudly. `fix_frontmatter_last.py` does this for
   `stale_af...[truncated]`.
4. **Write a control before you apply.** A control must assert the
   *value survived*, not that the file parses — a file can parse and
   have lost a key. Three rules in `fix_frontmatter_last.py` passed
   "does it parse" and had silently dropped or relocated data.
5. **Prove the control can fail.** `verify_schema_negative.py` exists
   only to demonstrate that corruption is detected. A control that has
   never failed has never been tested.
6. **Announce data loss, never do it quietly.** Truncation, dropped
   lines, and information you cannot recover all get printed.
7. **Do not add frontmatter to `.meta/`.** Those are logs.

---

## Where the state of the work lives

| File | What it holds |
|---|---|
| [WIKI-GOLD-STANDARD-STATE.md](WIKI-GOLD-STANDARD-STATE.md) | Every phase, what is done, what is NOT, and why. **The authority.** |
| `docs/CITATION-VERDICTS.md` | DOI/arXiv resolution outcomes |
| `docs/audit/confidence-rederivation.csv` | Confidence decisions, per file |
| [`archive/README.md`](../archive/README.md) | What is deliberately not in git, and why |
| `SCRATCHPAD.md` | Working notes, owner-set research rules |
