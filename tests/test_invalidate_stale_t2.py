"""A script that claims to invalidate rows must actually remove them.

scripts/invalidate_stale_t2.py computed the set of stale rows, printed
a count, and then wrote the table back without deleting any of them.
The verifier resumes from the table it loads at startup, so every run
after an "invalidation" re-derived nothing and reported the same
numbers. Four consecutive runs looked like evidence that a real fix had
failed, when the fix was fine and the invalidation was a no-op.

The same failure shape appeared twice in this work: a titler that
counted edits it never made, and this. Both are silent, both make the
next stage believe the work is done, and neither raises.

These tests assert the property directly: after running the
invalidation, no stale row may remain in the table it wrote.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, 'scripts', 'invalidate_stale_t2.py')
TABLE = os.path.join(REPO, 'docs', 'audit', 't2-verification.json')


class TestInvalidationActuallyRemovesRows(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='inval-')
        self.saved = os.path.join(self.tmp, 'saved.json')
        shutil.copy2(TABLE, self.saved)

    def tearDown(self):
        shutil.copy2(self.saved, TABLE)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_invalidation(self):
        return subprocess.run(
            ['python3', SCRIPT, '--apply'],
            capture_output=True, text=True, timeout=120)

    def seed_stale(self, table, n=3):
        """Inject untitled/mismatch rows so the test has something to
        invalidate. Without this the test passes vacuously on a table
        that is already clean, which is how a broken invalidation would
        sail through the suite.
        """
        keys = [k for k, v in table.items()
                if v.get('verdict') == 'match'][:n]
        self.assertEqual(len(keys), n, 'not enough match rows to seed')
        for i, k in enumerate(keys):
            table[k] = {'verdict': 'untitled_citation' if i % 2 == 0
                        else 'mismatch', 'title': 'Seeded stale row'}
        with open(TABLE, 'w', encoding='utf-8') as fh:
            json.dump(table, fh, indent=1, sort_keys=True)
        return keys

    def test_no_untitled_or_mismatch_row_survives(self):
        before = json.load(open(TABLE, encoding='utf-8'))
        stale = {k: v for k, v in before.items()
                 if v.get('verdict') in ('untitled_citation', 'mismatch')}
        self.seeded = self.seed_stale(before)
        stale = dict(stale)
        stale.update({k: before[k] for k in self.seeded})
        proc = self.run_invalidation()
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        after = json.load(open(TABLE, encoding='utf-8'))
        survivors = [k for k in stale if k in after]
        self.assertEqual(
            survivors, [],
            'these rows were reported as invalidated but are still in '
            'the table: %s' % survivors[:3])

    def test_row_count_actually_decreases(self):
        before = json.load(open(TABLE, encoding='utf-8'))
        self.seed_stale(before)
        before = json.load(open(TABLE, encoding='utf-8'))
        proc = self.run_invalidation()
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        after = json.load(open(TABLE, encoding='utf-8'))
        self.assertLess(
            len(after), len(before),
            'the table has the same number of rows after invalidation, '
            'so nothing was removed')

    def test_matching_rows_are_not_removed(self):
        before = json.load(open(TABLE, encoding='utf-8'))
        self.seed_stale(before)
        before = json.load(open(TABLE, encoding='utf-8'))
        keep = {k for k, v in before.items()
                if v.get('verdict') == 'match'}
        proc = self.run_invalidation()
        self.assertEqual(proc.returncode, 0, proc.stderr[-400:])
        after = json.load(open(TABLE, encoding='utf-8'))
        lost = [k for k in keep if k not in after]
        self.assertEqual(
            lost, [],
            'invalidation removed rows that were already matching: %s'
            % lost[:3])


if __name__ == '__main__':
    unittest.main()
