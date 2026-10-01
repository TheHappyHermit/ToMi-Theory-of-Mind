# Two jobs read the wrong data

Added 2026-09-28. Both diagnosed by reading the code and the stored data, not
by inference. No cron prompt was rewritten yet -- these are the findings.

## 1. Weekday Prompt-Me: "we haven't spoken in 15 days"

Job `ab26e06eee12` reported that the last real conversation was 2026-09-13.
the operator had been talking to Hermes daily, most recently the night of 2026-09-27.
The job's conclusion was wrong, and the reason is structural.

### The transcript archive stops on 2026-09-20

    ~/.hermes/archives/sessions/   1266 sessions
    oldest  2026-04-04_20260402_080502_26f3c46c
    newest  2026-09-20_cron_eba297436736_20260920_023008
    today   2026-09-28

Nothing from 2026-09-21 onward. Eight days of conversation -- including every
exchange since the migration work started -- are not in the archive at all.

### sessions.json is a legacy mirror holding one session

    ~/.hermes/sessions/sessions.json
    keys: ['_README', 'agent:main:telegram:dm:1234567890']
    _README: "LEGACY MIRROR of the gateway routing index (the primary copy
              lives in the gateway...)"

One real session. Its mtime is 2026-09-27 12:47, so it is being written to --
but it holds a single conversation, not a searchable history. Anything that
greps this file for "recent sessions" sees one thread and nothing else.

### sessions.db is empty and stale

    ~/.hermes/sessions.db   0.0 MB   mtime 2026-08-24   no tables

### Why the job concluded "13-15 days"

It reported "September 13". The nearest real data points are 2026-09-12
(the newest .jsonl in ~/.hermes/sessions/) and 2026-09-20 (the newest
archive). Neither is 09-13, so the job did not read a date from a store at
all -- it appears to have reasoned from a partial view, or from a session
listing that omits live sessions.

### What this needs

The live-session store needs locating, and either the archive job needs to
resume or the prompt needs to read the gateway's own index. Until then this
job cannot be trusted to know when we last spoke, and that is exactly the
kind of question it exists to answer.

Do not point it at ~/.hermes/archives -- that path is 8 days stale and
getting staler.

## 2. Morning Newsletter: the wrapper, not the article

the operator reported "headers and footers on top of everything" and no sense of what
was happening in the news.

### The generated file is clean

    ~/.hermes/cache/scratch/newsletter_20260928060443.txt   32 lines
    wrapper markers inside: 0

No "Summary:", no "Articles Processed", no "Model Used", no file paths. The
newsletter itself is well formed: a title, a timestamp, and three section
headings with one-line stories.

### The wrapper is the cron response

What arrived in Telegram was the agent's reply to the cron prompt, not the
newsletter. The prompt is:

    Run ~/.hermes/newsletter_venv/bin/python3
    ~/.hermes/scripts/newsletter_builder.py and deliver the result via
    Telegram.

The job runs the script, which writes a .txt, and then the *agent* narrates
what happened. The result of that narration is what got delivered:

    "The newsletter has been successfully generated and is ready for
     delivery."
    "Newsletter Summary:"
    "Articles Processed: 50 (23 had extractable content)"
    "Model Used: openrouter/auto -> deepseek-v3.2:free"
    "The newsletter text has been written to /home/.../newsletter_...txt"

So the "headers and footers" are the agent's status report wrapped around a
newsletter that was never sent. The article text exists on disk and is fine.

### The 23-of-50 figure is also a real bug, and is now fixed

Confirmed in code, fixed in this change:

- `fetch_unread_articles_ip_direct()` returned `filtered_items[:max_articles]`
  -- 50 candidates, cut before extraction. Failures were then dropped with no
  replacement, so 50 candidates yielded 23 articles.
- The "waterfall" had two stages. Its last one stripped tags off the whole
  document, keeping nav, footer and cookie banners, which is how operating
  boilerplate reached the summariser.
- The 4-stage version in the skill (Playwright, FlareSolverr, Wayback) was
  never implemented in the script.

After the fix, a live run reported:

    Found 131 non-sports articles
    50 extractable articles from 71 attempts
    extraction methods: {'freshrss': 32, 'trafilatura': 17, 'summary_fallback': 1}

71 attempts for 50 articles, versus 50 attempts for 23 before.

## Recommendation

Make the newsletter job `no_agent` so stdout is delivered verbatim, the same
way the staleness watchdog works. A job that must produce prose about its own
output will keep producing prose about its own output.
