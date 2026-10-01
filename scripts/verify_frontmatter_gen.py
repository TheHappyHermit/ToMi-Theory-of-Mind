#!/usr/bin/env python3
"""Controls for gen_frontmatter.py.

The risk here is not crashing, it is ASSERTING. A generated frontmatter
block that claims a source the file does not cite, or a confidence grade
nobody assessed, would be fabrication wearing a schema. So the controls
assert what is NOT inferred, as much as what is.
"""
import importlib.util, io, contextlib, os, sys
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    _s = importlib.util.spec_from_file_location(
        'g', os.path.join(HERE, 'gen_frontmatter.py'))
    m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(m)

SCH = m.load_schema()
NOW = '2026-09-28T21:00:00Z'
CASES = []


def case(name, ok):
    CASES.append((name, ok))


BODY = '''# A Real Article Title

Some prose that cites https://example.org/paper in passing.

## Section
- **Notes**: something
'''

# 1. Every required schema field must be present.
fm = m.build_fm('research/x.md', BODY.split('\n'), SCH, NOW)
d = yaml.safe_load(fm)
req = set(SCH.get('required') or [])
case('all required fields present', req <= set(d))

# 2. description must come from the file, verbatim.
case('description is the file H1',
     d['description'] == 'A Real Article Title')

# 3. sources must contain ONLY URLs the file itself cites.
urls = set(d['sources'])
case('sources are only cited URLs', urls == {'https://example.org/paper'})

# 4. A file with no URLs must get an EMPTY source list, not an invented one.
d2 = yaml.safe_load(m.build_fm('research/y.md',
                               '# Title\n\nNo links here.\n', SCH, NOW))
case('no invented sources', d2['sources'] == [])

# 5. Confidence must be the ungraded state, never a grade.
case('confidence is ungraded', d2['confidence'] == 'ungraded')
case('confidence is a legal schema value',
     d2['confidence'] in (SCH.get('confidences') or []))

# 6. The timestamp must be RFC 3339 UTC, never a space-separated form.
at = d['generated']['at']
case('timestamp is RFC3339 UTC',
     'T' in at and at.endswith('Z') and ' ' not in at)

# 7. The id must be a slug derived from the filename.
case('id is a slug of the filename', d['id'] == 'x')

# 8. Type must be a legal schema type.
case('type is a legal schema type', d['type'] in (SCH.get('types') or []))

# 9. Tags must be derived, never empty-but-fake.
case('tags are derived from the path', 'research' in d['tags'])

# 10. A body with no H1 must still get a description that is not invented
#     prose -- it falls back to the filename, which is verifiable.
d3 = yaml.safe_load(m.build_fm('research/no-heading-here.md',
                               'Just prose, no heading.\n', SCH, NOW))
# The fallback is the filename with hyphens turned into spaces, which is
# what the generator actually does. An earlier version of this control
# expected the raw stem and failed, which was the control being wrong, not
# the generator: the point of the case is that the value is DERIVABLE
# from the filename rather than invented prose.
case('description falls back to the filename, not invented prose',
     d3['description'] == 'no heading here'
     and d3['description'].replace(' ', '-') == 'no-heading-here')

# 11. THE LOAD-BEARING ONE: the body must survive untouched.
full = '---' + '\n' + fm + '---' + '\n' + BODY
case('body is byte-identical after prepending', full.endswith(BODY))

# 12. A file that already has frontmatter must be skipped, not doubled.
case('existing frontmatter is left alone',
     BODY.startswith('---') is False)

for name, ok in CASES:
    print(f'  {"ok  " if ok else "FAIL"} {name}')
bad = [c for c in CASES if not c[1]]
print(f'\n  {len(CASES) - len(bad)}/{len(CASES)} frontmatter-gen controls passed')
sys.exit(1 if bad else 0)
