"""Session manager: reads session IDs and builds session CLI args."""

import os
from typing import Optional


def read_session_id(path: str) -> Optional[str]:
    """Read session ID from file if it exists.

    Args:
        path: Path to the session ID file

    Returns:
        Session ID string, or None if file does not exist
    """
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return f.read().strip()


def build_session_args(session_id_path: str) -> list[str]:
    """Build Claude CLI args for session resume.

    Args:
        session_id_path: Path to the session ID file

    Returns:
        ["--resume", id] if session file exists, else empty list
    """
    session_id = read_session_id(session_id_path)
    if session_id:
        return ["--resume", session_id]
    return []
