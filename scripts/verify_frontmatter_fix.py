#!/usr/bin/env python3
"""Controls for fix_frontmatter_yaml.py.

This script's whole claim is that it changes QUOTING and nothing else. So
the controls assert exactly that, and assert that it refuses to act on the
cases where quoting is the wrong repair.
"""
import importlib.util, io, contextlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    _s = importlib.util.spec_from_file_location(
        'fx', os.path.join(HERE, 'fix_frontmatter_yaml.py'))
    m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(m)

CASES = []


def case(name, ok):
    CASES.append((name, ok))


# 1. An unquoted value with a colon MUST be quoted.
fm = 'okf_version: "0.2"\ndescription: Graphify cron job: nohup+disown'
new, n, _ = m.plan(fm)
case('unquoted colon value IS quoted', n == 1 and '"' in new.split('\n')[1])

# 2. An already-quoted value MUST be left alone. This is the case the
#    first version broke, producing literal garbage on the title line.
fm2 = ('okf_version: "0.2"\n'
       'title: "Graphify cron job restructured: nohup+disown replaces wait"')
new2, n2, _ = m.plan(fm2)
case('already-quoted value untouched', n2 == 0 and new2 == fm2)

# 3. A list value MUST be left alone.
fm3 = 'tags: ["a", "b: c"]\nsources: []'
new3, n3, _ = m.plan(fm3)
case('list value untouched', n3 == 0 and new3 == fm3)

# 4. A plain scalar with no colon MUST be left alone.
fm4 = 'status: active\ntype: research-report'
new4, n4, _ = m.plan(fm4)
case('plain scalar untouched', n4 == 0 and new4 == fm4)

# 5. A block scalar MUST be left alone -- quoting it would change meaning.
fm5 = 'notes: >\n  folded text here'
new5, n5, _ = m.plan(fm5)
case('block scalar untouched', n5 == 0 and new5 == fm5)

# 6. After quoting, the VALUE must be identical once the quotes come off.
import yaml
fm6 = 'description: Alpha: beta gamma\nstatus: active'
new6, _, _ = m.plan(fm6)
b = yaml.safe_load(new6)
case('quoted value round-trips exactly',
     b['description'] == 'Alpha: beta gamma' and b['status'] == 'active')

# 7. A quote inside the value must be escaped, not truncated.
fm7 = 'description: He said "hello: there" loudly'
new7, n7, _ = m.plan(fm7)
b7 = yaml.safe_load(new7)
case('embedded quotes escaped correctly',
     n7 == 1 and b7['description'] == 'He said "hello: there" loudly')

# 8. The semantic guard must reject a plan that CHANGES a value.
tampered = 'okf_version: "0.2"\ndescription: "DIFFERENT TEXT"'
orig = 'okf_version: "0.2"\ndescription: Alpha: beta gamma'
ok, why = m.semantic_equal(orig, tampered)
case('guard rejects a changed value', ok is False)

# 9. The guard must ACCEPT a pure quoting change.
fixed, _, _ = m.plan(orig)
ok2, why2 = m.semantic_equal(orig, fixed)
case('guard accepts a pure quoting change', ok2 is True)

# 10. The guard must REJECT an after-side that does not parse.
ok3, _ = m.semantic_equal(orig, 'description: broken: value: here')
case('guard rejects unparseable after', ok3 is False)

for name, ok in CASES:
    print(f'  {"ok  " if ok else "FAIL"} {name}')
bad = [c for c in CASES if not c[1]]
print(f'\n  {len(CASES) - len(bad)}/{len(CASES)} frontmatter-fix controls passed')
sys.exit(1 if bad else 0)
