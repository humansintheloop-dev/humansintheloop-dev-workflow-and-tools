"""Tests for session_manager extensions: create_session_id, get_or_create_session_args."""

import os

import pytest

from conftest import TempIdeaProject
from i2code.session_manager import create_session_id, get_or_create_session_args


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
class TestGetOrCreateSessionArgs:

    def test_returns_resume_for_existing_session(self):
        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("existing-session-id")
            result = get_or_create_session_args(project.session_id_file)
            assert result == ["--resume", "existing-session-id"]

    def test_returns_session_id_for_new_session(self):
        with TempIdeaProject("my-feature") as project:
            result = get_or_create_session_args(project.session_id_file)
            assert result[0] == "--session-id"
            assert len(result[1]) == 36  # UUID

    def test_creates_session_file_for_new_session(self):
        with TempIdeaProject("my-feature") as project:
            get_or_create_session_args(project.session_id_file)
            assert os.path.isfile(project.session_id_file)

    def test_does_not_overwrite_existing_session(self):
        with TempIdeaProject("my-feature") as project:
            with open(project.session_id_file, "w") as f:
                f.write("keep-this-id")
            get_or_create_session_args(project.session_id_file)
            with open(project.session_id_file) as f:
                assert f.read().strip() == "keep-this-id"
