"""Tests for revise_plan: revises plan via Claude interactively."""

import os
import sys

import pytest

from conftest import TempIdeaProject

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner

from i2code.implement.idea_project import IdeaProject
from i2code.go_cmd.revise_plan import revise_plan


def _create_all_files(project):
    """Create idea, spec, and plan files so validation passes."""
    idea_path = os.path.join(project.directory, f"{project.name}-idea.md")
    spec_path = os.path.join(project.directory, f"{project.name}-spec.md")
    plan_path = os.path.join(project.directory, f"{project.name}-plan.md")
    for path, content in [
        (idea_path, "My idea"),
        (spec_path, "My spec"),
        (plan_path, "My plan"),
    ]:
        with open(path, "w") as f:
            f.write(content)


def _fake_renderer(template_name, variables):
    parts = [f"template={template_name}"]
    for key, value in sorted(variables.items()):
        parts.append(f"{key}={value}")
    return " | ".join(parts)


def _run_revise_plan(project, runner=None):
    """Run revise_plan with a ready project and return (runner, method, cmd, cwd)."""
    _create_all_files(project)
    if runner is None:
        runner = FakeClaudeRunner()
    revise_plan(project, runner, _fake_renderer)
    method, cmd, cwd = runner.calls[0]
    return runner, method, cmd, cwd


def _create_files_except(project, excluded_suffix):
    """Create all required files except the one matching excluded_suffix."""
    all_files = {"idea.md": "My idea", "spec.md": "My spec", "plan.md": "My plan"}
    for suffix, content in all_files.items():
        if suffix != excluded_suffix:
            path = os.path.join(project.directory, f"{project.name}-{suffix}")
            with open(path, "w") as f:
                f.write(content)


@pytest.mark.unit
class TestRevisePlanValidation:

    @pytest.mark.parametrize("excluded", ["idea.md", "spec.md", "plan.md"])
    def test_exits_when_required_file_missing(self, excluded):
        with TempIdeaProject("my-feature") as project:
            _create_files_except(project, excluded)
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                revise_plan(project, runner, _fake_renderer)
            assert len(runner.calls) == 0


@pytest.mark.unit
class TestRevisePlanTemplateRendering:

    def test_renders_template_with_idea_spec_and_plan(self):
        with TempIdeaProject("my-feature") as project:
            _, _, cmd, _ = _run_revise_plan(project)
            assert "revise-plan.md" in cmd.prompt
            assert project.idea_file in cmd.prompt
            assert project.spec_file in cmd.prompt
            assert project.plan_file in cmd.prompt


@pytest.mark.unit
class TestRevisePlanClaudeInvocation:

    def test_invokes_claude_via_execute(self):
        with TempIdeaProject("my-feature") as project:
            _, method, _, _ = _run_revise_plan(project)
            assert method == "execute"

    def test_command_is_interactive(self):
        with TempIdeaProject("my-feature") as project:
            _, _, cmd, _ = _run_revise_plan(project)
            assert cmd.interactive is True


@pytest.mark.unit
class TestRevisePlanAllowedTools:

    def test_allowed_tools_included_when_repo_root_provided(self, tmp_path):
        repo_root = str(tmp_path / "repo")
        os.makedirs(repo_root)
        idea_dir = str(tmp_path / "repo" / "docs" / "ideas" / "my-idea")
        os.makedirs(idea_dir)
        project = IdeaProject(idea_dir)
        _create_all_files(project)
        runner = FakeClaudeRunner()

        revise_plan(project, runner, _fake_renderer, repo_root=repo_root)

        _, cmd, cwd = runner.calls[0]
        assert cmd.allowed_tools is not None
        assert f"Read(/{repo_root}/**)" in cmd.allowed_tools
        assert f"Write(/{idea_dir}/**)" in cmd.allowed_tools
        assert f"Edit(/{idea_dir}/**)" in cmd.allowed_tools
        assert cwd == repo_root

    def test_standalone_no_allowed_tools(self):
        """Standalone revise_plan (no repo_root) omits allowed_tools and uses project.directory as cwd."""
        with TempIdeaProject("my-feature") as project:
            _, _, cmd, cwd = _run_revise_plan(project)
            assert cmd.allowed_tools is None
            assert cwd == project.directory
