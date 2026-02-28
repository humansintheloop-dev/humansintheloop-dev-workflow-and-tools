"""Tests for review_issues: finds active issues from current year,
excludes type: unknown, creates resolved dirs, respects --project filter,
handles no issues found (exit 0), renders template, invokes Claude."""

import os
import tempfile
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from i2code.improve.review_issues import review_issues


def _create_tracking_dir(tmpdir):
    """Create a bare HITL tracking directory."""
    tracking_dir = os.path.join(tmpdir, "hitl-tracking")
    os.makedirs(tracking_dir)
    return tracking_dir


def _create_project_with_issues(tracking_dir, project_name, issue_specs):
    """Create a project directory with issues/active/ containing issue files.

    Args:
        tracking_dir: Root HITL tracking directory
        project_name: Name of the project subdirectory
        issue_specs: List of (filename, content) tuples
    """
    active_dir = os.path.join(tracking_dir, project_name, "issues", "active")
    os.makedirs(active_dir, exist_ok=True)
    for filename, content in issue_specs:
        with open(os.path.join(active_dir, filename), "w") as f:
            f.write(content)


@contextmanager
def _tracking_env(project_issues=None):
    """Create a temporary HITL tracking directory with mocked year and optional issues.

    Args:
        project_issues: dict of {project_name: [(filename, content), ...]}

    Yields tracking_dir.
    """
    with patch("i2code.improve.review_issues._current_year", return_value="2026"), \
         tempfile.TemporaryDirectory() as tmpdir:
        tracking_dir = _create_tracking_dir(tmpdir)
        if project_issues:
            for pname, specs in project_issues.items():
                _create_project_with_issues(tracking_dir, pname, specs)
        yield tracking_dir


def _review_with_issues(fake_runner, fake_renderer, project_issues, **kwargs):
    """Create tracking env, run review_issues, return result."""
    with _tracking_env(project_issues) as tracking_dir:
        return review_issues(tracking_dir, fake_runner, fake_renderer, **kwargs)


_SINGLE_BUG = {"my-project": [("2026-01-15-bug.md", "status: active\nBug")]}


@pytest.mark.unit
class TestValidation:

    def test_raises_when_tracking_dir_does_not_exist(self, fake_runner, fake_renderer):
        with pytest.raises(SystemExit):
            review_issues("/nonexistent/path", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_project_dir_does_not_exist(self, fake_runner, fake_renderer):
        with _tracking_env() as tracking_dir:
            with pytest.raises(SystemExit):
                review_issues(tracking_dir, fake_runner, fake_renderer, project="nonexistent")
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestIssueFinding:

    def test_finds_active_issues_from_current_year(self, fake_runner, fake_renderer):
        with _tracking_env({"my-project": [("2026-01-15-bug-report.md", "status: active\nSome bug")]}) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            _, variables = fake_renderer.calls[0]
            assert "2026-01-15-bug-report.md" in variables["ACTIVE_ISSUES"]

    def test_ignores_issues_from_previous_year(self, fake_runner, fake_renderer):
        with _tracking_env({"my-project": [
            ("2025-12-01-old-issue.md", "status: active\nOld issue"),
            ("2026-01-15-new-issue.md", "status: active\nNew issue"),
        ]}) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            _, variables = fake_renderer.calls[0]
            assert "2025-12-01-old-issue.md" not in variables["ACTIVE_ISSUES"]
            assert "2026-01-15-new-issue.md" in variables["ACTIVE_ISSUES"]


@pytest.mark.unit
class TestTypeUnknownExclusion:

    def test_excludes_issues_with_type_unknown(self, fake_runner, fake_renderer):
        with _tracking_env({"my-project": [
            ("2026-01-15-good-issue.md", "status: active\nReal issue"),
            ("2026-01-16-unknown-issue.md", "type: unknown\nNot relevant"),
        ]}) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            _, variables = fake_renderer.calls[0]
            assert "2026-01-15-good-issue.md" in variables["ACTIVE_ISSUES"]
            assert "2026-01-16-unknown-issue.md" not in variables["ACTIVE_ISSUES"]

    def test_all_issues_type_unknown_exits_zero(self, fake_runner, fake_renderer):
        result = _review_with_issues(fake_runner, fake_renderer, {"my-project": [
            ("2026-01-15-unknown1.md", "type: unknown\nNot relevant"),
            ("2026-01-16-unknown2.md", "type: unknown\nAlso not relevant"),
        ]})
        assert result is None
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestNoIssuesFound:

    def test_no_issues_found_returns_none(self, fake_runner, fake_renderer):
        with _tracking_env() as tracking_dir:
            os.makedirs(os.path.join(tracking_dir, "my-project"))
            result = review_issues(tracking_dir, fake_runner, fake_renderer)
        assert result is None
        assert len(fake_runner.calls) == 0

    def test_no_issues_dir_returns_none(self, fake_runner, fake_renderer):
        with _tracking_env() as tracking_dir:
            result = review_issues(tracking_dir, fake_runner, fake_renderer)
        assert result is None
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestResolvedDirCreation:

    def test_creates_resolved_dir_for_project_with_active_issues(self, fake_runner, fake_renderer):
        with _tracking_env({"my-project": [("2026-01-15-bug.md", "status: active\nBug report")]}) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            resolved_dir = os.path.join(tracking_dir, "my-project", "issues", "resolved")
            assert os.path.isdir(resolved_dir)

    def test_creates_resolved_dirs_for_multiple_projects(self, fake_runner, fake_renderer):
        with _tracking_env({
            "project-a": [("2026-01-15-bug.md", "status: active\nBug report")],
            "project-b": [("2026-01-16-feature.md", "status: active\nFeature request")],
        }) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            assert os.path.isdir(os.path.join(tracking_dir, "project-a", "issues", "resolved"))
            assert os.path.isdir(os.path.join(tracking_dir, "project-b", "issues", "resolved"))


@pytest.mark.unit
class TestProjectFilter:

    def test_restricts_to_specified_project(self, fake_runner, fake_renderer):
        with _tracking_env({
            "project-a": [("2026-01-15-bug.md", "status: active\nBug in A")],
            "project-b": [("2026-01-16-feature.md", "status: active\nFeature in B")],
        }) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer, project="project-a")
            _, variables = fake_renderer.calls[0]
            active = variables["ACTIVE_ISSUES"]
            assert "project-a" in active
            assert "project-b" not in active

    def test_project_filter_no_issues_returns_none(self, fake_runner, fake_renderer):
        with _tracking_env() as tracking_dir:
            os.makedirs(os.path.join(tracking_dir, "empty-project"))
            result = review_issues(tracking_dir, fake_runner, fake_renderer, project="empty-project")
        assert result is None
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestTemplateRendering:

    def test_renders_review_issues_template(self, fake_runner, fake_renderer):
        _review_with_issues(fake_runner, fake_renderer, _SINGLE_BUG)
        template_name, _ = fake_renderer.calls[0]
        assert template_name == "review-issues.md"

    def test_template_receives_active_issues(self, fake_runner, fake_renderer):
        _review_with_issues(fake_runner, fake_renderer, _SINGLE_BUG)
        _, variables = fake_renderer.calls[0]
        assert "ACTIVE_ISSUES" in variables

    def test_template_receives_tracking_dir(self, fake_runner, fake_renderer):
        with _tracking_env(_SINGLE_BUG) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            _, variables = fake_renderer.calls[0]
            assert variables["HITL_TRACKING_DIR"] == tracking_dir

    def test_active_issues_are_space_separated_paths(self, fake_runner, fake_renderer):
        with _tracking_env({"my-project": [
            ("2026-01-15-bug.md", "status: active\nBug 1"),
            ("2026-01-16-feature.md", "status: active\nFeature 1"),
        ]}) as tracking_dir:
            review_issues(tracking_dir, fake_runner, fake_renderer)
            _, variables = fake_renderer.calls[0]
            paths = variables["ACTIVE_ISSUES"].split()
            assert len(paths) == 2
            for p in paths:
                assert os.path.isfile(p)


@pytest.mark.unit
class TestClaudeInvocation:

    def test_invokes_claude_interactively(self, fake_runner, fake_renderer):
        _review_with_issues(fake_runner, fake_renderer, _SINGLE_BUG)
        method, _, _ = fake_runner.calls[0]
        assert method == "run_interactive"

    def test_claude_command_starts_with_claude(self, fake_runner, fake_renderer):
        _review_with_issues(fake_runner, fake_renderer, _SINGLE_BUG)
        _, cmd, _ = fake_runner.calls[0]
        assert cmd[0] == "claude"

    def test_claude_receives_rendered_prompt(self, fake_runner, fake_renderer):
        _review_with_issues(fake_runner, fake_renderer, _SINGLE_BUG)
        _, cmd, _ = fake_runner.calls[0]
        assert "template=review-issues.md" in cmd[1]

    def test_returns_claude_result(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult

        fake_runner.set_result(ClaudeResult(returncode=0))
        result = _review_with_issues(fake_runner, fake_renderer, _SINGLE_BUG)
        assert result.returncode == 0
