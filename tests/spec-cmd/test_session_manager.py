"""Tests for session_manager: reads session ID and builds session args."""


import pytest

from conftest import TempIdeaProject


@pytest.mark.unit
class TestReadSessionId:

    def test_returns_session_id_when_file_exists(self):
        from i2code.session_manager import read_session_id

        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("abc-123-session")
            result = read_session_id(project.session_id_file)
            assert result == "abc-123-session"

    def test_returns_none_when_file_missing(self):
        from i2code.session_manager import read_session_id

        result = read_session_id("/nonexistent/path/sessionID.txt")
        assert result is None

    def test_strips_whitespace_from_session_id(self):
        from i2code.session_manager import read_session_id

        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("  abc-123  \n")
            result = read_session_id(project.session_id_file)
            assert result == "abc-123"


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
