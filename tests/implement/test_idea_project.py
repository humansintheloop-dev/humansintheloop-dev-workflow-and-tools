"""Tests for IdeaProject value object."""

import os

import pytest

from conftest import TempIdeaProject
from i2code.implement.idea_project import IdeaProject


PLAN_WITH_UNCOMPLETED_TASK = """\
# Implementation Plan

## Steel Thread 1: Setup

- [ ] **Task 1.1: Create project structure**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Project compiles
  - Evidence: `pytest`
  - Steps:
    - [ ] Create directory layout
"""

PLAN_ALL_COMPLETED = """\
# Implementation Plan

## Steel Thread 1: Setup

- [x] **Task 1.1: Create project structure**
  - TaskType: code
  - Entrypoint: `src/main.py`
  - Observable: Project compiles
  - Evidence: `pytest`
  - Steps:
    - [x] Create directory layout
"""


def _make_project_with_plan(tmp_path, plan_content):
    """Create an IdeaProject whose plan_file contains the given content."""
    idea_name = "test"
    idea_dir = tmp_path / idea_name
    idea_dir.mkdir()
    plan_file = idea_dir / f"{idea_name}-plan.md"
    plan_file.write_text(plan_content)
    return IdeaProject(str(idea_dir))


@pytest.mark.unit
class TestIdeaProjectConstruction:
    """Test constructing IdeaProject from a directory path."""

    def test_name_extracted_from_directory_basename(self):
        """IdeaProject.name should be the last component of the directory path."""
        with TempIdeaProject("my-feature") as project:
            assert project.name == "my-feature"

    def test_directory_is_stored(self):
        """IdeaProject.directory should return the directory path."""
        with TempIdeaProject("my-feature") as project:
            assert project.directory.endswith("my-feature")

    def test_plan_file_path(self):
        """IdeaProject.plan_file should return <dir>/<name>-plan.md."""
        with TempIdeaProject("my-feature") as project:
            assert project.plan_file == os.path.join(
                project.directory, "my-feature-plan.md"
            )

    def test_state_file_path(self):
        """IdeaProject.state_file should return <dir>/<name>-wt-state.json."""
        with TempIdeaProject("my-feature") as project:
            assert project.state_file == os.path.join(
                project.directory, "my-feature-wt-state.json"
            )


@pytest.mark.unit
class TestIdeaProjectValidation:
    """Test IdeaProject.validate() method."""

    def test_validate_nonexistent_directory_raises_error(self):
        """validate() should raise SystemExit for non-existent directory."""
        from i2code.implement.idea_project import IdeaProject

        project = IdeaProject("/nonexistent/path/to/idea")

        with pytest.raises(SystemExit) as exc_info:
            project.validate()

        assert exc_info.value.code != 0

    def test_validate_existing_directory_returns_self(self):
        """validate() should return self when directory exists."""
        with TempIdeaProject("my-feature") as project:
            result = project.validate()

            assert result is project


@pytest.mark.unit
class TestIdeaProjectValidateFiles:
    """Test IdeaProject.validate_files() method."""

    def test_validate_files_missing_all_raises_error(self):
        """validate_files() should raise SystemExit when all files missing."""
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit) as exc_info:
                project.validate_files()

            assert exc_info.value.code != 0

    def test_validate_files_lists_missing_files(self, capsys):
        """Error message should list which files are missing."""
        with TempIdeaProject("my-feature") as project:
            # Create only the idea file
            with open(os.path.join(project.directory, "my-feature-idea.md"), "w") as f:
                f.write("# My Feature Idea")

            with pytest.raises(SystemExit):
                project.validate_files()

            captured = capsys.readouterr()
            assert "discussion" in captured.err.lower()
            assert "spec" in captured.err.lower()
            assert "plan" in captured.err.lower()

    def test_validate_files_all_present_succeeds(self):
        """validate_files() should succeed when all files exist."""
        with TempIdeaProject("my-feature") as project:
            for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
                with open(
                    os.path.join(project.directory, f"my-feature-{suffix}"), "w"
                ) as f:
                    f.write(f"# {suffix}")

            project.validate_files()  # Should not raise

    def test_validate_files_accepts_txt_idea(self):
        """validate_files() should accept .txt extension for idea file."""
        with TempIdeaProject("my-feature") as project:
            with open(
                os.path.join(project.directory, "my-feature-idea.txt"), "w"
            ) as f:
                f.write("My Feature Idea")
            for suffix in ["discussion.md", "spec.md", "plan.md"]:
                with open(
                    os.path.join(project.directory, f"my-feature-{suffix}"), "w"
                ) as f:
                    f.write(f"# {suffix}")

            project.validate_files()  # Should not raise


@pytest.mark.unit
class TestGetNextTask:

    def test_returns_numbered_task_for_first_uncompleted(self, tmp_path):
        project = _make_project_with_plan(tmp_path, PLAN_WITH_UNCOMPLETED_TASK)

        result = project.get_next_task()

        assert result is not None
        assert result.number.thread == 1
        assert result.number.task == 1
        assert result.task.title == "Create project structure"

    def test_returns_none_when_all_complete(self, tmp_path):
        project = _make_project_with_plan(tmp_path, PLAN_ALL_COMPLETED)

        result = project.get_next_task()

        assert result is None


@pytest.mark.unit
class TestIsTaskCompleted:

    def test_completed_task_returns_true(self, tmp_path):
        project = _make_project_with_plan(tmp_path, PLAN_ALL_COMPLETED)

        assert project.is_task_completed(thread=1, task=1) is True

    def test_uncompleted_task_returns_false(self, tmp_path):
        project = _make_project_with_plan(tmp_path, PLAN_WITH_UNCOMPLETED_TASK)

        assert project.is_task_completed(thread=1, task=1) is False


@pytest.mark.unit
class TestWorktreeIdeaDirectory:
    """Test that Claude is invoked with worktree idea directory, not main repo."""

    def test_worktree_idea_project(self):
        """Should return an IdeaProject for the path within the worktree."""
        project = IdeaProject("/home/user/my-repo/docs/ideas/my-feature")

        result = project.worktree_idea_project(
            "/tmp/my-repo-wt-my-feature",
            "/home/user/my-repo",
        )

        assert isinstance(result, IdeaProject)
        assert result.directory == "/tmp/my-repo-wt-my-feature/docs/ideas/my-feature"
