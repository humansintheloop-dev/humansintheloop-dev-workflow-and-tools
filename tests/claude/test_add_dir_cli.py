"""Acceptance test for the top-level --add-dir option."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestAddDirOption:

    def test_passes_each_add_dir_to_claude(self, tmp_path, monkeypatch):
        idea_dir = tmp_path / "project" / "docs" / "ideas" / "my-idea"
        idea_dir.mkdir(parents=True)
        (idea_dir / "my-idea-idea.md").write_text("An idea\n")
        monkeypatch.chdir(tmp_path)

        with patch("i2code.implement.claude_runner.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = CliRunner().invoke(
                main,
                ["--add-dir", "dir1", "--add-dir", "/abs/dir2", "spec", "create", str(idea_dir)],
            )

        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        argv = mock_run.call_args[0][0]
        add_dirs = [argv[i + 1] for i, token in enumerate(argv) if token == "--add-dir"]
        assert add_dirs == [str(tmp_path.resolve() / "dir1"), "/abs/dir2"]
