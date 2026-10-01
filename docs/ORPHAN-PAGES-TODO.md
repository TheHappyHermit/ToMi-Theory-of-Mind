# Orphaned brain pages — what they actually are

**RESOLVED 2026-09-27.** The 161 pages whose only copy was the database have
been written back to markdown files in `~/.hermes/active-wiki/`. See
"Resolution" at the bottom. Nothing was deleted at any point.

## Resolution

the operator chose to export **only the 161 that existed nowhere else** — the
smallest change that stops content living in a database alone. The 192 that
also exist in the Oracle vault were left there.

    wiki files:      452 -> 613   (+161)
    orphaned pages:  419 -> 259

Verified, not assumed:

    161 files written, all with real content
    0 empty, 0 suspiciously small
    frontmatter intact (okf_version, id, title, type, dates, tags)
    md5 of file == md5 of database content, byte-identical

Where the 259 remaining orphans stand:

    192  non-archive, every one has a copy in ~/.hermes/oracle/brain
     66  _archive/inbox-stale-2026-08-30/ -- retired Aug 2026, left alone
      0  pages that exist nowhere on disk

Backups taken before writing anything:

    ~/.hermes/cache/scratch/export-backup-20260927-221408/
      active-wiki-before.tar.gz   4.2M
      pages-data.sql              51M

The export tool is `~/.hermes/cache/scratch/export_orphans.py`. It previews
by default and only writes with `--write`; it never overwrites an existing
file, reports collisions instead of resolving them, and skips `_archive/`.

## Short version

The 161 are **real, complete, finished documents** — decisions, concepts,
research reports. Not fragments, not junk, not expired. They read like a
normal wiki. The only thing wrong with them is that the *file* is gone from
one folder while the *content* survives in the database.

## What one actually looks like

`decisions/brain-sync-llamacpp-fix.md`, in full from the database:

    ---
    okf_version: "0.2"
    id: brain-sync-llamacpp-fix
    title: "brain_sync.py — llama.cpp API Compatibility Fix"
    description: "Verified fix: brain_sync.py was failing because it used
      Ollama-specific API paths (/api/tags, /api/embed) against a llama.cpp
      server which uses OpenAI-compatible paths (/v1/models, /v1/embeddings)."
    type: decision
    status: current
    created: 2026-09-07
    updated: 2026-09-12
    tags: [decision, brain-sync, llama-cpp, ollama, api-compatibility, bug-fix, verified]
    confidence: high
    generated:
      by: "hermes-agent"
    verified:
      - by: "hermes-agent"
    stale_after: 2027-03-12
    ---

    # brain_sync.py — llama.cpp API Compatibility Fix

    ## Verified Fact
    The `brain_sync_cron` (job `50fd04244451`) was failing 5+ runs in a row
    because `brain_sync.py` used **Ollama-specific API paths** against a
    **llama.cpp** server.

A well-formed document: frontmatter, tags, verification metadata, body text.
Dated within the last three weeks.

## Sample titles from the 161

    concepts/autognosia-build-plan.md          Autognosia Consolidated Build Plan
    concepts/belief-revision-ai-agent-memory.md
                                               Belief Revision Theory for AI Agent Memory Systems
    concepts/continuity-acle-mcp-integration.md
                                               CONTINUITY + ACLE-MCP Integration Architecture
    concepts/dashboard-deployment.md           Dashboard deployment pattern: GitHub → local venv → port 8088
    concepts/decision-logger.md               Decision Logger plugin for Hermes Agent
    concepts/graph-collapse-recovery.md        Graph Collapse and Recovery
    concepts/graphify-wiki-extraction.md      Graphify Wiki Extraction Best Practices
    concepts/hermes-credential-pool.md        Hermes Credential Pool Strategies
    concepts/hermes-gateway-hooks.md          Hermes Gateway Hooks
    concepts/llamacpp-v100-bare-metal-server.md
                                               llama.cpp on bare metal with V100: home server GPU inference pattern

Type breakdown across all 800 active-wiki pages (the 161 are mostly
`research` and `decision`):

    research_report 460   research 135   reference 51   decision 30
    index 21   system 20   evergreen 19   temporal 12   idea 7
    entity 7   concept 6   log 5   person 3   project 2

Dates span **2026-09-10 to 2026-09-27**. The newest is days old.

## Reading one yourself

    docker exec brain-postgres psql -U brain -d brain -tAc \
      "SELECT content FROM pages WHERE source='active-wiki' AND slug='<slug>';"

## The situation

PostgreSQL holds 800 `active-wiki` pages. 381 `.md` files are live in
`~/.hermes/active-wiki`. Comparing slug lists:

    in DB but not on disk ......... 419   <- these
    on disk but not in DB ......... 0     <- nothing is missing from the DB

`brain_sync.py` has no `DELETE FROM pages` — its only DELETEs are chunk-level.
So pages for files that were moved or removed are never reaped. They stay in
the database and stay searchable.

## What the 419 are NOT

They are NOT expired, and expiry is NOT being proposed. Nothing in the sync
expires or deletes wiki content, and nothing here will.

Some of these documents carry a `stale_after: 2027-03-12` field in their own
frontmatter. That is a field inside the document, not a system deleting them.

An earlier read of this situation was wrong: the path mismatch was taken as
evidence the content was disposable. It is not. The database copy of
`concepts/brain-sync.md` is dated 2026-09-10; the file on disk is 2026-09-09.
The database is NEWER. It is a valid copy of a file that moved to
`~/.hermes/oracle/brain`. Deleting these would have destroyed real content.

The cause is that the wiki was reorganised and content moved to
`~/.hermes/oracle/brain`. The database kept the old path entries, and the
absence of a page-level DELETE means they were never reaped.

## The breakdown that matters

    161  exist nowhere else on disk
         The database is their ONLY copy. Checked against the oracle vault,
         wiki.bak-20260816, bak_autognosia, and the OpenClaw vault: zero
         matches. Losing these means losing the content.

     66  under _archive/inbox-stale-2026-08-30/
         Deliberately retired in August 2026. Probably safe to drop from the
         database, but that is your call, not mine.

    192  other — exist in ~/.hermes/oracle/brain under the same relative path

Examples of the 161 (none exist on disk anywhere):

    decisions/brain-sync-llamacpp-fix.md
    decisions/desktop-gpu-split-decision.md
    decisions/research-lanes-resumed.md
    concepts/llm-guardian-ambiguity-taxonomy-concept.md
    research/automated-dependency-extraction-benchmark.md
    research/band1-agency-schema-provenance.md
    ... 156 more

## The 66 `_archive/` pages — where else do they exist?

Checked 2026-09-27, because they were the one group I could not characterise.

    all 66 exist in ~/.hermes/oracle/brain at the same relative path
    0 exist in the active wiki directory
    also present in old backups:
      ~/wiki.bak-20260816        108 files under an _archive path
      ~/bak_autognosia           175 files under an _archive path

**So they are not lost, and they are not orphaned content.** Every one has a
file in the Oracle vault. They show up as "orphans" in `--report-orphans`
only because the report compares the database against the Active Wiki
directory, and these pages were never in it.

### But they are NOT exact duplicates

Comparing SHA-256 of the database content against the Oracle file:

    byte-identical:  15
    DIFFERENT:       51
    missing:          0

The difference is small and systematic. The Oracle files carry a `## Related`
block that the database copies lack:

    --- ORACLE (on disk)          +++
    @@ -15,9 +15,2 @@
     ---
    -
    -## Related
    -
    -[[military_radio_expert]]
    -[[dump1090]]
    -[[HARDWARE_INVENTORY]]
    -
     # GNU Radio: Software-Defined Radio Framework

`gnuradio.md`: 73,168 chars on disk, 73,087 in the database — an 81-char
difference, exactly the `## Related` block. Same pattern in
`osint_free_apis.md` (18,574 vs 18,493) and the others.

**Conclusion: the database copy is the older of the two**, and the Oracle
files were enriched with wikilink back-references after the database was
populated. Nothing is lost either way, but the 51 non-identical pages are not
safe to treat as disposable duplicates — the richer copy is the one on disk.

If these are ever cleared from the database, the Oracle vault copy is the one
to keep, and 51 of them carry content the database never had.

## Options for the 161

1. **Export to files** — write them back to `~/.hermes/active-wiki/` at their
   original paths, so they are files again and the DB and disk agree. This is
   the only option that loses nothing.
2. **Keep DB-only** — they stay searchable, nothing on disk. Fine as long as
   nobody treats the filesystem as the source of truth.
3. **Delete** — only for the 66 archived ones, and only if you agree they are
   genuinely retired.

## Also worth doing

DONE 2026-09-27 — `brain_sync.py --report-orphans` now prints this, read-only:

    python3 scripts/brain_sync.py --report-orphans

The session is genuinely read-only, not just labelled that way: it opens a
transaction and runs `SET TRANSACTION READ ONLY`, because pg8000 autocommits
and a bare `SET` was a no-op. Verified by attempting a DELETE inside the same
session — PostgreSQL refuses with `25006 read-only transaction`.

## Second finding: 633 oracle-brain files have never been indexed

The same report shows the opposite problem in `oracle-brain`:

    files on disk:      2102
    pages in DB:        1470
    never indexed:       633

633 files exist on disk and have never made it into the database. Newest file
on disk is dated 2026-09-27 21:41 — today. And `sync_state` has no row for
`oracle-brain` at all, so it appears never to have been synced by the cron job.

`brain_sync_cron.py` only syncs `["active-wiki", "exchange-research"]`.
`oracle-brain` is commented as "excluded, handled by separate monthly job"
— and that job either is not running or has not succeeded. This is a bigger
gap than the 419 orphans: that is content missing from search, not extra.

## Rollback note

`~/pgbackups/` holds a logical dump and a volume archive from the PG18
migration. Either can restore these pages if something goes wrong.
