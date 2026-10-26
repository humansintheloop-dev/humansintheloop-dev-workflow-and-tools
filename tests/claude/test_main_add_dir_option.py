"""Unit tests for how the top-level group handles --add-dir."""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


def invoke_main(*args):
    with patch("i2code.cli.use_added_dirs") as mock_use_added_dirs:
        result = CliRunner().invoke(main, [*args, "completion", "--help"])
    return result, mock_use_added_dirs


@pytest.mark.unit
class TestMainAddDirOption:

    def test_add_dir_can_be_repeated(self):
        result, mock_use_added_dirs = invoke_main("--add-dir", "dir1", "--add-dir", "dir2")

        assert result.exit_code == 0, result.output
        mock_use_added_dirs.assert_called_once_with(("dir1", "dir2"))

    def test_without_add_dir_does_not_use_added_dirs(self):
        result, mock_use_added_dirs = invoke_main()

        assert result.exit_code == 0, result.output
        mock_use_added_dirs.assert_not_called()
