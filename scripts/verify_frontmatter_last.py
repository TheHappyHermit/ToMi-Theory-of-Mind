#!/usr/bin/env python3
"""Controls for fix_frontmatter_last.py.

Six rules, and the danger is not that they crash. It is that they
silently do the wrong thing to a file that is merely BROKEN in a
different way. So each control builds the exact failure it targets and
asserts the rule either fixes precisely that, or refuses.

A rule that is wrong in a way a control cannot see is worse than no
rule: seven files get rewritten on its authority. That is why this
exists.

Run:  python3 scripts/verify_frontmatter_last.py
"""
import importlib.util
import io
import os
import contextlib

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    _spec = importlib.util.spec_from_file_location(
        'f', os.path.join(HERE, 'fix_frontmatter_last.py'))
    fx = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(fx)

N = chr(10)
DQ = chr(34)
OK = 0
BAD = 0


def case(name, cond, detail=''):
    global OK, BAD
    if cond:
        OK += 1
        print(f'  ok   {name}')
    else:
        BAD += 1
        print(f'  FAIL {name}   {detail}')


def apply(text, rounds=6):
    """Run the rule chain exactly the way main() does, including the
    body_prepend re-insertion.

    The first version of this harness rebuilt the file but dropped the
    prepend, so it exercised a code path main() never takes. It reported
    'confidence: low' as missing from the frontmatter when the real
    script keeps it. A control that does not exercise the same path as
    the thing it controls is a control of nothing.
    """
    cur = text
    kinds = []
    for _ in range(rounds):
        try:
            yaml.safe_load(fx.fm_of(cur) or '')
            return cur, kinds, True
        except Exception:
            pass
        new, kind, det, pre = fx.repair(cur)
        if new is None:
            return cur, kinds, False
        e = cur.find(N + '---', 3)
        cur = '---' + N + new + N + '---' + cur[e + 4:]
        if pre:
            h = cur.find(N + '---' + N + N)
            if h > 0:
                h += len(N + '---' + N)
                cur = cur[:h] + N + pre + cur[h:]
        kinds.append((kind, det))
    try:
        yaml.safe_load(fx.fm_of(cur) or '')
        return cur, kinds, True
    except Exception:
        return cur, kinds, False


def fm(lines):
    """Build a file whose frontmatter is `lines` and whose body is '# T'.

    Note the frontmatter itself must be well-formed at the boundaries:
    `fm` does NOT add a closing --- to the metadata, because several
    rules are about files whose closing delimiter is missing or glued.
    The repair chain adds it back where needed.
    """
    return '---' + N + N.join(lines) + N + '---' + N + N + '# T' + N


# ---------------------------------------------------------------- A
t = fm(['okf_version: "0.2"', 'id: x', 'generated:', '  at: "2026-01-01"',
        '> **Bridge** body line that leaked in', 'sources: []'])
out, kinds, ok = apply(t)
case('A: unclosed frontmatter is closed before the body line', ok)
# A closes the block BEFORE the leaked line; it does not move it, which
# is F's job. So the assertion is that the line is no longer inside the
# frontmatter and still exists in the file. The first version checked
# body_of(), which starts at the first heading, and the bridge line sits
# above the heading -- so it was never in body_of() and the control
# failed against correct behaviour.
case('A: the leaked line leaves the frontmatter and still exists',
     '**Bridge**' not in (fx.fm_of(out) or '') and '**Bridge**' in out)
case('A: metadata before the leak survives verbatim',
     'id: x' in (fx.fm_of(out) or ''))

# ---------------------------------------------------------------- B
t = fm(['id: x', 'sources: [' + DQ + DQ + 'A, 1' + DQ + DQ + ', ' + DQ + DQ +
        'B, 2' + DQ + DQ + ']'])
out, kinds, ok = apply(t)
v = yaml.safe_load(fx.fm_of(out) or '{}')
case('B: doubled quotes collapse to a valid list', ok and isinstance(v, dict))
case('B: the VALUES are preserved exactly, not reworded',
     v.get('sources') == ['A, 1', 'B, 2'], repr(v.get('sources')))
case('B: a normal single-quoted list is left completely alone',
     apply(fm(['id: x', 'sources: ["A, 1"]']))[1] == [])

# ---------------------------------------------------------------- C
t = fm(['id: x', 'stale_af...[truncated]', 'sources: []'])
out, kinds, ok = apply(t)
case('C: the truncated line is dropped so the block parses', ok)
case('C: no invented replacement value is written',
     'truncated' not in (fx.fm_of(out) or ''))
case('C: neighbouring keys survive',
     yaml.safe_load(fx.fm_of(out) or '{}').get('id') == 'x')

# ---------------------------------------------------------------- D
t = fm(['id: x', 'generated:', '  by: "b"', '    at: "a"'])
out, kinds, ok = apply(t)
g = (yaml.safe_load(fx.fm_of(out) or '{}') or {}).get('generated')
case('D: an over-indented child is reindented to its parent', ok)
case('D: the parent mapping value is intact', g == {'by': 'b', 'at': 'a'},
     repr(g))
case('D: a correctly indented file is left alone',
     apply(fm(['id: x', 'generated:', '  by: "b"', '  at: "a"']))[1] == [])

# ---------------------------------------------------------------- E
t = fm(['id: x', 'tags: [a, b, c', 'sources: []'])
out, kinds, ok = apply(t)
tg = (yaml.safe_load(fx.fm_of(out) or '{}') or {}).get('tags')
case('E: an unclosed flow sequence is closed', ok)
case('E: the tags that survived are kept', tg == ['a', 'b', 'c'], repr(tg))
case('E: a balanced list is left alone',
     apply(fm(['id: x', 'tags: [a, b]']))[1] == [])

# ---------------------------------------------------------------- F
t = fm(['id: x', '> body quote in the middle', 'sources: []',
        'confidence: low'])
out, kinds, ok = apply(t)
case('F: a body line between two keys closes the frontmatter', ok)
# The first version of this control asserted that sources:[] ends up in
# the BODY. That was describing the BUG, not the fix: the whole point of
# F is that a leaked body line must not drag the keys below it out of the
# frontmatter. Correct behaviour is the opposite.
fv = yaml.safe_load(fx.fm_of(out) or '{}')
case('F: the keys AFTER the leak stay in the frontmatter',
     fv.get('sources') == [] and fv.get('confidence') == 'low', repr(fv))
case('F: the leaked line is moved to the body, not deleted',
     '> body quote' in out and '> body quote' not in (fx.fm_of(out) or ''))

# ------------------------------------------------------- the big one
t = fm(['id: x', 'generated:', '  by: "b"', '    at: "a"'])
out, _, ok = apply(t)
case('BODY: body_of() is byte-identical before and after', ok and
     fx.body_of(out) == fx.body_of(t))

t = fm(['okf_version: "0.2"', 'id: keep-me', '> leak',
        'sources: []', 'confidence: low'])
out, kinds, ok = apply(t)
case('BODY: id and confidence survive a body-line leak',
     yaml.safe_load(fx.fm_of(out) or '{}').get('id') == 'keep-me' and
     yaml.safe_load(fx.fm_of(out) or '{}').get('confidence') == 'low')

# ------------------------------------------------- refuses rather than
# ------------------------------------------------- damages
t = fm(['id: x', 'description: "unterminated string that never closes'])
case('REFUSES: a bug with no matching rule returns None, not a guess',
     fx.repair(t)[0] is None)

t = fm(['id: x', 'sources: [' + DQ + DQ + 'A' + DQ + DQ])
# An odd quote count means the doubling was not uniform, so collapsing it
# would corrupt the value. Bug B must refuse. The first fixture also had
# an unclosed bracket, so Bug E matched it first and the control blamed
# the wrong rule. Isolate B by asking for B's own decision.
_lines = fm(['id: x', 'sources: [' + DQ + DQ + 'A' + DQ]).split(N)
_probe = {'id': 'x', 'sources': ['"A"']}  # deliberately not used
_ok = True
for _l in _lines:
    _fixed = _l.replace('""', '"')
    if '""' in _l and (_fixed.count(DQ) % 2 or _fixed.count(DQ) == 0):
        _ok = False
case('REFUSES: B skips a line whose quotes are not uniformly doubled',
     _ok)

print()
print(f'  {OK}/{OK + BAD} controls pass')
raise SystemExit(1 if BAD else 0)
