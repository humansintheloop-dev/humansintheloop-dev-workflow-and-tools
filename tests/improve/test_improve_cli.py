"""CLI integration tests for i2code improve subcommands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestAnalyzeSessionsCommandRegistered:

    def test_listed_in_improve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "--help"])
        assert "analyze-sessions" in result.output

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "analyze-sessions", "--help"])
        assert result.exit_code == 0
        assert "tracking_dir" in result.output.lower()

    def test_requires_tracking_dir_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "analyze-sessions"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestAnalyzeSessionsCommandInvocation:

    def test_invokes_analyze_sessions(self, tmp_path):
        with patch("i2code.improve.cli.analyze_sessions") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            result = runner.invoke(main, ["improve", "analyze-sessions", str(tmp_path)])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_passes_tracking_dir(self, tmp_path):
        with patch("i2code.improve.cli.analyze_sessions") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, ["improve", "analyze-sessions", str(tmp_path)])
            assert mock_fn.call_args[0][0] == str(tmp_path)

    def test_passes_claude_runner(self, tmp_path):
        with patch("i2code.improve.cli.analyze_sessions") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, ["improve", "analyze-sessions", str(tmp_path)])
            assert mock_fn.call_args[0][1] is mock_runner


@pytest.mark.unit
class TestSummaryReportsCommandRegistered:

    def test_listed_in_improve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "--help"])
        assert "summary-reports" in result.output

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "summary-reports", "--help"])
        assert result.exit_code == 0
        assert "tracking_dir" in result.output.lower()

    def test_requires_tracking_dir_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "summary-reports"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestSummaryReportsCommandInvocation:

    def test_invokes_create_summary_reports(self, tmp_path):
        with patch("i2code.improve.cli.create_summary_reports") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = []
            runner = CliRunner()
            result = runner.invoke(main, ["improve", "summary-reports", str(tmp_path)])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_passes_tracking_dir(self, tmp_path):
        with patch("i2code.improve.cli.create_summary_reports") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = []
            runner = CliRunner()
            runner.invoke(main, ["improve", "summary-reports", str(tmp_path)])
            assert mock_fn.call_args[0][0] == str(tmp_path)

    def test_passes_project_name_option(self, tmp_path):
        with patch("i2code.improve.cli.create_summary_reports") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = []
            runner = CliRunner()
            runner.invoke(main, [
                "improve", "summary-reports", str(tmp_path),
                "--project-name", "myproject",
            ])
            assert mock_fn.call_args[1]["project_name"] == "myproject"

    def test_project_name_defaults_to_none(self, tmp_path):
        with patch("i2code.improve.cli.create_summary_reports") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = []
            runner = CliRunner()
            runner.invoke(main, ["improve", "summary-reports", str(tmp_path)])
            assert mock_fn.call_args[1]["project_name"] is None


@pytest.mark.unit
class TestReviewIssuesCommandRegistered:

    def test_listed_in_improve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "--help"])
        assert "review-issues" in result.output

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "review-issues", "--help"])
        assert result.exit_code == 0
        assert "tracking_dir" in result.output.lower()

    def test_requires_tracking_dir_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "review-issues"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestReviewIssuesCommandInvocation:

    def test_invokes_review_issues(self, tmp_path):
        with patch("i2code.improve.cli.review_issues") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            result = runner.invoke(main, ["improve", "review-issues", str(tmp_path)])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_passes_tracking_dir(self, tmp_path):
        with patch("i2code.improve.cli.review_issues") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, ["improve", "review-issues", str(tmp_path)])
            assert mock_fn.call_args[0][0] == str(tmp_path)

    def test_passes_project_option(self, tmp_path):
        with patch("i2code.improve.cli.review_issues") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, [
                "improve", "review-issues", str(tmp_path),
                "--project", "myproject",
            ])
            assert mock_fn.call_args[1]["project"] == "myproject"

    def test_project_defaults_to_none(self, tmp_path):
        with patch("i2code.improve.cli.review_issues") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, ["improve", "review-issues", str(tmp_path)])
            assert mock_fn.call_args[1]["project"] is None


@pytest.mark.unit
class TestUpdateClaudeFilesCommandRegistered:

    def test_listed_in_improve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "--help"])
        assert "update-claude-files" in result.output

    def test_help_exits_zero(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "update-claude-files", "--help"])
        assert result.exit_code == 0
        assert "project_dir" in result.output.lower()

    def test_requires_project_dir_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "update-claude-files"])
        assert result.exit_code != 0

    def test_requires_config_dir_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "update-claude-files", "/tmp/proj"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestUpdateClaudeFilesCommandInvocation:

    def test_invokes_update_claude_files(self, tmp_path):
        with patch("i2code.improve.cli.update_claude_files") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            result = runner.invoke(main, [
                "improve", "update-claude-files", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert result.exit_code == 0
            mock_fn.assert_called_once()

    def test_passes_project_dir_and_config_dir(self, tmp_path):
        with patch("i2code.improve.cli.update_claude_files") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner_cls.return_value = MagicMock()
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, [
                "improve", "update-claude-files", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert mock_fn.call_args[0][0] == str(tmp_path)
            assert mock_fn.call_args[0][1] == "/tmp/config"

    def test_passes_claude_runner(self, tmp_path):
        with patch("i2code.improve.cli.update_claude_files") as mock_fn, \
             patch("i2code.improve.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            runner = CliRunner()
            runner.invoke(main, [
                "improve", "update-claude-files", str(tmp_path),
                "--config-dir", "/tmp/config",
            ])
            assert mock_fn.call_args[0][2] is mock_runner
