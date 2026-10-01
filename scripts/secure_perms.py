"""Set owner-only permissions on a secrets directory, portably.

On POSIX this is `chmod 700`. On Windows it is a no-op that reports why:
NTFS permissions come from ACLs, `st_mode` does not carry them, and
`os.chmod` there only toggles the read-only attribute -- so calling it
would either silently do nothing or flip the directory read-only and
break the processes that write secrets into it.

The original three call sites (init_db.py, init_experience_db.py,
init_graphify.py) called os.chmod unconditionally, which made every
Windows install of those scripts fail or mis-report its own state.
"""

from __future__ import annotations

import os
from pathlib import Path


def secure_secrets_dir(path: "str | os.PathLike[str]") -> str:
    """Apply owner-only permissions where the platform has them.

    Returns a short human-readable description of what was done, for
    logging. Never raises: a permissions problem on one directory should
    not abort an initialization that has already done its real work.
    """
    p = Path(path)
    try:
        if os.name == "nt":
            return "skipped (Windows: permissions are ACL-managed, not mode bits)"
        if not p.exists():
            return "skipped (does not exist)"
        os.chmod(p, 0o700)
        return "set to 700"
    except Exception as e:
        return f"could not set 700: {e}"
