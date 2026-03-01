"""CLI integration tests for i2code idea state."""

import os
import subprocess

import pytest
from click.testing import CliRunner

from i2code.cli import main


def _create_idea(base, state, name):
    """Create an idea directory under docs/ideas/{state}/{name}/ with a placeholder file."""
    idea_dir = os.path.join(base, "docs", "ideas", state, name)
    os.makedirs(idea_dir, exist_ok=True)
    placeholder = os.path.join(idea_dir, "idea.md")
    with open(placeholder, "w") as f:
        f.write(f"# {name}\n")
    return idea_dir


def _invoke_idea_state(monkeypatch, tmp_path, name_or_path):
    """Invoke `i2code idea state <name-or-path>` and return the result."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    return runner.invoke(main, ["idea", "state", name_or_path])


def _invoke_idea_state_transition(monkeypatch, tmp_path, name, new_state):
    """Invoke `i2code idea state <name> <new-state>` and return the result."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    return runner.invoke(main, ["idea", "state", name, new_state])


def _init_git_repo(path):
    """Initialize a git repo and make an initial commit."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, check=True, capture_output=True,
    )


def _git_add_and_commit(path, message):
    """Stage all files and create a commit."""
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path, check=True, capture_output=True,
    )


def _last_commit_message(path):
    """Return the most recent commit message."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=path, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


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


@pytest.mark.unit
class TestIdeaStateTransition:

    def test_moves_idea_directory_and_creates_commit(self, tmp_path, monkeypatch):
        _init_git_repo(tmp_path)
        _create_idea(tmp_path, "wip", "my-feature")
        _git_add_and_commit(tmp_path, "Initial commit")

        result = _invoke_idea_state_transition(
            monkeypatch, tmp_path, "my-feature", "completed"
        )

        assert result.exit_code == 0
        new_dir = tmp_path / "docs" / "ideas" / "completed" / "my-feature"
        old_dir = tmp_path / "docs" / "ideas" / "wip" / "my-feature"
        assert new_dir.is_dir()
        assert not old_dir.exists()
        assert _last_commit_message(tmp_path) == "Move idea my-feature from wip to completed"


@pytest.mark.unit
class TestIdeaStateTransitionNoop:

    def test_noop_when_already_in_target_state(self, tmp_path, monkeypatch):
        _init_git_repo(tmp_path)
        _create_idea(tmp_path, "wip", "my-feature")
        _git_add_and_commit(tmp_path, "Initial commit")

        result = _invoke_idea_state_transition(
            monkeypatch, tmp_path, "my-feature", "wip"
        )

        assert result.exit_code == 0
        assert "already" in result.output.lower()
        assert _last_commit_message(tmp_path) == "Initial commit"


@pytest.mark.unit
class TestIdeaStateTransitionGitError:

    def test_reports_git_error_when_target_exists(self, tmp_path, monkeypatch):
        _init_git_repo(tmp_path)
        _create_idea(tmp_path, "wip", "my-feature")
        _create_idea(tmp_path, "completed", "my-feature")
        _git_add_and_commit(tmp_path, "Initial commit")

        result = _invoke_idea_state_transition(
            monkeypatch, tmp_path, "my-feature", "completed"
        )

        assert result.exit_code == 1
        assert "my-feature" in result.output
