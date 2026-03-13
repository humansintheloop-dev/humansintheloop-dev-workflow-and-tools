"""Tests that orchestrator default step functions pass repo_root to Claude."""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner
from i2code.go_cmd.orchestrator import (
    _default_brainstorm_idea,
    _default_create_spec,
    _default_revise_spec,
    _default_create_plan,
    _default_revise_plan,
)
from i2code.implement.claude_runner import CapturedOutput, ClaudeResult
from i2code.implement.idea_project import IdeaProject


VALID_PLAN = """\
# Implementation Plan

## Steel Thread 1: Feature

- [ ] **Task 1.1: Do something useful**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/ -v`
  - Observable: Something observable happens
  - Evidence: Tests pass
  - Steps:
    - [ ] Step one
"""


def _make_idea_project(tmp_path, name="my-feature"):
    """Create an IdeaProject with docs/ideas/draft structure so _git_root_from_path works."""
    repo_root = tmp_path / "repo"
    idea_dir = repo_root / "docs" / "ideas" / "draft" / name
    os.makedirs(idea_dir)
    (idea_dir / f"{name}-idea.md").write_text("test idea")
    return IdeaProject(str(idea_dir)), str(repo_root)


def _make_idea_project_with_spec(tmp_path, name="my-feature"):
    """Create an IdeaProject with idea and spec files."""
    project, repo_root = _make_idea_project(tmp_path, name)
    idea_dir = tmp_path / "repo" / "docs" / "ideas" / "draft" / name
    (idea_dir / f"{name}-spec.md").write_text("test spec")
    return project, repo_root


def _make_idea_project_with_plan(tmp_path, name="my-feature"):
    """Create an IdeaProject with idea, spec, and plan files."""
    project, repo_root = _make_idea_project_with_spec(tmp_path, name)
    idea_dir = tmp_path / "repo" / "docs" / "ideas" / "draft" / name
    (idea_dir / f"{name}-plan.md").write_text("test plan")
    return project, repo_root


def _assert_repo_root_cwd(fake, expected_repo_root):
    _, cmd, cwd = fake.calls[0]
    assert cwd == expected_repo_root, (
        f"Expected cwd={expected_repo_root}, got cwd={cwd}"
    )
    assert "--allowedTools" in cmd


@pytest.mark.unit
class TestDefaultBrainstormPassesRepoRoot:

    @patch("i2code.go_cmd.orchestrator.ClaudeRunner")
    def test_cwd_is_repo_root_not_idea_dir(self, mock_runner_cls, tmp_path):
        fake = FakeClaudeRunner()
        mock_runner_cls.return_value = fake

        project, expected_repo_root = _make_idea_project(tmp_path)
        _default_brainstorm_idea(project)

        _assert_repo_root_cwd(fake, expected_repo_root)


@pytest.mark.unit
class TestDefaultCreateSpecPassesRepoRoot:

    @patch("i2code.go_cmd.orchestrator.ClaudeRunner")
    def test_cwd_is_repo_root_not_idea_dir(self, mock_runner_cls, tmp_path):
        fake = FakeClaudeRunner()
        mock_runner_cls.return_value = fake

        project, expected_repo_root = _make_idea_project(tmp_path)
        _default_create_spec(project)

        _assert_repo_root_cwd(fake, expected_repo_root)


@pytest.mark.unit
class TestDefaultReviseSpecPassesRepoRoot:

    @patch("i2code.go_cmd.orchestrator.ClaudeRunner")
    def test_cwd_is_repo_root_not_idea_dir(self, mock_runner_cls, tmp_path):
        fake = FakeClaudeRunner()
        mock_runner_cls.return_value = fake

        project, expected_repo_root = _make_idea_project_with_spec(tmp_path)
        _default_revise_spec(project)

        _assert_repo_root_cwd(fake, expected_repo_root)


def _run_default_create_plan(tmp_path):
    """Run _default_create_plan with all dependencies patched, return (fake, repo_root)."""
    fake = FakeClaudeRunner()
    fake.set_result(ClaudeResult(
        returncode=0,
        output=CapturedOutput(stdout=VALID_PLAN, stderr=""),
    ))
    project, repo_root = _make_idea_project_with_spec(tmp_path)
    with (
        patch("i2code.go_cmd.orchestrator.validate_plan", return_value=(True, [])),
        patch("i2code.go_cmd.orchestrator.list_plugin_skills", return_value=""),
        patch("i2code.go_cmd.orchestrator.render_template", return_value="prompt"),
        patch("i2code.go_cmd.orchestrator.ClaudeRunner", return_value=fake),
    ):
        _default_create_plan(project)
    return fake, repo_root


@pytest.mark.unit
class TestDefaultCreatePlanPassesRepoRoot:

    def test_cwd_is_repo_root_not_idea_dir(self, tmp_path):
        fake, expected_repo_root = _run_default_create_plan(tmp_path)
        _assert_repo_root_cwd(fake, expected_repo_root)


@pytest.mark.unit
class TestDefaultRevisePlanPassesRepoRoot:

    @patch("i2code.go_cmd.orchestrator.render_template", return_value="prompt")
    @patch("i2code.go_cmd.orchestrator.ClaudeRunner")
    def test_cwd_is_repo_root_not_idea_dir(
        self, mock_runner_cls, _render, tmp_path,
    ):
        fake = FakeClaudeRunner()
        mock_runner_cls.return_value = fake

        project, expected_repo_root = _make_idea_project_with_plan(tmp_path)
        _default_revise_plan(project)

        _assert_repo_root_cwd(fake, expected_repo_root)
