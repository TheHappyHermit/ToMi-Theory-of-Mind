"""Tests for the health-check contract.

The failure these guard against is specific and already observed: a health
check that reports success while the thing it checks is broken. Two separate
bugs had that shape — a `grep -q` that could never fail, and a script that
exited 0 regardless of its subject.

So the tests here are mostly negative. Each one breaks something on purpose
and asserts the check notices.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

SCRIPTS = Path.home() / ".hermes" / "scripts"


def _have_operands() -> bool:
    """The live organizer has to exist for these to be meaningful."""
    db = Path.home() / ".hermes" / "personal-organizer" / "data" / "organizer.db"
    return db.exists() and (SCRIPTS / "personal_ops.py").exists()


class TestPersonalOpsHealth(unittest.TestCase):
    """`personal_ops.py health` must distinguish healthy from broken."""

    def setUp(self):
        if not _have_operands():
            self.skipTest("organizer or personal_ops.py not present")
        self.ops = SCRIPTS / "personal_ops.py"

    def _run(self, **env):
        e = dict(os.environ)
        for k in ("ORGANIZER_DB_PATH", "ORGANIZER_API_URL"):
            e.pop(k, None)
        e.update(env)
        return subprocess.run(
            [sys.executable, str(self.ops), "health"],
            capture_output=True, text=True, env=e, timeout=60,
        )

    def test_healthy_exits_zero(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, f"healthy stack must exit 0, got:\n{r.stdout}")

    def test_unreachable_api_exits_nonzero(self):
        r = self._run(ORGANIZER_API_URL="http://127.0.0.1:9")
        self.assertNotEqual(r.returncode, 0,
                            "unreachable API must fail the check")

    def test_missing_db_exits_nonzero(self):
        r = self._run(ORGANIZER_DB_PATH="/tmp/definitely-not-here-12345.db")
        self.assertNotEqual(r.returncode, 0,
                            "missing database must fail the check")

    def test_reports_a_specific_reason(self):
        """A boolean with no reason is unactionable; require the reason."""
        import json
        r = self._run(ORGANIZER_API_URL="http://127.0.0.1:9")
        payload = json.loads(r.stdout)
        self.assertFalse(payload["ok"])
        self.assertTrue(payload["problems"], "failure must name a problem")

    def test_healthy_payload_names_what_it_verified(self):
        import json
        payload = json.loads(self._run().stdout)
        self.assertTrue(payload["ok"])
        self.assertIn("database", payload)
        self.assertIn("tasks", payload["counts"])


class TestPersonalOpsWrites(unittest.TestCase):
    """Writes run against a scratch copy; the real database is never touched."""

    def setUp(self):
        if not _have_operands():
            self.skipTest("organizer or personal_ops.py not present")
        self.tmp = tempfile.mkdtemp()
        self.db = Path(self.tmp) / "organizer.db"
        src = Path.home() / ".hermes" / "personal-organizer" / "data" / "organizer.db"
        shutil.copy2(src, self.db)
        self.env = dict(os.environ,
                        ORGANIZER_DB_PATH=str(self.db),
                        ORGANIZER_API_URL="http://127.0.0.1:9")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "personal_ops.py"), *args],
            capture_output=True, text=True, env=self.env, timeout=60,
        )

    def test_add_then_complete(self):
        self.assertEqual(self._run("add", "scratch task").returncode, 0)
        con = sqlite3.connect(self.db)
        tid = con.execute(
            "SELECT id FROM tasks WHERE title='scratch task'").fetchone()[0]
        con.close()
        self.assertEqual(self._run("done", str(tid)).returncode, 0)
        con = sqlite3.connect(self.db)
        status = con.execute(
            "SELECT status FROM tasks WHERE id=?", (tid,)).fetchone()[0]
        con.close()
        self.assertEqual(status, "completed")

    def test_rejects_status_outside_schema(self):
        """The schema has no 'pending' task status; the CLI must not offer it."""
        r = self._run("add", "bad status", "--status", "pending")
        self.assertNotEqual(r.returncode, 0,
                            "a status the CHECK constraint rejects must be refused")

    def test_rejects_unknown_task_id(self):
        r = self._run("done", "999999")
        self.assertNotEqual(r.returncode, 0)

    def test_timestamps_are_rfc3339(self):
        self._run("add", "timestamp check")
        con = sqlite3.connect(self.db)
        ts = con.execute(
            "SELECT created_at FROM tasks WHERE title='timestamp check'").fetchone()[0]
        con.close()
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                         f"created_at must be RFC 3339 UTC, got {ts!r}")


@unittest.skipUnless(
    (SCRIPTS / "daily_health_check.sh").exists(),
    "daily_health_check.sh not present",
)
class TestHealthCheckExitCodes(unittest.TestCase):
    """The wrapper's exit code is what a scheduled run reports.

    The bug this guards: only verify_stack could fail the script, so a broken
    organizer still exited 0 and the run looked green in the log.
    """

    SCRIPT = SCRIPTS / "daily_health_check.sh"

    def _run(self, **env):
        e = dict(os.environ)
        e.update(env)
        return subprocess.run(["bash", str(self.SCRIPT)],
                              capture_output=True, text=True, env=e, timeout=180)

    def test_healthy_stack_exits_zero(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, f"healthy stack must exit 0:\n{r.stdout}")

    def test_broken_organizer_exits_nonzero(self):
        r = self._run(ORGANIZER_API_URL="http://127.0.0.1:9")
        self.assertNotEqual(r.returncode, 0,
                            "a broken organizer must fail the run, not warn")

    def test_reports_all_failures_not_just_the_first(self):
        r = self._run(ORGANIZER_API_URL="http://127.0.0.1:9")
        self.assertIn("Personal Ops has issues", r.stdout)

    def test_uses_current_scripts_tree(self):
        """It must not read the stale ~/personal-agent copy."""
        src = self.SCRIPT.read_text()
        self.assertNotIn("personal-agent/verify_stack.py", src)
        self.assertNotIn("personal-agent/personal_ops.py", src)

    def test_does_not_invoke_gbrain(self):
        """GBrain was removed by decision; the check must not probe for it.

        An earlier version shelled out to `gbrain doctor`, which called a
        stale shim execing a binary that no longer exists, so it failed on
        every run. That is a permanent false negative, not something to
        repair — the guard is that nothing invokes GBrain at all.

        Matching on raw text would false-positive on the comment that explains
        the removal, so this looks only at executable lines: comments and
        quoted strings are excluded.
        """
        import re
        for line in self.SCRIPT.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            code = re.sub(r'"[^"]*"', '""', stripped)   # drop string literals
            self.assertNotIn("gbrain", code.lower(),
                             f"GBrain must not be invoked: {stripped!r}")

    def test_health_check_still_exits_zero_with_gbrain_absent(self):
        r = self._run()
        self.assertEqual(r.returncode, 0,
                         f"GBrain's absence must not fail the run:\n{r.stdout}")
        self.assertIn("GBrain removed", r.stdout)


class TestSecretsCheck(unittest.TestCase):
    """A secrets check must not pass vacuously.

    The failure this guards: creating a directory to satisfy the check would
    make it green while nothing is actually protected.
    """

    def setUp(self):
        live = SCRIPTS / "verify_stack.py"
        if not live.exists():
            self.skipTest("live verify_stack.py not present")
        # Import the LIVE script, not the repo copy: the two are different
        # files, and the repo's has no AUTOGNOSIA_HOME to patch. An earlier
        # version of this test put the repo's scripts/ on sys.path and so
        # tested the wrong file while still passing three of five cases.
        import importlib.util
        spec = importlib.util.spec_from_file_location("live_verify_stack", live)
        if spec is None or spec.loader is None:
            self.skipTest(f"cannot load {live}")
        self.vs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.vs)

    def test_passes_only_for_a_real_700_directory(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            good = Path(d) / "secrets"
            good.mkdir(mode=0o700)
            with mock.patch.object(self.vs, "AUTOGNOSIA_HOME", Path(d)):
                ok, _ = self.vs.check_secrets_dir()
            self.assertTrue(ok, "a 700 directory is a real pass")

    def test_rejects_world_readable(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "secrets"
            bad.mkdir(mode=0o755)
            with mock.patch.object(self.vs, "AUTOGNOSIA_HOME", Path(d)):
                ok, msg = self.vs.check_secrets_dir()
            self.assertFalse(ok, f"755 must fail, got {msg!r}")

    def test_reports_when_nothing_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(self.vs, "AUTOGNOSIA_HOME", Path(d)), \
                 mock.patch.object(self.vs.Path, "home",
                                   staticmethod(lambda: Path(d) / "nohome")):
                ok, msg = self.vs.check_secrets_dir()
            self.assertFalse(ok, "no secrets dir must fail, not pass quietly")


if __name__ == "__main__":
    unittest.main()
