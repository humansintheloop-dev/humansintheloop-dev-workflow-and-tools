"""Integration tests for git infrastructure setup in implement-with-worktree.

These tests run the actual shell script and verify git infrastructure is created.
"""

import os

import pytest
from git import Repo

from conftest import run_script, write_plan_file


def create_valid_idea_directory(tmpdir, repo, idea_name="test-feature"):
    """Create a valid idea directory with all required files committed."""
    idea_dir = os.path.join(tmpdir, idea_name)
    os.makedirs(idea_dir)

    # Create non-plan files
    for suffix in ["idea.md", "discussion.md", "spec.md"]:
        filepath = os.path.join(idea_dir, f"{idea_name}-{suffix}")
        with open(filepath, "w") as f:
            f.write(f"# {suffix}\n")

    # Create plan file with proper thread/task structure
    write_plan_file(idea_dir, idea_name, [
        (1, 1, "Test task", False),
    ])

    # Commit all files
    for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
        rel_path = os.path.join(idea_name, f"{idea_name}-{suffix}")
        repo.index.add([rel_path])
    repo.index.commit("Add idea files")

    return idea_dir


@pytest.mark.integration
class TestIdeaBranchCreation:
    """Test that script creates idea branch."""

    def test_idea_branch_created(self, test_git_repo_with_commit):
        """Running script should create idea branch."""
        tmpdir, repo = test_git_repo_with_commit
        idea_dir = create_valid_idea_directory(tmpdir, repo)

        result = run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Reload repo to see new branches
        repo = Repo(tmpdir)

        # Check idea branch exists
        branch_names = [b.name for b in repo.branches]
        assert "idea/test-feature" in branch_names, \
            f"Idea branch not found. Branches: {branch_names}. stderr: {result.stderr}"


@pytest.mark.integration
class TestWorktreeCreation:
    """Test that script creates worktree."""

    def test_worktree_directory_created(self, test_git_repo_with_commit):
        """Running script should create worktree directory."""
        tmpdir, repo = test_git_repo_with_commit
        repo_name = os.path.basename(tmpdir)
        idea_dir = create_valid_idea_directory(tmpdir, repo)

        # Expected worktree path: ../<repo-name>-wt-<idea-name>
        parent_dir = os.path.dirname(tmpdir)
        expected_worktree = os.path.join(parent_dir, f"{repo_name}-wt-test-feature")

        result = run_script(idea_dir, cwd=tmpdir, setup_only=True)

        assert os.path.isdir(expected_worktree), \
            f"Worktree not created at {expected_worktree}. stderr: {result.stderr}"


@pytest.mark.integration
class TestNoSliceBranchCreated:
    """Test that script does not create slice or integration branches."""

    def test_only_idea_branch_created(self, test_git_repo_with_commit):
        """Running script should only create idea branch, no slice or integration branches."""
        tmpdir, repo = test_git_repo_with_commit
        idea_dir = create_valid_idea_directory(tmpdir, repo)

        result = run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Reload repo to see new branches
        repo = Repo(tmpdir)

        branch_names = [b.name for b in repo.branches]
        idea_sub_branches = [b for b in branch_names if b.startswith("idea/test-feature/")]

        assert len(idea_sub_branches) == 0, \
            f"Unexpected sub-branches found: {idea_sub_branches}. stderr: {result.stderr}"


@pytest.mark.integration
class TestInfrastructureReuse:
    """Test that running script again reuses existing infrastructure."""

    def test_branches_reused_not_duplicated(self, test_git_repo_with_commit):
        """Running script twice should reuse branches, not create duplicates."""
        tmpdir, repo = test_git_repo_with_commit
        idea_dir = create_valid_idea_directory(tmpdir, repo)

        # First run
        run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Get branch count after first run
        repo = Repo(tmpdir)
        first_run_branches = [b.name for b in repo.branches]

        # Second run
        run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Get branch count after second run
        repo = Repo(tmpdir)
        second_run_branches = [b.name for b in repo.branches]

        # Branch count should be the same
        assert len(first_run_branches) == len(second_run_branches), \
            f"Branches duplicated. First: {first_run_branches}, Second: {second_run_branches}"
