"""CLI integration tests for i2code improve subcommands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


def _invoke_improve(*args):
    return CliRunner().invoke(main, ["improve", *args])


def _invoke_with_mocks(fn_name, cli_args, return_value=None):
    """Patch an improve CLI function and ClaudeRunner, invoke the CLI, return (result, mock_fn, mock_runner)."""
    with patch(f"i2code.improve.cli.{fn_name}") as mock_fn, \
         patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        mock_fn.return_value = return_value if return_value is not None else MagicMock(returncode=0)
        result = CliRunner().invoke(main, ["improve", *cli_args])
        return result, mock_fn, mock_runner


@pytest.mark.unit
class TestAnalyzeSessionsCommandRegistered:

    def test_listed_in_improve_help(self):
        assert "analyze-sessions" in _invoke_improve("--help").output

    def test_help_exits_zero(self):
        result = _invoke_improve("analyze-sessions", "--help")
        assert result.exit_code == 0
        assert "tracking_dir" in result.output.lower()

    def test_requires_tracking_dir_argument(self):
        assert _invoke_improve("analyze-sessions").exit_code != 0


@pytest.mark.unit
class TestAnalyzeSessionsCommandInvocation:

    def test_invokes_analyze_sessions(self, tmp_path):
        result, mock_fn, _ = _invoke_with_mocks("analyze_sessions", ["analyze-sessions", str(tmp_path)])
        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_passes_tracking_dir(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks("analyze_sessions", ["analyze-sessions", str(tmp_path)])
        assert mock_fn.call_args[0][0] == str(tmp_path)

    def test_passes_claude_runner(self, tmp_path):
        _, mock_fn, mock_runner = _invoke_with_mocks("analyze_sessions", ["analyze-sessions", str(tmp_path)])
        assert mock_fn.call_args[0][1] is mock_runner


@pytest.mark.unit
class TestSummaryReportsCommandRegistered:

    def test_listed_in_improve_help(self):
        assert "summary-reports" in _invoke_improve("--help").output

    def test_help_exits_zero(self):
        result = _invoke_improve("summary-reports", "--help")
        assert result.exit_code == 0
        assert "tracking_dir" in result.output.lower()

    def test_requires_tracking_dir_argument(self):
        assert _invoke_improve("summary-reports").exit_code != 0


@pytest.mark.unit
class TestSummaryReportsCommandInvocation:

    def test_invokes_create_summary_reports(self, tmp_path):
        result, mock_fn, _ = _invoke_with_mocks("create_summary_reports", ["summary-reports", str(tmp_path)], return_value=[])
        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_passes_tracking_dir(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks("create_summary_reports", ["summary-reports", str(tmp_path)], return_value=[])
        assert mock_fn.call_args[0][0] == str(tmp_path)

    def test_passes_project_name_option(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks(
            "create_summary_reports", ["summary-reports", str(tmp_path), "--project-name", "myproject"], return_value=[],
        )
        assert mock_fn.call_args[1]["project_name"] == "myproject"

    def test_project_name_defaults_to_none(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks("create_summary_reports", ["summary-reports", str(tmp_path)], return_value=[])
        assert mock_fn.call_args[1]["project_name"] is None


@pytest.mark.unit
class TestReviewIssuesCommandRegistered:

    def test_listed_in_improve_help(self):
        assert "review-issues" in _invoke_improve("--help").output

    def test_help_exits_zero(self):
        result = _invoke_improve("review-issues", "--help")
        assert result.exit_code == 0
        assert "tracking_dir" in result.output.lower()

    def test_requires_tracking_dir_argument(self):
        assert _invoke_improve("review-issues").exit_code != 0


@pytest.mark.unit
class TestReviewIssuesCommandInvocation:

    def test_invokes_review_issues(self, tmp_path):
        result, mock_fn, _ = _invoke_with_mocks("review_issues", ["review-issues", str(tmp_path)])
        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_passes_tracking_dir(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks("review_issues", ["review-issues", str(tmp_path)])
        assert mock_fn.call_args[0][0] == str(tmp_path)

    def test_passes_project_option(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks("review_issues", ["review-issues", str(tmp_path), "--project", "myproject"])
        assert mock_fn.call_args[1]["project"] == "myproject"

    def test_project_defaults_to_none(self, tmp_path):
        _, mock_fn, _ = _invoke_with_mocks("review_issues", ["review-issues", str(tmp_path)])
        assert mock_fn.call_args[1]["project"] is None


@pytest.mark.unit
class TestUpdateClaudeFilesCommandRegistered:

    def test_listed_in_improve_help(self):
        assert "update-claude-files" in _invoke_improve("--help").output

    def test_help_exits_zero(self):
        result = _invoke_improve("update-claude-files", "--help")
        assert result.exit_code == 0
        assert "project_dir" in result.output.lower()

    def test_requires_project_dir_argument(self):
        assert _invoke_improve("update-claude-files").exit_code != 0

    def test_requires_config_dir_option(self):
        assert _invoke_improve("update-claude-files", "/tmp/proj").exit_code != 0


@pytest.mark.unit
class TestUpdateClaudeFilesCommandInvocation:

    def _invoke_update(self, tmp_path, extra_args=None):
        cli_args = ["update-claude-files", str(tmp_path), "--config-dir", "/tmp/config"]
        if extra_args:
            cli_args.extend(extra_args)
        return _invoke_with_mocks("update_claude_files", cli_args)

    def test_invokes_update_claude_files(self, tmp_path):
        result, mock_fn, _ = self._invoke_update(tmp_path)
        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_passes_project_dir_and_config_dir(self, tmp_path):
        _, mock_fn, _ = self._invoke_update(tmp_path)
        assert mock_fn.call_args[0][0] == str(tmp_path)
        assert mock_fn.call_args[0][1] == "/tmp/config"

    def test_passes_claude_runner(self, tmp_path):
        _, mock_fn, mock_runner = self._invoke_update(tmp_path)
        assert mock_fn.call_args[0][2] is mock_runner
