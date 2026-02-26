"""Tests for brainstorm_idea: directory creation, editor detection, session management, Claude invocation."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))

from conftest import TempIdeaProject
from fake_claude_runner import FakeClaudeRunner
from i2code.idea_cmd.brainstorm import brainstorm_idea, detect_editor


@pytest.mark.unit
class TestDirectoryCreation:

    def test_creates_directory_when_missing(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "new-feature")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()
        editor_calls = []

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: editor_calls.append(cmd),
        )

        assert os.path.isdir(idea_dir)


@pytest.mark.unit
class TestEditorDetection:

    def test_detects_code_first(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/code" if cmd == "code" else None)
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        assert detect_editor() == ["code", "--wait"]

    def test_falls_back_to_visual(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.setenv("VISUAL", "subl")
        monkeypatch.delenv("EDITOR", raising=False)
        assert detect_editor() == ["subl"]

    def test_falls_back_to_editor(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.setenv("EDITOR", "nano")
        assert detect_editor() == ["nano"]

    def test_falls_back_to_vi(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.delenv("VISUAL", raising=False)
        monkeypatch.delenv("EDITOR", raising=False)
        assert detect_editor() == ["vi"]

    def test_visual_takes_priority_over_editor(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: None)
        monkeypatch.setenv("VISUAL", "subl")
        monkeypatch.setenv("EDITOR", "nano")
        assert detect_editor() == ["subl"]

    def test_code_takes_priority_over_visual(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/code" if cmd == "code" else None)
        monkeypatch.setenv("VISUAL", "subl")
        assert detect_editor() == ["code", "--wait"]


@pytest.mark.unit
class TestIdeaFileCreation:

    def test_creates_idea_file_with_template(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: None,
        )

        idea_file = os.path.join(idea_dir, "my-idea-idea.md")
        assert os.path.isfile(idea_file)
        with open(idea_file) as f:
            assert "PLEASE DESCRIBE YOUR IDEA" in f.read()

    def test_skips_editor_when_idea_file_exists(self):
        with TempIdeaProject("my-feature") as project:
            idea_path = os.path.join(project.directory, f"{project.name}-idea.md")
            with open(idea_path, "w") as f:
                f.write("Existing idea")

            runner = FakeClaudeRunner()
            editor_calls = []

            brainstorm_idea(
                project, runner,
                run_editor=lambda cmd: editor_calls.append(cmd),
            )

            assert len(editor_calls) == 0

    def test_launches_editor_for_new_idea(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()
        editor_calls = []

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: editor_calls.append(cmd),
        )

        assert len(editor_calls) == 1
        assert editor_calls[0][-1].endswith("my-idea-idea.md")


@pytest.mark.unit
class TestSessionManagement:

    def test_generates_session_id_for_new_session(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: None,
        )

        _, cmd, _ = runner.calls[0]
        assert "--session-id" in cmd
        assert os.path.isfile(project.session_id_file)

    def test_resumes_existing_session(self):
        with TempIdeaProject("my-feature") as project:
            idea_path = os.path.join(project.directory, f"{project.name}-idea.md")
            with open(idea_path, "w") as f:
                f.write("Existing idea")
            with open(project.session_id_file, "w") as f:
                f.write("existing-session-id")

            runner = FakeClaudeRunner()
            brainstorm_idea(
                project, runner,
                run_editor=lambda cmd: None,
            )

            _, cmd, _ = runner.calls[0]
            assert "--resume" in cmd
            assert "existing-session-id" in cmd


@pytest.mark.unit
class TestClaudeInvocation:

    def test_invokes_claude_interactively(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: None,
        )

        method, _, _ = runner.calls[0]
        assert method == "run_interactive"

    def test_claude_prompt_contains_idea_and_discussion_files(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: None,
        )

        _, cmd, _ = runner.calls[0]
        prompt = cmd[-1]
        assert project.idea_file in prompt
        assert project.discussion_file in prompt

    def test_claude_command_starts_with_claude(self, tmp_path):
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()

        brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: None,
        )

        _, cmd, _ = runner.calls[0]
        assert cmd[0] == "claude"

    def test_returns_claude_result(self, tmp_path):
        from i2code.implement.claude_runner import ClaudeResult
        from i2code.implement.idea_project import IdeaProject

        idea_dir = str(tmp_path / "my-idea")
        project = IdeaProject(idea_dir)
        runner = FakeClaudeRunner()
        runner.set_result(ClaudeResult(returncode=0))

        result = brainstorm_idea(
            project, runner,
            run_editor=lambda cmd: None,
        )

        assert result.returncode == 0
