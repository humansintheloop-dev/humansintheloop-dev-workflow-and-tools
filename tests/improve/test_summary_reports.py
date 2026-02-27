"""Tests for summary_reports: discovers projects with today's sessions,
filters by project name, gathers session/issue files, renders template,
invokes Claude per project, saves output to summary-reports/."""

import os
import tempfile
from unittest.mock import patch

import pytest

from i2code.improve.summary_reports import create_summary_reports


def _create_project(tracking_dir, project_name, session_filenames=None, issue_filenames=None):
    """Create a project directory with sessions and optional issues."""
    project_dir = os.path.join(tracking_dir, project_name)
    sessions_dir = os.path.join(project_dir, "sessions")
    os.makedirs(sessions_dir)
    for fname in (session_filenames or []):
        with open(os.path.join(sessions_dir, fname), "w") as f:
            f.write(f"Session content for {fname}")
    if issue_filenames:
        issues_dir = os.path.join(project_dir, "issues", "active")
        os.makedirs(issues_dir)
        for fname in issue_filenames:
            with open(os.path.join(issues_dir, fname), "w") as f:
                f.write(f"Issue content for {fname}")
    return project_dir


@pytest.mark.unit
class TestValidation:

    def test_raises_when_tracking_dir_does_not_exist(self, fake_runner, fake_renderer):
        with pytest.raises(SystemExit):
            create_summary_reports("/nonexistent/path", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_project_name_not_found(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(SystemExit):
                create_summary_reports(tmpdir, fake_runner, fake_renderer, project_name="nonexistent")
        assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestProjectDiscovery:

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_finds_project_with_todays_sessions(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            assert len(fake_runner.calls) == 1

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_skips_project_without_todays_sessions(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-14-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            assert len(fake_runner.calls) == 0

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_finds_multiple_projects(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "project-a", ["session-2025-06-15-100000-abc.md"])
            _create_project(tmpdir, "project-b", ["session-2025-06-15-110000-def.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            assert len(fake_runner.calls) == 2

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_returns_empty_list_when_no_projects_have_sessions(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "empty-project", "sessions"))

            result = create_summary_reports(tmpdir, fake_runner, fake_renderer)

            assert len(fake_runner.calls) == 0
            assert result == []


@pytest.mark.unit
class TestProjectNameFilter:

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_filters_to_specific_project(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "project-a", ["session-2025-06-15-100000-abc.md"])
            _create_project(tmpdir, "project-b", ["session-2025-06-15-110000-def.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer, project_name="project-a")

            assert len(fake_runner.calls) == 1

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_exits_when_filtered_project_has_no_sessions_today(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-14-100000-abc.md"])

            result = create_summary_reports(tmpdir, fake_runner, fake_renderer, project_name="my-project")

            assert len(fake_runner.calls) == 0
            assert result == []


@pytest.mark.unit
class TestReportsDirectory:

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_creates_summary_reports_directory(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            reports_dir = os.path.join(project_dir, "summary-reports")
            assert os.path.isdir(reports_dir)


@pytest.mark.unit
class TestTemplateRendering:

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_renders_create_summary_report_template(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            template_name, _ = fake_renderer.calls[0]
            assert template_name == "create-summary-report.md"

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_template_receives_project_name(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["PROJECT_NAME"] == "my-project"

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_template_receives_session_files(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", [
                "session-2025-06-15-100000-abc.md",
                "session-2025-06-15-110000-def.md",
            ])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            session_files = variables["SESSION_FILES"]
            assert "session-2025-06-15-100000-abc.md" in session_files
            assert "session-2025-06-15-110000-def.md" in session_files

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_template_receives_issue_files(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project",
                            ["session-2025-06-15-100000-abc.md"],
                            ["2025-06-15-bug.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert "2025-06-15-bug.md" in variables["ISSUE_FILES"]

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_template_receives_fallback_when_no_issues(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["ISSUE_FILES"] == "No issues filed today."


@pytest.mark.unit
class TestClaudeInvocation:

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_invokes_claude_with_print_flag(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            assert "--print" in cmd

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_invokes_claude_with_add_dir(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            add_dir_idx = cmd.index("--add-dir")
            assert cmd[add_dir_idx + 1] == project_dir

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_invokes_claude_with_allowed_tools(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            tools_idx = cmd.index("--allowedTools")
            assert cmd[tools_idx + 1] == "Read"

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_uses_run_batch(self, _mock_today, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            method, _, _ = fake_runner.calls[0]
            assert method == "run_batch"


@pytest.mark.unit
class TestReportOutput:

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_saves_claude_output_to_report_file(self, _mock_today, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import CapturedOutput, ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])
            fake_runner.set_result(ClaudeResult(
                returncode=0,
                output=CapturedOutput(stdout="# Summary Report\nGreat work today."),
            ))

            create_summary_reports(tmpdir, fake_runner, fake_renderer)

            reports_dir = os.path.join(project_dir, "summary-reports")
            report_files = os.listdir(reports_dir)
            assert len(report_files) == 1
            assert report_files[0].startswith("summary-")
            assert report_files[0].endswith(".md")
            content = open(os.path.join(reports_dir, report_files[0])).read()
            assert content == "# Summary Report\nGreat work today."

    @patch("i2code.improve.summary_reports._today", return_value="2025-06-15")
    def test_returns_list_of_report_paths(self, _mock_today, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import CapturedOutput, ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            _create_project(tmpdir, "my-project", ["session-2025-06-15-100000-abc.md"])
            fake_runner.set_result(ClaudeResult(
                returncode=0,
                output=CapturedOutput(stdout="Report content"),
            ))

            result = create_summary_reports(tmpdir, fake_runner, fake_renderer)

            assert len(result) == 1
            assert "summary-" in result[0]
            assert result[0].endswith(".md")
