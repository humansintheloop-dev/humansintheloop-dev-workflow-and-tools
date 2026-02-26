"""Tests for revise_plan: revises plan via Claude interactively."""

import os
import sys

import pytest

from conftest import TempIdeaProject

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner

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
    """Run revise_plan with a ready project and sensible defaults."""
    _create_all_files(project)
    if runner is None:
        runner = FakeClaudeRunner()
    revise_plan(project, runner, _fake_renderer)
    return runner


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
            runner = _run_revise_plan(project)
            prompt = runner.calls[0][1][-1]
            assert "revise-plan.md" in prompt
            assert project.idea_file in prompt
            assert project.spec_file in prompt
            assert project.plan_file in prompt


@pytest.mark.unit
class TestRevisePlanClaudeInvocation:

    def test_invokes_claude_in_interactive_mode(self):
        with TempIdeaProject("my-feature") as project:
            runner = _run_revise_plan(project)
            assert runner.calls[0][0] == "run_interactive"

    def test_claude_command_starts_with_claude(self):
        with TempIdeaProject("my-feature") as project:
            runner = _run_revise_plan(project)
            assert runner.calls[0][1][0] == "claude"
