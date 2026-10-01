#!/usr/bin/env python3
"""Fix a regression I introduced in the previous commit.

The retarget script did a blanket

    pr.replace('--source active-wiki', '--source oracle-brain')

on three lint jobs. Two of them -- Wiki Lint Weekly Deep and Research
Quality Check -- ALREADY ran both wikis, one line per wiki:

    Weekly Deep, before:
      2. research_quality_check.py --source active-wiki
      3. research_quality_check.py --source oracle-brain
      4. wiki_hit_counter.py list --source active-wiki
      5. wiki_hit_counter.py list --source oracle-brain

    Weekly Deep, after the blanket replace:
      2. research_quality_check.py --source oracle-brain
      3. research_quality_check.py --source oracle-brain   <- duplicate
      4. wiki_hit_counter.py list --source oracle-brain
      5. wiki_hit_counter.py list --source oracle-brain   <- duplicate

So those two jobs now run the same command twice and have STOPPED
checking active-wiki, while their own prompts still say "Report ...
in BOTH wikis". The claim in the report became false.

Only Wiki Lint Daily was genuinely active-wiki-only, so only that one
should have changed. This restores the paired lines in the two jobs
that were already covering both, and leaves Wiki Lint Daily pointed at
Oracle because that one was active-wiki only and the lint ought to
follow the research.
"""
import json
import os
import shutil
import sys

JOBS = os.path.expanduser('~/.hermes/cron/jobs.json')

# For these two, the two consecutive identical lines are the bug: one
# was active-wiki, one was oracle-brain. Restore the pair.
BOTH_WIKI_JOBS = ('Wiki Lint Weekly Deep', 'Research Quality Check')
RQC = ('research_quality_check.py --source oracle-brain '
       '--check-contradictions')
HIT = 'wiki_hit_counter.py list --source oracle-brain --limit'



import re as _re
_NUM = _re.compile(r'^\s*\d+\.\s*')


def _num_prefix(line):
    """The leading "N. " of a numbered list item, or ''."""
    m = _re.match(r'^(\s*\d+\.\s*)', line)
    return m.group(1) if m else ''


def _cmd(line):
    """The line with list numbering removed."""
    return _NUM.sub('', line)


def _same_cmd(a, b):
    """True when two lines are the same command, ignoring numbering and
    the --source value."""
    return (_cmd(a).replace('--source oracle-brain', 'SRC')
            == _cmd(b).replace('--source oracle-brain', 'SRC'))


def fix_prompt(pr):
    """Restore active-wiki|oracle-brain pairs from doubled lines."""
    lines = pr.split('\n')
    out = []
    i = 0
    fixed = 0
    while i < len(lines):
        ln = lines[i]
        # is this the first of a doubled pair?
        if (i + 1 < len(lines)
                and lines[i + 1].strip().lstrip('123456789. ')
                .replace('python3 ', '') in
                (RQC, RQC.replace('--check-contradictions',
                                  '--check-contradictions'))
                and ln.strip() == lines[i + 1].strip()):
            out.append(ln.replace('--source oracle-brain',
                                  '--source active-wiki'))
            out.append(lines[i + 1])
            fixed += 1
            i += 2
            continue
        out.append(ln)
        i += 1
    return '\n'.join(out), fixed


def main():
    apply = '--apply' in sys.argv
    d = json.load(open(JOBS, encoding='utf-8'))
    jobs = d if isinstance(d, list) else d.get('jobs', [])

    changed = 0
    for j in jobs:
        if str(j.get('name')) not in BOTH_WIKI_JOBS:
            continue
        pr = j.get('prompt') or ''
        # Find adjacent identical --source oracle-brain lines
        lines = pr.split('\n')
        new = []
        i = 0
        n = 0
        while i < len(lines):
            if (i + 1 < len(lines)
                    and '--source oracle-brain' in lines[i]
                    and _same_cmd(lines[i], lines[i + 1])):
                # The odd line of a doubled pair was the active-wiki
                # one. `_same_cmd` compares the command with any list
                # numbering ("2. ", "3. ") stripped, because Wiki Lint
                # Weekly Deep numbers its steps, so the duplicates are
                # NOT byte-identical and a plain equality test found
                # none of them.
                a, b = lines[i], lines[i + 1]
                # Preserve whichever of the two lines carried list
                # numbering. The first version rebuilt line i from b's
                # indentation, which silently DROPPED the "2. " and
                # "4. " prefixes and left the list renumbered
                # 1, 3, 5. Take the prefix from whichever line has it.
                pa = _num_prefix(a)
                pb = _num_prefix(b)
                new.append((pa or pb) + _cmd(a).replace(
                    '--source oracle-brain', '--source active-wiki'))
                new.append(b)
                n += 1
                i += 2
                continue
            new.append(lines[i])
            i += 1
        if n:
            j['prompt'] = '\n'.join(new)
            print(f"  {j['name']}: restored {n} active-wiki/oracle pair(s)")
            changed += n

    if not changed:
        print('  nothing to fix')
        return 0
    if not apply:
        print('\n  DRY RUN. Pass --apply.')
        return 0
    bak = JOBS + '.pre-dedupe.bak'
    shutil.copy2(JOBS, bak)
    with open(JOBS, 'w', encoding='utf-8') as fh:
        json.dump(d, fh, indent=2)
    print(f'\n  fixed {changed} lines')
    print(f'  backup: {bak}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
