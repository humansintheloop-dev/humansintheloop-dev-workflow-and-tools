"""CLI integration tests for i2code idea archive."""

import os
import subprocess

import pytest
import yaml
from click.testing import CliRunner

from i2code.cli import main


def _create_idea(base, name, location, state):
    """Create an idea in docs/ideas/<location>/<name>/ with a metadata file."""
    idea_dir = os.path.join(base, "docs", "ideas", location, name)
    os.makedirs(idea_dir, exist_ok=True)
    metadata_path = os.path.join(idea_dir, f"{name}-metadata.yaml")
    with open(metadata_path, "w") as f:
        yaml.safe_dump({"state": state}, f)
    placeholder = os.path.join(idea_dir, f"{name}-idea.md")
    with open(placeholder, "w") as f:
        f.write(f"# {name}\n")
    return idea_dir


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


def _invoke_archive(runner, name, **flags):
    """Invoke `i2code idea archive <name>` and return the result."""
    args = ["idea", "archive", name]
    if flags.get("no_commit"):
        args.append("--no-commit")
    return runner.invoke(main, args)


@pytest.fixture
def cli(tmp_path, monkeypatch):
    """CliRunner rooted at tmp_path."""
    monkeypatch.chdir(tmp_path)
    return CliRunner()


@pytest.fixture
def git_repo(tmp_path):
    """A tmp_path that is an initialized git repository."""
    _init_git_repo(tmp_path)
    return tmp_path


def _committed_idea(git_repo, name, location, state):
    """Create an idea in a git repo and commit it."""
    _create_idea(git_repo, name, location, state)
    _git_add_and_commit(git_repo, "Initial commit")
    return git_repo


@pytest.mark.unit
class TestArchive:

    def test_archive_moves_directory(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "active", "completed")

        result = _invoke_archive(cli, "old-feature")

        assert result.exit_code == 0
        active_dir = git_repo / "docs" / "ideas" / "active" / "old-feature"
        archived_dir = git_repo / "docs" / "ideas" / "archived" / "old-feature"
        assert not active_dir.exists()
        assert archived_dir.is_dir()

    def test_archive_commit_message(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "active", "completed")

        result = _invoke_archive(cli, "old-feature")

        assert result.exit_code == 0
        assert _last_commit_message(git_repo) == "Archive idea old-feature"

    def test_archive_preserves_metadata_state(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "active", "completed")

        result = _invoke_archive(cli, "old-feature")

        assert result.exit_code == 0
        metadata_path = git_repo / "docs" / "ideas" / "archived" / "old-feature" / "old-feature-metadata.yaml"
        with open(metadata_path) as f:
            data = yaml.safe_load(f)
        assert data["state"] == "completed"

    def test_archive_errors_if_already_archived(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _create_idea(git_repo, "old-feature", "archived", "completed")
        _git_add_and_commit(git_repo, "Initial commit")

        result = _invoke_archive(cli, "old-feature")

        assert result.exit_code == 1
        assert "already archived" in result.output.lower()

    def test_archive_no_commit_flag(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "active", "completed")
        commit_before = _last_commit_message(git_repo)

        result = _invoke_archive(cli, "old-feature", no_commit=True)

        assert result.exit_code == 0
        archived_dir = git_repo / "docs" / "ideas" / "archived" / "old-feature"
        assert archived_dir.is_dir()
        assert _last_commit_message(git_repo) == commit_before


def _invoke_unarchive(runner, name, **flags):
    """Invoke `i2code idea unarchive <name>` and return the result."""
    args = ["idea", "unarchive", name]
    if flags.get("no_commit"):
        args.append("--no-commit")
    return runner.invoke(main, args)


@pytest.mark.unit
class TestUnarchive:

    def test_unarchive_moves_directory(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "archived", "completed")

        result = _invoke_unarchive(cli, "old-feature")

        assert result.exit_code == 0
        archived_dir = git_repo / "docs" / "ideas" / "archived" / "old-feature"
        active_dir = git_repo / "docs" / "ideas" / "active" / "old-feature"
        assert not archived_dir.exists()
        assert active_dir.is_dir()

    def test_unarchive_commit_message(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "archived", "completed")

        result = _invoke_unarchive(cli, "old-feature")

        assert result.exit_code == 0
        assert _last_commit_message(git_repo) == "Unarchive idea old-feature"

    def test_unarchive_preserves_metadata_state(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "archived", "completed")

        result = _invoke_unarchive(cli, "old-feature")

        assert result.exit_code == 0
        metadata_path = git_repo / "docs" / "ideas" / "active" / "old-feature" / "old-feature-metadata.yaml"
        with open(metadata_path) as f:
            data = yaml.safe_load(f)
        assert data["state"] == "completed"

    def test_unarchive_errors_if_already_active(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "active", "completed")

        result = _invoke_unarchive(cli, "old-feature")

        assert result.exit_code == 1
        assert "already" in result.output.lower() and "active" in result.output.lower()

    def test_unarchive_no_commit_flag(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _committed_idea(git_repo, "old-feature", "archived", "completed")
        commit_before = _last_commit_message(git_repo)

        result = _invoke_unarchive(cli, "old-feature", no_commit=True)

        assert result.exit_code == 0
        active_dir = git_repo / "docs" / "ideas" / "active" / "old-feature"
        assert active_dir.is_dir()
        assert _last_commit_message(git_repo) == commit_before
