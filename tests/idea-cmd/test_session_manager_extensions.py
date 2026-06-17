"""Tests for session_manager extensions: create_session_id, read_or_create_session."""

import os

import pytest

from conftest import TempIdeaProject
from i2code.implement.claude_runner import SessionId
from i2code.session_manager import (
    create_session_id,
    read_or_create_session,
)


@pytest.mark.unit
class TestCreateSessionId:

    def test_generates_uuid_and_writes_to_file(self):
        with TempIdeaProject("my-feature") as project:
            session_id = create_session_id(project.session_id_file)
            assert len(session_id) == 36  # UUID format: 8-4-4-4-12
            assert "-" in session_id
            with open(project.session_id_file) as f:
                assert f.read().strip() == session_id

    def test_returns_string(self):
        with TempIdeaProject("my-feature") as project:
            session_id = create_session_id(project.session_id_file)
            assert isinstance(session_id, str)

    def test_creates_file_on_disk(self):
        with TempIdeaProject("my-feature") as project:
            create_session_id(project.session_id_file)
            assert os.path.isfile(project.session_id_file)


@pytest.mark.unit
class Test_read_or_create_session:

    def test_read_or_create_returns_existing_session(self):
        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("existing-session-id")
            result = read_or_create_session(project.session_id_file)
            assert result == SessionId(session_id="existing-session-id", is_new=False)
            with open(project.session_id_file) as f:
                assert f.read().strip() == "existing-session-id"

    def test_read_or_create_creates_new_session_and_writes_file(self):
        with TempIdeaProject("my-feature") as project:
            result = read_or_create_session(project.session_id_file)
            assert isinstance(result, SessionId)
            assert result.is_new is True
            assert len(result.session_id) == 36
            assert os.path.isfile(project.session_id_file)
            with open(project.session_id_file) as f:
                assert f.read().strip() == result.session_id
