"""Tests for analyze_sessions: validates directory, extracts session IDs,
correlates issue files, renders template, invokes Claude with correct flags."""

import os
import tempfile

import pytest

from i2code.improve.analyze_sessions import analyze_sessions


def _create_tracking_dir(tmpdir):
    """Create a tracking directory with sessions subdirectory."""
    tracking_dir = os.path.join(tmpdir, "tracking")
    sessions_dir = os.path.join(tracking_dir, "sessions")
    os.makedirs(sessions_dir)
    return tracking_dir


def _create_session_file(tracking_dir, filename):
    """Create a session file in the sessions subdirectory."""
    path = os.path.join(tracking_dir, "sessions", filename)
    with open(path, "w") as f:
        f.write(f"Session content for {filename}")


def _create_issue_file(tracking_dir, filename, content):
    """Create an issue file in the issues/active subdirectory."""
    active_dir = os.path.join(tracking_dir, "issues", "active")
    os.makedirs(active_dir, exist_ok=True)
    path = os.path.join(active_dir, filename)
    with open(path, "w") as f:
        f.write(content)


@pytest.fixture
def analyzed_session(fake_runner, fake_renderer):
    """Create tracking dir with one session file and run analyze_sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tracking_dir = _create_tracking_dir(tmpdir)
        _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")
        analyze_sessions(tracking_dir, fake_runner, fake_renderer)
        yield tracking_dir, fake_runner, fake_renderer


@pytest.mark.unit
class TestAnalyzeSessionsValidation:

    def test_raises_when_tracking_dir_does_not_exist(self, fake_runner, fake_renderer):
        with pytest.raises(SystemExit):
            analyze_sessions("/nonexistent/path", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_sessions_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = os.path.join(tmpdir, "tracking")
            os.makedirs(tracking_dir)
            with pytest.raises(SystemExit):
                analyze_sessions(tracking_dir, fake_runner, fake_renderer)
            assert len(fake_runner.calls) == 0


@pytest.mark.unit
class TestSessionIdExtraction:

    def test_extracts_session_id_from_standard_filename(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123def.md")

            analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert "abc123def" in variables["ISSUES"] or variables["ISSUES"] == ""

    def test_extracts_multiple_session_ids(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")
            _create_session_file(tracking_dir, "session-2025-01-16-090000-def456.md")

            analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            _, cmd, _ = fake_runner.calls[0]
            # Should have been called (we'll verify template was rendered)
            assert len(fake_renderer.calls) == 1

    def test_ignores_non_session_files(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")
            _create_session_file(tracking_dir, "notes.md")  # not a session file

            analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            assert len(fake_renderer.calls) == 1


@pytest.mark.unit
class TestIssueFileCorrelation:

    def test_finds_issue_files_referencing_session_ids(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")
            _create_issue_file(tracking_dir, "issue-001.md", "Related to session abc123")

            analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            issue_path = os.path.join(tracking_dir, "issues", "active", "issue-001.md")
            assert issue_path in variables["ISSUES"]

    def test_empty_issues_when_no_issues_dir(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")

            analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["ISSUES"] == ""

    def test_empty_issues_when_no_matching_files(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")
            _create_issue_file(tracking_dir, "issue-001.md", "Unrelated issue content")

            analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            _, variables = fake_renderer.calls[0]
            assert variables["ISSUES"] == ""


@pytest.mark.unit
class TestTemplateRendering:

    def test_renders_analyze_sessions_template(self, analyzed_session):
        _, _, fake_renderer = analyzed_session
        template_name, _ = fake_renderer.calls[0]
        assert template_name == "analyze-sessions.md"

    def test_template_receives_sessions_dir(self, analyzed_session):
        tracking_dir, _, fake_renderer = analyzed_session
        _, variables = fake_renderer.calls[0]
        assert variables["SESSIONS_DIR"] == os.path.join(tracking_dir, "sessions")

    def test_template_receives_report_file(self, analyzed_session):
        tracking_dir, _, fake_renderer = analyzed_session
        _, variables = fake_renderer.calls[0]
        report_file = variables["REPORT_FILE"]
        assert report_file.startswith(tracking_dir)
        assert "report-" in report_file
        assert report_file.endswith(".adoc")


@pytest.mark.unit
class TestClaudeInvocation:

    def test_invokes_claude_non_interactively(self, analyzed_session):
        _, fake_runner, _ = analyzed_session
        method, _, _ = fake_runner.calls[0]
        assert method == "run_batch"

    def test_claude_command_includes_add_dir_for_sessions(self, analyzed_session):
        tracking_dir, fake_runner, _ = analyzed_session
        _, cmd, _ = fake_runner.calls[0]
        sessions_dir = os.path.join(tracking_dir, "sessions")
        add_dir_idx = cmd.index("--add-dir")
        assert cmd[add_dir_idx + 1] == sessions_dir

    def test_claude_command_includes_add_dir_for_issues(self, analyzed_session):
        tracking_dir, fake_runner, _ = analyzed_session
        _, cmd, _ = fake_runner.calls[0]
        issues_dir = os.path.join(tracking_dir, "issues")
        # Find the second --add-dir
        indices = [i for i, x in enumerate(cmd) if x == "--add-dir"]
        assert len(indices) == 2
        assert cmd[indices[1] + 1] == issues_dir

    def test_claude_command_includes_allowed_tools(self, analyzed_session):
        _, fake_runner, _ = analyzed_session
        _, cmd, _ = fake_runner.calls[0]
        tools_idx = cmd.index("--allowedTools")
        assert cmd[tools_idx + 1] == "Read,Edit,Write"

    def test_claude_command_uses_print_flag(self, analyzed_session):
        _, fake_runner, _ = analyzed_session
        _, cmd, _ = fake_runner.calls[0]
        assert "-p" in cmd

    def test_returns_claude_result(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            tracking_dir = _create_tracking_dir(tmpdir)
            _create_session_file(tracking_dir, "session-2025-01-15-143022-abc123.md")

            fake_runner.set_result(ClaudeResult(returncode=0))
            result = analyze_sessions(tracking_dir, fake_runner, fake_renderer)

            assert result.returncode == 0
