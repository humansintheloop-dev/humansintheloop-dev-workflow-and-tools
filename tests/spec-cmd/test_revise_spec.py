"""Tests for revise_spec: validates idea and spec, constructs prompt, invokes Claude."""

import os
import sys

import pytest

from conftest import TempIdeaProject
from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject
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


@pytest.mark.unit
class TestReviseSpecAllowedTools:

    def test_allowed_tools_included_when_repo_root_provided(self, tmp_path):
        repo_root = str(tmp_path / "repo")
        os.makedirs(repo_root)
        idea_dir = str(tmp_path / "repo" / "docs" / "ideas" / "my-idea")
        os.makedirs(idea_dir)
        project = IdeaProject(idea_dir)
        _create_idea_file(project)
        _create_spec_file(project)
        runner = FakeClaudeRunner()

        revise_spec(project, runner, repo_root=repo_root)

        _, cmd, cwd = runner.calls[0]
        assert "--allowedTools" in cmd
        allowed_tools_idx = cmd.index("--allowedTools")
        allowed_tools_value = cmd[allowed_tools_idx + 1]
        assert f"Read({repo_root}/)" in allowed_tools_value
        assert f"Write({idea_dir}/)" in allowed_tools_value
        assert f"Edit({idea_dir}/)" in allowed_tools_value
        assert cwd == repo_root

    def test_standalone_no_allowed_tools(self):
        """Standalone revise_spec (no repo_root) omits --allowedTools and uses project.directory as cwd."""
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, cwd = _run_revise_spec(project)
            assert "--allowedTools" not in cmd
            assert cwd == project.directory
