"""Tests for create_spec: validates idea, renders template, invokes Claude."""

import os
import sys

import pytest

from conftest import TempIdeaProject
from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.spec_cmd.create_spec import create_spec

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner


def _create_idea_file(project, content="My idea"):
    path = os.path.join(project.directory, f"{project.name}-idea.md")
    with open(path, "w") as f:
        f.write(content)


def _run_create_spec(project, runner=None):
    """Run create_spec with a ready project and return (runner, result, method, cmd, cwd)."""
    _create_idea_file(project)
    if runner is None:
        runner = FakeClaudeRunner()
    result = create_spec(project, runner)
    method, cmd, cwd = runner.calls[0]
    return runner, result, method, cmd, cwd


@pytest.mark.unit
class TestCreateSpecValidation:

    def test_exits_when_idea_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                create_spec(project, runner)
            assert len(runner.calls) == 0


@pytest.mark.unit
class TestCreateSpecTemplateRendering:

    def test_renders_template_with_idea_and_discussion_files(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_spec(project)
            assert project.idea_file in cmd.prompt
            assert project.discussion_file in cmd.prompt


@pytest.mark.unit
class TestCreateSpecSessionResume:

    def test_resumes_session_when_session_file_exists(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_file(project)
            with open(project.session_id_file, "w") as f:
                f.write("existing-session-id")

            runner = FakeClaudeRunner()
            create_spec(project, runner)

            _, cmd, _ = runner.calls[0]
            assert cmd.session_id is not None
            assert cmd.session_id.session_id == "existing-session-id"
            assert cmd.session_id.is_new is False

    def test_no_resume_when_no_session_file(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_spec(project)
            assert cmd.session_id is None


@pytest.mark.unit
class TestCreateSpecClaudeInvocation:

    def test_invokes_claude_via_execute(self):
        with TempIdeaProject("my-feature") as project:
            _, _, method, _, _ = _run_create_spec(project)
            assert method == "execute"

    def test_command_is_interactive(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_spec(project)
            assert cmd.interactive is True

    def test_returns_claude_result(self):
        with TempIdeaProject("my-feature") as project:
            runner = FakeClaudeRunner()
            runner.set_result(ClaudeResult(returncode=0))
            _, result, _, _, _ = _run_create_spec(project, runner)
            assert result.returncode == 0


@pytest.mark.unit
class TestCreateSpecAllowedTools:

    def test_allowed_tools_included_when_repo_root_provided(self, tmp_path):
        repo_root = str(tmp_path / "repo")
        os.makedirs(repo_root)
        idea_dir = str(tmp_path / "repo" / "docs" / "ideas" / "my-idea")
        os.makedirs(idea_dir)
        project = IdeaProject(idea_dir)
        _create_idea_file(project)
        runner = FakeClaudeRunner()

        create_spec(project, runner, repo_root=repo_root)

        _, cmd, cwd = runner.calls[0]
        assert cmd.allowed_tools is not None
        assert f"Read(/{repo_root}/**)" in cmd.allowed_tools
        assert f"Write(/{idea_dir}/**)" in cmd.allowed_tools
        assert f"Edit(/{idea_dir}/**)" in cmd.allowed_tools
        assert cwd == repo_root

    def test_standalone_no_allowed_tools(self):
        """Standalone create_spec (no repo_root) omits allowed_tools and uses project.directory as cwd."""
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, cwd = _run_create_spec(project)
            assert cmd.allowed_tools is None
            assert cwd == project.directory
