"""Tests for create_spec: validates idea, renders template, invokes Claude."""

import os
import sys

import pytest

from conftest import TempIdeaProject
from i2code.implement.claude_runner import ClaudeResult
from i2code.spec_cmd.create_spec import create_spec

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner


def _create_idea_file(project, content="My idea"):
    path = os.path.join(project.directory, f"{project.name}-idea.md")
    with open(path, "w") as f:
        f.write(content)


def _run_create_spec(project, runner=None):
    """Run create_spec with a ready project and return (runner, method, cmd, cwd)."""
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
            prompt = cmd[-1]
            assert project.idea_file in prompt
            assert project.discussion_file in prompt


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
            assert "--resume" in cmd
            assert "existing-session-id" in cmd

    def test_no_resume_when_no_session_file(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_spec(project)
            assert "--resume" not in cmd


@pytest.mark.unit
class TestCreateSpecClaudeInvocation:

    def test_invokes_claude_interactively(self):
        with TempIdeaProject("my-feature") as project:
            _, _, method, _, _ = _run_create_spec(project)
            assert method == "run_interactive"

    def test_claude_command_starts_with_claude(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_spec(project)
            assert cmd[0] == "claude"

    def test_returns_claude_result(self):
        with TempIdeaProject("my-feature") as project:
            runner = FakeClaudeRunner()
            runner.set_result(ClaudeResult(returncode=0))
            _, result, _, _, _ = _run_create_spec(project, runner)
            assert result.returncode == 0
