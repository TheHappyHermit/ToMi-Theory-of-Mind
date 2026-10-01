# Research Quality Checker — Lessons Learned

## The Cron Script That Crashed And Lied

The `research_quality_check.py` script runs as a cron job, spot-checking research files for frontmatter validity, broken URLs, and contradictions. It crashed mid-run on the Oracle Brain vault — but `|| true` masked the crash as exit 0, so the cron reported success with only half the samples processed.

## Root Cause: Two Bugs Compounded

### Bug 1: Greedy Regex Captured Markdown Link Syntax

The regex `https?://[^\s\]]+` is too greedy. For markdown links `[url](url)`, the regex captures the second URL *including* the closing paren:

```
[github.com/hendrycks/test](https://github.com/hendrycks/test)
```

→ captures `https://github.com/hendrycks/test)` — trailing paren included.

YAML frontmatter can add trailing double-quotes:

```yaml
- LLM_EMBEDDING_BASE_URL=http://{LAN_IP}:8082/v1
```

→ captures `http://{LAN_IP}:8082/v1` (if the closing quote isn't stripped).

### Bug 2: InvalidURL Is Not a URLError

`urllib.request.urlopen` raises `http.client.InvalidURL: nonnumeric port: '8080)'`. The except clause only caught `(URLError, HTTPError, OSError)` — but `InvalidURL` is a subclass of `Exception`, not `URLError`. The exception was uncaught, killing the whole run.

## The Fix

```python
# Before:
except (urllib.error.URLError, urllib.error.HTTPError, OSError):

# After:
except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError, Exception):
```

Also fix the regex to strip trailing punctuation from URLs:

```python
# Before:
URL_PATTERN = re.compile(r"https?://[^\s\]]+")

# After:
URL_PATTERN = re.compile(r"https?://[^\s\]`\"']+(?<![).,!?'\"])")
```

## Orphan Page Repair Pattern

When the script reported 920 orphan pages (55% of the vault), the fix was:

1. **For leaf pages** — add a `## Related Pages` section after frontmatter with wikilinks to 2-3 sibling pages in the same directory. If no siblings, link to parent index.

2. **For index pages** — many index pages legitimately have 0 wikilinks (they're navigation hubs). These are expected, not errors.

3. **For imported archives** — add `## Related` links to same-directory siblings. The inbox/raw tree has many README.md files from Agent Zero imports that have no natural siblings — link to grandparent or nearest directory index.

The key rule: **never delete**, only add links. A disconnected page still has value; a deleted page is gone forever.

## Running the Fixed Script

```bash
python3 /home/{USER}/scripts/research_quality_check.py --source active-wiki --sample 30
python3 /home/{USER}/scripts/research_quality_check.py --source oracle-brain --sample 100
```

The script now handles malformed URLs gracefully and completes the full sample instead of crashing on the first bad URL.

## Related

- `scripts/research_quality_check.py` — the fixed script itself
- `references/web-research-methodology.md` — research methodology
- `templates/agenda.md` — research agenda template
