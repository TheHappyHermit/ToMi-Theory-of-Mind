#!/usr/bin/env python3
"""Gate: does every article's frontmatter actually PARSE as YAML?

WHY THIS EXISTS
scripts/okf_lint.py validates an article's frontmatter by walking it line
by line with TOPKEY_RE and checking the enum values it finds. It never
calls a YAML parser on the article. So a file whose frontmatter is
syntactically invalid -- an unquoted colon in a value, a leftover block
scalar, a frontmatter that never closes -- still reports its keys and
still passes every check the linter makes.

Measured on the live vaults: 391 of 3,008 files have frontmatter that does
not parse, and okf_lint reported none of them.

This gate is the missing check. It is deliberately separate from
okf_lint.py rather than inside it: okf_lint's line-based reader is used by
the auto-repair path, and teaching it to parse would change what "repair"
means. A gate that can fail loudly and change nothing is the safer place.

Exit 0 only when every file parses.
"""
import os
import sys
import yaml

N = chr(10)
ROOTS = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
EXCLUDE = {'graphify-out', '.git', '__pycache__', '_archive', 'inbox',
           'node_modules'}


def span(lines):
    """(start, end) line indices of the frontmatter body, or None."""
    if not lines or lines[0].strip() != '---':
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            return (1, i)
    return ('open', 1)


def check():
    bad = []
    total = 0
    for name, root in ROOTS.items():
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in EXCLUDE]
            for f in fn:
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                total += 1
                try:
                    lines = open(p, encoding='utf-8',
                                 errors='replace').read().split(N)
                except Exception as e:
                    bad.append((name, os.path.relpath(p, root), f'read: {e}'))
                    continue
                sp = span(lines)
                if sp is None:
                    bad.append((name, os.path.relpath(p, root),
                                'no frontmatter'))
                    continue
                if sp[0] == 'open':
                    bad.append((name, os.path.relpath(p, root),
                                'frontmatter never closes'))
                    continue
                a, b = sp
                fm = N.join(lines[a:b])
                try:
                    d = yaml.safe_load(fm)
                    if not isinstance(d, dict):
                        bad.append((name, os.path.relpath(p, root),
                                    f'not a mapping: {type(d).__name__}'))
                except Exception as ex:
                    bad.append((name, os.path.relpath(p, root),
                                str(ex).split(N)[0][:60]))
    return total, bad


if __name__ == '__main__':
    total, bad = check()
    print(f'  scanned {total} markdown files')
    if not bad:
        print('  every frontmatter parses as YAML')
        sys.exit(0)

    kinds = {}
    for _, _, why in bad:
        k = why.split(':')[0][:40]
        kinds[k] = kinds.get(k, 0) + 1
    print(f'  {len(bad)} files whose frontmatter does NOT parse:')
    for k, n in sorted(kinds.items(), key=lambda x: -x[1]):
        print(f'    {n:>4}  {k}')
    print()
    for name, rel, why in bad[:12]:
        print(f'    [{name:12}] {rel[:56]:58} {why}')
    if len(bad) > 12:
        print(f'    ... and {len(bad) - 12} more')
    sys.exit(1)
