"""Tests for session_manager: reads session ID."""


import pytest

from conftest import TempIdeaProject


@pytest.mark.unit
class TestReadSessionId:

    def test_read_session_id_returns_session_id_dataclass_when_file_present(self):
        from i2code.implement.claude_runner import SessionId
        from i2code.session_manager import read_session_id

        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("abc-123-session")
            result = read_session_id(project.session_id_file)
            assert result == SessionId(session_id="abc-123-session", is_new=False)

    def test_read_session_id_returns_none_when_file_absent(self):
        from i2code.session_manager import read_session_id

        result = read_session_id("/nonexistent/path/sessionID.txt")
        assert result is None
