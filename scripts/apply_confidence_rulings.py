#!/usr/bin/env python3
"""Apply the two confidence rulings the operator made, to the two safe classes.

THE RULINGS
  1. A decision record carries `high`. It is a record of the owner's own
     ruling, so it is the authority rather than a claim needing
     corroboration. Encoded in the schema as M0_decision_record.
  2. A table of contents carries `not_applicable`. It asserts nothing
     load-bearing, so confidence is a wrong question rather than a
     missing answer. Marking it `low` would be a downgrade of a page
     that was never making a claim.

SCOPE: 204 files (37 decisions + 167 navigational). Nothing else.

WHAT THIS DOES NOT DO
It does not touch the 496 unsourced synthesis files. Those get real
sources attached, which is separate work requiring research per file.
It does not touch the 527 that need individual reading. It does not
touch the 2 first-party pages beyond leaving them as they are.

SAFETY
  - dry-run by default; --apply to write
  - every file backed up to archive/ before modification
  - only `confidence:` is touched; the frontmatter is re-serialised by
    surgical line edit, not a yaml round-trip, so quoting, comments and
    key order in the rest of the frontmatter survive byte for byte.
    (A yaml.safe_dump round trip would reorder and requote the whole
    block and quietly rewrite content we were not asked to change.)
  - a backup manifest records the prior value for every file
"""
import argparse
import csv
import datetime
import json
import os
import re
import shutil
import sys

N = chr(10)
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
REPO = '/home/operator/hermes-brain'
CLASSES_CSV = f'{REPO}/docs/audit/overstatement-classes.csv'
BACKUP_DIR = f'{REPO}/archive/confidence_backup'
MANIFEST = f'{REPO}/docs/audit/confidence-writes-manifest.json'

APPLY = {
    'c_record_of_decision': 'high',
    'n_navigational_not_applicable': 'not_applicable',
}

# A confidence line inside YAML frontmatter. Anchored to the value, not
# the key alone, so a `confidence_reported: 0.85` line or a commented
# `# confidence: high` cannot be matched by accident.
CONF_LINE = re.compile(
    r'^(?P<ind>\s*)confidence:(?P<pre>\s*)(?P<val>.+?)(?P<post>\s*)$')


def set_confidence(text, newval):
    """Replace the top-level `confidence:` value in the frontmatter block.
    Returns (new_text, changed) or (text, False) if not found."""
    if not text.startswith('---'):
        return text, False
    end = text.find(N + '---', 3)
    if end == -1:
        return text, False
    head, fm, tail = text[:3], text[3:end], text[end:]
    out = []
    hit = False
    for line in fm.split(N):
        m = CONF_LINE.match(line)
        if m and not m.group('ind'):  # top level only, no indent
            cur = m.group('val').strip().strip('"\'')
            if cur != newval:
                line = f'confidence: {newval}'
                hit = True
            else:
                hit = False
        out.append(line)
    if not hit:
        return text, False
    return head + N.join(out) + tail, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='actually write (default is a dry run)')
    args = ap.parse_args()

    rows = list(csv.DictReader(open(CLASSES_CSV, encoding='utf-8')))
    targets = [r for r in rows if r['work_class'] in APPLY]
    print(f'\n  {len(targets)} files in the two ruled classes '
          f'({", ".join(f"{k}={len(APPLY)}" for k in APPLY)})\n')

    changes = []
    for r in targets:
        path = ROOTS[r['vault']] + '/' + r['path']
        newval = APPLY[r['work_class']]
        try:
            text = open(path, encoding='utf-8', errors='replace').read()
        except Exception as ex:
            print(f'  SKIP (unreadable) {r["path"]}: {ex}')
            continue
        newtext, changed = set_confidence(text, newval)
        if not changed:
            continue
        changes.append({'vault': r['vault'], 'path': r['path'],
                        'from': r['current_confidence'], 'to': newval,
                        'work_class': r['work_class'],
                        'abspath': path})

    by_to = {}
    for c in changes:
        by_to[c['to']] = by_to.get(c['to'], 0) + 1
    print('  would write:')
    for k, v in sorted(by_to.items()):
        print(f'    {v:>4} files -> confidence: {k}')
    print(f'    {len(changes):>4} total\n')

    if not args.apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    ts = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y%m%dT%H%M%SZ')
    bdir = os.path.join(BACKUP_DIR, ts)
    os.makedirs(bdir, exist_ok=True)
    written = failed = 0
    for c in changes:
        src = c['abspath']
        rel = c['vault'] + '__' + c['path'].replace('/', '__')
        try:
            shutil.copy2(src, os.path.join(bdir, rel))
        except Exception as ex:
            print(f'  BACKUP FAILED {c["path"]}: {ex}')
            failed += 1
            continue
        try:
            newtext, _ = set_confidence(
                open(src, encoding='utf-8', errors='replace').read(),
                c['to'])
            with open(src, 'w', encoding='utf-8') as fh:
                fh.write(newtext)
            c['backup'] = os.path.join(bdir, rel)
            written += 1
        except Exception as ex:
            print(f'  WRITE FAILED {c["path"]}: {ex}')
            failed += 1

    prev = {}
    if os.path.exists(MANIFEST):
        prev = json.load(open(MANIFEST, encoding='utf-8'))
    prev.setdefault('writes', []).extend(
        [{k: v for k, v in c.items() if k != 'abspath'} for c in changes])
    with open(MANIFEST, 'w', encoding='utf-8') as fh:
        json.dump(prev, fh, indent=1)

    print(f'\n  written: {written}   failed: {failed}')
    print(f'  backups: {bdir}')
    print(f'  manifest: {MANIFEST}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
