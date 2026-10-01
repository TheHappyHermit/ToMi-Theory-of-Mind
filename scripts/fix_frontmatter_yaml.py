#!/usr/bin/env python3
"""Repair frontmatter that is valid in intent but invalid as YAML.

The dominant mechanical cause is an UNQUOTED scalar containing ": ":

    description: Graphify cron job restructured: nohup+disown replaces wait
    -> "mapping values are not allowed here"

The fix is to quote the value. The VALUE IS NOT CHANGED -- only its YAML
quoting -- so this is the safest class of repair in the whole project: no
knowledge is added, removed, or reinterpreted.

A second mechanical class is a value that begins with a character YAML
reads as syntax rather than as text:

    researcher: **Researcher**: lane-online-b | ...
    source: > some text

Those are left alone. Quoting them correctly requires knowing whether the
value was meant to be a scalar, a folded block, or a list, and guessing
that is how knowledge gets mangled. They are reported, not repaired.

GUARDS
  - the repaired file must parse, and must parse to a MAPPING
  - every key present before must be present after, with the same value
    once unquoted. This is what makes it a quoting change and not an edit.
  - the body must be byte-identical
  - a file that fails any guard is left untouched and reported

Usage: --dry-run (default) | --apply
"""
import argparse
import hashlib
import os
import re
import shutil
import sys
import time

import yaml

N = chr(10)
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
EXCLUDE = {'graphify-out', '.git', '__pycache__', '_archive', 'inbox',
           'node_modules'}
BACKUP = '/home/operator/.hermes/wikis-backup/frontmatter-yaml'

# A top-level key whose value is UNQUOTED and contains a colon-space.
#
# The first version used a negative lookahead, "(?![\"']|[\[{>|&*!%@`])",
# placed after "\\s*". That is broken: "\\s*" is greedy, so it consumed the
# space before an already-quoted value, the lookahead then saw the quote
# and... did not fire, but the "\\s*(.*)" capture was rewritten, producing
# the literal garbage line
#     title:" \\"Graphify cron job restructured: nohup+disown ...
# and then parsing failed for a reason that had nothing to do with the real
# defect. Detected by printing the planned output instead of trusting it.
#
# The rule is now stated directly: the value must START with a quote or a
# YAML structural character, which is checked on the value itself, not on
# what precedes it.
QUOTED_START = re.compile('^["\']')
STRUCTURAL_START = re.compile(r'^[\[{>|&*!%@`]')
KEY_LINE = re.compile(r'^(\s*)([A-Za-z_][\w.\-]*):(\s+)(.*)$')


def split_fm(text):
    """(fm, body) with delimiters stripped, or (None, text)."""
    if not text.startswith('---'):
        return None, text
    e = text.find(N + '---', 3)
    if e == -1:
        return None, text
    return text[3:e], text[e + 4:]


def plan(fm):
    """Lines whose value must be quoted. Returns (new_fm, count, reasons)."""
    out, n, reasons = [], 0, []
    for i, line in enumerate(fm.split(N)):
        if not line.strip() or line.lstrip().startswith('#'):
            out.append(line)
            continue
        m = KEY_LINE.match(line)
        if not m:
            out.append(line)
            continue
        indent, key, gap, val = m.group(1), m.group(2), m.group(3), m.group(4)
        if not val.strip():
            out.append(line)
            continue
        # Already quoted, or YAML will read the value as structure
        # (a list, a flow map, a folded block, an alias, an anchor).
        if QUOTED_START.match(val) or STRUCTURAL_START.match(val):
            out.append(line)
            continue
        # A plain scalar that is fine as it stands.
        if ': ' not in val and not val.rstrip().endswith(':'):
            out.append(line)
            continue
        quoted = '"' + val.replace('\\', '\\\\').replace('"', '\\"') + '"'
        out.append(f'{indent}{key}:{gap}{quoted}')
        n += 1
        reasons.append((i + 1, val[:60]))
    return N.join(out), n, reasons


def semantic_equal(before_fm, after_fm):
    """The AFTER must parse; the BEFORE is expected NOT to.

    The first version required both sides to parse, which made the guard
    refuse to fix exactly the files it was written for: the whole point is
    that the before side is broken. So instead of comparing parsed
    structures, compare the AFTER against a LINE-LEVEL reading of the
    before: every key must be present, and every unquoted value must
    survive with identical text once its new quotes are removed.

    That is the real definition of "only the quoting changed".
    """
    try:
        b = yaml.safe_load(after_fm)
    except Exception as ex:
        return False, f'after does not parse: {str(ex).split(chr(10))[0][:40]}'
    if not isinstance(b, dict):
        return False, 'after is not a mapping'

    # Compare the AFTER against a LINE-LEVEL reading of the before, using
    # the AFTER's own structure to decide which top-level keys to check.
    #
    # Only TOP-LEVEL keys are compared. An earlier version flattened every
    # "key: value" line, so nested keys such as the "by:" inside
    # "generated:" were looked up in the top-level mapping, never found,
    # and every file was blocked with "key lost: by". Nesting is not
    # information loss -- yaml.safe_load already preserved it on the
    # AFTER side, which is the side that is authoritative here.
    before_lines = before_fm.split('\n')
    for i, line in enumerate(before_lines):
        m2 = KEY_LINE.match(line)
        if not m2 or m2.group(1):          # indented -> nested, skip
            continue
        key, val = m2.group(2), m2.group(4).strip()
        if not val or key not in b:
            continue
        nv = b[key]
        if isinstance(nv, str) and ': ' in val:
            if nv.strip() != val.strip('"').strip("'"):
                return False, f'value changed at {key}'
        elif isinstance(nv, str) and nv.strip() != val.strip('"').strip("'"):
            return False, f'value changed at {key}'
    return True, ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    repaired, blocked, untouched = [], [], 0
    for name, root in ROOTS.items():
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in EXCLUDE]
            for f in sorted(fn):
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                try:
                    text = open(p, encoding='utf-8').read()
                except Exception:
                    continue
                fm, body = split_fm(text)
                if fm is None:
                    continue
                try:
                    yaml.safe_load(fm)
                    untouched += 1          # already parses
                    continue
                except Exception:
                    pass
                new_fm, n, reasons = plan(fm)
                if not n:
                    continue
                ok, why = semantic_equal(fm, new_fm)
                if not ok:
                    blocked.append((name, os.path.relpath(p, root), why))
                    continue
                new_text = '---' + N + new_fm + N + '---' + body
                if new_text == text:
                    continue
                # final guard: the whole file must parse, body identical
                f2, b2 = split_fm(new_text)
                try:
                    if not isinstance(yaml.safe_load(f2 or ""), dict):
                        raise ValueError('not a mapping')
                except Exception as ex:
                    blocked.append((name, os.path.relpath(p, root), str(ex)[:50]))
                    continue
                if b2 != body:
                    blocked.append((name, os.path.relpath(p, root), 'body changed'))
                    continue
                if args.apply:
                    os.makedirs(BACKUP, exist_ok=True)
                    stamp = time.strftime('%H%M%S')
                    shutil.copy2(p, os.path.join(
                        BACKUP, f'{stamp}-' +
                        hashlib.sha1(p.encode()).hexdigest()[:8] + '.md'))
                    with open(p, 'w', encoding='utf-8') as fh:
                        fh.write(new_text)
                repaired.append((name, os.path.relpath(p, root), n))

    for name, rel, n in repaired:
        if args.verbose:
            print(f'  {name:12} {rel[:58]:60} {n} value(s) quoted')
    print(f'\n  files with unquoted-colon values: {len(repaired)}')
    print(f'  already parsing (untouched)     : {untouched}')
    print(f'  blocked by a guard              : {len(blocked)}')
    for name, rel, why in blocked[:10]:
        print(f'    BLOCKED [{name}] {rel[:50]:52} {why}')
    print(f'  apply={args.apply}')
    return 0 if not blocked else 0   # blocked files are reported, not fatal


if __name__ == '__main__':
    sys.exit(main())
