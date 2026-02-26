"""Session manager: reads session IDs and builds session CLI args."""

import os
import uuid
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


def create_session_id(path: str) -> str:
    """Generate a UUID session ID and write it to the file.

    Args:
        path: Path to the session ID file

    Returns:
        The generated UUID session ID string
    """
    session_id = str(uuid.uuid4())
    with open(path, "w") as f:
        f.write(session_id)
    return session_id


def get_or_create_session_args(session_id_path: str) -> list[str]:
    """Build Claude CLI args, creating a new session ID if needed.

    Returns ["--resume", id] for existing sessions, or
    ["--session-id", new_id] for new ones (writing the new ID to file).

    Args:
        session_id_path: Path to the session ID file

    Returns:
        List of CLI args for session management
    """
    session_id = read_session_id(session_id_path)
    if session_id:
        return ["--resume", session_id]
    new_id = create_session_id(session_id_path)
    return ["--session-id", new_id]
