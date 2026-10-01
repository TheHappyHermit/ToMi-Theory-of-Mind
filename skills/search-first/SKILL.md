---
name: search-first
description: >-
  Search the self-hosted stack before creating or fetching externally. Use when
  encountering a problem or needing information: check memory, then CamoFox →
  Firecrawl → SearXNG, and only then curl. Mandated order — do not reorder, do not
  substitute Playwright for curl, do not reach for web_search/web_extract while the
  self-hosted stack is up. Tavily is quota-exhausted and disabled.
platforms: [linux, macos]
tags: [search, research, camofox, firecrawl, searxng, process]
related_skills: [brain-search, graphify]
---

# Search-First Problem Solving

When encountering problems or needing information, search before creating.

## Search Priority Chain (MANDATORY — the operator's explicit order)

Use this EXACT priority order. This is the operator's mandated chain (corrected 2026-08-26 — he pushed back when curl was used as the default). Do not reorder, and do not substitute Playwright for curl.

1. **CamoFox** (self-hosted browser backend, `127.0.0.1:9377`) — **PRIMARY**. Navigate and READ pages with the browser tool.
2. **Firecrawl** (self-hosted, `POST http://127.0.0.1:3002/v1/scrape` with `{"url":"U","formats":["markdown"]}`) — SECOND.
3. **SearXNG** (self-hosted metasearch, `GET http://127.0.0.1:8080/search?q=Q&format=json`) — THIRD.
4. **Tavily** — **DISABLED this month** (quota exhausted). DO NOT USE until explicitly re-enabled.
5. **curl** raw page fetch — **LAST RESORT ONLY**.

Key rules:
- Camofox is FIRST, not curl. curl is the final fallback — never the default.
- Do NOT use `web_search` / `web_extract` (external internet) when the self-hosted stack is available.
- Because Tavily is out, the *effective* chain right now is: **Camofox → Firecrawl → SearXNG → curl**.
- For the live research profiles (`researcher`, `3090-researcher`, `5060-researcher`, `google-researcher`, `openrouter-researcher`, `oracle-researcher`), the chain is already baked into each profile's SOUL.md so it is automatic — do not re-instruct it per task. The `desktop-researcher` profile no longer exists live, so do not dispatch to it; see the `local-research-dispatch` skill for the current table.

## General Search Process

1. **Check memory first** — see if I've seen this exact issue before in past conversations
2. **Search with self-hosted tools** (CamoFox → Firecrawl → Playwright → SearXNG) before any paid API
3. **Search the internet** — look for GitHub issues, Stack Overflow, Reddit, forums where others have solved this
4. **Look for the official docs** — check upstream documentation, release notes, known issues
5. **Only then** try to solve it myself from scratch

This saves time, tokens, and prevents reinventing the wheel. The internet already has the answers — use them.
