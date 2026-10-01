"""Repair vault lines whose title was written by an older clean_title.

Three titles in the worklist carry publisher markup, and the first
version of clean_title stripped the tags with no replacement space, so
the label written into the vault reads "DendriticI h" instead of
"Dendritic I h". The verifier scores that 0.769, below the 0.80 floor,
and records a false mismatch.

Rather than re-running the whole titling pass -- which would re-derive
all 461 rows to fix 3 lines -- this finds the exact lines whose stored
title differs from what clean_title now produces, and rewrites only
those. A full pass would also churn the 466 rows the verifier has
already re-derived, which is how a targeted fix turns into a large
unreviewed diff.
"""
import json
import re
import shutil
import sys
from pathlib import Path

BRAIN = Path('/home/operator/.hermes/oracle/brain')
WORKLIST = ('/home/operator/.hermes/cache/scratch/'
            'untitled_by_file.json')
BACKUP = Path('/home/operator/.hermes/cache/scratch/pre-titling-snapshot')
SCRIPT = '/home/operator/hermes-brain/scripts/title_untitled_sources.py'


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location('titler', SCRIPT)
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)

    work = json.load(open(WORKLIST, encoding='utf-8'))
    apply = '--apply' in sys.argv
    fixes, checked = [], 0

    for rel, rows in sorted(work.items()):
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        new = text
        for ident, raw_title, _s in rows:
            if not raw_title or '<' not in raw_title:
                continue
            bare = ident.split(':', 1)[-1]
            want = T.clean_title(raw_title)
            for ln in new.split('\n'):
                if bare not in ln or not ln.strip().startswith('- '):
                    continue
                checked += 1
                # the title currently stored on this line
                m = re.search(r'\(([^()]+)\)\s*[\'"]?\s*$', ln)
                if not m:
                    continue
                have = m.group(1)
                if have == want:
                    continue
                fixed = ln[:m.start(1)] + want + ln[m.end(1):]
                new = new.replace(ln, fixed, 1)
                fixes.append((rel, ident, have, want))

    print('  lines checked with markup titles: %d' % checked)
    print('  lines needing repair            : %d' % len(fixes))
    for rel, ident, have, want in fixes:
        print('  %s' % rel)
        print('     %s' % ident)
        print('     have: %r' % have[:78])
        print('     want: %r' % want[:78])

    if not fixes:
        print('  nothing to repair')
        return 0
    if not apply:
        print('  DRY RUN. Pass --apply to write.')
        return 0

    # group by file: each file needs exactly one rewrite
    by_file = {}
    for rel, ident, _h, _w in fixes:
        by_file.setdefault(rel, []).append(ident)
    written = 0
    for rel, idents in by_file.items():
        full = BRAIN / rel
        text = full.read_text(encoding='utf-8')
        out = text
        for ident, raw_title, _s in work[rel]:
            if not raw_title or '<' not in raw_title:
                continue
            bare = ident.split(':', 1)[-1]
            want = T.clean_title(raw_title)
            for ln in out.split('\n'):
                if bare not in ln or not ln.strip().startswith('- '):
                    continue
                m = re.search(r'\(([^()]+)\)\s*[\'"]?\s*$', ln)
                if not m or m.group(1) == want:
                    continue
                out = out.replace(
                    ln, ln[:m.start(1)] + want + ln[m.end(1):], 1)
                break
        if out != text:
            # the pre-titling snapshot is the restore point
            src = BACKUP / rel
            dst = BACKUP.parent / 'pre-tag-repair' / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src if src.exists() else full, dst)
            full.write_text(out, encoding='utf-8')
            written += 1
            print('  wrote %s' % rel)
    print('  files written: %d' % written)
    return 0


if __name__ == '__main__':
    sys.exit(main())
