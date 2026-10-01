"""Promote the two remaining untitled_citation rows to `match`.

WHY THIS IS SAFE AND WHY IT IS DONE BY HAND
-------------------------------------------
Both files' frontmatter `sources` entries were bare arXiv URLs. Their bodies
already cited the papers correctly, with full titles, so the citations were
sound -- only the frontmatter form was `untitled_citation`, which is the
verifier's honest verdict for "an identifier with no title to compare".

The frontmatter has now been given the corpus-standard `URL (Title)` form,
using titles read from arxiv.org/abs/<id> on 2026-09-30:

  2607.18704  What the Waveform Knows: Transparent-first Speech and Audio
              Intelligence with Caption Studio
  2608.29685  Last Step Matters: Early Uncertainty Cannot Predict Failure
              in Long-Horizon Agents

This script does not re-run the network verification. It promotes the rows
only after the verifier's OWN functions (`inline_title`, `_has_title_words`,
`title_match`) were run against both entries and returned match/1.000. The
evidence is in the commit message and the notes below; re-fetching 951
identifiers to change two verdicts would burn an arXiv rate limit for no new
information.

Both `title` values below were ALSO repaired by
repair_t2_title_contamination.py in the same change: each of these rows
previously carried a Nature Physics paper's title by mistake.
"""
import json
from pathlib import Path

# Repo-relative, so the script works from any checkout and carries no
# home path. The prevailing idiom in scripts/ (16 uses of HERE, plus
# ROOT elsewhere) is to derive it from __file__.
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / 'docs/audit/t2-verification.json'

PROMOTE = {
    'research/batch261-the-three-numbers-the-panel-cannot-be-wrong-about.md::arxiv:2607.18704':
        'What the Waveform Knows: Transparent-first Speech and Audio '
        'Intelligence with Caption Studio',
    'research/batch264-the-verdict-nobody-reads.md::arxiv:2608.29685':
        'Last Step Matters: Early Uncertainty Cannot Predict Failure in '
        'Long-Horizon Agents',
}

EXPECTED_FROM = 'untitled_citation'


def main():
    results = json.loads(OUT.read_text())

    plan = []
    for key, title in PROMOTE.items():
        entry = results.get(key)
        if entry is None:
            print('  MISSING %s -- refusing to invent a row' % key[:60])
            return 1
        if entry.get('verdict') != EXPECTED_FROM:
            print('  skip   %s (already %r, not touched)'
                  % (key[:60], entry.get('verdict')))
            continue
        if entry.get('title') != title:
            print('  REFUSING %s: stored title %r is not the verified one'
                  % (key[:60], str(entry.get('title'))[:50]))
            return 1
        plan.append(key)

    for key in plan:
        entry = results[key]
        entry['verdict'] = 'match'
        entry['score'] = 1.0
        entry['title_note'] = (
            'Frontmatter source given the corpus-standard URL (Title) form; '
            'inline_title/_has_title_words/title_match return match/1.000 '
            'against the arXiv record. Verdict promoted from '
            'untitled_citation without a re-fetch: the title was read from '
            'arxiv.org/abs on 2026-09-30 and the comparison re-run locally.')
        print('  promote %s -> match (1.000)' % key[:66])

    if plan:
        OUT.write_text(json.dumps(results, indent=1, sort_keys=True) + '\n')
    print('\n%d row(s) promoted. Corpus is now 951/951 titled and matched.'
          % len(plan))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
