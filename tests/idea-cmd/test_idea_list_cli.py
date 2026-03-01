"""CLI integration tests for i2code idea list."""

import os

import pytest
from click.testing import CliRunner

from i2code.cli import main


def _create_idea(base, state, name):
    """Create an idea directory under docs/ideas/{state}/{name}/."""
    idea_dir = os.path.join(base, "docs", "ideas", state, name)
    os.makedirs(idea_dir, exist_ok=True)
    return idea_dir


@pytest.mark.unit
class TestIdeaListEmpty:

    def test_empty_output_when_no_ideas_exist(self, tmp_path, monkeypatch):
        os.makedirs(tmp_path / "docs" / "ideas" / "draft")
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["idea", "list"])
        assert result.exit_code == 0
        assert result.output.strip() == ""

    def test_empty_output_when_ideas_dir_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["idea", "list"])
        assert result.exit_code == 0
        assert result.output.strip() == ""


@pytest.mark.unit
class TestIdeaListSorted:

    def test_ideas_sorted_alphabetically(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "wip", "zebra-project")
        _create_idea(tmp_path, "draft", "alpha-idea")
        _create_idea(tmp_path, "ready", "middle-feature")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["idea", "list"])

        assert result.exit_code == 0
        lines = result.output.strip().splitlines()
        assert len(lines) == 3
        assert "alpha-idea" in lines[0]
        assert "middle-feature" in lines[1]
        assert "zebra-project" in lines[2]


@pytest.mark.unit
class TestIdeaListColumns:

    def test_output_contains_name_state_and_directory(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "wip", "my-feature")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["idea", "list"])

        assert result.exit_code == 0
        line = result.output.strip()
        assert "my-feature" in line
        assert "wip" in line
        assert "docs/ideas/wip/my-feature" in line

    def test_columns_are_aligned(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "draft", "short")
        _create_idea(tmp_path, "completed", "a-very-long-idea-name")
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(main, ["idea", "list"])

        assert result.exit_code == 0
        lines = result.output.strip().splitlines()
        assert len(lines) == 2

        # State column should start at the same position in both lines
        state_positions = []
        for line in lines:
            parts = line.split()
            # Find where the state word starts
            name = parts[0]
            state_start = line.index(parts[1], len(name))
            state_positions.append(state_start)

        assert state_positions[0] == state_positions[1], (
            f"State columns not aligned: positions {state_positions}"
        )
