#!/usr/bin/env python3
"""Redact PII from a SKILL.md so it can be published publicly.

The local skill keeps its host-specific detail -- LAN addresses, real service
names, the author's handle -- because that is what makes it useful HERE. The
published copy replaces those with placeholders so the *method* survives
without the *infrastructure*.

Redaction is deliberately conservative: it replaces identifying values and
leaves every technical instruction intact. A redacted skill that no longer
works on a real host is worse than one that was never published, so the rule is
"substitute, never delete."

Usage:
    redact_skill.py <in.md> <out.md> [--name NAME]

Exit 1 on any finding it could not confidently redact, so a publish step
cannot pass silently on a partially-scrubbed file.
"""
import os
import re
import sys

# Ordered: most specific first. Each entry is (label, pattern, replacement).
# Replacements keep the surrounding code runnable.
#
# ORDER MATTERS and it is not alphabetical. Two bugs found by reading the
# redacted output rather than trusting the residue check:
#
#   1. home_path must run BEFORE handle. Otherwise "/home/operator" has its
#      basename eaten first and becomes "/home/the-author" -- which the
#      residue check passes, because the real username is gone and the
#      leftover reads like a legitimate path.
#   2. numeric_id must not match inside shell arithmetic. "$1>2GB" became
#      "$1>{ID}" because the digits ran together.
RULES = [
    # Home directories FIRST -- see note (1) above.
    ("home_path",   r"/home/operator", "/home/{USER}"),
    # Author / account handles.
    #
    # The noreply exception cannot be expressed as "domain starts with
    # noreply" because the real identity is 260156429+TheHappyHermit@
    # users.noreply.github.com -- the subdomain is users.noreply, not
    # noreply. The exclusion is therefore on the full noreply host, and it
    # must come before the generic email rule, which matches any
    # "local@domain.tld" including this one.
    ("email",       r"[\w.+-]+@(?!users\.noreply\.github\.com\b)"
                      r"(?!(?:noreply|example)\b)[a-z0-9.-]+\.[a-z]{2,}", "{EMAIL}"),
    # Handles. Matched case-insensitively (see redact()), so the
    # negative lookaheads below are all that stand between a genuine leak
    # and a public identity that must survive publication.
    #
    # TheHappyHermit is DELIBERATELY public: it is the commit identity on
    # every push to the public repo, and my PII rules in SOUL.md require
    # that name and nothing else. It must reach GitHub intact. It is
    # therefore excluded from every handle rule below, and the noreply
    # email form is excluded by the email rule above.
    #
    # Without those exclusions, adding re.IGNORECASE broke
    # test_keeps_public_noreply_identity -- the flag was doing its job, and
    # the rule was wrong to be case-insensitive about a public name.
    ("handle",      r"(?<![\w-])(?:(?!TheHappyHermit\b)operator\b"
                      r"|(?!thehappyhermit\b)Josh434434\b"
                      r"|operator\b)", "{USER}"),
    # RFC1918 addresses -- non-identifying in principle, but they map to a
    # real topology when combined with the service names below.
    ("lan_ip",      r"\b(?:10|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "{LAN_IP}"),
    ("lan_range",   r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}\b", "{LAN_IP}/{CIDR}"),
    # Long numeric identifiers: bot/chat IDs, user IDs.
    #
    # Digit count ALONE cannot separate an identifier from a threshold: a
    # real Telegram chat ID is 10 digits, and the awk size filter in
    # disk-io-attribution is 100000000 -- 9 digits. Both match \d{9,}, and
    # the naive fix mangled the filter into "awk '$1>{ID}'", which does not
    # run. Context is the discriminator: an identifier appears bare, or in a
    # JSON/API/config position; a threshold follows a comparison operator.
    ("numeric_id",  r"(?<![\d.$='])(?<![<>=/-])\d{9,}(?![\d.])", "{ID}"),
    # Internal service/database names that map to a private deployment.
    #
    # Neither `brain_sync` nor `fill_oracle_gaps` belongs here. Both are the
    # names of scripts TRACKED IN THIS REPO, so the filename is already
    # visible to anyone reading it -- redacting the name in prose protects
    # nothing while destroying the instruction. `brain_sync` made it worse
    # than useless: the rule matched the stem without `\.py`, so every
    # reference became "{SERVICE}.py", a file that does not exist. No
    # published SKILL.md referenced fill_oracle_gaps at all, so it was pure
    # downside.
    #
    # The test that pins this is
    # test_no_rule_strands_a_public_script_name.
    ("svc",         r"\bhoncho_db\b|\bhermes_db\b|\bokf-queue\b", "{SERVICE}"),
    # Personal hardware model names
    ("hardware",    r"\bRadeon 890M\b|\bgfx1150\b|\bRTX 5060 Ti\b", "{IGPU}"),
    # Key filenames and remote login names. A key named
    # id_ed25519_lab and an "ssh the operator@host" both leak the environment
    # even with the address itself redacted -- the name is the tell.
    #
    # The login rule must not span an -i flag: written as
    # "ssh\s+(?:-i\s+\S+\s+)?[a-z...]+@" it matched across "-i ~/.ssh/" and
    # swallowed the whole key path along with the username, so the key
    # never got its own substitution. Anchor the search to the position
    # immediately before the "@" instead.
    # A bare id_ed25519 / id_rsa is the generic default and carries no
    # information, so it is left alone; only a suffixed variant such as
    # id_ed25519_lab names an environment. The quantifier must match
    # the residue rule's {2,} -- with * the redaction rule also swallowed
    # the default name, which the residue check then had to disagree with.
    ("ssh_key",     r"id_(?:rsa|ed25519|dsa|ecdsa)[a-z0-9_-]{2,}", "{SSH_KEY}"),
    # Login names in `user@host` form.
    #
    # The leading [a-z] was doing double duty as a case guard: it matched
    # only lowercase, so the public identity `TheHappyHermit@users.noreply`
    # was skipped. That worked by accident until redact() gained
    # re.IGNORECASE, at which point [a-z] started matching uppercase and
    # this rule began eating the public commit identity.
    #
    # The guard is now explicit rather than implicit: match any case, and
    # exclude the public name and the public host directly. A behaviour that
    # depends on a quantifier's case range is one edit away from being
    # load-bearing and invisible.
    ("login_name",  r"(?<![\w./-])(?!TheHappyHermit\b)\w{3,}@"
                     r"(?!users\.noreply\.github\.com\b)"
                     r"(?=[a-z0-9{])", "{USER}@"),
    # Project-internal paths. A path whose user component is already
    # "{USER}" is redacted, but the *directory* names inside it still
    # identify a real deployment (.autognosia, hermes-cortex), so they are
    # generalized too. Applied after home_path and handle so the leading
    # /home/<name> is already a placeholder by this point.
    ("proj_path",   r"~/autognosia-clean", "~/hermes-brain"),
    ("proj_path2",  r"(?<=/)autognosia(?=/)", "project"),
    ("proj_path3",  r"hermes-cortex", "other-repo"),
    # Project names identify a real deployment even inside an otherwise
    # redacted path. Matched as a bare substring, not a word: the name
    # survives inside a compound filename such as
    # check_autognosia_dbs.py, where the surrounding underscores mean a
    # \b-delimited pattern never fires.
    ("proj_name",   r"autognosia", "project"),
]

# Patterns that must not survive. If any hits, the caller is told to stop.
RESIDUE = [
    ("handle",   r"\bjosh434\b|\bJosh434434\b|\bopenclaw434\b"),
    ("home",     r"/home/operator"),
    ("lan",      r"\b(?:10|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
    # Same context rule as numeric_id above. These two MUST stay in sync:
    # if the residue check is looser than the redaction rule it flags a
    # deliberately-preserved threshold; if it is tighter it lets a real
    # identifier through. Both were wrong once already, so they are now
    # the same expression.
    ("numeric",  r"(?<![\d.$='])(?<![<>=/-])\d{9,}(?![\d.])"),
    # Must stay in sync with the RULES `svc` entry: if a name is removed from
    # one it has to leave the other, or the residue check flags a file the
    # redactor now considers clean and the publish step refuses to write it.
    # That divergence is not hypothetical -- it is what these two tests
    # caught the first time.
    ("svc",      r"\bhoncho_db\b|\bhermes_db\b|\bokf-queue\b"),
    ("hw",       r"\bRadeon 890M\b|\bgfx1150\b|\bRTX 5060 Ti\b"),
    # An SSH key filename whose suffix names an environment, e.g.
    # id_ed25519_lab. A bare id_ed25519 is the generic default and is
    # allowed; only a suffixed variant identifies anything.
    ("ssh_key",  r"id_(?:rsa|ed25519|dsa|ecdsa)[a-z0-9_-]{2,}"),
    # A bare "name@" that is not the intended {USER}@ placeholder. The
    # redaction rule above rewrites every user@host, so this must be the
    # exact complement of that rule, not a looser approximation.
    ("login",    r"(?<![\w./-])(?!\{USER\})(?!TheHappyHermit\b)\w{3,}@"
                  r"(?!users\.noreply\.github\.com\b)(?=[a-z0-9{])"),
    # Project names identify a real deployment even inside an otherwise
    # redacted path, so they are checked by name rather than by path shape.
    #
    # `personal-organizer` is NOT in this list on purpose, and that is a
    # correction rather than an oversight. It is one of the standard Hermes
    # profile directories -- the same shape as `researcher`, `coder`,
    # `planner` -- and appears in 13 profiles on this machine. Redacting it
    # would refuse to publish organizer-state/SKILL.md, whose only "leak" is
    # the documented default path of a tool the reader is installing. A rule
    # that blocks correct documentation gets worked around, and a rule that
    # gets worked around stops being a rule.
    ("proj",     r"autognosia|hermes-cortex"),
    # A username left in a path position, e.g. "/home/the-author" from a
    # rule-ordering bug that ate the basename before the directory matched.
    # The INTENDED replacement is "/home/{USER}", so that is allowed.
    # Generic literals a skill may legitimately use as examples are also
    # allowed -- "user", "you", and the standard account names that show up
    # in generic Linux examples. Flagging those caused a false refusal on a
    # file that was already anonymized. What this must catch is a real
    # personal username, which is what a mangled substitution leaves behind.
    ("mangled_path", r"/home/(?!\{USER\})(?!(?:user|you|someuser|ubuntu|debian|"
                      r"centos|fedora|arch|alpine|pi|node|runner|admin)\b)"
                      r"[a-z][a-z0-9]{2,}"),
]


def redact(text: str) -> tuple[str, dict]:
    counts = {}
    for label, pat, repl in RULES:
        # re.IGNORECASE, and it is load-bearing.
        #
        # The rules are written with the canonical capitalisation
        # (\bJosh434434\b, \bRTX 5060 Ti\b) but text carries them lowercase
        # too -- a private repo named `TheHappyHermit/laptop-config` in a
        # backticked path, a host described as `rtx 5060 ti`. Without the
        # flag the handle and hardware rules matched NOTHING in that
        # spelling and the file published with the real account in it.
        #
        # It escaped the residue check for the same reason: residue() has
        # its own pattern list, also case-sensitive, also silent. Two
        # lists with the same blind spot cannot catch each other -- which
        # is the argument for the independent scan in
        # publish_profiles_and_skills.py, which found this.
        #
        # Safe to apply globally: every replacement is a fixed placeholder,
        # so case-insensitive matching changes WHICH text is caught, never
        # what it is replaced with.
        text, n = re.subn(pat, repl, text, flags=re.IGNORECASE)
        if n:
            counts[label] = counts.get(label, 0) + n
    return text, counts


def residue(text: str) -> list[str]:
    # Same flag, same reason. Without it this function reports a clean file
    # for a handle it would have been asked about in the wrong case.
    return [label for label, pat in RESIDUE
            if re.search(pat, text, flags=re.IGNORECASE)]


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    text = open(src, encoding="utf-8").read()

    out, counts = redact(text)
    left = residue(out)

    if left:
        print("REFUSING to write %s -- unredacted residue: %s" % (dst, ", ".join(left)))
        print("The publish step must not pass on a partially scrubbed file.")
        return 1

    # Create the destination directory. The caller writes into a per-skill
    # subdirectory that does not exist yet, and a missing parent here
    # surfaced as a FileNotFoundError buried in a subprocess traceback.
    parent = os.path.dirname(os.path.abspath(dst))
    if parent:
        os.makedirs(parent, exist_ok=True)

    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(out)

    if counts:
        print("redacted %s -> %s" % (src, dst))
        for label, n in sorted(counts.items()):
            print("   %-10s %d" % (label, n))
    else:
        print("clean, nothing to redact: %s" % src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
