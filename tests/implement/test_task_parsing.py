"""Tests for task parsing from plan files in implement-with-worktree."""

import os
import tempfile
import pytest


@pytest.mark.unit
class TestTaskParsing:
    """Test parsing tasks from plan files."""

    def test_parse_uncompleted_tasks(self):
        """Should extract uncompleted tasks from plan file."""
        from i2code.implement.implement import parse_tasks_from_plan

        plan_content = """# Implementation Plan

## Steel Thread 1

- [ ] **Task 1.1: First task**
  - [ ] Subtask A
  - [ ] Subtask B

- [x] **Task 1.2: Completed task**
  - [x] Done

- [ ] **Task 1.3: Another task**
"""
        tasks = parse_tasks_from_plan(plan_content)

        assert len(tasks) == 2
        assert "Task 1.1: First task" in tasks[0]
        assert "Task 1.3: Another task" in tasks[1]

    def test_parse_skips_completed_tasks(self):
        """Should skip tasks marked with [x]."""
        from i2code.implement.implement import parse_tasks_from_plan

        plan_content = """
- [x] **Task 1: Done**
- [ ] **Task 2: Not done**
- [x] **Task 3: Also done**
"""
        tasks = parse_tasks_from_plan(plan_content)

        assert len(tasks) == 1
        assert "Task 2" in tasks[0]

    def test_parse_returns_tasks_in_order(self):
        """Tasks should be returned in document order."""
        from i2code.implement.implement import parse_tasks_from_plan

        plan_content = """
- [ ] **Task A**
- [ ] **Task B**
- [ ] **Task C**
"""
        tasks = parse_tasks_from_plan(plan_content)

        assert len(tasks) == 3
        assert "Task A" in tasks[0]
        assert "Task B" in tasks[1]
        assert "Task C" in tasks[2]

    def test_parse_empty_plan(self):
        """Should return empty list for plan with no tasks."""
        from i2code.implement.implement import parse_tasks_from_plan

        plan_content = """# Empty Plan

Just some text, no tasks.
"""
        tasks = parse_tasks_from_plan(plan_content)

        assert tasks == []

    def test_parse_all_completed(self):
        """Should return empty list when all tasks are completed."""
        from i2code.implement.implement import parse_tasks_from_plan

        plan_content = """
- [x] **Task 1**
- [x] **Task 2**
"""
        tasks = parse_tasks_from_plan(plan_content)

        assert tasks == []

    def test_parse_extracts_task_title(self):
        """Should extract the task title without markdown formatting."""
        from i2code.implement.implement import parse_tasks_from_plan

        plan_content = """
- [ ] **Task 1.1: Create the config file**
"""
        tasks = parse_tasks_from_plan(plan_content)

        assert len(tasks) == 1
        # Should contain the task text
        assert "Task 1.1: Create the config file" in tasks[0]


@pytest.mark.unit
class TestGetFirstTaskName:
    """Test extracting the first task name for slice naming."""

    def test_get_first_task_name(self):
        """Should extract name from first uncompleted task."""
        from i2code.implement.implement import get_first_task_name

        plan_content = """
- [x] **Task 1.1: Completed**
- [ ] **Task 1.2: Project Setup**
- [ ] **Task 1.3: Another task**
"""
        name = get_first_task_name(plan_content)
        assert "project" in name.lower() or "setup" in name.lower()

    def test_get_first_task_name_empty_returns_default(self):
        """Should return default name if no tasks."""
        from i2code.implement.implement import get_first_task_name

        plan_content = """# No tasks"""
        name = get_first_task_name(plan_content)
        assert name == "implementation"
