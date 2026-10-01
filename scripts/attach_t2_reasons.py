"""Re-attach every adjudication reason to the evidence table.

The reasons live in the two decision scripts; the table stores the
verdict. That split is what let a restore of the table silently drop 27
reasons -- an override with no recorded justification is exactly what
this whole exercise is trying to avoid, so it is made idempotent and
re-runnable rather than done by hand.

Run after any restore of docs/audit/t2-adjudication.json.
"""
import importlib.util
import json
import os
from collections import Counter

REPO = '/home/operator/hermes-brain'
TABLE = os.path.join(REPO, 'docs/audit/t2-adjudication.json')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    band = load('band', os.path.join(REPO, 'scripts/adjudicate_t2_band.py'))
    rest = load('rest', os.path.join(REPO,
                                     'scripts/adjudicate_t2_rest.py'))
    tbl = json.load(open(TABLE, encoding='utf-8'))

    reasons = {}
    for path, ident, _v, reason in band.ADJUDICATION:
        reasons['%s::%s' % (path, ident)] = reason
    dec_file = '/home/operator/.hermes/cache/scratch/decisions.json'
    if os.path.exists(dec_file):
        for d in json.load(open(dec_file, encoding='utf-8')):
            reasons['%s::%s' % (d['path'], d['ident'])] = d['reason']

    applied, missing, unkeyed = 0, [], []
    for key, reason in reasons.items():
        if key not in tbl:
            unkeyed.append(key)
            continue
        tbl[key]['reason'] = reason
        tbl[key]['adjudicated'] = True
        applied += 1

    flagged = [k for k, v in tbl.items() if v.get('adjudicated')]
    print('  reasons available : %d' % len(reasons))
    print('  applied           : %d' % applied)
    print('  unkeyed           : %d' % len(unkeyed))
    print('  flagged in table  : %d' % len(flagged))
    no_reason = [k for k in flagged if not tbl[k].get('reason')]
    print('  flagged w/o reason: %d' % len(no_reason))
    for k in (unkeyed + no_reason)[:5]:
        print('      %s' % k[88:])
    if unkeyed:
        raise SystemExit('refusing: reasons naming no real row')
    with open(TABLE, 'w', encoding='utf-8') as fh:
        json.dump(tbl, fh, indent=1, sort_keys=True)
    print('  wrote %s' % TABLE)


if __name__ == '__main__':
    main()
