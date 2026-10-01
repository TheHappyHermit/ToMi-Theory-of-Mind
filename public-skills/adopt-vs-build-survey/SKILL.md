---
name: adopt-vs-build-survey
description: Use when surveying prior art to adopt, extend, or link.
version: 1.0.0
author: Hermes Agent
license: MIT
---

# Adopt vs Build: Surveying Existing Prior Art

Use when asked to look at what other people have already built in some
domain and decide whether to adopt it, extend ours, or just link to it.

## Order of operations

### 1. Establish the decision criterion BEFORE the survey

The single most expensive mistake is surveying first and asking what the
user optimizes for afterwards. Ask one question up front:

> Self-hosted personal use only, or does this need to ship / be monetised?

The answer inverts the ranking, and getting it wrong wastes the whole
survey.

- **Self-hosted, personal, no monetisation** → **copyleft (AGPL/GPL) is a
  non-issue.** It binds redistribution; there is none. Say this explicitly,
  because a user hearing "AGPL" without that context assumes a blocker that
  does not exist. Treat AGPL and MIT as equally usable.
- **Shipping in a product or SaaS** → copyleft genuinely constrains
  architecture; viral licences need a deliberate decision.
- **No licence at all** → all rights reserved by default. Fine privately, a
  blocker for redistribution. Name which case you are in.

**For a self-hoster the real blocker is almost never the licence — it is
whether the thing makes a metered API call.** Rank on that instead.

### 2. Survey (delegate if wide)

Dispatch subagents per candidate class. Require every entry to return:
GitHub URL, star count, last-commit date, licence, **and whether real code
exists**. Insist on the last one — see the trap list below.

### 3. Prove the cloud-dependency question from source, not the README

Shallow-clone each shortlist repo and grep the source. A README can promise
Ollama/local support while the code hardcodes an API key.

```python
import os, re, subprocess, tempfile

LOCAL = re.compile(r'ollama|localhost|127\.0\.0\.1|base_url|vllm|'
                   r'llama\.cpp|OpenAI\(|LMStudio', re.I)
CLOUD = re.compile(r'openai\.OpenAI\(|anthropic\.Anthropic\(|'
                   r'api\.openai\.com|api\.anthropic\.com', re.I)
```

Count matches per repo and report both. A project that calls
`from_pretrained` / `AutoModelForCausalLM` is **fully local** even if a
narrow grep for `openai.OpenAI(` finds nothing — check the model-loading
path, not just the client-construction path, before calling anything
cloud-bound.

`from_pretrained` ⇒ local weights. `base_url` / `localhost` / `ollama` ⇒
local endpoint. Plain `OpenAI(api_key=...)` with no override ⇒ metered.
No LLM call at all (pure logic, formal methods) ⇒ nothing to pay for, ever.

### 4. Verify every claim about your own code before repeating it

Subagent reports about YOUR codebase are claims, not evidence. Re-read the
source before relaying "never written" / "not implemented" / "empty" — cheap
to check, and a false "this is dead code" invites deleting something
load-bearing. Widen the grep with a different root/pattern once before
accepting any negative.

## Trap list

These recur and each one has produced a confidently wrong answer:

- **Star count is a bad quality signal in fast niches.** Everything above
  a few hundred stars can be a prompt collection, a coding-agent plugin, or
  docs with no source. Judge on small repos that contain real code.
- **Check the default branch actually has code.** At least one very
  high-star repo's `main` was a dozen files — README, LICENSE,
  CONTRIBUTING, and nothing else. `git clone --depth 1`, count source files.
  Do not plan around a repo you have not confirmed ships code.
- **Guessed owner/repo paths 404.** Derive the URL from a search result or
  the API; never construct one from memory and report it.
- **Zero files found may mean the wrong language.** Kotlin/Java repos and
  TS-only repos look "empty" to a `.py` walker. Count by actual extensions
  before concluding anything.
- **Non-emptiness is not the property you need.** See the verification note
  below.
- **A silent helper swallows failures.** A clone helper returning `''` on
  non-zero exit makes nine good repos look broken. Capture and print
  `stderr`/`returncode` so a failure is visible instead of inferred.
- **Marketing claims can be empty.** Repos describing themselves as
  "state of the art" have been found containing a single README and zero
  code. Verify via the contents API.

## Do not recommend deleting thin modules because they look thin

Survey results often say "X is a placeholder, fix or delete." Record the
finding; do not execute the deletion. Neuroscience-inspired architecture work
shows that under moderate load, most ablations look costless and only reveal
their contribution under stress — apparent inertness at low load is not
evidence of uselessness. A module can also be wired up by a caller the
survey never read.

## Verification note

When verifying extractor/matcher fixes, assert the **end-to-end property**
(extract → normalise → compare), not a weak proxy. Asserting a value is
non-empty passes while the real defect is that it normalises to nothing
downstream — the failure lives in the handoff between stages where no single
stage looks wrong. And require **keep-cases alongside drop-cases**: a rule
that deletes real data is indistinguishable from a correct one until a
keep-case exists.

## Numbers must reconcile

Before reporting counts, confirm each unit still exists. A CSV generated
before a bulk move/delete keeps listing stale rows; the gap between "N rows"
and "N reachable rows" is the finding — report both. When counts disagree,
check the timeline of what you deleted before inventing a mechanism: the
mundane explanation (files you removed yourself) is usually right, and
asserting a code bug first burns cycles and erodes trust.

## Reporting shape

Lead with the decision table, one row per candidate, sorted by fit for the
user's stated criterion. Then: what each option does that you do not, and
what is genuinely missing in your own implementation. Then the honest
caveats. Do not lead with the survey narrative.
