"""Tests for prospective memory (implementation intentions).

The behaviour worth protecting is not the happy path — it is that a *missed*
intention fails silently. These tests cover matching, expiry, and the guarantee
that nothing is ever deleted.
"""
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain.prospective.intentions import (  # noqa: E402
    Intention,
    ProspectiveMemory,
    parse_rfc3339,
    rfc3339,
    tokenize,
    utc_now,
)


def _get(pm, intention_id) -> Intention:
    """Assert-then-narrow helper: get() is Optional, tests need the value."""
    got = pm.get(intention_id)
    if got is None:
        raise AssertionError(f"intention {intention_id} unexpectedly missing")
    return got


class TestTokenize(unittest.TestCase):
    def test_drops_stopwords_and_short_tokens(self):
        t = tokenize("The postgres is down and it is a very bad day")
        self.assertIn("postgres", t)
        self.assertIn("down", t)
        self.assertIn("bad", t)
        self.assertNotIn("the", t)
        self.assertNotIn("is", t)
        self.assertNotIn("it", t)

    def test_empty_and_none_safe(self):
        self.assertEqual(tokenize(""), frozenset())
        self.assertEqual(tokenize(None), frozenset())

    def test_case_and_punctuation_insensitive(self):
        self.assertEqual(tokenize("Postgres DOWN!"), tokenize("postgres down"))


class TestRFC3339(unittest.TestCase):
    def test_format_is_utc_with_z(self):
        s = rfc3339(utc_now())
        self.assertTrue(s.endswith("Z"), s)
        self.assertNotIn(" ", s)
        self.assertRegex(s, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_roundtrip(self):
        now = utc_now().replace(microsecond=0)
        self.assertEqual(parse_rfc3339(rfc3339(now)), now)

    def test_parse_bad_returns_none(self):
        self.assertIsNone(parse_rfc3339("2026-01-01 00:00:00"))
        self.assertIsNone(parse_rfc3339("garbage"))
        self.assertIsNone(parse_rfc3339(""))


class TestDBPathGuard(unittest.TestCase):
    """A falsy db_path must fail loudly.

    Regression test. `str(None)` is the four-character string "None", and
    `sqlite3.connect("None")` does not raise -- it creates a file named
    `None` in the cwd and hands back a working connection. That produced a
    real stray database in the repo root holding one orphaned intention.
    The guard is what stops it; these tests are what stop the guard going.
    """

    def test_none_path_rejected(self):
        with self.assertRaises(ValueError):
            ProspectiveMemory(None)

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            ProspectiveMemory("")

    def test_whitespace_path_rejected(self):
        with self.assertRaises(ValueError):
            ProspectiveMemory("   ")

    def test_rejection_creates_no_file(self):
        # The real defect was a silent write, so assert on the filesystem,
        # not only on the exception. cwd is the repo root when this runs.
        cwd = os.getcwd()
        with self.assertRaises(ValueError):
            ProspectiveMemory(None)
        self.assertFalse(
            os.path.exists(os.path.join(cwd, "None")),
            "a file named 'None' was created despite the guard",
        )

    def test_valid_path_still_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            pm = ProspectiveMemory(Path(tmp) / "pm.db")
            self.assertTrue(pm.db_path.endswith("pm.db"))


class TestAdd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pm = ProspectiveMemory(Path(self.tmp.name) / "pm.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_add_returns_pending_intention(self):
        i = self.pm.add("postgres down", "check the pg logs")
        self.assertEqual(i.state, "pending")
        self.assertEqual(i.fired_count, 0)
        self.assertIsNotNone(i.expires_at)
        self.assertIn("check the pg logs", i.action_text)

    def test_empty_trigger_rejected(self):
        with self.assertRaises(ValueError):
            self.pm.add("", "do something")
        with self.assertRaises(ValueError):
            self.pm.add("   ", "do something")

    def test_empty_action_rejected(self):
        with self.assertRaises(ValueError):
            self.pm.add("a trigger", "")

    def test_stopword_only_trigger_rejected(self):
        # "the is of" tokenizes to nothing; firing on that would fire constantly.
        with self.assertRaises(ValueError):
            self.pm.add("the is of", "act")

    def test_unknown_trigger_kind_rejected(self):
        with self.assertRaises(ValueError):
            self.pm.add("a trigger", "act", trigger_kind="vibes")

    def test_creates_db_and_parent_dirs(self):
        nested = Path(self.tmp.name) / "a" / "b" / "pm.db"
        pm2 = ProspectiveMemory(nested)
        pm2.add("postgres down", "check pg logs")
        self.assertTrue(nested.exists())

    def test_ids_unique(self):
        a = self.pm.add("postgres down", "act")
        b = self.pm.add("redis down", "act")
        self.assertNotEqual(a.intention_id, b.intention_id)


class TestCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pm = ProspectiveMemory(Path(self.tmp.name) / "pm.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fires_on_exact_trigger(self):
        self.pm.add("postgres down", "check pg logs")
        hits = self.pm.check("postgres down again")
        self.assertEqual(len(hits), 1)
        self.assertIn("check pg logs", hits[0].action_text)

    def test_substring_match_catches_inflection(self):
        # A missed intention is a silent failure; this is the case that matters.
        self.pm.add("postgres down", "check pg logs")
        self.assertEqual(len(self.pm.check("the postgres appears to be down")), 1)

    def test_does_not_fire_on_unrelated_text(self):
        self.pm.add("postgres down", "check pg logs")
        self.assertEqual(len(self.pm.check("the build is green")), 0)

    def test_empty_text_returns_nothing(self):
        self.pm.add("postgres down", "act")
        self.assertEqual(self.pm.check(""), [])
        self.assertEqual(self.pm.check("   "), [])

    def test_all_kind_requires_every_token(self):
        self.pm.add("postgres and redis both down", "page someone",
                    trigger_kind="all")
        self.assertEqual(len(self.pm.check("postgres is down but redis is up")), 0)
        self.assertEqual(len(self.pm.check("postgres and redis both down")), 1)

    def test_phrase_kind_requires_contiguous_string(self):
        self.pm.add("restart the service", "run systemctl",
                    trigger_kind="phrase")
        self.assertEqual(len(self.pm.check("you should restart the service now")), 1)
        self.assertEqual(len(self.pm.check("restart, then check the service")), 0)

    def test_max_fires_caps_results(self):
        for i in range(8):
            self.pm.add(f"alert {i} fired", f"handle {i}")
        # all share the token "fired"
        self.assertEqual(len(self.pm.check("alert fired", max_fires=3)), 3)

    def test_check_is_side_effect_free(self):
        self.pm.add("postgres down", "act")
        for _ in range(5):
            self.pm.check("postgres down")
        self.assertEqual(_get(self.pm, self.pm.all_intentions()[0].intention_id).fired_count, 0)

    def test_cancelled_intention_does_not_fire(self):
        i = self.pm.add("postgres down", "act")
        self.assertTrue(self.pm.cancel(i.intention_id))
        self.assertEqual(len(self.pm.check("postgres down")), 0)

    def test_expired_intention_does_not_fire(self):
        i = self.pm.add("postgres down", "act", ttl_days=-1)
        self.assertEqual(len(self.pm.check("postgres down")), 0)
        self.assertEqual(_get(self.pm, i.intention_id).state, "expired")


class TestExpiry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pm = ProspectiveMemory(Path(self.tmp.name) / "pm.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_expire_due_transitions_pending(self):
        i = self.pm.add("a trigger", "act", ttl_days=-1)
        self.assertEqual(self.pm.expire_due(), 1)
        self.assertEqual(_get(self.pm, i.intention_id).state, "expired")

    def test_expire_due_leaves_live_ones(self):
        self.pm.add("live trigger", "act", ttl_days=30)
        self.assertEqual(self.pm.expire_due(), 0)
        self.assertEqual(len(self.pm.pending()), 1)

    def test_never_expires_when_ttl_none(self):
        i = self.pm.add("permanent", "act", ttl_days=None)
        self.assertIsNone(i.expires_at)
        self.pm.expire_due()
        self.assertEqual(_get(self.pm, i.intention_id).state, "pending")

    def test_expired_excluded_from_pending(self):
        self.pm.add("dead", "act", ttl_days=-1)
        self.assertEqual(len(self.pm.pending()), 0)
        self.assertEqual(len(self.pm.pending(include_expired=True)), 1)


class TestMarkFired(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pm = ProspectiveMemory(Path(self.tmp.name) / "pm.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_increments_and_stamps(self):
        i = self.pm.add("postgres down", "act")
        self.pm.mark_fired([i.intention_id])
        self.pm.mark_fired([i.intention_id])
        got = _get(self.pm, i.intention_id)
        self.assertEqual(got.fired_count, 2)
        self.assertIsNotNone(got.last_fired_at)

    def test_marking_does_not_expire(self):
        # A standing check should keep firing; expiry is the explicit stop.
        i = self.pm.add("postgres down", "act")
        self.pm.mark_fired([i.intention_id])
        self.assertEqual(_get(self.pm, i.intention_id).state, "pending")

    def test_empty_list_is_safe(self):
        self.assertEqual(self.pm.mark_fired([]), 0)

    def test_unknown_id_does_not_raise(self):
        self.assertEqual(self.pm.mark_fired(["nonexistent"]), 0)


class TestStats(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pm = ProspectiveMemory(Path(self.tmp.name) / "pm.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_counts_by_state(self):
        a = self.pm.add("live one", "act", ttl_days=30)
        b = self.pm.add("dead one", "act", ttl_days=-1)
        self.pm.cancel(a.intention_id)
        s = self.pm.stats()
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["cancelled"], 1)
        self.assertEqual(s["expired"], 1)
        self.assertEqual(s["by_state"].get("cancelled"), 1)

    def test_empty_db(self):
        s = self.pm.stats()
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["pending"], 0)


class TestDurability(unittest.TestCase):
    def test_intentions_survive_reopen(self):
        tmp = tempfile.TemporaryDirectory()
        db = Path(tmp.name) / "pm.db"
        pm1 = ProspectiveMemory(db)
        i = pm1.add("postgres down", "check pg logs")
        pm1.mark_fired([i.intention_id])
        pm2 = ProspectiveMemory(db)  # simulate a restart
        got = _get(pm2, i.intention_id)
        self.assertIsNotNone(got)
        self.assertEqual(got.fired_count, 1)
        self.assertEqual(len(pm2.check("postgres down")), 1)
        tmp.cleanup()

    def test_nothing_is_ever_deleted(self):
        tmp = tempfile.TemporaryDirectory()
        pm = ProspectiveMemory(Path(tmp.name) / "pm.db")
        ids = [pm.add(f"trigger {i}", "act").intention_id for i in range(5)]
        for iid in ids:
            pm.cancel(iid)
        pm.expire_due()
        self.assertEqual(len(pm.all_intentions()), 5)
        tmp.cleanup()


class TestConnectionHygiene(unittest.TestCase):
    def test_fk_pragmas_enabled_on_every_connection(self):
        # Writers must enable FKs; an orphan row is silent data loss. The schema has
        # no FK today, but the pragma is set on every connection so that adding one
        # later is not a silent regression.
        tmp = tempfile.TemporaryDirectory()
        pm = ProspectiveMemory(Path(tmp.name) / "pm.db")
        conn = pm._connect()
        try:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        finally:
            conn.close()
            tmp.cleanup()

    def test_each_call_gets_fresh_pragma(self):
        tmp = tempfile.TemporaryDirectory()
        pm = ProspectiveMemory(Path(tmp.name) / "pm.db")
        for _ in range(3):
            conn = pm._connect()
            try:
                self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            finally:
                conn.close()
        tmp.cleanup()


class TestHubIntegration(unittest.TestCase):
    """The intention must surface through the real agent loop, not just in isolation.

    An intention store that nothing calls is the same defect this project found with
    six other subsystems, so the wiring itself is under test.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        from brain.hermes_brain import HermesBrain
        self.brain = HermesBrain(db_path=str(Path(self.tmp.name) / "brain.db"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_intention_fires_through_process_incoming_stimulus(self):
        self.brain.prospective_memory.add("postgres down", "check the pg logs")
        out = self.brain.process_incoming_stimulus(
            source="user", text="the postgres is down"
        )
        self.assertEqual(len(out["fired_intentions"]), 1)
        self.assertIn("check the pg logs", out["fired_intentions"][0]["action_text"])

    def test_surfaces_post_fire_count(self):
        self.brain.prospective_memory.add("postgres down", "check the pg logs")
        out = self.brain.process_incoming_stimulus(
            source="user", text="the postgres is down"
        )
        # Regression: this used to report 0 for the intention that had just fired.
        self.assertEqual(out["fired_intentions"][0]["fired_count"], 1)
        self.assertIsNotNone(out["fired_intentions"][0]["last_fired_at"])

    def test_unrelated_stimulus_surfaces_nothing(self):
        self.brain.prospective_memory.add("postgres down", "check the pg logs")
        out = self.brain.process_incoming_stimulus(
            source="user", text="the build is green"
        )
        self.assertEqual(out["fired_intentions"], [])

    def test_intentions_persist_across_brain_instances(self):
        self.brain.prospective_memory.add("postgres down", "check the pg logs")
        from brain.hermes_brain import HermesBrain
        b2 = HermesBrain(db_path=str(Path(self.tmp.name) / "brain.db"))
        out = b2.process_incoming_stimulus(source="user", text="postgres is down")
        self.assertEqual(len(out["fired_intentions"]), 1)


if __name__ == "__main__":
    unittest.main()
