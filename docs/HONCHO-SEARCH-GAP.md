# Honcho search does not cover anything before 2026-09-28

Added 2026-09-28. Found while investigating why the Weekday Prompt-Me job
believed we had not spoken for 13 days.

## The summary

The conversation is **not lost**. Every message from 2026-09-13 to 2026-09-27
is in the Honcho database in full text, continuously, with no gaps.

What is broken is **retrieval**. `honcho_search` and `honcho_reasoning` return
nothing for that window, because those tools are semantic and the messages
have no embeddings.

## The data is there

    docker exec honcho-database-1 psql -U honcho -d honcho

    day     | messages
    --------+----------
    2026-09-13 |    192
    2026-09-14 |    168
    2026-09-15 |    100
    2026-09-16 |     40
    2026-09-17 |     56
    2026-09-18 |     70
    2026-09-19 |    140
    2026-09-20 |     70
    2026-09-21 |     60
    2026-09-22 |     64
    2026-09-23 |     53
    2026-09-24 |     48
    2026-09-25 |    184
    2026-09-26 |    252
    2026-09-27 |    162
    2026-09-28 |     98   <- today, and the only searchable day

1,659 messages for 13-27, 316 KB of text, verified by reading excerpts.

## Why search returns nothing

Embedding coverage for the same window:

    day     | msgs | embedded
    --------+------+---------
    2026-09-13 |  192 |        0
    ...
    2026-09-27 |  162 |        0

Zero for every day except today. The deriver is not processing them.

## Why the deriver is not processing them

Two errors, both from `honcho-deriver-1`, 941 occurrences in the log:

    src.exceptions.ValidationException: Missing API key for openai model config
    openai.BadRequestError: request (5780 tokens) exceeds the available
      context size (2048 tokens)

The deriver is configured for an `openai` model config it has no key for, so
every representation batch fails. A second, separate failure is a context
window problem: a request of 5,780 tokens against a 2,048-token limit. Both
retry three times and give up. The container is up (0 restarts) and looks
healthy, so nothing surfaces the failure -- it is a hot retry loop, not a
crash.

`active_queue_sessions` is empty and the deriver is idle-but-failing, which
is why the peer context still shows a correct card and recent messages: that
comes from the last successful pass, not from the queue.

## The immediate fix

`scripts/export_honcho_window.py` writes the window to plain markdown, one
file per day, with a manifest:

    python3 scripts/export_honcho_window.py --start 2026-09-13 --end 2026-09-28

Done on 2026-09-28. Output: `~/.hermes/archives/conversation-export/`,
1,659 messages, 316 KB, 15 daily files plus `EXPORT-MANIFEST.json`.

This is a safety copy, not a repair. It exists because the only working
retrieval path for that window is direct SQL, and that is not something to
rely on for the long-term record.

## The real fix, not yet done

The deriver needs a model config it can actually reach. Either supply a key
for the `openai` config, or point the deriver at a provider already reachable
from this host. The 2048-token context failure suggests the configured model
is also the wrong size for the work, so both need changing together.

Until then: do not trust `honcho_search` or `honcho_reasoning` for anything
before today. Use the export, or query the database directly.
