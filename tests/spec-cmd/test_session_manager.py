"""Tests for session_manager: reads session ID and builds session args."""


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


@pytest.mark.unit
class TestBuildSessionArgs:

    def test_returns_resume_args_when_session_file_exists(self):
        from i2code.session_manager import build_session_args

        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("session-xyz")
            result = build_session_args(project.session_id_file)
            assert result == ["--resume", "session-xyz"]

    def test_returns_empty_list_when_no_session_file(self):
        from i2code.session_manager import build_session_args

        result = build_session_args("/nonexistent/path/sessionID.txt")
        assert result == []
