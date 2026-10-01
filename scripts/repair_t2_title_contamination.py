"""Repair the carried-over `title` field in t2-verification.json.

THE DEFECT
----------
Five rows carried the title "Entanglement-induced provable and robust quantum
learning advantages" -- the title of 10.1038/s41534-025-01078-x, a Nature
Physics paper. That row legitimately owns it. The other five did not.

Every contaminated row also carried a `note` naming the CORRECT resolved
title, so the file contradicted itself: `note` said one paper, `title` said
another. The `note` is the trustworthy field; `title` is the corrupted one.

Verified against the primary sources before this repair (not inferred):

  10.1038/s41534-025-01078-x  Entanglement-induced provable and robust
                               quantum learning advantages   <- CORRECT here
  arXiv:2607.18704            What the Waveform Knows: Transparent-first
                               Speech and Audio Intelligence with Caption Studio
  arXiv:2608.29685            Last Step Matters: Early Uncertainty Cannot
                               Predict Failure in Long-Horizon Agents
  arXiv:2512.24722            Equivalence of Personalized PageRank and
                               Successor Representations
  arXiv:2509.14347            On the Illusion of Success: An Empirical Study
                               of Build Reruns and Silent Failures in
                               Industrial CI
  arXiv:2609.26836            Silent Failures in Agent-Tool Interaction:
                               An Audit of ToolUniverse

WHY IT HAPPENED
---------------
The contaminated rows were hand-written during the manual T2 repair (commit
9c55494), not written by verify_t2_titles.py. That script emits
`{'verdict': ..., 'title': <the title it just resolved for THIS key>}`, and
its resolution is keyed per-identifier, so it cannot emit another paper's
title. A human assembling the row copied a neighbouring row's dict. The
verdict is unaffected -- `match`/`untitled_citation` was decided on the real
title, which is why the file's verdicts stayed sound while `title` rotted.

WHAT THIS SCRIPT DOES
---------------------
Corrects `title` on exactly the rows whose stored title is the known-bad
string, and only those. It refuses to touch a row whose title is already
correct, so it is safe to re-run and cannot overwrite good data. Every
correction records `title_corrected_from` and `title_source` so the next
reader can see the field was repaired rather than resolved.

It does NOT change any verdict. Verdicts were correct.
"""
import json
from pathlib import Path

# Repo-relative, so the script works from any checkout and carries no
# home path. The prevailing idiom in scripts/ (16 uses of HERE, plus
# ROOT elsewhere) is to derive it from __file__.
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / 'docs/audit/t2-verification.json'

# The single contaminated value, and the one row that legitimately owns it.
BAD_TITLE = ('Entanglement-induced provable and robust quantum learning '
             'advantages')
LEGITIMATE_OWNER = ('AI-Architecture/AI-Architecture-Historical-Context-and-'
                    'Alternatives.md::doi:10.1038/s41534-025-01078-x')

# Resolved against arxiv.org/abs/<id> and api.crossref.org on 2026-09-30.
CORRECT = {
    'research/batch261-the-three-numbers-the-panel-cannot-be-wrong-about.md::arxiv:2607.18704':
        'What the Waveform Knows: Transparent-first Speech and Audio '
        'Intelligence with Caption Studio',
    'research/batch264-the-verdict-nobody-reads.md::arxiv:2608.29685':
        'Last Step Matters: Early Uncertainty Cannot Predict Failure in '
        'Long-Horizon Agents',
    'research/batch276-the-edge-that-does-not-know-which-way-time-runs.md::arxiv:2512.24722':
        'Equivalence of Personalized PageRank and Successor Representations',
    'research/batch287-the-action-gate-that-cannot-block-because-it-speaks-a-language-the-host-does-not-parse.md::arxiv:2509.14347':
        'On the Illusion of Success: An Empirical Study of Build Reruns and '
        'Silent Failures in Industrial CI',
    'research/batch287-the-action-gate-that-cannot-block-because-it-speaks-a-language-the-host-does-not-parse.md::arxiv:2609.26836':
        'Silent Failures in Agent-Tool Interaction: An Audit of ToolUniverse',
}

SOURCES = {
    'arxiv': 'https://arxiv.org/abs/',
    'doi': 'https://api.crossref.org/works/',
}


def source_url(key):
    kind, _, ident = key.rpartition('::')
    scheme, _, value = ident.partition(':')
    base = SOURCES.get(scheme)
    return (base + value) if base else 'unknown'


def main():
    results = json.loads(OUT.read_text())

    # Audit first, mutate second. Read the whole file, decide everything, and
    # only then write -- so a surprise halfway through cannot leave the file
    # half-repaired.
    plan = []
    for key, entry in results.items():
        if not isinstance(entry, dict):
            continue
        if key == LEGITIMATE_OWNER:
            if entry.get('title') == BAD_TITLE:
                plan.append((key, entry, None, 'owner, left alone'))
            continue
        if entry.get('title') != BAD_TITLE:
            continue
        fixed = CORRECT.get(key)
        if fixed is None:
            # Contaminated but I have no verified replacement. Refuse to
            # guess: a wrong title is the exact defect being repaired, and
            # inventing a second one would be worse than leaving this.
            plan.append((key, entry, None, 'CONTAMINATED, no verified fix'))
        else:
            plan.append((key, entry, fixed, 'corrected'))

    unfixed = [p for p in plan if p[3] == 'CONTAMINATED, no verified fix']
    if unfixed:
        print('REFUSING TO WRITE: %d contaminated row(s) with no verified '
              'replacement:' % len(unfixed))
        for key, _, _, _ in unfixed:
            print('  ' + key)
        return 1

    changed = 0
    for key, entry, fixed, action in plan:
        if action != 'corrected':
            print('  skip   %s (%s)' % (key[:60], action))
            continue
        entry['title_corrected_from'] = entry.get('title')
        entry['title'] = fixed
        entry['title_source'] = source_url(key)
        changed += 1
        print('  fix    %s' % key[:70])
        print('           was: %s' % entry['title_corrected_from'][:60])
        print('           now: %s' % fixed[:60])

    if changed:
        OUT.write_text(json.dumps(results, indent=1, sort_keys=True) + '\n')
    print('\n%d row(s) corrected; verdicts untouched.' % changed)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
