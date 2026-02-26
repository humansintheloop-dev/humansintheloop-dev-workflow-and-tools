"""Tests for revise_spec: validates idea and spec, constructs prompt, invokes Claude."""

import os
import sys

import pytest

from conftest import TempIdeaProject
from i2code.implement.claude_runner import ClaudeResult
from i2code.spec_cmd.revise_spec import revise_spec

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner


def _create_idea_file(project, content="My idea"):
    path = os.path.join(project.directory, f"{project.name}-idea.md")
    with open(path, "w") as f:
        f.write(content)


def _create_spec_file(project, content="My spec"):
    path = os.path.join(project.directory, f"{project.name}-spec.md")
    with open(path, "w") as f:
        f.write(content)


def _run_revise_spec(project, runner=None):
    """Run revise_spec with a ready project and return (runner, result, method, cmd, cwd)."""
    _create_idea_file(project)
    _create_spec_file(project)
    if runner is None:
        runner = FakeClaudeRunner()
    result = revise_spec(project, runner)
    method, cmd, cwd = runner.calls[0]
    return runner, result, method, cmd, cwd


@pytest.mark.unit
class TestReviseSpecValidation:

    def test_exits_when_idea_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            _create_spec_file(project)
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                revise_spec(project, runner)
            assert len(runner.calls) == 0

    def test_exits_when_spec_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_file(project)
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                revise_spec(project, runner)
            assert len(runner.calls) == 0


@pytest.mark.unit
class TestReviseSpecPromptContent:

    def test_prompt_contains_idea_file_path(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_revise_spec(project)
            prompt = cmd[-1]
            assert project.idea_file in prompt

    def test_prompt_contains_discussion_file_path(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_revise_spec(project)
            prompt = cmd[-1]
            assert project.discussion_file in prompt

    def test_prompt_contains_spec_file_path(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_revise_spec(project)
            prompt = cmd[-1]
            assert project.spec_file in prompt

    def test_prompt_describes_three_files(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_revise_spec(project)
            prompt = cmd[-1]
            assert "three files" in prompt.lower()


@pytest.mark.unit
class TestReviseSpecClaudeInvocation:

    def test_invokes_claude_interactively(self):
        with TempIdeaProject("my-feature") as project:
            _, _, method, _, _ = _run_revise_spec(project)
            assert method == "run_interactive"

    def test_claude_command_starts_with_claude(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_revise_spec(project)
            assert cmd[0] == "claude"

    def test_returns_claude_result(self):
        with TempIdeaProject("my-feature") as project:
            runner = FakeClaudeRunner()
            runner.set_result(ClaudeResult(returncode=0))
            _, result, _, _, _ = _run_revise_spec(project, runner)
            assert result.returncode == 0

    def test_runs_in_project_directory(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, _, cwd = _run_revise_spec(project)
            assert cwd == project.directory
