"""Contract tests for profiles/oracle/SOUL.md.

The Oracle SOUL is instructions to a model, so nothing executes it and a wrong
command sits there until someone tries it by hand. These tests check the claims
the file makes that can be checked mechanically: that every `graphify` subcommand
it names is real, and that the retrieval order keeps the derived index below the
source it is derived from.

They are deliberately narrow. They do not assert on prose.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOUL = REPO / "profiles" / "oracle" / "SOUL.md"


def _soul_text() -> str:
    return SOUL.read_text(encoding="utf-8")


def _declared_variables() -> dict[str, str]:
    """NAME="value" assignments the SOUL itself declares, e.g. ORACLE_GRAPH=...

    Used so a ${VAR} passed to a CLI can be checked as the concrete value the
    reader would end up with, not waved through because it is a variable.
    """
    found: dict[str, str] = {}
    for name, value in re.findall(
        r'^\s*([A-Z_][A-Z0-9_]*)="([^"]*)"', _soul_text(), re.MULTILINE
    ):
        found[name] = value
    return found


def _graphify_subcommands() -> set[str]:
    """Every subcommand the installed graphify CLI advertises, or empty if absent."""
    if shutil.which("graphify") is None:
        return set()
    try:
        proc = subprocess.run(
            ["graphify", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    # graphify's help indents subcommands by exactly 2 spaces and their flags by
    # 4. Both indentation rules matter: matching anything looser picks up flag
    # names, and matching only column 0 finds nothing at all. Prose inside a
    # description can also contain command-like words ("--type T  query type:
    # query|path_query|explain"), which is why this cannot be a loose word search.
    found = set()
    for line in (proc.stdout + proc.stderr).splitlines():
        if not line.startswith("  ") or line.startswith("    "):
            continue
        body = line[2:]
        if not body or body.startswith("-"):
            continue
        head = body.split()[0]
        if re.fullmatch(r"[a-z][a-z0-9-]*", head):
            found.add(head)
    return found


class TestOracleSoulGraphifyCommands(unittest.TestCase):
    """Every graphify command the SOUL teaches must actually exist."""

    def test_graphify_is_available_or_test_skips(self):
        if shutil.which("graphify") is None:
            self.skipTest("graphify CLI not installed")

    def test_no_documented_subcommand_is_fictional(self):
        subcommands = _graphify_subcommands()
        if not subcommands:
            self.skipTest("graphify --help produced no parseable command list")

        # Only consider `graphify <word>` occurrences inside bash fences, so the
        # prose ("a graphify query step") cannot fail this test.
        text = _soul_text()
        documented = set()
        for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
            for match in re.finditer(r"\bgraphify\s+([a-z][a-z0-9-]*)", block):
                documented.add(match.group(1))

        self.assertTrue(
            documented,
            "expected the SOUL to document at least one graphify command",
        )
        fictional = documented - subcommands
        self.assertEqual(
            fictional,
            set(),
            f"SOUL documents nonexistent graphify subcommand(s): {sorted(fictional)}. "
            f"Real subcommands: {sorted(subcommands)}",
        )

    def test_graph_flag_is_documented_as_a_file_not_a_directory(self):
        """`--graph` takes graph.json. Passing its directory raises IsADirectoryError."""
        text = _soul_text()
        variables = _declared_variables()
        self.assertTrue(
            variables,
            "no NAME=\"value\" variables declared, so --graph cannot be checked "
            "concretely; the SOUL should define its graph paths once and reuse them",
        )
        for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
            for line in block.splitlines():
                if "--graph" not in line:
                    continue
                value = line.split("--graph", 1)[1].strip().strip('"').strip("'")
                # A literal path must name the file. A ${VAR} is resolved through
                # the variable assignments the SOUL itself defines, so a variable
                # cannot smuggle a directory past this check.
                match = re.fullmatch(r"\$\{([A-Z_]+)\}", value)
                if match:
                    assigned = variables.get(match.group(1))
                    self.assertIsNotNone(
                        assigned,
                        f"--graph uses ${{{match.group(1)}}} but the SOUL never "
                        "assigns it",
                    )
                    value = assigned or ""
                self.assertTrue(
                    value.endswith("graph.json"),
                    f"--graph is given '{value}', which is a directory; "
                    "graphify needs the graph.json file",
                )

    def test_graph_json_paths_it_cites_look_like_files(self):
        text = _soul_text()
        for match in re.finditer(r"\$\{HOME\}(\S*graphify-out)", text):
            tail = match.group(1)
            self.assertFalse(
                tail.endswith("/"),
                "graphify-out directory cited without the graph.json filename",
            )


class TestOracleSoulRetrievalOrder(unittest.TestCase):
    """The graph is a derived index; it must not outrank its own source."""

    def test_ripgrep_is_ranked_above_graphify(self):
        text = _soul_text()
        match = re.search(r"##\s*Retrieval Order\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
        self.assertIsNotNone(match, "no Retrieval Order section found")
        assert match is not None

        lines = [
            line for line in match.group(1).splitlines()
            if re.match(r"\s*\d+\.", line)
        ]
        self.assertGreaterEqual(len(lines), 2, "retrieval order is not a numbered list")

        ripgrep_rank = next(
            (i for i, line in enumerate(lines) if "ripgrep" in line.lower()), None
        )
        graph_rank = next(
            (i for i, line in enumerate(lines) if "graphify" in line.lower()), None
        )

        self.assertIsNotNone(ripgrep_rank, "ripgrep missing from retrieval order")
        self.assertIsNotNone(graph_rank, "graphify missing from retrieval order")
        assert ripgrep_rank is not None and graph_rank is not None
        self.assertLess(
            ripgrep_rank,
            graph_rank,
            "the derived graph must rank below the Markdown it is derived from",
        )

    def test_consultation_section_was_not_dropped(self):
        """The live Oracle profile once lost its escalation rules entirely."""
        self.assertIn(
            "## Consultation",
            _soul_text(),
            "Oracle lost its escalation rules; that section must not silently vanish",
        )

    def test_no_stale_wall_clock_threshold(self):
        """A literal '39+ minutes' came from an old timeout and can never be right."""
        hit = re.search(r"\d+\s*\+?\s*(?:minute|hour|min|hr)s?\b", _soul_text(), re.I)
        if hit is not None:
            self.fail(
                f"wall-clock threshold {hit.group(0)!r} found; a fixed number of "
                "minutes cannot stay correct as machine speed changes -- trigger on "
                "a retry count instead"
            )


if __name__ == "__main__":
    unittest.main()
