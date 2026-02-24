"""Integration test for isolate mode worktree creation.

Verifies that --isolation-type creates a worktree and does not
change the main repository's branch.
"""

import os
import shutil
import stat
import subprocess
import tempfile
import uuid

import pytest
from git import Repo

from conftest import SCRIPT_CMD, create_github_repo, delete_github_repo


def _create_fake_isolarium(directory):
    """Create a fake isolarium script that captures args, cwd, and branch.

    Writes plain text files to <directory>/fake-bin/:
      - isolarium-args.txt: all arguments, one per line
      - isolarium-cwd.txt: working directory
      - isolarium-branch.txt: current git branch

    Args:
        directory: Directory to create the script in.

    Returns:
        Path to the directory containing the fake isolarium.
    """
    bin_dir = os.path.join(directory, "fake-bin")
    os.makedirs(bin_dir)
    script_path = os.path.join(bin_dir, "isolarium")
    with open(script_path, "w") as f:
        f.write("#!/bin/bash\n"
                'printf "%s\\n" "$@" > "' + bin_dir + '/isolarium-args.txt"\n'
                'pwd > "' + bin_dir + '/isolarium-cwd.txt"\n'
                'git branch --show-current > "' + bin_dir + '/isolarium-branch.txt"\n'
                "exit 0\n")
    os.chmod(script_path, os.stat(script_path).st_mode | stat.S_IEXEC)
    return bin_dir


def _read_capture(fake_bin_dir, name):
    """Read a capture file written by the fake isolarium."""
    with open(os.path.join(fake_bin_dir, f"isolarium-{name}.txt")) as f:
        return f.read().strip()


@pytest.fixture(scope="function")
def github_repo_for_isolate():
    """Create a GitHub repo with a simple plan for isolate mode testing."""
    repo_name = f"test-tmp-isolate-{uuid.uuid4().hex[:8]}"
    repo_full_name = create_github_repo(repo_name)

    try:
        tmpdir = tempfile.mkdtemp()

        subprocess.run(
            ["gh", "repo", "clone", repo_full_name, tmpdir],
            capture_output=True, check=True,
        )

        repo = Repo(tmpdir)
        repo.config_writer().set_value("user", "email", "test@test.com").release()
        repo.config_writer().set_value("user", "name", "Test").release()

        readme = os.path.join(tmpdir, "README.md")
        with open(readme, "w") as f:
            f.write(f"# {repo_name}")
        repo.index.add(["README.md"])
        repo.index.commit("Initial commit")

        idea_name = "isolate-test"
        idea_dir = os.path.join(tmpdir, idea_name)
        os.makedirs(idea_dir)

        with open(os.path.join(idea_dir, f"{idea_name}-idea.md"), "w") as f:
            f.write("# Isolate Test Idea\n\nTest idea for isolate mode.")

        with open(os.path.join(idea_dir, f"{idea_name}-discussion.md"), "w") as f:
            f.write("# Discussion\n\nNo discussion needed.")

        with open(os.path.join(idea_dir, f"{idea_name}-spec.md"), "w") as f:
            f.write("# Specification\n\nSimple spec.")

        plan_path = os.path.join(idea_dir, f"{idea_name}-plan.md")
        with open(plan_path, "w") as f:
            f.write("""# Isolate Test Plan

## Instructions for Coding Agent

- Use TDD

---

## Steel Thread 1: Test Tasks

- [ ] **Task 1.1: First task**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: First thing works
  - Evidence: `pytest`
  - Steps:
    - [ ] Do something first
""")

        for filename in os.listdir(idea_dir):
            filepath = os.path.join(idea_dir, filename)
            rel_path = os.path.relpath(filepath, tmpdir)
            repo.index.add([rel_path])
        repo.index.commit("Add isolate test idea files")

        repo.remote("origin").push("HEAD:main")

        yield {
            "tmpdir": tmpdir,
            "repo_full_name": repo_full_name,
            "idea_dir": idea_dir,
            "idea_name": idea_name,
            "repo": repo,
        }

    finally:
        delete_github_repo(repo_full_name)
        if "tmpdir" in locals():
            shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.integration_gh
class TestIsolateModeCreatesWorktree:
    """--isolation-type creates a worktree and preserves the main repo branch."""

    def test_main_repo_branch_unchanged_after_isolate_mode(self, github_repo_for_isolate):
        info = github_repo_for_isolate
        repo = info["repo"]
        tmpdir = info["tmpdir"]
        idea_dir = info["idea_dir"]
        idea_name = info["idea_name"]

        original_branch = repo.active_branch.name
        fake_bin = _create_fake_isolarium(tmpdir)

        mock_claude = os.path.join(tmpdir, "mock-claude.sh")
        with open(mock_claude, "w") as f:
            f.write("#!/bin/bash\necho '<NOTHING-TO-DO>'\n")
        os.chmod(mock_claude, os.stat(mock_claude).st_mode | stat.S_IEXEC)

        env = os.environ.copy()
        env["PATH"] = fake_bin + os.pathsep + env["PATH"]
        env.pop("CLAUDECODE", None)

        result = subprocess.run(
            SCRIPT_CMD + [
                idea_dir,
                "--isolation-type", "fake",
                "--non-interactive",
                "--skip-ci-wait",
                "--mock-claude", mock_claude,
            ],
            capture_output=True, text=True,
            cwd=tmpdir, timeout=120, env=env,
        )

        assert result.returncode == 0, (
            f"i2code failed: rc={result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        repo = Repo(tmpdir)
        assert repo.active_branch.name == original_branch, (
            f"Main repo branch changed from {original_branch} to "
            f"{repo.active_branch.name}"
        )

        tmpdir_name = os.path.basename(tmpdir)
        worktree_path = os.path.join(
            os.path.dirname(tmpdir), f"{tmpdir_name}-wt-{idea_name}",
        )
        assert os.path.isdir(worktree_path), (
            f"Expected worktree directory at {worktree_path}"
        )

        captured_branch = _read_capture(fake_bin, "branch")
        assert captured_branch == f"idea/{idea_name}", (
            f"Expected isolarium to run on idea branch, got {captured_branch}"
        )

        captured_cwd = _read_capture(fake_bin, "cwd")
        assert os.path.realpath(captured_cwd) == os.path.realpath(worktree_path), (
            f"Expected isolarium cwd to be worktree, got {captured_cwd}"
        )

        captured_args = _read_capture(fake_bin, "args").splitlines()
        assert "--type" in captured_args, "Expected --type in isolarium args"
        type_idx = captured_args.index("--type")
        assert captured_args[type_idx + 1] == "fake"

        assert "--name" in captured_args, "Expected --name in isolarium args"
        name_idx = captured_args.index("--name")
        assert captured_args[name_idx + 1] == f"i2code-{idea_name}"
