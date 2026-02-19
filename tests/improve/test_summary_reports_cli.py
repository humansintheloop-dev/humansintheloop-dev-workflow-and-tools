import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from i2code.cli import main


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"


class TestSummaryReportsInvokesBundledScript:
    def test_invokes_create_summary_reports_sh_with_directory_arg(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(main, ["improve", "summary-reports", "my-hitl-dir"])

            assert result.exit_code == 0
            mock_subprocess.run.assert_called_once()
            call_args = mock_subprocess.run.call_args[0][0]
            assert Path(call_args[0]) == SCRIPTS_DIR / "create-summary-reports.sh"
            assert call_args[1:] == ["my-hitl-dir"]

    def test_propagates_script_exit_code(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=42
            )
            result = runner.invoke(main, ["improve", "summary-reports", "my-hitl-dir"])

            assert result.exit_code == 42

    def test_forwards_project_name_argument(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(
                main,
                ["improve", "summary-reports", "my-hitl-dir", "--project-name", "my-project"],
            )

            assert result.exit_code == 0
            call_args = mock_subprocess.run.call_args[0][0]
            assert call_args[1:] == ["my-hitl-dir", "--project-name", "my-project"]


class TestSummaryReportsInHelp:
    def test_summary_reports_listed_in_improve_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["improve", "--help"])
        assert result.exit_code == 0
        assert "summary-reports" in result.output
