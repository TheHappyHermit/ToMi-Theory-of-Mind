#!/usr/bin/env python3
"""Phase 3 citation parser controls.

Every guard in ref_entries() exists because a dry run caught it destroying
knowledge. A numbered CONTENT list ("1. **Self-organization...**") sitting
under a References heading is indistinguishable from a reference list line by
shape alone, and an early version of this parser turned such lines into
footnote definitions -- deleting body content.

Run: python3 scripts/verify_citation_parser.py
Exit 0 only if every case behaves as specified.
"""
import importlib.util
import io
import contextlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'citation_refs.py')

_buf = io.StringIO()
with contextlib.redirect_stdout(_buf):
    _spec = importlib.util.spec_from_file_location('citation_refs', SRC)
    m = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(m)

CASES = []


def case(name, expect_desc, got, want):
    ok = (got == want)
    CASES.append((name, ok, expect_desc, got, want))
    return ok


# 1. A numbered content list under a References heading must yield NOTHING.
CONTENT_LIST = '''---
id: t
---
# T
## References
1. **Self-organization without predefined ontologies.** Scale-free structures result.
3. **A universal organizing principle.** Adaptive systems are governed.
2. Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*. https://doi.org/10.1038/nn.3045
'''
case('content list refused', 'must refuse', m.ref_entries(CONTENT_LIST), {})

# 2. A real, ascending reference list must parse -- all three syntaxes.
REAL_LIST = '''---
id: t
---
# T
## References
1. Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*. https://doi.org/10.1038/nn.3045
2. Murray, J. D. (2017). Stable population coding. *PNAS*, 114(10), E1923-E1932.
[[3]] George, D. (2009). Micro-circuits. *PLOS Computational Biology*, 5(10), e1000520.
'''
case('real list parses', '3 references', len(m.ref_entries(REAL_LIST)), 3)

# 3. Bold must not be mistaken for an italic journal title.
case('bold is not a citation signal',
     '**S** must not satisfy the italic test',
     bool(m.CITATION_SIGNAL.search('**Self-organization** and more text')), False)
case('single-italic IS a signal',
     '*PNAS* must satisfy it',
     bool(m.CITATION_SIGNAL.search('Stable coding. *PNAS*, 114(10).')), True)

# 4. A list not starting at 1 is not a reference list.
OFF_BY_ONE = '''---
id: t
---
# T
## References
2. Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*. https://doi.org/10.1/x
3. Murray, J. D. (2017). Stable coding. *PNAS*, 114(10), E1923.
'''
case('off-by-one list refused', 'must refuse', m.ref_entries(OFF_BY_ONE), {})

# 5. No references heading, nothing is a reference.
NO_HEADING = '''---
id: t
---
# T
## Notes
1. Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*. https://doi.org/10.1/x
'''
case('no heading, nothing parsed', 'must refuse', m.ref_entries(NO_HEADING), {})

# 6. PHASE 3.2: the bold-bracket syntax, found in Cognitive-Architecture-Models.md.
#    The parser reported "no reference list" for a file that HAS one, because
#    every line is "**[1]** Author (2007). Title. Press."
BOLD_LIST = '''---
id: t
---
# T
## Sources
**[1]** Anderson, J. R. (2007). A role for systems research. *Psychological Review*, 114(4), 1083-1094.
**[2]** Fuster, E. (2009). Memory. *Science*, 325(5941), 30-33.
**[3]** Gershman, S. J. (2018). Deconstructing the human algorithms. *Trends in Cognitive Sciences*, 22(6), 492-502.
'''
_b = m.ref_entries(BOLD_LIST)
case('bold-bracket list parses', '3 references', len(_b), 3)
case('bold-bracket text kept', 'author and year survive',
     'Anderson' in _b.get(1, ''), True)

# 7. PHASE 3.2: the bullet-bracket list under "## Key Works", which is NOT a
#    References heading but holds exactly a reference list in these files.
KEY_WORKS = '''---
id: t
---
# T
## Key Works
- [1] Large Ontology Models -- arXiv 2602.00029
- [2] OntoLLM -- ESWA 2026
- [3] Semantic Training Gap -- arXiv 2605.11234
'''
_k = m.ref_entries(KEY_WORKS)
case('bullet bracket parses', '3 references', len(_k), 3)
case('key works text kept', 'venue survives', 'ESWA' in _k.get(2, ''), True)

# 8. The guard must STILL hold under a Key Works heading: a numbered content
#    list there is content, not references. This is the control that keeps
#    case 6/7 from weakening case 1.
KEY_WORKS_CONTENT = '''---
id: t
---
# T
## Key Works
1. **Self-organization without predefined ontologies.** Scale-free structures result.
3. **A universal organizing principle.** Adaptive systems are governed.
2. Honey, O. J., et al. (2012). ECoG. *Nature Neuroscience*. https://doi.org/10.1/x
'''
case('content list under Key Works refused', 'must refuse',
     m.ref_entries(KEY_WORKS_CONTENT), {})

# 8b. The list heading may be NUMBERED: "## 7. Key Works". An earlier
#     pattern was anchored at the first word and missed this, so
#     frontier-research-ontology-round34 was reported as having no
#     reference list when it had five.
NUMBERED_HEADING = '''---
id: t
---
# T
## 7. Key Works
- [1] GrOIL: Graph-Grounded Domain Ontology Induction (CIKM 2026)
- [2] NeurOWL: Neuro-Symbolic Reasoning Over Incomplete OWL Ontologies
'''
case('numbered Key Works heading parses', '2 references',
     len(m.ref_entries(NUMBERED_HEADING)), 2)

# 9. PHASE 3.2: [[N]](url) is a dead label on a link that already has its
#    source. It must be DETECTED...
INLINE = 'Reduced failed retrievals by 49% [[1]](https://www.anthropic.com/engineering/x) this year.'
case('inline link detected', '1 occurrence', len(m.inline_link_markers(INLINE)), 1)
#    ...and the number must be part of the match, so a transform can drop it
#    without also dropping the URL.
case('inline link keeps url', 'url is captured, not discarded',
     m.inline_link_markers(INLINE)[0][2].startswith('https://www.anthropic.com'), True)

# 10. A bare wikilink marker NOT followed by a link is not an inline link --
#     it may be a real reference marker needing a footnote.
case('bare marker is not an inline link', 'must not match',
     len(m.inline_link_markers('A finding [[1]] with no link.')), 0)

failed = [c for c in CASES if not c[1]]
for name, ok, desc, got, want in CASES:
    mark = 'ok  ' if ok else 'FAIL'
    print(f'  {mark} {name}: {desc}  got={got!r} want={want!r}')
print(f'\n  {len(CASES) - len(failed)}/{len(CASES)} citation parser controls passed')
sys.exit(1 if failed else 0)
