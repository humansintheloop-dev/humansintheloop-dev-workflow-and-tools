"""Integration tests for ensure_project_setup() with mock Claude."""

import os
import stat
import tempfile

import pytest
from git import Repo

from i2code.implement.project_setup import ensure_project_setup
from i2code.implement.git_repository import GitRepository

from fake_github_client import FakeGitHubClient


def create_mock_claude_script(path):
    """Create a mock Claude script that creates scaffolding and commits."""
    script = """#!/bin/bash
# Mock Claude script for scaffolding setup
# Receives "setup" as argument from build_scaffolding_prompt

if [ ! -f scaffolding.txt ]; then
    echo "mock scaffolding" > scaffolding.txt
    git add scaffolding.txt
    git commit -m "Add scaffolding via mock Claude"
fi
"""
    with open(path, "w") as f:
        f.write(script)
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)


def init_repo_with_remote(tmpdir):
    """Create a git repo with a bare remote and initial commit."""
    remote_path = os.path.join(tmpdir, "remote.git")
    Repo.init(remote_path, bare=True)

    repo_path = os.path.join(tmpdir, "repo")
    repo = Repo.init(repo_path)
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    repo.config_writer().set_value("user", "name", "Test").release()

    readme = os.path.join(repo_path, "README.md")
    with open(readme, "w") as f:
        f.write("# Test")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    repo.create_remote("origin", remote_path)
    repo.remotes.origin.push(repo.active_branch.name)

    # Create idea directory with minimal files
    idea_dir = os.path.join(repo_path, "docs", "features", "test-idea")
    os.makedirs(idea_dir)
    with open(os.path.join(idea_dir, "test-idea-idea.txt"), "w") as f:
        f.write("Test idea for scaffolding")
    with open(os.path.join(idea_dir, "test-idea-spec.md"), "w") as f:
        f.write("# Test Spec")

    return repo, repo_path, idea_dir


@pytest.mark.integration
class TestEnsureProjectSetupWithMockClaude:
    """Integration tests for ensure_project_setup with a mock Claude script."""

    def test_mock_claude_setup_creates_scaffolding_commit(self):
        """Mock Claude creates scaffolding, ensure_project_setup detects and pushes it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, repo_path, idea_dir = init_repo_with_remote(tmpdir)

            mock_script = os.path.join(tmpdir, "mock-claude.sh")
            create_mock_claude_script(mock_script)

            integration_branch = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_integration_branch("test-idea")

            result = ensure_project_setup(
                repo=repo,
                idea_directory=idea_dir,
                idea_name="test-idea",
                integration_branch=integration_branch,
                mock_claude=mock_script,
                skip_ci_wait=True,
            )

            assert result is True

            # Verify the integration branch has the scaffolding commit
            repo.git.checkout(integration_branch)
            assert os.path.isfile(os.path.join(repo_path, "scaffolding.txt"))

            # Verify the commit is on the branch
            log = repo.git.log("--oneline")
            assert "mock Claude" in log

    def test_idempotent_second_run_is_noop(self):
        """Second run with idempotent mock should detect no new commits and return True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo, repo_path, idea_dir = init_repo_with_remote(tmpdir)

            mock_script = os.path.join(tmpdir, "mock-claude.sh")
            create_mock_claude_script(mock_script)

            integration_branch = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_integration_branch("test-idea")

            # First run — creates scaffolding
            result1 = ensure_project_setup(
                repo=repo,
                idea_directory=idea_dir,
                idea_name="test-idea",
                integration_branch=integration_branch,
                mock_claude=mock_script,
                skip_ci_wait=True,
            )
            assert result1 is True

            # Record commit count after first run
            commit_count_after_first = int(repo.git.rev_list("--count", "HEAD"))

            # Second run — should be a no-op (no new commits)
            result2 = ensure_project_setup(
                repo=repo,
                idea_directory=idea_dir,
                idea_name="test-idea",
                integration_branch=integration_branch,
                mock_claude=mock_script,
                skip_ci_wait=True,
            )
            assert result2 is True

            # Commit count should not have changed
            commit_count_after_second = int(repo.git.rev_list("--count", "HEAD"))
            assert commit_count_after_second == commit_count_after_first
