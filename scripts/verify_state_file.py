#!/usr/bin/env python3
"""The state file is markdown that must ALSO parse as YAML, because a new
context window will machine-read it. An unquoted colon in a value silently
breaks that, and the failure mode is invisible to a human reading the prose.

So: parse it, and if it fails, report EVERY unquoted-colon risk rather than
fixing one at a time.
"""
import re, sys, yaml

P = '/home/operator/hermes-brain/docs/WIKI-GOLD-STANDARD-STATE.md'

try:
    d = yaml.safe_load(open(P, encoding='utf-8'))
    print('PARSES OK')
except yaml.YAMLError as e:
    print('PARSE FAILED:')
    print(' ', str(e)[:300])
    mark = getattr(e, 'problem_mark', None)
    if mark:
        print(f'  at line {mark.line + 1}')
        lines = open(P, encoding='utf-8').read().split('\n')
        for i in range(max(0, mark.line - 2), min(len(lines), mark.line + 2)):
            tag = '>>' if i == mark.line else '  '
            print(f'  {tag} L{i+1}: {lines[i][:100]}')
    sys.exit(1)

print(f'  top-level keys : {len(d)}')
print(f'  phases         : {len(d.get("phases", []))}')
ids = [p['id'] for p in d.get('phases', [])]
dupes = [i for i in set(ids) if ids.count(i) > 1]
print(f'  phase ids      : {ids}')
print(f'  duplicates     : {dupes if dupes else "none"}')
v = d.get('vaults', {})
print(f'  active wiki    : {v.get("active_wiki")}')
print(f'  oracle brain   : {v.get("oracle_brain")}')
print(f'  off_limits     : {len(d.get("off_limits", []))} entries')
print(f'  ledger entries : {d.get("ledger", "").count("2026-09-28")}')
print(f'  rubric status  : {d.get("confidence_rubric_status")}')
print(f'  next_action    : {d.get("next_action", "").splitlines()[0][:60]}')
print(f'  history items  : {d.get("history", "").count("  ") and "present"}')

# Now scan for any REMAINING unquoted-colon risk, so this cannot recur.
print('\n=== scanning for unquoted colons in scalar positions ===')
risky = []
for i, line in enumerate(open(P, encoding='utf-8').read().split('\n'), 1):
    s = line.rstrip()
    if not s or s.lstrip().startswith('#'):
        continue
    m = re.match(r'^(\s*)([A-Za-z_][\w.-]*):\s+(.*)$', s)
    if not m:
        continue
    indent, key, val = m.groups()
    v = val.strip()
    if v.startswith(('|', '>', '[', '{', '"', "'", '&', '*')):
        continue
    # A bare scalar containing ": " breaks YAML.
    if ': ' in v or v.endswith(':'):
        risky.append((i, key, v[:70]))
if risky:
    for i, k, v in risky:
        print(f'  L{i}  {k}: {v}   <-- UNQUOTED COLON, will break YAML')
    sys.exit(1)
print('  none found')
