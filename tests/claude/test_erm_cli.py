"""Acceptance tests for the top-level --erm option."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.fixture
def idea_dir(tmp_path):
    directory = tmp_path / "workspace" / "project" / "docs" / "ideas" / "my-idea"
    directory.mkdir(parents=True)
    (directory / "my-idea-idea.md").write_text("An idea\n")
    return directory


def invoke_spec_create(idea_dir, *global_options):
    with patch("i2code.implement.claude_runner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        result = CliRunner().invoke(
            main, [*global_options, "spec", "create", str(idea_dir)],
        )
    return result, mock_run


def add_dir_values(argv):
    return option_values(argv, "--add-dir")


def permission_mode(argv):
    values = option_values(argv, "--permission-mode")
    return values[0] if values else None


def option_values(argv, option):
    return [argv[i + 1] for i, token in enumerate(argv) if token == option]


def claude_argv_inside_erm_workspace(tmp_path, idea_dir, monkeypatch, *global_options):
    """Run spec create from a project inside an ERM workspace and return Claude's argv."""
    (tmp_path / "workspace" / ".erm").mkdir()
    monkeypatch.chdir(tmp_path / "workspace" / "project")

    result, mock_run = invoke_spec_create(idea_dir, *global_options)

    assert result.exit_code == 0, result.output
    mock_run.assert_called_once()
    return mock_run.call_args[0][0]


@pytest.mark.unit
class TestErmOption:

    def test_adds_erm_parent_directory_to_claude(self, tmp_path, idea_dir, monkeypatch):
        argv = claude_argv_inside_erm_workspace(tmp_path, idea_dir, monkeypatch, "--erm")

        assert add_dir_values(argv) == [str((tmp_path / "workspace").resolve())]
        assert permission_mode(argv) == "auto"

    def test_exits_with_error_when_no_erm_directory_found(self, tmp_path, idea_dir, monkeypatch):
        monkeypatch.chdir(tmp_path / "workspace" / "project")

        result, mock_run = invoke_spec_create(idea_dir, "--erm")

        assert result.exit_code != 0
        assert "No .erm directory found" in result.output
        mock_run.assert_not_called()

    def test_adds_no_directory_without_erm_option(self, tmp_path, idea_dir, monkeypatch):
        argv = claude_argv_inside_erm_workspace(tmp_path, idea_dir, monkeypatch)

        assert add_dir_values(argv) == []
        assert permission_mode(argv) is None
