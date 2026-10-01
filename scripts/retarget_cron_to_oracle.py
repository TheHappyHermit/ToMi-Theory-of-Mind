#!/usr/bin/env python3
"""Point the research cron jobs at the Oracle wiki instead of active-wiki.

the operator: "I want all of the research cron jobs pointed at the Oracle wiki
instead of the active wiki."

WHAT THE AUDIT FOUND, WHICH CHANGES WHAT THIS DOES
All six research lanes ALREADY write their deliverables to Oracle:

    /home/operator/.hermes/oracle/brain/research/batch<N>-<slug>.md

That path is the explicit two-path write boundary at the top of every
lane prompt. The lanes have been writing to Oracle all along; their
`workdir` has been sitting in active-wiki/research/, which is only
where they happen to launch. So the change is to the working directory,
not to the output.

This mattered enough to check rather than assume, because a blind
find-and-replace of `active-wiki` -> `oracle` across the prompts would
have corrupted two things that are not output targets:

  L75  names the corpus the SEPARATE `wiki-cognition` job excludes. If
       the lane stops treating that tree as excluded, a child task
       could read files it is not allowed to read.
  L147 is a historical incident record -- 1,074 writes by spawned
       children, 21 of which landed in active-wiki/. Rewriting it would
       falsify a record of what actually went wrong.

So prompts are left alone, except where a prompt's own lint command
hardcodes `--source active-wiki` and that lint is meant to cover the
wiki the research now lives in.

JOBS CHANGED
  workdir only, on the six research lanes:
    Online Lane A            (enabled)   Online Lane B      (enabled)
    Frontier Research Lane A (disabled)  Frontier Research Lane B (disabled)
    Desktop Research A       (disabled)  Desktop Research B (disabled)

  --source active-wiki -> oracle-brain on the two read-only LINT jobs,
  because those audit whichever wiki the research lands in:
    Wiki Lint Daily, Wiki Lint Weekly Deep, Research Quality Check

NOT CHANGED, AND WHY
  Graphify Active Wiki Ingestion  -- a distinct job whose entire purpose
                                    is ingesting active-wiki into the
                                    graph. Repointing it would delete
                                    that coverage.
  Graphify Oracle Brain Ingestion -- already correct.
  Brain-Sync Oracle, Brain Sync Staleness Check -- already correct.
  Weekday Prompt-Me               -- not a research lane; it captures
                                    user preferences and archives to
                                    active-wiki by design.
  Wiki Lint Weekly Deep           -- runs BOTH sources already; left
                                    alone rather than narrowed.

BACKUP
jobs.json is copied before any write, and --apply is required.
"""
import argparse
import json
import os
import shutil
import sys

JOBS = os.path.expanduser('~/.hermes/cron/jobs.json')
# Spelled with ~ to match the house style already used by
# "Graphify Oracle Brain Ingestion", whose workdir is
# ~/.hermes/oracle/brain/ -- and the active-wiki lanes being replaced
# used ~/.hermes/active-wiki/research/. Mixed absolute/tilde spellings
# in the same file would be gratuitous.
ORACLE_RESEARCH = '~/.hermes/oracle/brain/research'
ORACLE_RESEARCH_ABS = '/home/operator/.hermes/oracle/brain/research'

# (job name, what changes)
WORKDIR_JOBS = (
    'Online Lane A', 'Online Lane B',
    'Frontier Research Lane A', 'Frontier Research Lane B',
    'Desktop Research A', 'Desktop Research B',
)
LINT_JOBS = ('Wiki Lint Daily', 'Research Quality Check',
             'Wiki Lint Weekly Deep')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    raw = open(JOBS, encoding='utf-8').read()
    d = json.loads(raw)
    jobs = d if isinstance(d, list) else d.get('jobs', [])

    plan = []
    for j in jobs:
        n = j.get('name')
        if n in WORKDIR_JOBS:
            old = j.get('workdir') or ''
            if 'active-wiki' in old:
                plan.append((j, 'workdir', old, ORACLE_RESEARCH,
                             f'research lane working dir -> {ORACLE_RESEARCH}'))
        elif n in LINT_JOBS:
            pr = j.get('prompt') or ''
            if '--source active-wiki' in pr:
                newpr = pr.replace('--source active-wiki',
                                   '--source oracle-brain')
                plan.append((j, 'prompt', pr, newpr,
                             'lint --source -> oracle-brain'))

    print(f'\n  {len(plan)} changes\n')
    for j, f, old, new, why in plan:
        shown_old = old if f == 'workdir' else (
            f'{len(old)} chars, contains --source active-wiki')
        shown_new = new if f == 'workdir' else (
            f'{len(new)} chars, contains --source oracle-brain')
        print(f'  {j.get("name")}  [{"EN" if j.get("enabled") else "DIS"}]')
        print(f'    {why}')
        print(f'    {f}: {shown_old}')
        if f == 'workdir':
            print(f'      ->  {shown_new}')
        print()

    # confirm the target exists
    if not os.path.isdir(os.path.expanduser(ORACLE_RESEARCH)):
        print(f'  TARGET MISSING: {ORACLE_RESEARCH}')
        return 1
    n_files = len([f for f in os.listdir(ORACLE_RESEARCH_ABS)
                   if f.endswith('.md')])
    print(f'  target exists: {ORACLE_RESEARCH} ({n_files} .md files)')

    if not args.apply:
        print('\n  DRY RUN. Pass --apply to write.')
        return 0

    bak = JOBS + '.pre-oracle-retarget.bak'
    shutil.copy2(JOBS, bak)
    for j, f, old, new, _ in plan:
        j[f] = new
    with open(JOBS, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, indent=2)
    print(f'\n  written: {len(plan)} changes')
    print(f'  backup:  {bak}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
