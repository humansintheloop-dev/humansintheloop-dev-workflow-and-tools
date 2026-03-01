"""CLI tests for i2code completion command."""

import pytest
from click.testing import CliRunner

from i2code.cli import main

SHELL_MARKERS = [
    ("bash", "complete -o nosort"),
    ("zsh", "compdef"),
    ("fish", "complete --no-files --command"),
]


@pytest.mark.unit
class TestCompletionScript:

    @pytest.mark.parametrize("shell,marker", SHELL_MARKERS)
    def test_completion_exits_with_code_0(self, shell, marker):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", shell])
        assert result.exit_code == 0

    @pytest.mark.parametrize("shell,marker", SHELL_MARKERS)
    def test_completion_outputs_shell_specific_script(self, shell, marker):
        runner = CliRunner()
        result = runner.invoke(main, ["completion", shell])
        assert marker in result.output


@pytest.mark.unit
class TestCompletionUsageHelp:

    def test_no_arguments_exits_with_code_0(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion"])
        assert result.exit_code == 0

    def test_no_arguments_lists_supported_shells(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion"])
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output

    def test_no_arguments_shows_installation_example(self):
        runner = CliRunner()
        result = runner.invoke(main, ["completion"])
        assert 'eval "$(i2code completion zsh)"' in result.output
