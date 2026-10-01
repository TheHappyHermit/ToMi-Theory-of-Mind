#!/usr/bin/env python3
"""
scripts/migrate_frontmatter_timestamps.py — Add RFC 3339 created/updated to wiki frontmatter.

Backfill `created` from git history where possible, else file mtime.
Sets `updated` = file mtime. RFC 3339 UTC format (YYYY-MM-DDTHH:MM:SSZ).
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import active_wiki_path, oracle_brain_path

REPO_ROOT = Path(__file__).resolve().parent.parent
WIKI_DIRS = [
    active_wiki_path(),
    oracle_brain_path(),
]

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
CREATED_RE = re.compile(r"^created:", re.MULTILINE)
UPDATED_RE = re.compile(r"^updated:", re.MULTILINE)


def get_git_creation_time(filepath):
    """Get the first commit time for a file from git history."""
    try:
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%aI", "--", str(filepath)],
            capture_output=True, text=True, cwd=str(REPO_ROOT)
        )
        if result.returncode == 0:
            dates = result.stdout.strip().split("\n")
            if dates and dates[0]:
                # Last entry is the first commit (git log --follow reverses)
                return dates[-1].strip()
    except Exception:
        pass
    return None


def format_timestamp(dt):
    """Format datetime as RFC 3339 UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def migrate_file(filepath):
    """Add created/updated to frontmatter if missing."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    
    # Check for frontmatter
    match = FRONTMATTER_RE.search(content)
    if not match:
        return False  # No frontmatter, skip
    
    fm_text = match.group(1)
    
    has_created = CREATED_RE.search(fm_text)
    has_updated = UPDATED_RE.search(fm_text)
    
    if has_created and has_updated:
        return False  # Already has both
    
    # Get timestamps
    git_time = get_git_creation_time(filepath)
    if git_time:
        created_dt = datetime.fromisoformat(git_time.replace("Z", "+00:00"))
    else:
        stat = filepath.stat()
        created_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    
    stat = filepath.stat()
    updated_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    
    created_str = format_timestamp(created_dt)
    updated_str = format_timestamp(updated_dt)
    
    # Add missing fields to frontmatter
    additions = []
    if not has_created:
        additions.append(f"created: {created_str}")
    if not has_updated:
        additions.append(f"updated: {updated_str}")
    
    # Insert after the closing --- of frontmatter
    new_fm = fm_text.rstrip() + "\n" + "\n".join(additions)
    new_content = content[:match.start(1)] + new_fm + content[match.end(1):]
    
    filepath.write_text(new_content, encoding="utf-8")
    return True


def migrate_all():
    """Migrate all markdown files in wiki directories."""
    count = 0
    for wiki_dir in WIKI_DIRS:
        if not wiki_dir.exists():
            continue
        for root, dirs, files in os.walk(wiki_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in {"node_modules", "__pycache__"}]
            for f in files:
                if f.endswith(".md"):
                    filepath = Path(root) / f
                    if migrate_file(filepath):
                        count += 1
                        print(f"  Migrated: {filepath.relative_to(REPO_ROOT)}")
    print(f"\nTotal files migrated: {count}")


if __name__ == "__main__":
    migrate_all()
