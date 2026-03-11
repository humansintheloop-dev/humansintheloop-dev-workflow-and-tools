"""CLI integration tests for i2code idea migrate."""

import os
import subprocess

import pytest
import yaml
from click.testing import CliRunner

from i2code.cli import main


def _init_git_repo(path):
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
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path, check=True, capture_output=True,
    )


def _last_commit_message(path):
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=path, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def _commit_count(path):
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=path, check=True, capture_output=True, text=True,
    )
    return int(result.stdout.strip())


def _create_idea(base, state, name):
    idea_dir = os.path.join(base, "docs", "ideas", state, name)
    os.makedirs(idea_dir, exist_ok=True)
    placeholder = os.path.join(idea_dir, f"{name}-idea.md")
    with open(placeholder, "w") as f:
        f.write(f"# {name}\n")
    return idea_dir


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return CliRunner()


@pytest.fixture
def git_repo(tmp_path):
    _init_git_repo(tmp_path)
    return tmp_path


def _invoke_migrate(runner, **flags):
    args = ["idea", "migrate"]
    if flags.get("no_commit"):
        args.append("--no-commit")
    return runner.invoke(main, args)


@pytest.mark.unit
class TestMigrateCommand:

    def test_migrates_ideas_from_different_state_dirs(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _create_idea(git_repo, "draft", "idea-alpha")
        _create_idea(git_repo, "wip", "idea-beta")
        _git_add_and_commit(git_repo, "initial ideas")

        result = _invoke_migrate(cli)

        assert result.exit_code == 0
        active_dir = git_repo / "docs" / "ideas" / "active"
        assert (active_dir / "idea-alpha").is_dir()
        assert (active_dir / "idea-beta").is_dir()

    def test_creates_metadata_files_with_correct_state(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _create_idea(git_repo, "draft", "idea-alpha")
        _create_idea(git_repo, "wip", "idea-beta")
        _git_add_and_commit(git_repo, "initial ideas")

        _invoke_migrate(cli)

        alpha_meta = git_repo / "docs" / "ideas" / "active" / "idea-alpha" / "idea-alpha-metadata.yaml"
        beta_meta = git_repo / "docs" / "ideas" / "active" / "idea-beta" / "idea-beta-metadata.yaml"
        with open(alpha_meta) as f:
            assert yaml.safe_load(f)["state"] == "draft"
        with open(beta_meta) as f:
            assert yaml.safe_load(f)["state"] == "wip"

    def test_removes_old_state_directories(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _create_idea(git_repo, "draft", "idea-alpha")
        _create_idea(git_repo, "wip", "idea-beta")
        _git_add_and_commit(git_repo, "initial ideas")

        _invoke_migrate(cli)

        assert not (git_repo / "docs" / "ideas" / "draft").exists()
        assert not (git_repo / "docs" / "ideas" / "wip").exists()

    def test_creates_single_commit(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _create_idea(git_repo, "draft", "idea-alpha")
        _create_idea(git_repo, "completed", "idea-beta")
        _git_add_and_commit(git_repo, "initial ideas")
        commits_before = _commit_count(git_repo)

        _invoke_migrate(cli)

        commits_after = _commit_count(git_repo)
        assert commits_after == commits_before + 1
        assert _last_commit_message(git_repo) == "Migrate ideas from directory-based state to metadata files"

    def test_no_commit_flag_stages_without_committing(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        _create_idea(git_repo, "draft", "idea-alpha")
        _git_add_and_commit(git_repo, "initial ideas")
        commits_before = _commit_count(git_repo)

        result = _invoke_migrate(cli, no_commit=True)

        assert result.exit_code == 0
        commits_after = _commit_count(git_repo)
        assert commits_after == commits_before
        # But files should be in active/
        assert (git_repo / "docs" / "ideas" / "active" / "idea-alpha").is_dir()

    def test_idempotent_when_no_old_style_ideas(self, git_repo, cli, monkeypatch):
        monkeypatch.chdir(git_repo)
        # Create an initial commit so HEAD exists
        (git_repo / "README.md").write_text("hello")
        _git_add_and_commit(git_repo, "initial")

        result = _invoke_migrate(cli)

        assert result.exit_code == 0
        assert "nothing to migrate" in result.output.lower() or "no ideas" in result.output.lower()
