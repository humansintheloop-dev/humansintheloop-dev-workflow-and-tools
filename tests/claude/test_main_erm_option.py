"""Unit tests for how the top-level group handles --erm."""

from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


def invoke_main(*args):
    with patch("i2code.cli.use_erm_root") as mock_use_erm_root:
        result = CliRunner().invoke(main, [*args, "completion", "--help"])
    return result, mock_use_erm_root


@pytest.mark.unit
class TestMainErmOption:

    def test_erm_uses_erm_root_above_current_directory(self):
        result, mock_use_erm_root = invoke_main("--erm")

        assert result.exit_code == 0, result.output
        mock_use_erm_root.assert_called_once_with(Path.cwd())

    def test_without_erm_does_not_use_erm_root(self):
        result, mock_use_erm_root = invoke_main()

        assert result.exit_code == 0, result.output
        mock_use_erm_root.assert_not_called()
