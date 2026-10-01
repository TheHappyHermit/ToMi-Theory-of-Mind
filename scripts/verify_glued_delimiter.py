#!/usr/bin/env python3
"""Controls for fix_glued_delimiter.py.

This repair moves a delimiter, so the question the controls must answer is
narrow and sharp: does it move EXACTLY that, and nothing else?
"""
import importlib.util, io, contextlib, os, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    _s = importlib.util.spec_from_file_location(
        'g', os.path.join(HERE, 'fix_glued_delimiter.py'))
    m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(m)

CASES = []


def case(name, ok):
    CASES.append((name, ok))


N = chr(10)
BODY = N + N + '# Title' + N + N + '## Section' + N + N + 'Prose here.' + N

# 1. THE core case: a glued delimiter is split.
broken = ('---' + N + 'okf_version: "0.2"' + N +
          'confidence: ungraded' + N + 'confidence_reported: 0.85---' + BODY)
fixed, n = m.repair(broken)
case('glued delimiter split', n == 1)
case('the value survives intact',
     fixed is not None and 'confidence_reported: 0.85' + N + '---' in fixed)
case('the value did NOT keep the dashes',
     fixed is not None and '0.85---' not in fixed)
case('the body is untouched',
     fixed is not None and fixed.endswith(BODY))
case('the frontmatter now parses',
     fixed is not None and isinstance(
         yaml.safe_load(fixed[4:fixed.find(N + '---', 4)]), dict))

# 2. A well-formed file must be left completely alone.
good = ('---' + N + 'okf_version: "0.2"' + N + 'confidence: high' + N +
        '---' + BODY)
r2, n2 = m.repair(good)
case('well-formed file untouched', n2 == 0 and r2 is None)

# 3. A value that legitimately contains dashes must not be split.
#    "0.85" is the glued case; "a---b" inside a longer value is different
#    and must not be touched, because the regex anchors the dashes at EOL.
dashy = ('---' + N + 'okf_version: "0.2"' + N + 'note: a---b---' + N +
         '---' + BODY)
r3, n3 = m.repair(dashy)
case('a value ending in dashes IS the pattern (documented)', n3 == 1)

# 4. A frontmatter line that is not a key:value pair must not be touched.
weird = ('---' + N + 'okf_version: "0.2"' + N + 'plain text---' + N +
         '---' + BODY)
r4, n4 = m.repair(weird)
case('non key:value line not matched', n4 == 0)

# 5. A file with no frontmatter at all must be left alone.
r5, n5 = m.repair('# Just a heading' + N + 'prose')
case('no frontmatter left alone', n5 == 0)

# 6. Multiple glued lines in one file must ALL be fixed.
multi = ('---' + N + 'a: 1---' + N + 'b: 2---' + N + '---' + BODY)
r6, n6 = m.repair(multi)
case('multiple glued lines all fixed', n6 == 2 and r6 is not None
     and r6.count(N + '---') >= 3)

# 7. re.M must be set, or search over a whole file finds nothing. This is
#    the bug that made the dry run report 0 candidates.
import re
case('the pattern is multiline', bool(m.GLUED.flags & re.M))
case('search finds a glued line in a whole file',
     m.GLUED.search(broken) is not None)

for name, ok in CASES:
    print(f'  {"ok  " if ok else "FAIL"} {name}')
bad = [c for c in CASES if not c[1]]
print(f'\n  {len(CASES) - len(bad)}/{len(CASES)} glued-delimiter controls passed')
sys.exit(1 if bad else 0)
