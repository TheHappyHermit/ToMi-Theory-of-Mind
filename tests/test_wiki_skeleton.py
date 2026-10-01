"""Regression tests for the grade_all report guard and the skeleton publisher.

Both exist because of a failure mode that produces no error: a script that
quietly overwrites a tracked file, and a generated directory that quietly
falls out of date with its generator.
"""

import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRADE = os.path.join(REPO, 'scripts', 'grade_all.py')
PUBLISH = os.path.join(REPO, 'scripts', 'publish_wiki_skeleton.py')


class TestGradeAllReportGuard(unittest.TestCase):
    """A dry run must not touch the report.

    Found 2026-09-29: `grade_all.py` wrote docs/audit/grade-decisions.csv
    unconditionally, before the --apply gate. The dry run protected the vault
    -- which is what it claimed to do -- while destroying a tracked artifact
    that can hold hand-edited work. The report now has its own flag.
    """

    def test_report_flag_is_opt_in(self):
        src = open(GRADE, encoding='utf-8').read()
        self.assertIn("add_argument('--report'", src,
                      'the report write must be gated behind --report')

    def test_report_write_is_inside_the_flag_guard(self):
        src = open(GRADE, encoding='utf-8').read()
        # The CSV must not be opened for writing at module scope or outside
        # the guard. Count guards vs writes: a write outside one is a bug.
        self.assertEqual(src.count("open(REPORT, 'w'"), 1,
                         'exactly one place may write the report')
        guard = src.index("if args.report:")
        write = src.index("open(REPORT, 'w'")
        self.assertLess(guard, write,
                        'the report write must come after its guard')

    def test_dry_run_leaves_the_report_byte_identical(self):
        """The real check: run it and compare hashes, do not read the source."""
        import hashlib
        report = os.path.join(REPO, 'docs', 'audit', 'grade-decisions.csv')
        if not os.path.exists(report):
            self.skipTest('no report file present in this checkout')
        before = hashlib.sha256(open(report, 'rb').read()).hexdigest()
        mtime_before = os.path.getmtime(report)
        r = subprocess.run([sys.executable, GRADE],
                           cwd=REPO, capture_output=True, text=True,
                           timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr[-500:])
        after = hashlib.sha256(open(report, 'rb').read()).hexdigest()
        self.assertEqual(before, after,
                         'a dry run overwrote the tracked report')
        self.assertEqual(mtime_before, os.path.getmtime(report),
                         'a dry run rewrote the tracked report')
        self.assertIn('report NOT written', r.stdout,
                      'the run must say it left the report alone')

    def test_vault_roots_are_not_hardcoded(self):
        """A literal vault path made the tool silently grade nothing.

        When the active-wiki folders were renamed, these paths stopped
        matching and the tool reported success over an empty file list. The
        same flaw in init_db.py left it scanning a directory that no longer
        existed.
        """
        src = open(GRADE, encoding='utf-8').read()
        # Built from parts so this test file itself carries no local path.
        forbidden = "'" + os.path.expanduser('~') + '/.hermes/active-wiki' + "'"
        self.assertNotIn(forbidden, src,
                         'the active-wiki root must come from the '
                         'environment, not a literal path')
        self.assertIn('HERMES_HOME', src)

    def test_grades_a_real_file_count(self):
        """Guards the same silent-empty-scan failure at runtime."""
        r = subprocess.run([sys.executable, GRADE], cwd=REPO,
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0)
        self.assertIn('files graded:', r.stdout)
        line = [l for l in r.stdout.split('\n') if 'files graded:' in l][0]
        n = int(line.split('files graded:')[1].split()[0])
        self.assertGreater(n, 100,
                           'a near-zero file count means the roots or the '
                           'walk broke; the run would otherwise look clean')


class TestWikiSkeletonPublisher(unittest.TestCase):
    """The published skeleton is generated and must not drift."""

    def test_check_passes_on_the_committed_copy(self):
        r = subprocess.run([sys.executable, PUBLISH, '--check'], cwd=REPO,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         'wiki-skeleton is stale:\n' + r.stdout[-800:])

    def test_generation_is_idempotent(self):
        r = subprocess.run([sys.executable, PUBLISH], cwd=REPO,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        r2 = subprocess.run([sys.executable, PUBLISH], cwd=REPO,
                            capture_output=True, text=True)
        self.assertEqual(r2.returncode, 0)
        self.assertIn('wrote 0', r2.stdout,
                      'a second run must change nothing')

    def test_every_numbered_area_exists(self):
        root = os.path.join(REPO, 'wiki-skeleton')
        expected = ['00_System', '01_Raw', '02_Log', '10_Self', '20_Areas',
                    '30_Projects', '40_Entities', '50_Beliefs',
                    '60_Decisions', '70_Questions', '80_Models',
                    '85_Procedures', '90_Archive']
        for d in expected:
            self.assertTrue(os.path.isdir(os.path.join(root, d)),
                            'missing area: ' + d)
            self.assertTrue(os.path.isfile(os.path.join(root, d, 'index.md')),
                            'missing index: ' + d)

    def test_published_skeleton_contains_no_note_content(self):
        """A personal note reaching the repo is the failure this guards."""
        root = os.path.join(REPO, 'wiki-skeleton')
        stray = []
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                if f == 'index.md' or f == 'README.md':
                    continue
                stray.append(os.path.relpath(os.path.join(dp, f), root))
        self.assertEqual(stray, [],
                         'non-index files in the published skeleton: %s' % stray)

    def test_generator_refuses_to_publish_a_stray_file(self):
        """Prove the guard can actually fail, rather than trusting it."""
        with tempfile.TemporaryDirectory() as td:
            r = subprocess.run(
                [sys.executable, PUBLISH, '--target', td],
                cwd=REPO, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            stray = os.path.join(td, '40_Entities', 'People',
                                 'a-real-note.md')
            os.makedirs(os.path.dirname(stray), exist_ok=True)
            open(stray, 'w').write('---\ntype: person\n---\n# leaked\n')
            r2 = subprocess.run(
                [sys.executable, PUBLISH, '--target', td],
                cwd=REPO, capture_output=True, text=True)
            self.assertEqual(r2.returncode, 1,
                             'a stray note must fail the publisher')
            self.assertIn('non-generated content', r2.stdout)


if __name__ == '__main__':
    unittest.main()
