#!/usr/bin/env python3
"""
Tests for the installer's vault-configuration check.

Why this exists: a Hermes Brain with no vault is a *working* Hermes Brain. Every
subsystem degrades to empty-but-valid, the scripts exit 0, and the graph
returns nothing while reporting nothing. A fresh install is therefore
indistinguishable from a broken one -- and the natural reading is "the graph is
broken" rather than "the graph was never fed".

So the check has to actually distinguish the states. These tests exercise every
branch against a real temporary directory, because a check that cannot fail is
not a check -- the previous installer had exactly that problem and it is called
out in run_verification()'s docstring.

Run:  PYTHONPATH=<repo> python3 tests/test_install_vault_check.py
"""

import importlib.util
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_installer():
    spec = importlib.util.spec_from_file_location("hb_install", REPO / "install.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_check(mod, env_text=None, env_exists=True):
    """Run check_vault_config against a temporary .env, capturing its output."""
    buf = io.StringIO()
    original_root = mod.REPO_ROOT
    tmp = Path(tempfile.mkdtemp(prefix="vaultchk-"))
    try:
        mod.REPO_ROOT = tmp
        if env_exists:
            if env_text is None:
                env_text = ""
            (tmp / ".env").write_text(env_text, encoding="utf-8")
        with redirect_stdout(buf):
            result = mod.check_vault_config()
        return result, buf.getvalue()
    finally:
        mod.REPO_ROOT = original_root


class TestNoEnvAtAll(unittest.TestCase):
    def test_reports_clearly_and_does_not_raise(self):
        mod = load_installer()
        result, out = run_check(mod, env_exists=False)
        self.assertIsNone(result)
        self.assertIn("No .env", out)

    def test_points_at_the_documentation(self):
        mod = load_installer()
        _, out = run_check(mod, env_exists=False)
        self.assertIn("README.md", out)


class TestUnsetVaultPaths(unittest.TestCase):
    """The common fresh-install case: example.env copied, paths still blank."""

    def setUp(self):
        self.mod = load_installer()
        self.env = "HERMES_OPERATOR_NAME=bob\nORACLE_BRAIN_PATH=\nACTIVE_WIKI_PATH=\n"

    def test_blank_values_count_as_unset(self):
        result, out = run_check(self.mod, self.env)
        self.assertEqual(len(result["unset"]), 2)
        self.assertIn("not set in .env", out)

    def test_names_both_variables(self):
        _, out = run_check(self.mod, self.env)
        self.assertIn("ORACLE_BRAIN_PATH=", out)
        self.assertIn("ACTIVE_WIKI_PATH=", out)

    def test_says_it_will_be_silent_not_loud(self):
        """The whole point: an empty vault does not raise, so the warning has to
        say so, or the user has no way to tell the states apart."""
        _, out = run_check(self.mod, self.env)
        self.assertIn("will not error", out)
        self.assertIn("mistake for a bug", out)

    def test_does_not_raise_an_exception(self):
        """A check that throws on a legitimate starting state is worse than no
        check, so this is asserted rather than assumed."""
        try:
            run_check(self.mod, self.env)
        except Exception as e:  # pragma: no cover - the failure is the message
            self.fail(f"check_vault_config raised on a blank .env: {e}")


class TestMissingDirectories(unittest.TestCase):
    def setUp(self):
        self.mod = load_installer()

    def test_nonexistent_directory_is_reported_distinctly(self):
        result, out = run_check(
            self.mod, "ORACLE_BRAIN_PATH=/nonexistent/place/xyz\n")
        self.assertEqual(len(result["missing"]), 1)
        self.assertIn("no such directory", out)

    def test_a_file_where_a_directory_belongs_is_reported(self):
        with tempfile.NamedTemporaryFile(suffix=".md") as f:
            result, out = run_check(self.mod, f"ORACLE_BRAIN_PATH={f.name}\n")
        self.assertEqual(len(result["missing"]), 1)
        self.assertIn("not a directory", out)

    def test_a_bad_path_is_not_also_reported_as_unset(self):
        """A set-but-nonexistent path is 'missing', not 'unset'. The two are
        different problems: unset means you never configured it, missing means
        you configured it wrongly."""
        result, _ = run_check(
            self.mod, "ORACLE_BRAIN_PATH=/nonexistent/place/xyz\nACTIVE_WIKI_PATH=/tmp\n")
        self.assertEqual(len(result["unset"]), 0)
        self.assertEqual(len(result["missing"]), 1)
        self.assertEqual(result["missing"][0][0], "ORACLE_BRAIN_PATH")

    def test_an_absent_key_is_unset_even_when_its_sibling_is_missing(self):
        result, _ = run_check(self.mod, "ORACLE_BRAIN_PATH=/nonexistent/place/xyz\n")
        self.assertEqual([v for v, _ in result["unset"]], ["ACTIVE_WIKI_PATH"])
        self.assertEqual(len(result["missing"]), 1)


class TestWorkingVault(unittest.TestCase):
    def setUp(self):
        self.mod = load_installer()
        self.vault = Path(tempfile.mkdtemp(prefix="fakevault-"))
        for i in range(3):
            (self.vault / f"n{i}.md").write_text(f"# note {i}\n", encoding="utf-8")
        self.env = (f"ORACLE_BRAIN_PATH={self.vault}\n"
                    f"ACTIVE_WIKI_PATH={self.vault}\n")

    def test_counts_the_markdown_files(self):
        result, out = run_check(self.mod, self.env)
        self.assertEqual(len(result["ready"]), 2)
        self.assertIn("3 markdown files", out)

    def test_says_when_no_graph_has_been_built(self):
        """A vault that exists but was never indexed is the exact silent state
        this check exists to catch."""
        _, out = run_check(self.mod, self.env)
        self.assertIn("no graph built yet", out)

    def test_reports_a_built_graph_and_stops_nagging(self):
        out_dir = self.vault / "graphify-out"
        out_dir.mkdir()
        (out_dir / "graph.json").write_text("{}", encoding="utf-8")
        result, out = run_check(self.mod, self.env)
        self.assertEqual(len(result["ready"]), 2)
        self.assertIn("graph built", out)
        self.assertNotIn("no graph built yet", out)

    def test_a_healthy_vault_emits_no_warnings(self):
        out_dir = self.vault / "graphify-out"
        out_dir.mkdir()
        (out_dir / "graph.json").write_text("{}", encoding="utf-8")
        _, out = run_check(self.mod, self.env)
        self.assertNotIn("[!]", out)


class TestParsing(unittest.TestCase):
    def setUp(self):
        self.mod = load_installer()

    def test_comments_and_blank_lines_are_ignored(self):
        result, _ = run_check(
            self.mod,
            "# a comment\n\n   \nORACLE_BRAIN_PATH=\nACTIVE_WIKI_PATH=\n")
        self.assertEqual(len(result["unset"]), 2)

    def test_quoted_values_are_unwrapped(self):
        v = Path(tempfile.mkdtemp(prefix="q-"))
        result, _ = run_check(self.mod, f'ORACLE_BRAIN_PATH="{v}"\n')
        self.assertEqual(len(result["ready"]), 1)

    def test_a_value_containing_an_equals_sign_is_not_truncated(self):
        result, _ = run_check(self.mod, "A=b=c\nORACLE_BRAIN_PATH=\nACTIVE_WIKI_PATH=\n")
        self.assertEqual(len(result["unset"]), 2)

    def test_tilde_is_expanded(self):
        """A literal '~' in a path is a config mistake; it must be expanded to
        HOME so the check reports the real target, and never echo the raw tilde
        back as if it were a directory name."""
        result, _ = run_check(self.mod, "ORACLE_BRAIN_PATH=~/definitely-not-here\n")
        self.assertEqual(len(result["missing"]), 1)
        reported = result["missing"][0][2]
        self.assertEqual(reported, Path.home() / "definitely-not-here")
        self.assertNotIn("~", reported.as_posix())


class TestItDoesNotObstruct(unittest.TestCase):
    """A missing vault is a legitimate starting state, so this must never be
    the thing that fails an install."""

    def test_returns_data_rather_than_raising(self):
        mod = load_installer()
        result, _ = run_check(mod, "ORACLE_BRAIN_PATH=\nACTIVE_WIKI_PATH=\n")
        self.assertIsInstance(result, dict)
        for key in ("unset", "missing", "ready"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
