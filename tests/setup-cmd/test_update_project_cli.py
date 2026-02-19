import subprocess
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from i2code.cli import main


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "i2code" / "scripts"


class TestUpdateProjectInvokesBundledScript:
    def test_invokes_update_project_claude_files_sh_with_args(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(
                main,
                [
                    "setup",
                    "update-project",
                    "my-project-dir",
                    "--config-dir",
                    "/path/to/config-files",
                ],
            )

            assert result.exit_code == 0
            mock_subprocess.run.assert_called_once()
            call_args = mock_subprocess.run.call_args[0][0]
            assert Path(call_args[0]) == SCRIPTS_DIR / "update-project-claude-files.sh"
            assert call_args[1:] == [
                "my-project-dir",
                "--config-dir",
                "/path/to/config-files",
            ]

    def test_propagates_script_exit_code(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=42
            )
            result = runner.invoke(
                main,
                [
                    "setup",
                    "update-project",
                    "my-project-dir",
                    "--config-dir",
                    "/path/to/config-files",
                ],
            )

            assert result.exit_code == 42

    def test_forwards_all_args_including_extra_claude_args(self):
        runner = CliRunner()
        with patch("i2code.script_runner.subprocess") as mock_subprocess:
            mock_subprocess.run.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(
                main,
                [
                    "setup",
                    "update-project",
                    "my-project-dir",
                    "--config-dir",
                    "/path/to/config-files",
                    "--",
                    "--verbose",
                ],
            )

            assert result.exit_code == 0
            call_args = mock_subprocess.run.call_args[0][0]
            assert call_args[1:] == [
                "my-project-dir",
                "--config-dir",
                "/path/to/config-files",
                "--verbose",
            ]


class TestUpdateProjectInHelp:
    def test_update_project_listed_in_setup_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["setup", "--help"])
        assert result.exit_code == 0
        assert "update-project" in result.output
