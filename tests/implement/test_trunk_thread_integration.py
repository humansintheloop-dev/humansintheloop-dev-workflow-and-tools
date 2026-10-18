"""Integration tests for `i2code implement --trunk --thread N`.

These tests run the CLI as a subprocess against a real git repository
with a mock Claude script.
"""

import os
from dataclasses import dataclass

import pytest
from git import Repo

from conftest import (
    create_mock_claude_script_that_marks_tasks_complete,
    run_script,
    write_plan_file,
)
from i2code.plan_domain.parser import parse as parse_plan

IDEA_NAME = "test-feature"
THREADS = [1, 2, 3]
TASKS_PER_THREAD = 2


@dataclass
class ThreeThreadIdea:
    tmpdir: str
    idea_dir: str
    plan_path: str
    repo: Repo


def _create_three_thread_idea(tmpdir, repo, completed_threads):
    idea_dir = os.path.join(tmpdir, IDEA_NAME)
    os.makedirs(idea_dir)

    for suffix in ["idea", "spec"]:
        with open(os.path.join(idea_dir, f"{IDEA_NAME}-{suffix}.md"), "w") as f:
            f.write(f"# Test Feature {suffix}\n")

    tasks = [(thread, task, f"Task {thread}.{task} title", thread in completed_threads)
             for thread in THREADS
             for task in range(1, TASKS_PER_THREAD + 1)]
    plan_path = write_plan_file(idea_dir, IDEA_NAME, tasks)

    repo.git.add(IDEA_NAME)
    repo.index.commit("Add test-feature idea")

    return ThreeThreadIdea(tmpdir=tmpdir, idea_dir=idea_dir, plan_path=plan_path, repo=repo)


@pytest.fixture
def three_thread_idea(test_git_repo_with_commit):
    """A committed idea directory whose plan has three threads of two incomplete tasks."""
    tmpdir, repo = test_git_repo_with_commit
    return _create_three_thread_idea(tmpdir, repo, completed_threads=[])


@pytest.fixture
def three_thread_idea_with_last_thread_incomplete(test_git_repo_with_commit):
    """A committed idea directory whose plan has threads 1 and 2 complete and thread 3 incomplete."""
    tmpdir, repo = test_git_repo_with_commit
    return _create_three_thread_idea(tmpdir, repo, completed_threads=[1, 2])


def _completion_by_thread(plan_path):
    with open(plan_path) as f:
        plan = parse_plan(f.read())
    return {thread_number: [task.is_completed for task in thread.tasks]
            for thread_number, thread in enumerate(plan.threads, 1)}


def _lines_in_order(stdout, expected_line_endings):
    """True when consecutive stdout lines end with the expected texts."""
    lines = stdout.splitlines()
    count = len(expected_line_endings)
    return any(
        all(line.endswith(text) for line, text in zip(lines[i:i + count], expected_line_endings))
        for i in range(len(lines) - count + 1)
    )


def _commit_count(repo):
    return int(repo.git.rev_list("--count", "HEAD"))


@pytest.mark.integration
class TestRunSelectedThread:

    def test_runs_only_selected_thread_and_names_next_thread(self, three_thread_idea, tmp_path):
        idea = three_thread_idea
        script = create_mock_claude_script_that_marks_tasks_complete(str(tmp_path), IDEA_NAME)
        commits_before = _commit_count(idea.repo)

        result = run_script(idea.idea_dir, cwd=idea.tmpdir,
                            extra_args=["--mock-claude", script, "--trunk", "--thread", "1"])

        assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert _completion_by_thread(idea.plan_path) == {
            1: [True, True],
            2: [False, False],
            3: [False, False],
        }
        assert _commit_count(idea.repo) - commits_before == TASKS_PER_THREAD
        assert _lines_in_order(result.stdout, [
            "Thread 1 (Thread 1) is complete.",
            f"Next: i2code implement --trunk --thread 2 {idea.idea_dir}",
        ]), result.stdout

    def test_last_thread_reports_all_tasks_completed(self, three_thread_idea_with_last_thread_incomplete,
                                                     tmp_path):
        idea = three_thread_idea_with_last_thread_incomplete
        script = create_mock_claude_script_that_marks_tasks_complete(str(tmp_path), IDEA_NAME)

        result = run_script(idea.idea_dir, cwd=idea.tmpdir,
                            extra_args=["--mock-claude", script, "--trunk", "--thread", "3"])

        assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert _completion_by_thread(idea.plan_path) == {
            1: [True, True],
            2: [True, True],
            3: [True, True],
        }
        assert "All tasks completed!" in result.stdout
        assert "Thread 3 (Thread 3) is complete." not in result.stdout
        assert "Next:" not in result.stdout


def _worktree_dir(repo_dir):
    return f"{repo_dir}-wt-{IDEA_NAME}"


@pytest.mark.integration
class TestThreadRequiresTrunk:

    @pytest.mark.parametrize("extra_args", [
        ["--thread", "2"],
        ["--isolate", "--thread", "2"],
        ["--shell", "--thread", "2"],
    ])
    def test_thread_without_trunk_is_usage_error_before_setup(self, three_thread_idea, extra_args):
        idea = three_thread_idea

        result = run_script(idea.idea_dir, cwd=idea.tmpdir, extra_args=extra_args)

        assert result.returncode == 2, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert "Error: --thread requires --trunk" in result.stderr
        assert f"idea/{IDEA_NAME}" not in [head.name for head in idea.repo.heads]
        assert not os.path.exists(_worktree_dir(idea.tmpdir))


def _read_file(path):
    with open(path) as f:
        return f.read()


@pytest.mark.integration
class TestThreadOutOfRange:

    @pytest.mark.parametrize("thread", ["4", "0"])
    def test_out_of_range_thread_is_usage_error_naming_valid_range(self, three_thread_idea, tmp_path, thread):
        idea = three_thread_idea
        script = create_mock_claude_script_that_marks_tasks_complete(str(tmp_path), IDEA_NAME)
        head_before = idea.repo.head.commit.hexsha
        plan_before = _read_file(idea.plan_path)

        result = run_script(idea.idea_dir, cwd=idea.tmpdir,
                            extra_args=["--mock-claude", script, "--trunk", "--thread", thread])

        assert result.returncode == 2, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert "Error: --thread must be between 1 and 3" in result.stderr
        assert idea.repo.head.commit.hexsha == head_before
        assert _read_file(idea.plan_path) == plan_before


@pytest.mark.integration
class TestThreadOrder:

    @pytest.mark.parametrize("completed_threads, incomplete_threads", [
        ([], "1, 2"),
        ([1], "2"),
    ])
    def test_thread_with_incomplete_earlier_threads_is_error_naming_them(
            self, test_git_repo_with_commit, tmp_path, completed_threads, incomplete_threads):
        tmpdir, repo = test_git_repo_with_commit
        idea = _create_three_thread_idea(tmpdir, repo, completed_threads=completed_threads)
        script = create_mock_claude_script_that_marks_tasks_complete(str(tmp_path), IDEA_NAME)
        head_before = idea.repo.head.commit.hexsha
        plan_before = _read_file(idea.plan_path)

        result = run_script(idea.idea_dir, cwd=idea.tmpdir,
                            extra_args=["--mock-claude", script, "--trunk", "--thread", "3"])

        assert result.returncode == 1, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert (f"Error: Cannot run thread 3: earlier threads have incomplete tasks: {incomplete_threads}"
                in result.stderr)
        assert idea.repo.head.commit.hexsha == head_before
        assert _read_file(idea.plan_path) == plan_before


@pytest.mark.integration
class TestThreadAlreadyComplete:

    def test_already_complete_thread_is_reported_and_names_next_thread(
            self, three_thread_idea_with_last_thread_incomplete, tmp_path):
        idea = three_thread_idea_with_last_thread_incomplete
        script = create_mock_claude_script_that_marks_tasks_complete(str(tmp_path), IDEA_NAME)
        head_before = idea.repo.head.commit.hexsha
        plan_before = _read_file(idea.plan_path)

        result = run_script(idea.idea_dir, cwd=idea.tmpdir,
                            extra_args=["--mock-claude", script, "--trunk", "--thread", "2"])

        assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert _lines_in_order(result.stdout, [
            "Thread 2 (Thread 2) is already complete.",
            f"Next: i2code implement --trunk --thread 3 {idea.idea_dir}",
        ]), result.stdout
        assert idea.repo.head.commit.hexsha == head_before
        assert _read_file(idea.plan_path) == plan_before


def _assert_trunk_dry_run_succeeds_printing(idea, extra_args, trailing_lines):
    result = run_script(idea.idea_dir, cwd=idea.tmpdir, extra_args=["--dry-run", "--trunk", *extra_args])

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert _lines_in_order(result.stdout, [
        "Mode: trunk",
        f"Idea: {IDEA_NAME}",
        f"Directory: {idea.idea_dir}",
        *trailing_lines,
    ]), result.stdout
    return result


@pytest.mark.integration
class TestThreadDryRun:

    def test_dry_run_prints_selected_thread_without_range_check(self, three_thread_idea):
        _assert_trunk_dry_run_succeeds_printing(three_thread_idea, ["--thread", "5"], ["Thread: 5"])

    def test_dry_run_thread_without_trunk_is_usage_error(self, three_thread_idea):
        idea = three_thread_idea

        result = run_script(idea.idea_dir, cwd=idea.tmpdir, extra_args=["--dry-run", "--thread", "5"])

        assert result.returncode == 2, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        assert "Error: --thread requires --trunk" in result.stderr

    def test_dry_run_without_thread_prints_no_thread_line(self, three_thread_idea):
        result = _assert_trunk_dry_run_succeeds_printing(three_thread_idea, [], [])

        assert "Thread:" not in result.stdout
