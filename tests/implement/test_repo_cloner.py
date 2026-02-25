"""Tests for RepoCloner.create_clone() and clone_path_for()."""

import os
import subprocess

import pytest

from i2code.implement.repo_cloner import RepoCloner, clone_path_for


def _init_git_repo(path):
    """Create a minimal git repo with one commit at the given path."""
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, check=True, capture_output=True,
    )
    readme = os.path.join(path, "README.md")
    with open(readme, "w") as f:
        f.write("# test\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=path, check=True, capture_output=True,
    )


@pytest.mark.unit
class TestClonePathFor:

    def test_computes_sibling_clone_path(self):
        assert clone_path_for("/home/user/my-project", "my-feature") == (
            "/home/user/my-project-cl-my-feature"
        )

    def test_handles_trailing_slash(self):
        result = clone_path_for("/home/user/repo/", "feat")
        assert result.endswith("-cl-feat")


def _git_output(clone_dir, *args):
    """Run a git command in clone_dir and return stripped stdout."""
    result = subprocess.run(
        ["git", *args],
        cwd=clone_dir, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


_GITHUB_URL = "https://github.com/org/repo.git"


@pytest.mark.unit
class TestRepoCloner:

    def _create_clone(self, tmp_path, repo_name="repo", idea_name="feat", origin_url=_GITHUB_URL):
        source = str(tmp_path / repo_name)
        _init_git_repo(source)
        clone_dir = RepoCloner().create_clone(source, idea_name, origin_url)
        return source, clone_dir

    def test_clone_directory_created_at_expected_path(self, tmp_path):
        source, clone_dir = self._create_clone(tmp_path, repo_name="my-repo", idea_name="my-idea")

        expected = str(tmp_path / "my-repo-cl-my-idea")
        assert clone_dir == expected
        assert os.path.isdir(expected)

    def test_clone_origin_is_github_url(self, tmp_path):
        _, clone_dir = self._create_clone(tmp_path)

        assert _git_output(clone_dir, "remote", "get-url", "origin") == _GITHUB_URL

    def test_clone_has_independent_git_directory(self, tmp_path):
        _, clone_dir = self._create_clone(tmp_path)

        assert os.path.isdir(os.path.join(clone_dir, ".git"))

    def test_clone_is_shallow(self, tmp_path):
        _, clone_dir = self._create_clone(tmp_path)

        assert _git_output(clone_dir, "rev-list", "--count", "HEAD") == "1"

    def test_returns_existing_path_when_clone_already_exists(self, tmp_path):
        source, first = self._create_clone(tmp_path)
        second = RepoCloner().create_clone(source, "feat", _GITHUB_URL)

        assert first == second
