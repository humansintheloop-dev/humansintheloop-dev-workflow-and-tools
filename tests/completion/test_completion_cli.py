"""CLI tests for i2code completion command."""

import pytest
from click.testing import CliRunner

from i2code.cli import main

SHELL_MARKERS = [
    ("bash", "complete -o nosort"),
    ("zsh", "compdef"),
    ("fish", "complete --no-files --command"),
]


def run(*args):
    return CliRunner().invoke(main, ["completion", *args])


@pytest.mark.unit
class TestCompletionScript:

    @pytest.mark.parametrize("shell,marker", SHELL_MARKERS)
    def test_completion_exits_with_code_0(self, shell, marker):
        result = run(shell)
        assert result.exit_code == 0

    @pytest.mark.parametrize("shell,marker", SHELL_MARKERS)
    def test_completion_outputs_shell_specific_script(self, shell, marker):
        result = run(shell)
        assert marker in result.output


@pytest.mark.unit
class TestCompletionUsageHelp:

    def test_no_arguments_exits_with_code_0(self):
        result = run()
        assert result.exit_code == 0

    def test_no_arguments_lists_supported_shells(self):
        result = run()
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output

    def test_no_arguments_shows_installation_example(self):
        result = run()
        assert 'eval "$(i2code completion zsh)"' in result.output


@pytest.mark.unit
class TestCompletionInvalidShell:

    def test_invalid_shell_exits_with_nonzero_code(self):
        result = run("powershell")
        assert result.exit_code != 0

    def test_invalid_shell_lists_valid_choices(self):
        result = run("powershell")
        assert "bash" in result.output
        assert "zsh" in result.output
        assert "fish" in result.output
