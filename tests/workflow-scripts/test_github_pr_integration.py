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

from conftest import run_script


# Test idea directory source
TEST_IDEA_SOURCE = os.path.join(
    os.path.dirname(__file__),
    '../kafka-security-poc'
)


def get_github_username():
    """Get the authenticated GitHub username."""
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def create_github_repo(repo_name):
    """Create a new GitHub repository.

    Returns:
        Tuple of (repo_full_name, clone_url) or None if creation failed
    """
    result = subprocess.run(
        ["gh", "repo", "create", repo_name, "--private"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return None

    # Get username to construct full name
    username = get_github_username()
    if not username:
        return None

    repo_full_name = f"{username}/{repo_name}"
    clone_url = f"git@github.com:{repo_full_name}.git"

    return repo_full_name, clone_url


def delete_github_repo(repo_full_name):
    """Delete a GitHub repository."""
    subprocess.run(
        ["gh", "repo", "delete", repo_full_name, "--yes"],
        capture_output=True,
        text=True
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
    result = create_github_repo(repo_name)
    if result is None:
        pytest.skip("Could not create GitHub repository (check gh auth)")

    repo_full_name, clone_url = result

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
            pytest.skip(f"Could not clone repository: {clone_result.stderr}")

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


@pytest.mark.integration
class TestDraftPRCreation:
    """Test that script creates Draft PR on GitHub."""

    def test_draft_pr_created(self, github_test_repo):
        """Running script should create a Draft PR on GitHub."""
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

        # Make an empty commit on the slice branch to enable PR creation
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
            ["git", "push", "origin", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )
        assert push_result.returncode == 0, \
            f"Push failed: {push_result.stderr}"

        # Verify the push actually worked by checking remote refs
        remote_refs = subprocess.run(
            ["git", "ls-remote", "origin", current_branch],
            cwd=worktree_path,
            capture_output=True,
            text=True
        )

        # Run the script again - now it should create the PR
        result = run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Get new PR count
        new_count = get_pr_count(repo_full_name)

        assert new_count == initial_count + 1, \
            f"Expected 1 new PR. Before: {initial_count}, After: {new_count}. " \
            f"Branch: {current_branch}. Remote refs: {remote_refs.stdout}. " \
            f"stdout: {result.stdout}. stderr: {result.stderr}"


@pytest.mark.integration
class TestPRContent:
    """Test that PR has correct title and body."""

    def test_pr_title_contains_idea_name(self, github_test_repo):
        """PR title should contain the idea name."""
        tmpdir = github_test_repo["tmpdir"]
        idea_dir = github_test_repo["idea_dir"]
        repo_full_name = github_test_repo["repo_full_name"]

        # Run the script (may reuse existing PR from previous test)
        run_script(idea_dir, cwd=tmpdir, setup_only=True)

        # Get PR details (assume PR #1)
        pr_details = get_pr_details(repo_full_name, 1)

        assert pr_details is not None, "Could not get PR details"
        assert "kafka-security-poc" in pr_details.get("title", "").lower(), \
            f"PR title doesn't contain idea name: {pr_details.get('title')}"

    def test_pr_is_draft(self, github_test_repo):
        """PR should be created in Draft state."""
        repo_full_name = github_test_repo["repo_full_name"]

        pr_details = get_pr_details(repo_full_name, 1)

        assert pr_details is not None, "Could not get PR details"
        assert pr_details.get("isDraft") is True, \
            f"PR is not a draft: isDraft={pr_details.get('isDraft')}"


@pytest.mark.integration
class TestPRReuse:
    """Test that running script again reuses existing PR."""

    def test_pr_not_duplicated_on_second_run(self, github_test_repo):
        """Running script twice should not create duplicate PRs."""
        tmpdir = github_test_repo["tmpdir"]
        idea_dir = github_test_repo["idea_dir"]
        repo_full_name = github_test_repo["repo_full_name"]

        # First run (may already have run in previous tests)
        run_script(idea_dir, cwd=tmpdir, setup_only=True)
        first_count = get_pr_count(repo_full_name)

        # Second run
        run_script(idea_dir, cwd=tmpdir, setup_only=True)
        second_count = get_pr_count(repo_full_name)

        assert first_count == second_count, \
            f"PR count changed on second run. First: {first_count}, Second: {second_count}"
