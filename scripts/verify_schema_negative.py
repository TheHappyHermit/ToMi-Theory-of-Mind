#!/usr/bin/env python3
"""A negative control that ACTUALLY mutates, or it proves nothing.

The first attempt injected a bogus type using the anchor "  - type\\n". After
the schema was re-serialised by yaml.safe_dump the list items are flush
left ("- type\\n"), so the replace matched nothing, the file was unchanged,
and the gate correctly reported SCHEMA OK. The test was vacuous -- it would
have passed against a completely broken gate.

This version derives the anchor from the parsed document, so it cannot
silently no-op, and it ASSERTS that the file actually changed before
trusting the gate's verdict.
"""
import hashlib, shutil, subprocess, sys

P = '/home/operator/hermes-brain/schemas/okf-schema.yaml'
BAK = '/tmp/negctl.bak'
shutil.copy2(P, BAK)


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def gate():
    r = subprocess.run(['python3', 'scripts/verify_schema_integrity.py'],
                       capture_output=True, text=True,
                       cwd='/home/operator/hermes-brain')
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:]


print('=== control 0: unmodified file must PASS ===')
rc, last = gate()
print(f'  exit={rc}  {last}  {"OK" if rc == 0 else "*** should have passed"}')

CASES = [
    ('add a bogus page type', 'types', lambda d: d['types'].append('bogus_type')),
    ('add a bogus status', 'statuses', lambda d: d['statuses'].append('bogus_status')),
    ('add a required field', 'required', lambda d: d['required'].append('bogus_field')),
    ('delete a required field', 'required', lambda d: d['required'].remove('sources')),
    ('delete a whole top-level key', 'epistemic', lambda d: d.pop('epistemic')),
    ('delete type_map', 'type_map', lambda d: d.pop('type_map')),
    # The confidences pin gained `ungraded` on 2026-09-28. A pin with no
    # matching negative test is a pin nobody has checked, so when the enum
    # grows the control has to grow with it.
    ('remove ungraded from confidences', 'confidences',
     lambda d: d.__setitem__('confidences', [c for c in d['confidences']
                                              if c != 'ungraded'])),
    ('add a bogus confidence level', 'confidences',
     lambda d: d['confidences'].append('very-high')),
    # Same again for `not_applicable`, added 2026-09-28 for the 167
    # table-of-contents pages. The pattern is now: every enum value has a
    # negative control, so a value cannot be added or removed without
    # this test noticing.
    ('remove not_applicable from confidences', 'confidences',
     lambda d: d.__setitem__('confidences', [c for c in d['confidences']
                                              if c != 'not_applicable'])),
]

print('\n=== negative controls: each MUST make the gate fail ===')
import yaml
results = []
for label, key, mutate in CASES:
    shutil.copy2(BAK, P)
    d = yaml.safe_load(open(P))
    try:
        mutate(d)
    except Exception as e:
        results.append((label, 'SKIP', f'mutation failed: {e}'))
        print(f'  {label:32} SKIP ({e})')
        continue
    with open(P, 'w') as f:
        yaml.safe_dump(d, f, sort_keys=False, default_flow_style=False)

    before, after = md5(BAK), md5(P)
    if before == after:
        results.append((label, 'VACUOUS', 'file did not change'))
        print(f'  {label:32} *** VACUOUS - file unchanged, test proves nothing')
        continue

    rc, last = gate()
    ok = rc != 0
    results.append((label, 'PASS' if ok else 'FAIL', last[0] if last else ''))
    print(f'  {label:32} {"detected" if ok else "*** NOT DETECTED"}  {last[0] if last else ""}')

shutil.copy2(BAK, P)

print('\n=== restore and confirm green again ===')
rc, last = gate()
print(f'  exit={rc}  {last}  {"OK" if rc == 0 else "*** FAILED TO RESTORE"}')

fails = [r for r in results if r[1] != 'PASS']
print(f'\n=== VERDICT: {len(results) - len(fails)}/{len(results)} negative controls detected ===')
if fails:
    print('  PROBLEMS:')
    for r in fails:
        print(f'    {r[0]}: {r[1]} {r[2]}')
    sys.exit(1)
