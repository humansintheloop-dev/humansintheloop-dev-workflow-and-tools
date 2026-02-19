import subprocess
from unittest.mock import patch

import click
from click.testing import CliRunner

from i2code.script_command import script_command


class TestScriptCommandRegistersOnGroup:
    def test_command_is_registered_on_group(self):
        group = click.Group("test-group")
        script_command(group, "my-cmd", "my-script.sh", "My help text")

        assert "my-cmd" in group.commands

    def test_help_text_is_set(self):
        group = click.Group("test-group")
        script_command(group, "my-cmd", "my-script.sh", "My help text")

        cmd = group.commands["my-cmd"]
        assert cmd.help == "My help text"


class TestScriptCommandForwardsArgsToRunScript:
    def test_args_are_forwarded_to_run_script(self):
        group = click.Group("test-group")
        script_command(group, "my-cmd", "my-script.sh", "My help text")

        runner = CliRunner()
        with patch("i2code.script_command.run_script") as mock_run_script:
            mock_run_script.return_value = subprocess.CompletedProcess(
                args=[], returncode=0
            )
            result = runner.invoke(group, ["my-cmd", "arg1", "--flag", "arg2"])

            assert result.exit_code == 0
            mock_run_script.assert_called_once_with(
                "my-script.sh", ("arg1", "--flag", "arg2")
            )


class TestScriptCommandPropagatesExitCode:
    def test_exit_code_is_propagated(self):
        group = click.Group("test-group")
        script_command(group, "my-cmd", "my-script.sh", "My help text")

        runner = CliRunner()
        with patch("i2code.script_command.run_script") as mock_run_script:
            mock_run_script.return_value = subprocess.CompletedProcess(
                args=[], returncode=42
            )
            result = runner.invoke(group, ["my-cmd"])

            assert result.exit_code == 42
