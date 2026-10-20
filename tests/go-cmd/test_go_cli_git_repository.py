"""Tests for the go command's check that the idea is inside a git repository."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


def _make_idea_dir(root: Path) -> Path:
    idea_dir = root / "docs" / "ideas" / "active" / "my-idea"
    idea_dir.mkdir(parents=True)
    return idea_dir


@pytest.mark.unit
class TestGoCommandOutsideGitRepository:
    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_runs_git_init_at_project_root_when_user_accepts(self, mock_orch_cls, tmp_path):
        root = tmp_path.resolve()
        idea_dir = _make_idea_dir(root)
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = CliRunner().invoke(main, ["go", str(idea_dir)], input="y\n")

        assert result.exit_code == 0, result.output
        assert "not in a git repository" in result.output
        assert (root / ".git").is_dir()
        mock_orch.run.assert_called_once()

    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_exits_without_git_init_when_user_declines(self, mock_orch_cls, tmp_path):
        root = tmp_path.resolve()
        idea_dir = _make_idea_dir(root)

        result = CliRunner().invoke(main, ["go", str(idea_dir)], input="n\n")

        assert result.exit_code == 1
        assert not (root / ".git").exists()
        mock_orch_cls.assert_not_called()

    @patch("i2code.go_cmd.cli.Orchestrator")
    def test_does_not_prompt_when_already_in_git_repository(self, mock_orch_cls, tmp_path):
        root = tmp_path.resolve()
        idea_dir = _make_idea_dir(root)
        subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
        mock_orch = MagicMock()
        mock_orch_cls.return_value = mock_orch

        result = CliRunner().invoke(main, ["go", str(idea_dir)])

        assert result.exit_code == 0, result.output
        assert "not in a git repository" not in result.output
        mock_orch.run.assert_called_once()
