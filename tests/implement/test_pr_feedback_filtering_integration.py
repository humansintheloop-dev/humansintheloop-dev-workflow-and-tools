"""Integration tests for PR feedback filtering (self-replies and resolved threads).

These tests create real GitHub repos/PRs and verify that production
filtering methods correctly exclude marker-bearing replies and
resolved-thread comments.
"""

import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass

import pytest
from git import Repo

from conftest import create_github_repo, delete_github_repo
from i2code.implement.github_client import GitHubClient
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor


@dataclass
class GitHubTestPR:
    repo_full_name: str
    pr_number: int
    commit_sha: str


@pytest.fixture
def github_repo_with_initial_commit():
    """Create a temporary GitHub repo with an initial commit containing hello.py."""
    repo_name = f"test-pr-feedback-{uuid.uuid4().hex[:8]}"
    tmpdir = tempfile.mkdtemp()
    repo_full_name = None

    try:
        repo = Repo.init(tmpdir, initial_branch="main")
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        hello_path = os.path.join(tmpdir, "hello.py")
        with open(hello_path, "w") as f:
            f.write('def greet(name):\n    return f"Hello, {name}!"\n\n\n'
                     'def farewell(name):\n    return f"Goodbye, {name}!"\n')

        repo.index.add(["hello.py"])
        repo.index.commit("Initial commit with source file")

        repo_full_name = create_github_repo(repo_name)


        subprocess.run(
            ["git", "remote", "add", "origin",
             f"git@github.com:{repo_full_name}.git"],
            cwd=tmpdir, capture_output=True, text=True, check=True,
        )

        print(f"\n\nPushing {repo_full_name}\n")
        subprocess.run(
            ["git", "push", "-u", "origin", "main"],
            cwd=tmpdir, capture_output=True, text=True, check=True,
        )
        print(f"\n\nPushed {repo_full_name}\n")

        yield tmpdir, repo, repo_full_name

    finally:
        if repo_full_name:
            delete_github_repo(repo_full_name)
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


def _gh_api(endpoint, *args):
    """Call gh api and return parsed JSON."""
    result = subprocess.run(
        ["gh", "api", endpoint, *args],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"gh api failed: {result.stderr}"
    return json.loads(result.stdout)


def _create_branch_and_pr(repo, tmpdir, branch_spec):
    """Create a branch with a new file, push it, and open a PR.

    Args:
        repo: GitPython Repo instance
        tmpdir: Working directory for the repo
        branch_spec: dict with keys: repo_full_name, branch, filename, content, title
    """
    repo.git.checkout("-b", branch_spec["branch"])

    filepath = os.path.join(tmpdir, branch_spec["filename"])
    with open(filepath, "w") as f:
        f.write(branch_spec["content"])

    repo.index.add([branch_spec["filename"]])
    repo.index.commit(f"Add {branch_spec['filename']}")
    repo.git.push("-u", "origin", branch_spec["branch"])

    result = subprocess.run(
        ["gh", "pr", "create", "--repo", branch_spec["repo_full_name"],
         "--title", branch_spec["title"], "--body", "Integration test",
         "--head", branch_spec["branch"], "--base", "main"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"PR creation failed: {result.stderr}"

    pr_url = result.stdout.strip()
    pr_number = int(pr_url.rstrip("/").split("/")[-1])

    return GitHubTestPR(
        repo_full_name=branch_spec["repo_full_name"],
        pr_number=pr_number,
        commit_sha=repo.head.commit.hexsha,
    )


def _post_review_comment(pr, path, line, body):
    """Post a review comment on a PR and return the comment ID."""
    comment = _gh_api(
        f"repos/{pr.repo_full_name}/pulls/{pr.pr_number}/comments",
        "-f", f"body={body}",
        "-f", f"commit_id={pr.commit_sha}",
        "-f", f"path={path}",
        "-F", f"line={line}",
        "-f", "side=RIGHT",
    )
    return comment["id"]


def _resolve_review_thread(pr, comment_id):
    """Resolve the review thread containing the given comment."""
    owner, repo_name = pr.repo_full_name.split("/")

    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
              comments(first: 100) {
                nodes { databaseId }
              }
            }
          }
        }
      }
    }"""

    result = subprocess.run(
        ["gh", "api", "graphql",
         "-f", f"query={query}",
         "-F", f"owner={owner}",
         "-F", f"repo={repo_name}",
         "-F", f"pr={pr.pr_number}"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"GraphQL query failed: {result.stderr}"
    data = json.loads(result.stdout)

    threads = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    thread_id = None
    for thread in threads:
        for comment in thread["comments"]["nodes"]:
            if comment["databaseId"] == comment_id:
                thread_id = thread["id"]
                break
        if thread_id:
            break

    assert thread_id is not None, f"Thread not found for comment {comment_id}"

    mutation = """
    mutation($threadId: ID!) {
      resolveReviewThread(input: {threadId: $threadId}) {
        thread { isResolved }
      }
    }"""

    result = subprocess.run(
        ["gh", "api", "graphql",
         "-f", f"query={mutation}",
         "-f", f"threadId={thread_id}"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, f"Resolve mutation failed: {result.stderr}"


def _fetch_review_comments(pr):
    """Fetch all review comments for a PR."""
    return _gh_api(f"repos/{pr.repo_full_name}/pulls/{pr.pr_number}/comments", "--jq", ".")


@pytest.mark.integration_gh
class TestPrFeedbackFiltering:
    """Verify that PR feedback filtering excludes marker replies and resolved threads."""

    def test_marker_bearing_replies_are_filtered(self, github_repo_with_initial_commit):
        """Replies prefixed with <!-- i2code --> are excluded by _filter_self_comments."""
        tmpdir, repo, repo_full_name = github_repo_with_initial_commit

        pr = _create_branch_and_pr(repo, tmpdir, {
            "repo_full_name": repo_full_name,
            "branch": "test-marker-filtering",
            "filename": "feature.py",
            "content": 'def new_feature():\n    return "implemented"\n',
            "title": "Test marker filtering",
        })

        comment_id = _post_review_comment(pr, "feature.py", 1, "Please refactor this function")

        marker_body = "<!-- i2code -->\nFixed in abc1234"
        _gh_api(
            f"repos/{pr.repo_full_name}/pulls/{pr.pr_number}/comments/{comment_id}/replies",
            "-f", f"body={marker_body}",
        )

        human_reply_body = "Thanks, but could you also add a docstring?"
        _gh_api(
            f"repos/{pr.repo_full_name}/pulls/{pr.pr_number}/comments/{comment_id}/replies",
            "-f", f"body={human_reply_body}",
        )

        comments = _fetch_review_comments(pr)
        assert len(comments) == 3, f"Expected 3 comments (original + marker reply + human reply), got {len(comments)}"

        user_comments, self_comment_ids = PullRequestReviewProcessor._filter_self_comments(comments)

        assert len(user_comments) == 2
        user_bodies = [c["body"] for c in user_comments]
        assert any("Please refactor" in b for b in user_bodies)
        assert any("add a docstring" in b for b in user_bodies)
        assert len(self_comment_ids) == 1

        marker_comment = [c for c in comments if c["id"] == self_comment_ids[0]][0]
        assert marker_comment["body"].startswith("<!-- i2code -->")

    def test_resolved_thread_comments_are_filtered(self, github_repo_with_initial_commit):
        """Comments in resolved threads are excluded by _exclude_resolved_comments."""
        tmpdir, repo, repo_full_name = github_repo_with_initial_commit

        repo.git.checkout("main")
        pr = _create_branch_and_pr(repo, tmpdir, {
            "repo_full_name": repo_full_name,
            "branch": "test-resolved-threads",
            "filename": "utils.py",
            "content": ("def add(a, b):\n    return a + b\n\n\n"
                        "def subtract(a, b):\n    return a - b\n\n\n"
                        "def multiply(a, b):\n    return a * b\n"),
            "title": "Test resolved thread filtering",
        })

        comment_a_id = _post_review_comment(pr, "utils.py", 1, "Thread A: Please rename this function")
        comment_b_id = _post_review_comment(pr, "utils.py", 5, "Thread B: Add type hints here")

        _resolve_review_thread(pr, comment_a_id)

        owner, repo_name = pr.repo_full_name.split("/")
        gh_client = GitHubClient()
        resolved_ids = gh_client.get_resolved_review_comment_ids(owner, repo_name, pr.pr_number)

        assert comment_a_id in resolved_ids
        assert comment_b_id not in resolved_ids

        comments = _fetch_review_comments(pr)

        remaining, filtered_ids = PullRequestReviewProcessor._exclude_resolved_comments(
            comments, resolved_ids
        )

        assert len(remaining) == 1
        assert remaining[0]["id"] == comment_b_id
        assert "Thread B" in remaining[0]["body"]
        assert len(filtered_ids) == 1
        assert filtered_ids[0] == comment_a_id
