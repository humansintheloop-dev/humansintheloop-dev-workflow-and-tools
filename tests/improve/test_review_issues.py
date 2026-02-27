"""Tests for review_issues: finds active issues from current year,
excludes type: unknown, creates resolved dirs, respects --project filter,
handles no issues found (exit 0), renders template, invokes Claude."""

import os
import tempfile
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


@pytest.mark.unit
class TestValidation:

    def test_raises_when_tracking_dir_does_not_exist(self, fake_runner, fake_renderer):
        with pytest.raises(SystemExit):
            review_issues("/nonexistent/path", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_raises_when_project_dir_does_not_exist(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            with pytest.raises(SystemExit):
                review_issues(tracking_dir, fake_runner, fake_renderer, project="nonexistent")
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestIssueFinding:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_finds_active_issues_from_current_year(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug-report.md", "status: active\nSome bug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert "2026-01-15-bug-report.md" in variables["ACTIVE_ISSUES"]

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_ignores_issues_from_previous_year(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2025-12-01-old-issue.md", "status: active\nOld issue"),
                ("2026-01-15-new-issue.md", "status: active\nNew issue"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert "2025-12-01-old-issue.md" not in variables["ACTIVE_ISSUES"]
            assert "2026-01-15-new-issue.md" in variables["ACTIVE_ISSUES"]


@pytest.mark.unit
class TestTypeUnknownExclusion:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_excludes_issues_with_type_unknown(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-good-issue.md", "status: active\nReal issue"),
                ("2026-01-16-unknown-issue.md", "type: unknown\nNot relevant"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert "2026-01-15-good-issue.md" in variables["ACTIVE_ISSUES"]
            assert "2026-01-16-unknown-issue.md" not in variables["ACTIVE_ISSUES"]

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_all_issues_type_unknown_exits_zero(self, _mock_year, fake_runner, fake_renderer, capsys):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-unknown1.md", "type: unknown\nNot relevant"),
                ("2026-01-16-unknown2.md", "type: unknown\nAlso not relevant"),
            ])

            result = review_issues(tracking_dir, fake_runner, fake_renderer)

            assert result is None
            assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestNoIssuesFound:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_no_issues_found_returns_none(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            os.makedirs(os.path.join(tracking_dir, "my-project"))

            result = review_issues(tracking_dir, fake_runner, fake_renderer)

            assert result is None
            assert len(fake_runner.calls) == 0

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_no_issues_dir_returns_none(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)

            result = review_issues(tracking_dir, fake_runner, fake_renderer)

            assert result is None
            assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestResolvedDirCreation:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_creates_resolved_dir_for_project_with_active_issues(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug report"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            resolved_dir = os.path.join(tracking_dir, "my-project", "issues", "resolved")
            assert os.path.isdir(resolved_dir)

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_creates_resolved_dirs_for_multiple_projects(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "project-a", [
                ("2026-01-15-bug.md", "status: active\nBug report"),
            ])
            _create_project_with_issues(tracking_dir, "project-b", [
                ("2026-01-16-feature.md", "status: active\nFeature request"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            assert os.path.isdir(os.path.join(tracking_dir, "project-a", "issues", "resolved"))
            assert os.path.isdir(os.path.join(tracking_dir, "project-b", "issues", "resolved"))


@pytest.mark.unit
class TestProjectFilter:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_restricts_to_specified_project(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "project-a", [
                ("2026-01-15-bug.md", "status: active\nBug in A"),
            ])
            _create_project_with_issues(tracking_dir, "project-b", [
                ("2026-01-16-feature.md", "status: active\nFeature in B"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer, project="project-a")

            _, variables = fake_renderer.calls[0]
            active = variables["ACTIVE_ISSUES"]
            assert "project-a" in active
            assert "project-b" not in active

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_project_filter_no_issues_returns_none(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            project_dir = os.path.join(tracking_dir, "empty-project")
            os.makedirs(project_dir)

            result = review_issues(tracking_dir, fake_runner, fake_renderer, project="empty-project")

            assert result is None
            assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestTemplateRendering:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_renders_review_issues_template(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            template_name, _ = fake_renderer.calls[0]
            assert template_name == "review-issues.md"

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_template_receives_active_issues(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert "ACTIVE_ISSUES" in variables

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_template_receives_tracking_dir(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["HITL_TRACKING_DIR"] == tracking_dir

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_active_issues_are_space_separated_paths(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug 1"),
                ("2026-01-16-feature.md", "status: active\nFeature 1"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            paths = variables["ACTIVE_ISSUES"].split()
            assert len(paths) == 2
            for path in paths:
                assert os.path.isfile(path)


@pytest.mark.unit
class TestClaudeInvocation:

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_invokes_claude_interactively(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            method, _, _ = fake_runner.calls[0]
            assert method == "run_interactive"

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_claude_command_starts_with_claude(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            assert cmd[0] == "claude"

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_claude_receives_rendered_prompt(self, _mock_year, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            review_issues(tracking_dir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            # The prompt is passed as the second positional argument
            assert "template=review-issues.md" in cmd[1]

    @patch("i2code.improve.review_issues._current_year", return_value="2026")
    def test_returns_claude_result(self, _mock_year, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_project_with_issues(tracking_dir, "my-project", [
                ("2026-01-15-bug.md", "status: active\nBug"),
            ])

            fake_runner.set_result(ClaudeResult(returncode=0))
            result = review_issues(tracking_dir, fake_runner, fake_renderer)

            assert result.returncode == 0
