"""Tests for the independent residue scan used before publishing.

This scanner is deliberately NOT the redactor's own residue check. The
redactor missed a real handle leak -- `TheHappyHermit/laptop-config` in
lowercase, because its rules ran without re.IGNORECASE -- and its residue
check missed the same one for the same reason. Two lists that share a blind
spot cannot catch each other.

So the scan is a second opinion with its own patterns. That only works if it
is correct in BOTH directions:

  * a real leak must be reported, or the check is theatre;
  * standard documentation text must NOT be reported, or the check gets
    ignored and stops being one.

The allowlist entries all came from false positives observed against real
files: ssh-keygen's default `~/.ssh/id_ed25519`, its `.pub` form, and the
IANA-reserved `example.com` used in setup walkthroughs.
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_MOD = os.path.join(os.path.dirname(_HERE), "scripts",
                    "publish_profiles_and_skills.py")
spec = importlib.util.spec_from_file_location("publish_pps", _MOD)
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)


class TestCatchesRealLeaks(unittest.TestCase):
    def test_lowercase_github_handle(self):
        f = P.residue_findings("Repo: `TheHappyHermit/laptop-config` (private)")
        self.assertIn("github handle", f)

    def test_real_email(self):
        self.assertIn("email", P.residue_findings("write to operator@example.com"))

    def test_lan_ip(self):
        self.assertIn("LAN IP", P.residue_findings("vllm on 10.0.0.151:18020"))

    def test_home_path(self):
        self.assertIn("home path",
                      P.residue_findings("cd /home/operator/hermes-brain"))

    def test_named_ssh_key(self):
        self.assertIn("ssh key name",
                      P.residue_findings("ssh -i ~/.ssh/id_ed25519_lab h"))

    def test_bare_named_key_without_prefix(self):
        """The prefix is not required for a key name to be identifying."""
        self.assertIn("ssh key name", P.residue_findings("use id_ed25519_work"))

    def test_named_non_ed25519_key(self):
        """Scope must match the redactor's ssh_key rule, not be narrower."""
        self.assertIn("ssh key name", P.residue_findings("id_rsa_lab_key"))

    def test_ssh_login(self):
        self.assertIn("ssh login", P.residue_findings("ssh the operator@server uptime"))


class TestIgnoresStandardText(unittest.TestCase):
    """A check that cries wolf gets ignored, and then it is not a check."""

    def test_default_ssh_keygen_path(self):
        self.assertEqual(
            P.residue_findings("ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519"),
            {})

    def test_default_ssh_key_pub_path(self):
        self.assertEqual(
            P.residue_findings("gh ssh-key add ~/.ssh/id_ed25519.pub"), {})

    def test_cat_the_public_key(self):
        self.assertEqual(
            P.residue_findings("cat ~/.ssh/id_ed25519.pub"), {})

    def test_default_rsa_path(self):
        self.assertEqual(
            P.residue_findings("ssh -i ~/.ssh/id_rsa user@host"), {})

    def test_example_com_placeholder_email(self):
        self.assertEqual(
            P.residue_findings('git config user.email "a@example.com"'), {})

    def test_example_org_url(self):
        self.assertEqual(
            P.residue_findings("see https://example.org/docs"), {})

    def test_clean_file_is_clean(self):
        self.assertEqual(
            P.residue_findings("# Title\n\nSome prose about a topic.\n"), {})


class TestKeyGuardReadsSurroundingText(unittest.TestCase):
    def test_guard_uses_a_window_not_the_match(self):
        """The match excludes `.ssh/`, so the guard needs context.

        The pattern starts at `id_`, so a test against the matched text
        alone can never see the `.ssh/` prefix and flags every tutorial.
        """
        flagged = P.residue_findings("cat ~/.ssh/id_ed25519.pub")
        self.assertNotIn("ssh key name", flagged)


if __name__ == "__main__":
    unittest.main()
