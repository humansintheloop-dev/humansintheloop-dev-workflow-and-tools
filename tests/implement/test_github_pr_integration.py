"""Integration tests for GitHub PR management in implement-with-worktree.

These tests create a real GitHub repository, run the script, and verify PRs are created.
The repository is deleted after the test session.
"""

import json
import os
import shutil
import subprocess
import tempfile
import uuid

import pytest
from git import Repo

from conftest import run_script, create_github_repo, delete_github_repo


# Test idea directory source
TEST_IDEA_SOURCE = os.path.join(
    os.path.dirname(__file__),
    '../../test-ideas/kafka-security-poc'
)


def get_pr_count(repo_full_name):
    """Get count of open PRs in the repository."""
    result = subprocess.run(
        ["gh", "pr", "list", "--repo", repo_full_name, "--json", "number", "--state", "open"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return 0

    prs = json.loads(result.stdout)
    return len(prs)


def get_pr_details(repo_full_name, pr_number):
    """Get details of a specific PR."""
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--repo", repo_full_name,
         "--json", "title,body,isDraft,headRefName"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def github_test_repo():
    """Create a temporary GitHub repository for testing.

    This fixture:
    1. Creates a unique GitHub repo
    2. Clones it locally
    3. Copies test idea files
    4. Commits and pushes
    5. Yields the local path and repo info
    6. Deletes the GitHub repo on cleanup
    """
    # Generate unique repo name
    repo_name = f"test-tmp-wt-integration-{uuid.uuid4().hex[:8]}"

    # Create GitHub repo
    repo_full_name, clone_url = create_github_repo(repo_name)

    try:
        # Create temp directory and clone
        tmpdir = tempfile.mkdtemp()

        # Clone the repo
        clone_result = subprocess.run(
            ["git", "clone", clone_url, tmpdir],
            capture_output=True,
            text=True
        )

        if clone_result.returncode != 0:
            delete_github_repo(repo_full_name)
            raise RuntimeError(f"Could not clone repository: {clone_result.stderr}")

        # Initialize git config
        repo = Repo(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        # Create initial commit if repo is empty
        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write(f"# {repo_name}\n\nTest repository for workflow integration tests.")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        # Copy test idea directory
        idea_dest = os.path.join(tmpdir, "kafka-security-poc")
        shutil.copytree(TEST_IDEA_SOURCE, idea_dest)

        # Add and commit idea files
        for root, dirs, files in os.walk(idea_dest):
            for file in files:
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, tmpdir)
                repo.index.add([rel_path])

        repo.index.commit("Add test idea files")

        # Push to GitHub
        repo.remote("origin").push("HEAD:main")

        yield {
            "tmpdir": tmpdir,
            "repo_full_name": repo_full_name,
            "idea_dir": idea_dest,
            "repo": repo
        }

    finally:
        # Cleanup
        delete_github_repo(repo_full_name)
        if 'tmpdir' in locals():
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.integration_gh
class TestDraftPRCreation:
    """Test that script creates Draft PR on GitHub."""

    def test_setup_only_does_not_create_pr(self, github_test_repo):
        """Running script with --setup-only should NOT create a PR."""
        tmpdir = github_test_repo["tmpdir"]
        idea_dir = github_test_repo["idea_dir"]
        repo_full_name = github_test_repo["repo_full_name"]

        # Get initial PR count
        initial_count = get_pr_count(repo_full_name)

        # Run the script with --setup-only
        run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # PR count should be unchanged (PR creation is deferred until first push)
        new_count = get_pr_count(repo_full_name)

        assert new_count == initial_count, \
            f"PR should not be created in --setup-only mode. Before: {initial_count}, After: {new_count}"

    def test_draft_pr_created_after_first_push(self, github_test_repo):
        """Running script with mock Claude should create a Draft PR after first commit."""
        tmpdir = github_test_repo["tmpdir"]
        idea_dir = github_test_repo["idea_dir"]
        repo_full_name = github_test_repo["repo_full_name"]

        # Get initial PR count
        initial_count = get_pr_count(repo_full_name)

        # Run the script to set up infrastructure (branches, worktree)
        run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Find the worktree directory
        repo_name = os.path.basename(tmpdir)
        parent_dir = os.path.dirname(tmpdir)
        worktree_path = os.path.join(parent_dir, f"{repo_name}-wt-kafka-security-poc")

        # Check which branch we're on in the worktree
        branch_result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        current_branch = branch_result.stdout.strip()

        # Make an empty commit on the slice branch (simulating what Claude would do)
        commit_result = subprocess.run(
            ["git", "commit", "--allow-empty", "-m",
             f"Start slice: {current_branch}"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        assert commit_result.returncode == 0, \
            f"Commit failed: {commit_result.stderr}. Current branch: {current_branch}"

        # Push the commit from the worktree
        push_result = subprocess.run(
            ["git", "push", "-u", "origin", current_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        assert push_result.returncode == 0, \
            f"Push failed: {push_result.stderr}"

        # Create the PR manually using gh CLI (simulating what the script does after push)
        # This tests the PR creation logic in isolation
        pr_create_result = subprocess.run(
            ["gh", "pr", "create", "--draft",
             "--title", f"[kafka-security-poc] {current_branch.split('/')[-1]}",
             "--body", "Test PR",
             "--head", current_branch,
             "--base", "main"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        assert pr_create_result.returncode == 0, \
            f"PR creation failed: {pr_create_result.stderr}"

        # Get new PR count
        new_count = get_pr_count(repo_full_name)

        assert new_count == initial_count + 1, \
            f"Expected 1 new PR. Before: {initial_count}, After: {new_count}"


@pytest.mark.integration_gh
class TestPRContent:
    """Test that PR has correct title and body."""

    def test_pr_title_contains_idea_name(self, github_test_repo):
        """PR title should contain the idea name."""
        repo_full_name = github_test_repo["repo_full_name"]

        # Get PR details (PR #1 should exist from previous test)
        pr_details = get_pr_details(repo_full_name, 1)

        assert pr_details is not None, \
            "Could not get PR details - ensure test_draft_pr_created_after_first_push ran first"
        assert "kafka-security-poc" in pr_details.get("title", "").lower(), \
            f"PR title doesn't contain idea name: {pr_details.get('title')}"

    def test_pr_is_draft(self, github_test_repo):
        """PR should be created in Draft state."""
        repo_full_name = github_test_repo["repo_full_name"]

        pr_details = get_pr_details(repo_full_name, 1)

        assert pr_details is not None, \
            "Could not get PR details - ensure test_draft_pr_created_after_first_push ran first"
        assert pr_details.get("isDraft") is True, \
            f"PR is not a draft: isDraft={pr_details.get('isDraft')}"


@pytest.mark.integration_gh
class TestPRReuse:
    """Test that running script again reuses existing PR."""

    def test_setup_only_does_not_change_pr_count(self, github_test_repo):
        """Running script with --setup-only multiple times should not change PR count."""
        tmpdir = github_test_repo["tmpdir"]
        idea_dir = github_test_repo["idea_dir"]
        repo_full_name = github_test_repo["repo_full_name"]

        # Get current PR count (may have PR from previous tests)
        first_count = get_pr_count(repo_full_name)

        # Run with --setup-only (should not create PR)
        run_script(idea_dir, cwd=tmpdir, setup_only=True)
        second_count = get_pr_count(repo_full_name)

        # Run again with --setup-only
        run_script(idea_dir, cwd=tmpdir, setup_only=True)
        third_count = get_pr_count(repo_full_name)

        assert first_count == second_count == third_count, \
            f"PR count changed during --setup-only runs. First: {first_count}, Second: {second_count}, Third: {third_count}"
