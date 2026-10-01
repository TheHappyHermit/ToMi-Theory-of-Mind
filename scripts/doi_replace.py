"""Replace a DOI without matching it inside a LONGER one.

`re.sub(re.escape(bad), new, text)` is wrong when `bad` is a PREFIX of
another identifier in the same file. It happened here:

    bad       10.1016/0010-0285            (a journal ISSN stem)
    new       10.1016/0010-0285(74)90009-7
    other     10.1016/0010-0285(80)90005-5 (a complete, valid DOI)

The stem matched inside the other identifier, so the file ended up
holding

    10.1016/0010-0285(74)90009-7(80)90005-5

Two valid citations destroyed by a repair, and the vault was right
before it. The fix is a boundary: the match must not be followed by a
character that could continue an identifier.

    (?<![0-9A-Za-z./])  before, so we do not start mid-identifier
    (?![\w./(])        after,  so we do not stop before a suffix

The "after" set includes "(" because Elsevier suffixes begin with it,
which is exactly the case that broke.

`replace_doi` returns the number of substitutions so a caller can
assert it matched the expected number of lines rather than assuming.
"""
import re

# Characters that can continue a DOI after the matched prefix. The "("
# matters most: Elsevier suffixes begin with it, which is the case that
# broke.
TAIL = r'(?![\w./(])'
# What may precede the identifier. A DOI usually sits after
# "doi.org/" or "doi:", so "/" and ":" are legal -- but a digit, letter,
# dot or "(" is not, because those mean we are inside a longer token.
HEAD = r'(?<![0-9A-Za-z.(])'


def replace_doi(text, bad, new, expected=None):
    """Replace every WHOLE-token occurrence of `bad` with `new`.

    Raises if `expected` is given and the count differs, so a caller
    cannot silently substitute zero times and still report success --
    the same class of bug as the titler's no-op edit and the
    invalidation that deleted nothing.
    """
    pat = HEAD + re.escape(bad) + TAIL
    out, n = re.subn(pat, new.replace('\\', '\\\\'), text)
    if expected is not None and n != expected:
        raise SystemExit('expected %d replacements of %r, made %d'
                         % (expected, bad, n))
    return out, n


if __name__ == '__main__':
    T = ('- "https://doi.org/10.1016/0010-0285(80)90005-5 (A title)"\n'
         '- "https://doi.org/10.1016/0010-0285(82)90006-8 (Another)"\n'
         '- "https://doi.org/10.1016/0010-0285 (Bare stem)"\n')
    print('  before:')
    for ln in T.strip().split('\n'):
        print('     %s' % ln)
    out, n = replace_doi(T, '10.1016/0010-0285',
                         '10.1016/0010-0285(74)90009-7')
    print('  after (%d replacements):' % n)
    for ln in out.strip().split('\n'):
        print('     %s' % ln)
    assert '(74)90009-7(80)' not in out, 'still splicing'
    print('  OK: the complete DOIs were left alone')
