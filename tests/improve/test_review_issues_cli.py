import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from i2code.cli import main


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"


class TestReviewIssuesInvokesBundledScript:
    def test_invokes_review_issues_sh_with_directory_arg(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(main, ["improve", "review-issues", "my-hitl-dir"])

            assert result.exit_code == 0
            mock_subprocess.run.assert_called_once()
            call_args = mock_subprocess.run.call_args[0][0]
            assert Path(call_args[0]) == SCRIPTS_DIR / "review-issues.sh"
            assert call_args[1:] == ["my-hitl-dir"]

    def test_propagates_script_exit_code(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=42
            )
            result = runner.invoke(main, ["improve", "review-issues", "my-hitl-dir"])

            assert result.exit_code == 42

    def test_forwards_project_and_extra_args(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(
                main,
                ["improve", "review-issues", "my-hitl-dir", "--project", "my-project"],
            )

            assert result.exit_code == 0
            call_args = mock_subprocess.run.call_args[0][0]
            assert call_args[1:] == ["my-hitl-dir", "--project", "my-project"]


class TestReviewIssuesInHelp:
    def test_review_issues_listed_in_improve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "--help"])
        assert result.exit_code == 0
        assert "review-issues" in result.output
