#!/usr/bin/env python3
"""
Config backup with mandatory PII scrubbing and a hard pre-push gate.

WHY THIS EXISTS
    The previous Config Backup cron did a blind `rsync ... && git add -A && push`
    of ~/.hermes/{config.yaml,SOUL.md,profiles/,skills/,cron/} into a PUBLIC
    repo. On 2026-08-22 that published a real SSH password across 32 files and
    private email identities across 35 more.

DESIGN RULES (do not weaken these)
    1. SCRUB, don't trust. Every file is filtered through PII_RULES before it is
       written into the repo. Nothing is copied verbatim.
    2. EXCLUDE machine-specific trees entirely (per-profile skill mirrors, the
       operator's home-lab host inventory). They are duplicates or useless to
       anyone else and only widen the PII surface.
    3. HARD GATE before push. After staging, the diff is re-scanned. If ANY
       forbidden pattern survives, the script aborts WITHOUT pushing and exits
       non-zero so the failure is loud.
    4. Never `git add -A` blindly -- only the whitelisted subtrees are synced.

Exit codes: 0 = pushed (or nothing to push), 2 = PII gate tripped, 1 = other error.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Each sync item maps an explicit SOURCE path to its destination name in the
# repo. Sources are named individually because they do NOT all live under one
# root: skills/cron/config live in ~/.hermes, project data lives in
# ~/.hermes. An earlier version assumed a single root and silently wiped
# the repo's skills/ tree by syncing it from an empty directory.
HERMES = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
HERMES_DATA = Path(os.environ.get("HERMES_SRC", Path.home() / ".hermes"))
REPO = Path(os.environ.get("HERMES_REPO", Path.home()))

# (source_path, repo_destination_name)
#
# NOTE: cron/ is deliberately NOT synced. Everything in ~/.hermes/cron is
# runtime state (jobs.json, .fire-*.lock, executions.db, output/) which must
# never be published. The repo's cron/README-CRON-SETUP.md is hand-written
# REPO SOURCE, not a synced artifact -- syncing cron/ would delete it every
# run because no matching file exists upstream.
SYNC_ITEMS: list[tuple[Path, str]] = [
    (HERMES / "config.yaml", "config.yaml"),
    (HERMES / "SOUL.md", "SOUL.md"),
    (HERMES / "skills", "skills"),
]

# A sync that would REMOVE more than this fraction of an existing tree is
# treated as a bug, not an intentional deletion. Refuse and report.
MAX_DELETE_FRACTION = 0.25

# Never sync these, at any depth. Two distinct reasons:
#   (a) machine-specific / duplicate PII surface, and
#   (b) PERSONAL DATA BY NATURE -- backups, wiki content, databases and
#       runtime state have no business in a public repo whether or not a PII
#       scan happens to flag them today. A clean scan is not a licence to
#       publish the operator's notes, memory or database contents.
EXCLUDE_DIRS = {
    # (a) machine-specific
    "home-lab-ssh",        # operator's specific hosts + credentials
    "__pycache__",
    ".git",
    ".hub",                # skill index cache, embeds absolute paths
    # (b) personal data by nature
    "backups",
    ".curator_backups",
    "archives",
    "checkpoints",
    "active-wiki",
    "oracle",
    "incoming",
    "Documents",
    "output",              # cron transcripts: can contain anything
    "sessions",
    "logs",
    "memories",
    "personal-state",
    "cascade-reports",
    "reports",
    "audio_cache",
    "cache",
    "node_modules",
    # (c) CognitivePlatform -- a SEPARATE client project. None of it belongs in
    #     Hermes Brain: not the project, not its infrastructure, not its
    #     confidential domain material. Named explicitly because .gitignore
    #     does NOT protect us here -- this script stages paths directly, so an
    #     ignore rule is never consulted. These names are the real gate.
    "research-cron-knowledge-base",
    "vine-copula-modeling",
    "shap-accuracy-benchmarking",
    "stacked-marginal-rate-calculator",
    "cross-document-transfer-learning",
    "ensemble-weight-management",
    "ocr-quality-metrics",
    "wealth-document-classification",
    "financial-planning-tool-development-pattern",
    "safe-research-append",
    "research-md-append-only",
    "paperclip-integration",
    "Gateway-deployment",
    "Gateway-search",
    "ppli-carrier-monitoring",
    "CognitivePlatform-github-sync",
    "CognitivePlatform-subsystem-integration",
    "CognitivePlatform-subsystem-integration-pattern",
    "CognitivePlatform-research-format",
    "CognitivePlatform-ai-context",
    # Personal home-automation / workflow infra -- not product components, and
    # their examples carry real bearer tokens.
    "home-assistant-mcp-integration",
    "n8n-mcp-integration",
}
EXCLUDE_SUFFIXES = {
    ".log", ".jsonl",
    ".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".db-journal",
    ".pem", ".key", ".p12", ".keystore", ".env",
    ".lock", ".pid", ".sock", ".tmp", ".bak", ".orig", ".old",
    ".pyc",
}
EXCLUDE_NAMES = {
    ".env", "credentials.json", "token.json",
    "auth.json", "auth.lock",
    "google_token.json", "google_client_secret.json",
    "jobs.json", "usage_audit.jsonl", "catch_up_occurrences",
    ".bundled_manifest", ".curator_state", ".curator_ledger.jsonl",
    ".usage.json", "gateway_state.json", "gateway-starts.log",
    "context_length_cache.yaml", "desktop-build-stamp.json",
    "channel_directory.json", "ticker_heartbeat", "ticker_last_success",
}
# Any filename matching these is skipped regardless of suffix.
EXCLUDE_PATTERNS = [
    re.compile(r"^\.fire-.*\.lock$"),
    re.compile(r"\.bak(-.*)?$"),
    re.compile(r"^id_(ed25519|rsa)"),
]

# ---------------------------------------------------------------------------
# PII scrubbing. Order matters: most specific first.
# ---------------------------------------------------------------------------
HOME = str(Path.home())
USER = Path.home().name

PII_RULES: list[tuple[re.Pattern, str]] = [
    # Real secrets -> placeholders
    (re.compile(r"<REDACTED_PASSWORD>\$?"),                        "<REDACTED-PASSWORD>"),
    (re.compile(r"password\s*=\s*['\"][^'\"]{4,}['\"]"), "password='<REDACTED>'"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{12,}"), "Bearer <REDACTED>"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}"),          "<REDACTED-TOKEN>"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"),                 "<REDACTED-KEY>"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
                re.DOTALL),                              "[REDACTED PRIVATE KEY]"),
    # Identities. Order matters: longer/more specific forms first, otherwise a
    # shorter rule consumes the prefix and leaves a mangled tail behind.
    (re.compile(r"<personal-email>\.com"),              "<email>"),
    (re.compile(r"github\.com/<old-username>"),          "github.com/<username>"),
    (re.compile(r"<username>"),                     "<username>"),
    (re.compile(r"\b7791814261\b"),                      "<telegram-chat-id>"),
    (re.compile(r"\b50\.35\.186\.212\b"),                "<public-ip>"),
    (re.compile(r"\bTheHappyHermit\b"),                      "<username>"),
    (re.compile(re.escape(HOME)),                        "$HOME"),
    (re.compile(r"/home/operator\b"),                      "$HOME"),
    (re.compile(r"\boperator\b"),                         "<username>"),
    (re.compile(r"C:[\\/]Users[\\/]operator\b"),            r"C:\\Users\\<username>"),
    (re.compile(r"\bjosh-hermes\b"),                     "<workspace>"),
    (re.compile(r"\bjosh-\b"),                           "<username>-"),
    (re.compile(r"\bHermesAgent\b"),                       "<hostname>"),
    (re.compile(r"\bjoshes\b"),                          "<username>"),
    (re.compile(r"\boperator\b"),                           "<username>"),
    # Personal name -> generic. Possessives first so "the operator's" -> "the user's".
    (re.compile(r"\bJoshua\b"),                          "the user"),
    (re.compile(r"\bJosh's\b"),                          "the user's"),
    (re.compile(r"\bJOSH'S\b"),                          "THE USER'S"),
    (re.compile(r"\bJosh\b"),                            "the user"),
    (re.compile(r"\bJOSH\b"),                            "THE USER"),
    (re.compile(r"\bjosh\b"),                            "<username>"),
    # CognitivePlatform -- separate client project. Any incidental mention inside a
    # general-purpose skill is genericized rather than published.
    (re.compile(r"CognitivePlatform\s+AI", re.I),              "the client platform"),
    (re.compile(r"CognitivePlatform", re.I),                   "the client platform"),
    (re.compile(r"Gateway\.com"),                   "<oracle-server>"),
    (re.compile(r"Gateway"),                        "<oracle-server>"),
    (re.compile(r"paperclipai"),                         "<upstream-org>"),
    (re.compile(r"(?i)paperclip"),                       "the workspace app"),
    (re.compile(r"\bUHNW\b", re.I),                      "high-net-worth"),
    (re.compile(r"\bPPLI\b"),                            "private placement insurance"),
]

# Patterns that must NOT survive into a push. The gate checks these.
FORBIDDEN = [
    ("password", re.compile(r"<REDACTED_PASSWORD>")),
    ("private email", re.compile(r"<old-username>")),
    ("alt identity", re.compile(r"TheHappyHermit")),
    ("username", re.compile(r"\boperator\b")),
    ("personal name", re.compile(r"(?i)\bjosh\b")),
    ("telegram chat id", re.compile(r"\b7791814261\b")),
    ("public ip", re.compile(r"\b50\.35\.186\.212\b")),
    ("home path", re.compile(re.escape(HOME))),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    # CognitivePlatform belongs to a different repo entirely.
    ("CognitivePlatform project", re.compile(r"(?i)CognitivePlatform")),
    ("CognitivePlatform infra", re.compile(r"(?i)Gateway|paperclip")),
    ("client domain term", re.compile(r"(?i)\buhnw\b")),
]

TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".json", ".py", ".sh", ".txt", ".toml",
                 ".cfg", ".ini", ".bash", ".service", ".conf", ""}


def scrub(text: str) -> str:
    for pat, repl in PII_RULES:
        text = pat.sub(repl, text)
    return text


def is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDE_DIRS for part in rel.parts):
        return True
    if path.name in EXCLUDE_NAMES or path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    if any(p.search(path.name) for p in EXCLUDE_PATTERNS):
        return True
    return False


def sync_tree(src: Path, dst: Path) -> tuple[int, int]:
    """Copy src->dst, scrubbing text files. Returns (copied, skipped)."""
    copied = skipped = 0
    if dst.exists():
        shutil.rmtree(dst)
    for cur, dirs, files in os.walk(src):
        curp = Path(cur)
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fname in files:
            sp = curp / fname
            if is_excluded(sp, src):
                skipped += 1
                continue
            rel = sp.relative_to(src)
            dp = dst / rel
            dp.parent.mkdir(parents=True, exist_ok=True)
            if sp.suffix.lower() in TEXT_SUFFIXES:
                try:
                    dp.write_text(scrub(sp.read_text(encoding="utf-8", errors="replace")),
                                  encoding="utf-8", newline="\n")
                    copied += 1
                    continue
                except (UnicodeDecodeError, OSError):
                    pass
            skipped += 1
    return copied, skipped


def git(*args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def main() -> int:
    if not (REPO / ".git").is_dir():
        print(f"FATAL: {REPO} is not a git repo", file=sys.stderr)
        return 1

    total_copied = total_skipped = 0
    for src_path, dest_name in SYNC_ITEMS:
        if not src_path.exists():
            print(f"WARNING: source missing, skipping: {src_path}", file=sys.stderr)
            continue

        dst = REPO / dest_name

        # ---- MASS-DELETION GUARD -------------------------------------
        # If the destination already has many files and the source has far
        # fewer, this is almost certainly a misconfigured source path.
        # Refuse rather than wipe the tree. (This exact bug destroyed the
        # repo's skills/ tree once by syncing from an empty directory.)
        if src_path.is_dir() and dst.is_dir():
            have = sum(1 for _ in dst.rglob("*") if _.is_file())
            incoming = sum(1 for _ in src_path.rglob("*") if _.is_file())
            if have and incoming < have * (1 - MAX_DELETE_FRACTION):
                print(f"FATAL: refusing to sync {dest_name}: destination has "
                      f"{have} files but source {src_path} has only {incoming}. "
                      f"Check the source path.", file=sys.stderr)
                return 1

        if src_path.is_dir():
            c, s = sync_tree(src_path, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(scrub(src_path.read_text(encoding="utf-8", errors="replace")),
                           encoding="utf-8", newline="\n")
            c, s = 1, 0
        total_copied += c
        total_skipped += s
        print(f"synced {dest_name}: {c} files scrubbed, {s} skipped")

    # Stage ONLY the whitelisted destinations -- never `git add -A`.
    for _, dest_name in SYNC_ITEMS:
        if (REPO / dest_name).exists():
            git("add", "--", dest_name, check=False)

    staged = git("diff", "--cached", "--name-only").strip()
    if not staged:
        print("nothing to commit")
        return 0

    # ---- HARD PII GATE -------------------------------------------------
    diff = git("diff", "--cached")
    added = "\n".join(l for l in diff.splitlines() if l.startswith("+"))
    violations = [(label, len(p.findall(added))) for label, p in FORBIDDEN
                  if p.search(added)]
    if violations:
        print("\n*** PII GATE TRIPPED -- REFUSING TO PUSH ***", file=sys.stderr)
        for label, n in violations:
            print(f"    {label}: {n} occurrence(s)", file=sys.stderr)
        git("reset", check=False)
        return 2
    print(f"PII gate: clean ({len(staged.splitlines())} files staged)")

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    git("commit", "-m", f"chore(backup): config snapshot {ts} (PII scrubbed)")
    git("push", "origin", "HEAD")
    print(f"pushed at {ts}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
