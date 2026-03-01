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
