"""Tests for the skill redactor.

The redactor gates what gets published to GitHub, so its failure modes matter
in both directions: a miss leaks PII into a public repo, and an over-eager
rule refuses to write a file that was already clean. Both happened during
development, which is why each one is pinned here.

Run: python3 -m unittest discover -s tests -v
"""
import importlib.util
import os
import re
import unittest
from pathlib import Path

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = Path(os.path.dirname(_HERE))
_MOD = os.path.join(os.path.dirname(_HERE), "scripts", "redact_skill.py")
spec = importlib.util.spec_from_file_location("redact_skill", _MOD)
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


def _residue_pattern(label):
    return next(p for l, p in rs.RESIDUE if l == label)


class TestRedactionBasics(unittest.TestCase):

    def test_strips_username_and_home_path_together(self):
        """Regression: the handle rule used to run first and turn
        /home/operator into /home/the-author -- which passed the residue
        check while leaving an obviously mangled, non-runnable path."""
        out, counts = rs.redact("cp /home/operator/.hermes/x /home/operator/y")
        self.assertNotIn("operator", out)
        self.assertIn("/home/{USER}/.hermes/x", out)
        self.assertEqual(out.count("{USER}"), 2)

    def test_redacts_lan_ip(self):
        out, _ = rs.redact("ssh operator@10.0.0.10 'echo ok'")
        self.assertNotIn("10.0.0.10", out)
        self.assertIn("{LAN_IP}", out)

    def test_redacts_email(self):
        out, _ = rs.redact("mail me at user@example.com please")
        self.assertNotIn("gmail.com", out)
        self.assertIn("{EMAIL}", out)

    def test_keeps_public_noreply_identity(self):
        """The commit identity is intentionally public and must survive."""
        src = "TheHappyHermit <260156429+TheHappyHermit@users.noreply.github.com>"
        out, _ = rs.redact(src)
        self.assertEqual(out, src)


class TestShellSyntaxSurvives(unittest.TestCase):
    """Redaction must not break runnable commands. A size filter of
    100000000 is nine digits, the same length range as a Telegram ID, so a
    plain digit-count rule corrupts it into $1>{ID}."""

    def test_awk_threshold_after_comparison_is_preserved(self):
        out, _ = rs.redact("awk '$1>100000000' | sort -rn")
        self.assertEqual(out, "awk '$1>100000000' | sort -rn")
        self.assertNotIn("{ID}", out)

    def test_bare_identifier_is_still_redacted(self):
        out, _ = rs.redact('{"chat_id": 1234567890}')
        self.assertIn("{ID}", out)
        self.assertNotIn("1234567890", out)

    def test_threshold_passes_its_own_residue_check(self):
        """The residue rule and the redaction rule must agree. When they
        diverged, the residue check flagged a deliberately-kept threshold
        and refused the write."""
        out, _ = rs.redact("awk '$1>100000000' | sort -rn")
        self.assertEqual(rs.residue(out), [])


class TestMangledPathDetector(unittest.TestCase):
    """Catches a real username left in a path position while allowing the
    generic literals that appear in legitimate Linux examples."""

    PAT = _residue_pattern("mangled_path")

    def test_catches_real_looking_usernames(self):
        for probe in ("/home/the-author/x", "/home/operator/.hermes",
                      "/home/realname/x", "/home/someguy/a"):
            with self.subTest(probe=probe):
                self.assertRegex(probe, self.PAT)

    def test_allows_generic_and_intended_placeholders(self):
        for probe in ("/home/{USER}/x", "/home/user/.config", "/home/you/.config",
                      "/usr/local/bin", "/home/ubuntu/.ssh", "/home/debian/x",
                      "/home/node/app", "/home/admin/.config"):
            with self.subTest(probe=probe):
                self.assertNotRegex(probe, self.PAT)


class TestSshRedaction(unittest.TestCase):
    """An SSH line leaks the environment through the key filename and the
    login name even after the address is redacted -- the name is the tell."""

    def test_lab_named_key_and_login_are_redacted(self):
        src = "ssh -i ~/.ssh/id_ed25519_lab operator@10.0.0.10 'echo ok'"
        out, counts = rs.redact(src)
        self.assertNotIn("home_lab", out)
        self.assertNotIn("the operator@", out)
        self.assertIn("{SSH_KEY}", out)
        self.assertIn("{USER}@", out)
        self.assertIn("ssh_key", counts)
        self.assertIn("login_name", counts)

    def test_redacted_ssh_line_has_no_residue(self):
        """The residue rule must accept its own intended output, or the
        publish step refuses a correctly scrubbed file."""
        out, _ = rs.redact("ssh -i ~/.ssh/id_ed25519_lab operator@10.0.0.10 'echo ok'")
        self.assertEqual(rs.residue(out), [])

    def test_generic_login_names_are_also_redacted(self):
        for src in ("ssh admin@server", "ssh -i k.pem root@h"):
            with self.subTest(src=src):
                out, _ = rs.redact(src)
                self.assertIn("{USER}@", out)
                self.assertEqual(rs.residue(out), [])

    def test_bare_default_key_name_is_allowed(self):
        """A bare id_ed25519 is a generic default, not an environment tell."""
        out, _ = rs.redact("cp ~/.ssh/id_ed25519 /tmp/k")
        self.assertIn("id_ed25519", out)
        self.assertEqual(rs.residue(out), [])


class TestResidueGating(unittest.TestCase):

    def test_residue_reports_every_class(self):
        dirty = "operator lives at /home/operator on 10.0.0.10"
        found = set(rs.residue(dirty))
        self.assertTrue({"handle", "home", "lan"} <= found)

    def test_clean_text_has_no_residue(self):
        out, _ = rs.redact("ssh {LAN_IP} and read /home/{USER}/notes.md")
        self.assertEqual(rs.residue(out), [])


class TestCaseInsensitiveRedaction(unittest.TestCase):
    """Rules must match the identity in any case.

    The rules are written with the canonical capitalisation
    (\\bJosh434434\\b) but real text carries the handle lowercase -- in a
    backticked repo path, for instance. redact() ran re.subn with no
    flags, so the handle and hardware rules matched nothing in that
    spelling and the file published with the real account in it.

    residue() had the same blind spot for the same reason, so the file
    reported clean. Two lists that cannot see each other's gap is the whole
    argument for the independent scan in publish_profiles_and_skills.py,
    which is what found this.
    """

    def test_lowercase_handle_is_redacted(self):
        out, counts = rs.redact("Repo: `TheHappyHermit/laptop-config` (private)")
        self.assertNotIn("operator", out)
        # The rule that fired is asserted by name, so a future edit cannot
        # make this pass via a different rule that happens to catch it.
        self.assertEqual(counts.get("handle"), 1)

    def test_uppercase_handle_is_redacted(self):
        out, _ = rs.redact("Repo: `Josh434434/hermes-laptop`")
        self.assertNotIn("osh434434", out)

    def test_lowercase_hardware_is_redacted(self):
        out, _ = rs.redact("the rtx 5060 ti box")
        self.assertNotIn("5060", out)

    def test_residue_detects_lowercase_handle(self):
        """The residue check must not be the one that stays silent."""
        self.assertIn("handle", rs.residue("repo TheHappyHermit/x"))
        self.assertIn("hw", rs.residue("the rtx 5060 ti"))

    def test_public_identity_survives_case_insensitive_matching(self):
        """The deliberate exception must hold under the new flag.

        This is the exact regression that re.IGNORECASE introduced: the
        [a-z] in the login rule had been acting as an implicit case guard,
        and the flag turned it into a match on the public commit identity.
        """
        src = "TheHappyHermit <260156429+TheHappyHermit@users.noreply.github.com>"
        out, _ = rs.redact(src)
        self.assertEqual(out, src)

    def test_a_real_login_is_still_redacted(self):
        """The narrowing must not disable the rule it was protecting."""
        out, _ = rs.redact("ssh operator@10.0.0.10 uptime")
        self.assertNotIn("the operator@", out)
        self.assertIn("{USER}@", out)


class TestServiceNameRedaction(unittest.TestCase):
    """The `svc` rule replaces private-deployment names with {SERVICE}.

    `brain_sync` used to be in that rule written without `\\.py`, so the stem
    was consumed and the extension survived: every reference became
    `{SERVICE}.py`, an instruction that no longer runs. The residue check had
    no opinion, because `{SERVICE}.py` is not PII -- it is a broken command.
    That is the whole argument for testing what the output DOES, not whether
    a substitution happened.
    """

    def test_brain_sync_command_stays_runnable(self):
        src = 'python3 "$HOME/scripts/brain_sync.py" --source active-wiki'
        out, _ = rs.redact(src)
        self.assertIn("brain_sync.py", out)
        self.assertNotIn("{SERVICE}", out)
        self.assertEqual(rs.residue(out), [])

    def test_bare_brain_sync_reference_survives(self):
        out, _ = rs.redact("brain_sync.py and graphify are both reconstructible")
        self.assertIn("brain_sync.py", out)

    def test_brain_query_is_untouched(self):
        out, _ = rs.redact('python3 "$HOME/hermes-brain/scripts/brain_query.py" "q"')
        self.assertIn("brain_query.py", out)
        self.assertNotIn("{SERVICE}", out)

    def test_genuine_private_names_are_still_redacted(self):
        """Removing brain_sync must not gut the rule it lived in."""
        for name in ("honcho_db", "hermes_db", "okf-queue"):
            with self.subTest(name=name):
                out, counts = rs.redact(name)
                self.assertIn("{SERVICE}", out)
                self.assertIn("svc", counts)

    def test_residue_and_rules_agree_on_service_names(self):
        """The two lists must name the same private services.

        They are written separately. When `brain_sync` was dropped from RULES
        but left in RESIDUE, the redactor produced output its own residue
        check rejected -- so a correctly scrubbed file could not be published
        at all. Asserting agreement directly is cheaper than discovering it
        through a failed publish.
        """
        rule_pat = next(p for l, p, _ in rs.RULES if l == "svc")
        res_pat = _residue_pattern("svc")
        names = lambda pat: set(re.findall(r"\\b([a-z][a-z0-9_-]+)\\b", pat))
        self.assertEqual(
            names(rule_pat) - {"honcho_db", "hermes_db", "okf-queue"},
            set(),
            "RULES svc gained a name that is not a known private service",
        )
        for n in ("honcho_db", "hermes_db", "okf-queue"):
            with self.subTest(name=n):
                self.assertIn(n, rule_pat)
                self.assertIn(n, res_pat)

    def test_no_rule_strands_a_public_script_name(self):
        """General guard for the shape of the real bug.

        The failure was not "a rule matched a stem" -- several legitimately
        do, and a private DB name redacting to {SERVICE}.py is correct. It was
        a rule matching a name that is a PUBLISHED SCRIPT in this very repo,
        so the published copy told a reader to run a file that cannot exist.

        Scoped to names that resolve to a real tracked file, which is what
        makes them safe to publish and what made the redaction wrong.
        """
        public_scripts = (
            {p.name for p in (REPO / "scripts").glob("*.py")}
            | {p.name for p in Path(os.path.expanduser("~/scripts")).glob("*.py")}
        )
        for label, pattern, repl in rs.RULES:
            with self.subTest(rule=label):
                for m in re.finditer(r"\\b([a-z][a-z0-9_-]{3,})\\b", pattern):
                    stem = m.group(1)
                    for ext in (".py", ".sh"):
                        if stem + ext not in public_scripts:
                            continue
                        out = re.sub(pattern, repl, stem + ext)
                        self.assertNotIn(
                            "{", out,
                            "rule %r redacts the public script %r, so the "
                            "published copy names a file that does not "
                            "exist: %r" % (label, stem + ext, out))


if __name__ == "__main__":
    unittest.main()
