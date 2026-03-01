"""CLI integration tests for i2code idea state."""

import os

import pytest
from click.testing import CliRunner

from i2code.cli import main


def _create_idea(base, state, name):
    """Create an idea directory under docs/ideas/{state}/{name}/."""
    idea_dir = os.path.join(base, "docs", "ideas", state, name)
    os.makedirs(idea_dir, exist_ok=True)
    return idea_dir


def _invoke_idea_state(monkeypatch, tmp_path, name_or_path):
    """Invoke `i2code idea state <name-or-path>` and return the result."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    return runner.invoke(main, ["idea", "state", name_or_path])


@pytest.mark.unit
class TestIdeaStateByName:

    def test_returns_state_for_known_idea(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "draft", "my-feature")

        result = _invoke_idea_state(monkeypatch, tmp_path, "my-feature")

        assert result.exit_code == 0
        assert result.output.strip() == "draft"

    def test_returns_wip_state(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "wip", "active-project")

        result = _invoke_idea_state(monkeypatch, tmp_path, "active-project")

        assert result.exit_code == 0
        assert result.output.strip() == "wip"


@pytest.mark.unit
class TestIdeaStateByPath:

    def test_returns_state_for_directory_path(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "ready", "path-idea")
        idea_path = os.path.join(
            str(tmp_path), "docs", "ideas", "ready", "path-idea"
        )

        result = _invoke_idea_state(monkeypatch, tmp_path, idea_path)

        assert result.exit_code == 0
        assert result.output.strip() == "ready"

    def test_returns_state_for_relative_directory_path(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "completed", "done-idea")

        result = _invoke_idea_state(
            monkeypatch, tmp_path, "docs/ideas/completed/done-idea"
        )

        assert result.exit_code == 0
        assert result.output.strip() == "completed"


@pytest.mark.unit
class TestIdeaStateErrors:

    def test_unknown_name_returns_error(self, tmp_path, monkeypatch):
        _create_idea(tmp_path, "draft", "other-idea")

        result = _invoke_idea_state(monkeypatch, tmp_path, "nonexistent")

        assert result.exit_code == 1
        assert "not found" in result.output.lower()
