#!/usr/bin/env python3
"""Make the Oracle lint incremental and keep a full sweep off the daily job.

the operator: "I don't need a daily wiki lint on the oracle brain. And if we do
one then it should only be any new files rather than all. The files is
far too large to lint on a daily basis."

WHAT CHANGES

  Wiki Lint Daily        keeps running. Its FIRST step becomes
                         lint_incremental.py, which reports only new and
                         changed files. A quiet day produces two lines
                         and no full sweep. active-wiki coverage is
                         unchanged -- it is small and was never the
                         problem.

  Research Quality Check DELETED from the schedule. It is disabled, not
                         removed, so the definition survives in
                         jobs.json. Its entire content was the two
                         --source lines, both of which the daily job
                         now covers.

  Wiki Lint Weekly Deep  stays a FULL sweep, unchanged. This is the
                         part that must not be made incremental: it is
                         the only job that can see cross-file breakage
                         -- a link target that was deleted, an orphan
                         that became reachable, a contradiction between
                         two files. Per-file checks cannot detect any of
                         those, and the operator's objection was to sweeping
                         2,393 files DAILY, not to sweeping them at all.

WHY DELETE ONE JOB RATHER THAN REWRITE IT
Research Quality Check ran exactly two commands, both --source pairs
that Wiki Lint Daily already runs. Making it incremental would have
produced a second incremental job duplicating the first, and leaving it
daily would have kept an LLM wake-up per day for no additional
coverage. Disabling it is reversible; deleting the job definition
would not be.

EXPECTED BEHAVIOUR WHILE THE LANES KEEP WRITING
The corpus will report large "new" counts for a while, because the
research lanes genuinely are writing new files and those DO need
checking. That is the honest answer, not a failure of the incremental
logic. It goes quiet once writing settles.
"""
import json
import os
import shutil
import sys

JOBS = os.path.expanduser('~/.hermes/cron/jobs.json')
REPO = '/home/operator/hermes-brain'

INCREMENTAL_STEP = (
    '1. Incremental lint -- new and changed files only:\n'
    f'   python3 {REPO}/scripts/lint_incremental.py\n'
    '   A quiet day prints "NOTHING CHANGED" in two lines and stops.\n'
    '   Do NOT run a full-corpus sweep here; the weekly job does that.')
DISABLE = ('Research Quality Check',)


def main():
    apply = '--apply' in sys.argv
    d = json.load(open(JOBS, encoding='utf-8'))
    jobs = d if isinstance(d, list) else d.get('jobs', [])

    for j in jobs:
        n = str(j.get('name'))
        if n == 'Wiki Lint Daily':
            pr = j.get('prompt') or ''
            if 'lint_incremental.py' in pr:
                print('  Wiki Lint Daily: already incremental')
            else:
                lines = pr.split('\n')
                # replace the first numbered step, keep everything else
                for i, ln in enumerate(lines):
                    if 'okf_lint.py' in ln and ln.strip().startswith('1.'):
                        lines[i:i + 1] = INCREMENTAL_STEP.split('\n')
                        break
                else:
                    lines.insert(1, INCREMENTAL_STEP)
                j['prompt'] = '\n'.join(lines)
                print('  Wiki Lint Daily: step 1 is now incremental')
        elif n in DISABLE:
            if j.get('enabled'):
                j['enabled'] = False
                j['paused_reason'] = (
                    'Duplicated Wiki Lint Daily, which is now incremental. '
                    'Definition kept in jobs.json so it can be restored.')
                print(f'  {n}: DISABLED (not deleted)')
            else:
                print(f'  {n}: already disabled')

    if not apply:
        print('\n  DRY RUN. Pass --apply.')
        return 0
    bak = JOBS + '.pre-lint-incremental.bak'
    shutil.copy2(JOBS, bak)
    with open(JOBS, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, indent=2)
    print(f'\n  written. backup: {bak}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
