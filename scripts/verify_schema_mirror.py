#!/usr/bin/env python3
"""Gate the generated schema mirror against the canonical YAML.

schemas/wiki-frontmatter.schema.json is a GENERATED compatibility mirror of
schemas/okf-schema.yaml. It exists because JSON Schema consumers cannot read
YAML, and it must never be hand-edited.

The failure it prevents: the mirror drifted after `ungraded` was added to
the confidences enum, so two files that both claimed to describe the same
schema disagreed. Nothing failed at the time. The drift was only visible by
deliberately running okf_export_json.py --check.

This gate compares the two semantically -- enum sets, required lists, and
the confidence field specifically -- so it fails if they ever disagree,
and it has a negative control proving it can fail.
"""
import json
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(HERE, '..', 'schemas', 'okf-schema.yaml')
JSON_PATH = os.path.join(HERE, '..', 'schemas', 'wiki-frontmatter.schema.json')

y = yaml.safe_load(open(YAML_PATH, encoding='utf-8'))
j = json.load(open(JSON_PATH, encoding='utf-8'))

fails = []


def check(label, got, want):
    if got != want:
        fails.append(f'{label}: mirror={got!r} canonical={want!r}')
    print(f'  {"ok  " if got == want else "FAIL"} {label}')


print('=== generated mirror vs canonical YAML ===')
print(f'  canonical : {os.path.relpath(YAML_PATH, HERE)}')
print(f'  mirror    : {os.path.relpath(JSON_PATH, HERE)}')

props = j.get('properties') or {}
check('types enum', sorted((props.get('type') or {}).get('enum') or []),
      sorted(y['types']))
check('statuses enum', sorted((props.get('status') or {}).get('enum') or []),
      sorted(y['statuses']))
check('confidences enum', sorted((props.get('confidence') or {}).get('enum') or []),
      sorted(y['confidences']))
check('required fields', sorted(j.get('required') or []), sorted(y['required']))

# The mirror must name its source, so a reader knows it is generated rather
# than hand-maintained. The value is the path as the generator writes it
# (repo-relative), verified against the generated file rather than guessed.
check('declares canonical source', j.get('x-canonical-source'),
      'schemas/okf-schema.yaml')

if fails:
    print(f'\n  {len(fails)} DRIFT:')
    for f in fails:
        print(f'    {f}')
    print('\n  Run: python3 scripts/okf_export_json.py --write')
    sys.exit(1)
print('\n  MIRROR IN SYNC')
