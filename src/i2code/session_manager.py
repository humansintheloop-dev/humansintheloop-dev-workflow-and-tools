"""Session manager: reads session IDs and writes new ones."""

import os
import uuid
from typing import Optional

from i2code.implement.claude_runner import SessionId


def read_session_id(path: str) -> Optional[SessionId]:
    """Read session ID from file as a typed SessionId.

    Args:
        path: Path to the session ID file

    Returns:
        SessionId(session_id, is_new=False) if file exists, else None
    """
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        session_id = f.read().strip()
    return SessionId(session_id=session_id, is_new=False)


def read_or_create_session(path: str) -> SessionId:
    """Read existing session ID or create a new one, returning a typed SessionId.

    Args:
        path: Path to the session ID file

    Returns:
        SessionId with is_new=False when the file exists, otherwise a freshly
        generated UUID written to the file with is_new=True.
    """
    existing = read_session_id(path)
    if existing is not None:
        return existing
    new_id = create_session_id(path)
    return SessionId(session_id=new_id, is_new=True)


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
