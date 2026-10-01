#!/usr/bin/env python3
"""
Screen + exclusion list for the untitled-source titling pass.

Reviewing all 461 rows by eye found exactly ONE source that does not
belong to the file it sits in:

  AI-Architecture/Neuromorphic-Computing.md
    https://doi.org/10.1142/10269
    resolves to "Real Options in Energy and Commodity Markets" -- a
    finance paper. It appears as a bare entry in the sources list, is
    never mentioned in the body, and shares no vocabulary with the
    file's subject. It is a stray.

It is EXCLUDED rather than titled. Titling it would attach a confident
finance title to a neuromorphic-computing file, and the T2 gate would
then read that as a verified citation. Excluding it keeps the row
untitled, which is the honest state: something in that sources list is
wrong and this work does not know what the right reference was.

Two other rows were screened and CLEARED, recorded here so the screen
is auditable rather than a silent filter:

  Social-Cognition/Stereotype-Threat-Steele.md
    10.1037/0003-066X.59.1.7 flagged on the word "accounting". It is
    Sackett et al. on interpreting stereotype threat, the standard
    critique, and shares {stereotype, threat} with the subject.

  research/calibrate-absence-model-on-real-sessions.md
    10.1111/2041-210x.12333 flagged on "accounting" and "abundance". It
    is a zero-inflated abundance paper, genuinely the right source for
    a file validating a zero/absence model -- and the vault already
    cites it correctly elsewhere in that file.
"""
import json
import os
import sys

REPO = '/home/operator/hermes-brain'
AUDIT = os.path.join(REPO, 'docs/audit/t2-source-titling.json')

# (file, identifier) pairs that must NOT be titled, with the reason.
EXCLUDE = {
    ('AI-Architecture/Neuromorphic-Computing.md', 'doi:10.1142/10269'):
        'Stray source. The DOI resolves to "Real Options in Energy and '
        'Commodity Markets" (Hu, 2002), a finance paper. It sits in the '
        'sources list of a neuromorphic-computing note, is never '
        'referenced in the body, and shares no vocabulary with the '
        'subject. Left untitled because titling it would make the T2 '
        'gate treat a stray URL as a verified citation. The correct '
        'replacement is unknown and is not guessed.',
}

# Rows the screen flagged and a reviewer cleared.
CLEARED = [
    ('Social-Cognition/Stereotype-Threat-Steele.md', 'doi:10.1037/0003-066X.59.1.7',
     'Sackett, Hardison & Cullen (2004) on interpreting stereotype '
     'threat -- the standard critique, and the right source for a '
     'Steele/Aronson note. Shares {stereotype, threat} with subject.'),
    ('research/calibrate-absence-model-on-real-sessions.md',
     'doi:10.1111/2041-210x.12333',
     'A zero-inflated abundance-estimation paper, genuinely the right '
     'source for a file validating a Poisson zero/absence model. '
     'Already cited with a correct title elsewhere in the same file.'),
]


def main():
    path = os.path.join(REPO, 'docs/audit/t2-source-exclusions.json')
    payload = {
        'note': 'Sources deliberately NOT titled during the untitled-'
                'citation pass, and sources the mismatch screen flagged '
                'but a reviewer cleared. Titling an excluded row would '
                'turn "unknown" into "vouched for" and satisfy the T2 '
                'gate on a citation the file should not have made.',
        'excluded': {'%s::%s' % k: v for k, v in EXCLUDE.items()},
        'screened_and_cleared': {
            '%s::%s' % (f, i): {'title': None, 'reason': r}
            for f, i, r in CLEARED},
    }
    if '--check' in sys.argv:
        print('  excluded     : %d' % len(payload['excluded']))
        print('  cleared      : %d' % len(payload['screened_and_cleared']))
        return
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    print('  wrote %s' % path)


if __name__ == '__main__':
    main()
