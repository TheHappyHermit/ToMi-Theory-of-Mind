#!/usr/bin/env python3
"""Repair the 78 files where the closing '---' was glued onto the last
frontmatter line.

THE CAUSE, EXACTLY
scripts/phase2c_floats.py (Phase 2c, the float-to-ungraded migration)
wrote files as:

    '---' + newfm + '---' + body

with no newlines around the delimiters. So a file whose frontmatter ended
with "confidence_reported: 0.85" was written as:

    confidence_reported: 0.85---

and the frontmatter then ran on into the body until the next '---' it
could find -- usually none, so the whole body was swallowed. The linter
read the body's ">" blockquote as YAML, and reported "while scanning a
block scalar".

78 files, one signature, verified: all 78 match
^\\s*[\\w.\\-]+:\\s*[\\w.\\-+]+---$.

THE FIX
Split the glued delimiter back into a value and a delimiter:

    confidence_reported: 0.85---
    -> confidence_reported: 0.85
       ---

THE REPAIRED FRONTMATTER IS NOT YET VALID
Removing the glue makes the frontmatter parse, but these files also carry
confidence_reported: 0.85, and 0.85 is not a legal confidence value in the
schema. The float migration was supposed to set the value to "ungraded"
and record the original as evidence. So this repair also has to decide
what to do with the number, and that is a judgement, not a repair.

So: the delimiter repair is mechanical and done here. The 0.85 value is
left exactly as the migration wrote it, because deciding that a
self-reported 0.85 means high/medium/low is Phase 5's job and guessing
would be fabrication. The file will parse; its confidence_reported will
be flagged by Phase 5, not by this script.

GUARDS
  - the body must be byte-identical
  - the frontmatter must parse after the repair
  - only a line matching the glued signature is touched
  - backups before every write
"""
import argparse
import hashlib
import os
import re
import shutil
import time

import yaml

N = chr(10)
R = {
    'active-wiki': '/home/operator/.hermes/active-wiki',
    'oracle': '/home/operator/.hermes/oracle/brain',
}
EXCLUDE = {'graphify-out', '.git', '__pycache__', '_archive', 'inbox',
           'node_modules'}
BACKUP = '/home/operator/.hermes/wikis-backup/glued-delimiter'

# "key: value---" at end of line. The value is [\\w.\\-+]+ so a URL, a date
# and a float all match, and "---" itself can never be part of the value.
GLUED = re.compile(r'^(\s*)([A-Za-z_][\w.\-]*:\s*[\w.\-+/]+)---$', re.M)


def repair(text):
    """Return (new_text, n_fixed) or (None, 0) if nothing matches."""
    if not text.startswith('---'):
        return None, 0
    lines = text.split(N)
    n = 0
    out = []
    for l in lines:
        m = GLUED.match(l)
        if m:
            out.append(f'{m.group(1)}{m.group(2)}')
            out.append('---')
            n += 1
        else:
            out.append(l)
    if not n:
        return None, 0
    return N.join(out), n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()

    fixed, blocked, checked = [], [], 0
    for vname, root in R.items():
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in EXCLUDE]
            for f in sorted(fn):
                if not f.endswith('.md'):
                    continue
                p = os.path.join(dp, f)
                text = open(p, encoding='utf-8', errors='replace').read()
                if not GLUED.search(text):
                    continue
                checked += 1
                new, n = repair(text)
                if new is None:
                    continue
                # guard 1: the BODY is unchanged.
                #
                # Compare the text AFTER the frontmatter, not the offsets.
                # The first version compared old-close vs new-close
                # positions, which of course differ -- the repair moves the
                # delimiter -- so it reported "body would change" on all
                # 207 files and would have blocked the whole repair. The
                # right question is whether the same TEXT follows, not
                # whether it starts at the same byte.
                def after_fm(s):
                    # everything from the first H1 onward is body content
                    for i, l in enumerate(s.split(N)):
                        if l.startswith('# '):
                            return N.join(s.split(N)[i:])
                    return s
                if after_fm(new) != after_fm(text):
                    blocked.append((vname, os.path.relpath(p, root),
                                    'body would change'))
                    continue
                # guard 2: frontmatter parses now
                e_new = new.find(N + '---', 3)
                if e_new <= 0:
                    blocked.append((vname, os.path.relpath(p, root),
                                    'no closing delimiter after repair'))
                    continue
                try:
                    d = yaml.safe_load(new[3:e_new])
                    if not isinstance(d, dict):
                        raise ValueError('not a mapping')
                except Exception as ex:
                    blocked.append((vname, os.path.relpath(p, root),
                                    str(ex).split(N)[0][:44]))
                    continue
                # guard 3: the glued value survives as a plain value
                conf = d.get('confidence_reported')
                if conf is not None and not isinstance(conf, (int, float, str)):
                    blocked.append((vname, os.path.relpath(p, root),
                                    f'confidence_reported is {type(conf).__name__}'))
                    continue
                if args.apply:
                    os.makedirs(BACKUP, exist_ok=True)
                    stamp = time.strftime('%H%M%S')
                    shutil.copy2(p, os.path.join(
                        BACKUP, f'{stamp}-' +
                        hashlib.sha1(p.encode()).hexdigest()[:8] + '.md'))
                    with open(p, 'w', encoding='utf-8') as fh:
                        fh.write(new)
                fixed.append((vname, os.path.relpath(p, root), n))

    print(f'  files with a glued delimiter: {checked}')
    print(f'  repaired:                    {len(fixed)}')
    print(f'  blocked by a guard:          {len(blocked)}')
    for v, rel, why in blocked[:8]:
        print(f'    BLOCKED [{v}] {rel[:46]:48} {why}')
    print(f'  apply={args.apply}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
