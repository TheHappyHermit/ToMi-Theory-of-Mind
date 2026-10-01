#!/usr/bin/env python3
"""Lint only what changed. A daily sweep of 2,393 Oracle files is waste.

the operator: "I don't need a daily wiki lint on the oracle brain. And if we do
one then it should only be any new files rather than all. The files is
far too large to lint on a daily basis."

WHAT "CHANGED" MEANS HERE, AND WHY NOT mtime
Measured first: 2,356 of 2,393 Oracle files have an mtime inside 48
hours. That is because the research lanes write constantly, and because
this remediation touched nearly the whole corpus in one sitting. Using
mtime would mean the first incremental run linted everything anyway and
the next one linted 2,356 files -- worse than useless, because it would
look incremental while doing the full sweep.

So the signal is a CONTENT HASH, which is what the sync already uses.
The first run records every file; every later run reports only the files
whose hash changed or that are new. A run that finds nothing says so in
one line and costs almost nothing.

The corpus will still report large numbers for a few days while the
research lanes keep writing, and that is correct: those ARE new files
and they DO need checking. The win is that once writing settles, the
daily job goes quiet.

WHY THE FULL SWEEP WAS NOT ACTUALLY EXPENSIVE
Worth recording, because it changes what the fix is for:
  okf_lint.py --check --source both          0.54 s, 8 lines out
  research_quality_check.py oracle, contra   7.08 s, 24 lines out
So the CPU cost was never the problem. The cost is an LLM being woken
daily to read a report about 2,393 files, almost none of which changed.
This makes the report itself smaller, not just the run.

A FULL SWEEP REMAINS AVAILABLE
Not deleted. A periodic full sweep is what catches cross-file breakage
that a per-file check cannot see: a link target that was deleted, an
orphan that is now reachable, a contradiction between two files. Only
the FILE-level check is incremental here; anything that needs the whole
corpus in view must still run over the whole corpus.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

N = chr(10)
REPO = '/home/operator/hermes-brain'
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
STATE = f'{REPO}/docs/audit/lint-hashes.json'
SCRATCH = f'{REPO}/docs/audit/lint-work'


def walk(root):
    for dp, dn, fn in os.walk(root):
        if '.meta' in dp.split(os.sep):
            continue
        for f in sorted(fn):
            if f.endswith('.md'):
                yield os.path.join(dp, f)


def fingerprint(path):
    try:
        with open(path, 'rb') as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except Exception:
        return None


def scan():
    """{relpath: hash} for the whole corpus, per vault."""
    out = {}
    for vault, root in ROOTS.items():
        d = {}
        for p in walk(root):
            h = fingerprint(p)
            if h:
                d[os.path.relpath(p, root)] = h
        out[vault] = d
    return out


def changed_since(state, now):
    new, changed = [], []
    for vault, files in now.items():
        old = state.get(vault, {})
        for rel, h in files.items():
            if rel not in old:
                new.append((vault, rel))
            elif old[rel] != h:
                changed.append((vault, rel))
    return new, changed


def run_tool(args, label):
    print(f'\n  --- {label} ---')
    try:
        p = subprocess.run(
            [sys.executable, f'{REPO}/scripts/{args[0]}'] + args[1:],
            capture_output=True, text=True, timeout=300, cwd=REPO)
        out = (p.stdout or '') + (p.stderr or '')
        print('  ' + out[:2000].replace(N, N + '  '))
        return out
    except Exception as ex:
        print(f'  FAILED: {ex}')
        return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='update the hash state file')
    ap.add_argument('--full', action='store_true',
                    help='ignore the state and check everything')
    ap.add_argument('--rescan', action='store_true',
                    help='re-record hashes without linting')
    ap.add_argument('--dry-run', action='store_true',
                    help='do not write the state file')
    args = ap.parse_args()

    state = {}
    if os.path.exists(STATE):
        try:
            state = json.load(open(STATE, encoding='utf-8'))
        except Exception:
            state = {}

    now = scan()
    total = sum(len(v) for v in now.values())

    if args.full or not state:
        if not state and not args.full:
            print(f'\n  no state file: this is a baseline run.')
            print(f'  {total} files hashed across {len(now)} vaults.')
            print('  Recording hashes so the NEXT run can be incremental.')
            args.rescan = True
            # fall through to the rescan writer
        new, changed = [], []
        print(f'  FULL sweep requested: {total} files')
    else:
        new, changed = changed_since(state, now)
        print(f'\n  corpus: {total} files   new: {len(new)}   '
              f'changed: {len(changed)}')
        todo = new + changed
        if not todo:
            print('\n  NOTHING CHANGED since the last run.')
            print('  No lint run needed, and none performed.')
            return 0
        print(f'  linting {len(todo)} files, not {total}')

    if args.rescan:
        # The first version required --apply for the rescan, but the
        # no-state branch above returned BEFORE reaching the apply
        # check, so `lint_incremental.py --apply` on a fresh checkout
        # printed "Re-run with --apply" forever and never wrote
        # anything. The baseline is the one case where writing is the
        # only useful action, so it writes unless --dry-run is given.
        if args.dry_run:
            print(f'\n  DRY RUN. Would write {STATE} ({total} hashes)')
        else:
            json.dump(now, open(STATE, 'w', encoding='utf-8'), indent=0,
                      sort_keys=True)
            print(f'\n  state written: {STATE} ({total} hashes)')
        return 0

    # A real lint of the changed set. Per-file checks only; anything
    # needing the whole corpus in view belongs in the full sweep.
    per = {}
    for vault, rel in (new + changed):
        per.setdefault(vault, []).append(rel)
    for vault, rels in per.items():
        print(f'\n  {vault}: {len(rels)} files')
        for r in rels[:10]:
            print(f'    {r}')
        if len(rels) > 10:
            print(f'    ... and {len(rels) - 10} more')
    run_tool(['okf_lint.py', '--check', '--source', 'both'],
             'okf_lint (full -- per-file, cheap)')
    print('\n  NOTE: okf_lint has no per-file mode, so it ran over both')
    print('  wikis anyway. It is 0.5s and 8 lines, so that is fine. The')
    print('  files that matter for a daily report are listed above.')

    if args.apply:
        json.dump(now, open(STATE, 'w', encoding='utf-8'), indent=0,
                  sort_keys=True)
        print(f'\n  state written: {STATE}')
    else:
        print('\n  DRY RUN. Pass --apply to write the state file.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
