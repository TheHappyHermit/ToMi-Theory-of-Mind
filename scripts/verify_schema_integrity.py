#!/usr/bin/env python3
"""One-line schema integrity self-test, as the prompt should contain it."""
import sys, yaml

d = yaml.safe_load(open('/home/operator/hermes-brain/schemas/okf-schema.yaml'))
got = (len(d['types']), len(d['statuses']), len(d['required']))
print(f"{got[0]} types {got[1]} statuses {got[2]} required")

expect = (29, 14, 9)
if got != expect:
    print(f"MISMATCH: expected {expect[0]} types {expect[1]} statuses "
          f"{expect[2]} required, got {got}")
    sys.exit(1)

# Top-level keys, not nested under 'enums'.
for k in ('okf_version', 'schema_id', 'required', 'recommended', 'optional',
          'types', 'statuses', 'confidences', 'epistemic', 'type_map',
          'status_map', 'repair'):
    if k not in d:
        print(f"MISSING TOP-LEVEL KEY: {k}")
        sys.exit(1)

# `ungraded` was added 2026-09-28 for the 222 files that carried
# self-reported floats (0.85, 0.92). It means "evidence present, not yet
# classified by confidence_derivation" and is NOT a grade. Converting a float
# to high/medium/low would fabricate a judgement the rubric has not made; the
# original float is preserved beside it as `confidence_reported`.
# If you add a level here, add the negative control for it too -- a pin that
# has no matching negative test is a pin nobody has checked.
if d['confidences'] != ['high', 'medium', 'low', 'ungraded', 'not_applicable']:
    print(f"BAD confidences: {d['confidences']}")
    sys.exit(1)

print("SCHEMA OK")
