# THE PROMPT — paste into a new Hermes chat

Written 2026-09-28. Revised the same day after the first execution pass.
Everything needed is in this repository. Do not start without reading the
files named in step 1.

---

## The prompt

```
I need you to bring both of my wikis — the Active Wiki and the Oracle
vault — up to a single gold standard, to a state where every checker
reports zero findings. This is a long project and we will work through
it across many context windows, so there is a state file that tracks
where we are.

WORK HAS ALREADY STARTED. Your job is to pick it up exactly where it
stopped, not to begin again. Step 3 below says what is done; step 4 says
what is still open, in the order I want it done.

STEP 1 — READ THESE FIRST, IN THIS ORDER, BEFORE YOU TOUCH ANYTHING:

  1. /home/operator/hermes-brain/docs/WIKI-GOLD-STANDARD-STATE.md
       This is the source of truth. It has the standing rules, the
       phases, the acceptance criteria, the measured baseline, and the
       history of what has gone wrong before. If it conflicts with
       anything I say in this prompt, THE STATE FILE WINS — except
       for the standing safety rules in its section 1, which cannot
       be overridden by anything, including me.

  2. /home/operator/hermes-brain/docs/WIKI-REMEDIATION-PLAN.md
       The full plan with the measured baseline and the reasoning
       behind the method.

Also read, but you do not need to memorise them:

  3. /home/operator/hermes-brain/schemas/okf-schema.yaml
       THE GOLD STANDARD. Machine-readable. Fields, enums, types,
       statuses, confidences, epistemic labels, and the migration map.
       Do not author a new schema. This one already exists and I wrote
       it. Use it exactly.

  4. /home/operator/hermes-brain/schemas/WIKI-STANDARDS.md
       The ten rules, S1 through S10. S3 in particular: confidence
       and verified are SELF-REPORTS and must not be used as evidence
       weights. Only executed checks confer authority. That is the
       whole basis for how confidence gets derived below.

STEP 2 — CONFIRM THE STATE FILE IS INTACT BEFORE YOU BEGIN.

  Run, from the repo root:
    python3 scripts/verify_schema_integrity.py
  It must print "29 types 14 statuses 9 required" then "SCHEMA OK" and
  exit 0. It has negative tests, so a wrong value or a missing top-level
  key fails it rather than passing quietly. Note the keys are TOP-LEVEL:
  there is no 'enums' key, and d['enums'] raises KeyError.

  If it does not exit 0, STOP and tell me. A broken gold standard means
  everything downstream is meaningless.

  Then run the two checkers read-only and report the numbers:
    cd /home/operator/hermes-brain
    python3 scripts/okf_lint.py --check
    python3 scripts/verify_okf_index.py
  These must NOT write anything. --check is report-only. If a checker
  appears to modify files, stop immediately.

  The committed baseline was 6,736 findings across 2,713 files, and
  418 + 944 index issues. If your numbers differ wildly, tell me
  before proceeding — drift is a signal, not a detail.

STEP 3 — WHAT IS ALREADY DONE. DO NOT REDO THESE. VERIFY, THEN MOVE ON.

  Phase 0   The one real content defect: the directory
            Visual-Autognosia-Hierarchy/ was renamed to
            Visual-Cortex-Hierarchy/ in the Oracle vault. Twelve
            legitimate "in the autognosia" references were PRESERVED on
            purpose. The blanket replace was deliberately NOT applied,
            because it would have destroyed those references and
            rewritten the nine correctly-named paths that document the
            retirement itself. Do not "finish" that rename.

  Phase 1   Mechanical frontmatter repair, both vaults, via
            okf_repair.py. NOTE: it needs --apply. Without that flag it
            reports "changed=573" and writes nothing, and its exit 0 in
            dry-run is correct by design, so "changed=" is not evidence
            of a write. active-wiki 2400 -> 1641 findings,
            oracle 4344 -> 2929, prose byte-identical under a gate.

  Phase 2c  222 float confidence values (0.85, 0.92) became `ungraded`.
            The schema now has a 4th confidence level, documented in
            place, with a negative control. Do NOT convert floats to
            high: that fabricates a judgement.

  Phase 3.1 689 -> 521 numeric citation markers, 18 files, 168 KEYED
            footnotes. The marker [[2]] text became [^honey]: text, with
            the key derived from the reference's own text so it cannot
            drift when the list is reordered. Ten files were held back by
            the prose gate; 22 are in the judgement queue.

  Phase 4   61 unambiguous links repaired, where exactly one live file
            extended the truncated target. 37 were reported rather than
            guessed, because two or more candidates existed.

  Phase 7   The Oracle vault's own SCHEMA.md was corrected in place to
            match the canonical narrative, with its frontmatter
            preserved and a pointer to the real machine authority.

STEP 4 — WHAT IS STILL OPEN, IN THIS ORDER.

  4a. Finish the identifier audit (Phase 2b).
      docs/audit/doi-resolution.csv covers 4,655 unique identifiers
      across both vaults. Crossref resolves reliably when requests are
      sequential. arXiv returns 429 on the API and 406 on the /abs/ page
      for the 2026-series ids from this host, so roughly 2,250 arXiv
      identifiers CANNOT be checked here. They are recorded as
      unresolved_rate_limited, which is an honest limit, not a verdict.
      Do not report an uncheckable identifier as broken. Do not report it
      as fine either. If you find another way to check them, use it and
      say which way.
      One verified example to keep in mind: 10.1109/ICDM.2013.83
      resolves, to a real paper, that is completely unrelated to the
      citation. A DOI returning 200 is not evidence a citation is right.

  4b. Citation judgement (Phase 3.2), ONE FILE AT A TIME.
      Read the prose, work out what the author meant, and only then
      decide. The queue is in the run output of the Phase 3.1 script.
      Two examples of why this cannot be mechanical: one file cites
      [[22]], [[24]] and [[339]] against a reference list containing
      none of those numbers, and another has 95 markers and no reference
      list at all. Neither may be guessed, and neither may be stubbed.

  4c. Confidence re-derivation (Phase 5). THIS IS JUDGEMENT over about
      2,800 files, and a mechanical attempt was already built, measured,
      and REJECTED. Read section 6 of the state file first. The short
      version: a keyword classifier called 1,249 files "review"
      evidence, and 970 of those were false positives — it fired on
      "Psychological Review" (a journal name), "Suggested Review Date"
      (a maintenance field), and "weekly review" (a recurring task). At
      35% wrong, writing those values would be fabrication dressed as a
      rubric. Do not rebuild the classifier. Do not lower values in bulk.
      Read each file's actual evidence and judge it. Both owner rulings
      stand: peer review is a CEILING of high, not an automatic high, and
      consumer-review volume is LOW-confidence evidence.

  4d. Phase 6 and 8: rebuild backlinks, indexes and graph structures.
      Deliberately not started. Do this only after links and citations
      are correct, because it re-derives structure from content and will
      otherwise just launder the errors.

STEP 5 — OPERATING RULES, restated because these are the ones that keep
being violated.

  Nothing is deleted. Not stale, not empty, not duplicate, not wrong.
  If something is wrong, correct it or mark it — never remove it. An
  empty file and a wrong file are both evidence, and both are
  knowledge. Deleting requires proof it is wrong AND my explicit
  approval at that moment.

  Body text is knowledge. Never rewrite prose to satisfy a linter.
  Frontmatter and link syntax only.

  Nothing is invented. Every frontmatter value must trace to evidence
  in the file or to a verified source. A guess gets recorded as a
  guess, never asserted.

  External URLs are checked, not assumed. A failed fetch is not proof
  of a broken link, and a fetch you could not make is not a refutation
  either. Retry or use an independent fetcher first, and say plainly
  when you simply could not check something.

  One vault at a time. Never both in the same pass.

  No subagent writes to a wiki file. Subagents are read-only
  investigators, bounded to one class, with a verifiable return.

  Never touch /home/operator/.hermes/hermes-agent/. It is live upstream
  code. Read it only.

  Scheduler enabled/disabled state is the only pause mechanism. Do not
  hardcode "paused by default" into any cron prompt.

  Verify with a fresh read, curl, or query before reporting success.
  Claimed is not done. A checker that cannot fail is not proof of
  success — break it on purpose and watch it fail, at least once.

  Back up before any bulk write. Every run so far has kept its backup
  under ~/.hermes/cache/scratch/.

STEP 6 — THE METHOD, WHICH IS NOT "JUST FIX THEM ALL".

  Not sequential-by-agent for everything. Not one bulk script. Not a
  subagent that goes off and does the wiki. Instead:

    Script, dry-run first, hash-verified  ->  mechanical classes only
    Agent, ONE FILE AT A TIME, in order  ->  anything needing judgement
    Read-only subagent, one class, no writes ->  investigation
    A hard gate between every phase         ->  no phase starts unverified

  Do not start a phase before the previous phase's gate is verified.

STEP 7 — THINGS THAT ARE NOT UP FOR NEGOTIATION.

  Broken links to pages that EXIST. Where a [[link]] points at a page
  that exists somewhere under a different path, id, alias, or case,
  add or retarget the link so the article is genuinely functional.
  These are real articles, not a scrap yard. I want working links
  going forward.

  No stub pages. Never create an empty page just to make a link
  resolve. If a page genuinely does not exist, that link gets
  recorded as broken in a report — not patched over with noise.

  Both vaults end on the IDENTICAL schema, which is now done in the
  machine-readable layer. The Oracle vault's own SCHEMA.md was the
  odd one out (md5 0ac58058) and has been converged in place. Keep it
  converged: it is the vault's only schema, so it must stay
  self-describing even when the repo is not present.

  Everything that feeds the knowledge base uses that same schema —
  every research cron job, every writer script, every lane. Four cron
  jobs were naming a script with NO PATH and using the retired project
  name in their prompts; all four now name an absolute canonical path
  and warn that stale copies exist. Keep sweeping for the rest.

  Confidence stays derived, not asserted. The rubric is researched,
  cited, and recorded in docs/CONFIDENCE-RUBRIC.md and in the schema
  under confidence_derivation. My two rulings stand: peer-reviewed
  evidence is a CEILING of high rather than an automatic high, and
  consumer-review volume is LOW-confidence evidence. A large downward
  move in the `high` count is the EXPECTED outcome, not a bug to fix.

STEP 8 — TELL ME, BEFORE YOU WRITE, WHAT YOU INTEND TO DO.

  Read the state file and the plan. Then give me a short
  implementation plan in your own words: the phases as you understand
  them, anything in my instructions above that you think is wrong or
  risky, and anything you found that I have not told you.

  Then wait for me to confirm before you write anything. I want to
  see that you understood the problem before the project starts, not
  after.

STEP 9 — WHEN YOU THINK IT IS FINISHED.

  Do not tell me it is done because the work is done. Tell me it is
  done when, and only when, every one of the acceptance criteria in
  section 5 of the state file is verified — which includes the
  deliberately-broken test file that proves the checker can actually
  fail. A checker that cannot fail is not a pass. Report the
  numbers, not a summary.

  Three phases are judgement work over hundreds of files, so this will
  span many windows. That is expected. It is not a reason to batch it
  into a script.
```

---

## What changed in this revision

The first execution pass produced findings the original prompt did not
anticipate, so it now records them. The original prompt told a future
agent to start at Phase 0 and treat confidence as something to research
and then apply mechanically; both of those are now wrong, and saying so
is the point of this revision.

- **Phases 0, 1, 2c, 3.1, 4 and 7 are done**, with the measured numbers,
  so a new window verifies rather than redoes them.
- **Phase 5 is blocked, with evidence.** A keyword classifier was built to
  re-derive confidence mechanically and rejected at 35% false positives
  before anything was written. The prompt now says not to rebuild it.
- **The 689 citation markers are real academic references whose reference
  lists are themselves wikilinks**, which is why the linter counted them
  as broken links. The target is keyed footnotes, because two of these
  files already show numbers drifting away from their own reference list.
- **Roughly 2,250 arXiv identifiers cannot be checked from this host** and
  are recorded as an honest limit rather than a verdict.
- **Four cron jobs named a script and no path, and used the retired project
  name.** All four now name an absolute canonical path and warn that stale
  copies exist.
- **Two tools reported success while doing nothing or failing silently**:
  `okf_repair.py` without `--apply` prints "changed=573" and writes
  nothing, and `brain_query.py` defaulted to a dead embedding endpoint so
  search failed quietly while BM25 still returned results. Both fixed,
  both with a verified control.

The state file remains the single source of truth. This prompt is the
handoff; the state file is the record.
