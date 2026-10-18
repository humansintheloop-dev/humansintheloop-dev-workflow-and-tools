"""Tests for the task selections that TrunkMode iterates over."""

import click
import pytest

from i2code.implement.task_selection import AllTasksSelection, ThreadSelection
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task

from fake_idea_project import FakeIdeaProject


def _numbered_task(thread, task):
    return NumberedTask(
        number=TaskNumber(thread=thread, task=task),
        task=Task(_lines=[f'- [ ] **Task {thread}.{task}: Task {thread}.{task}**']),
    )


@pytest.mark.unit
class TestAllTasksSelection:

    def test_next_task_returns_projects_next_task(self):
        project = FakeIdeaProject()
        next_task = _numbered_task(2, 1)
        project.set_next_task(next_task)

        assert AllTasksSelection(project).next_task() is next_task

    def test_report_completion_prints_all_tasks_completed(self, capsys):
        AllTasksSelection(FakeIdeaProject()).report_completion()

        assert "All tasks completed!" in capsys.readouterr().out


@pytest.mark.unit
class TestThreadSelection:

    def test_next_task_returns_next_task_in_selected_thread(self):
        project = FakeIdeaProject()
        thread_task = _numbered_task(2, 1)
        project.set_thread(2, "Feature", thread_task)
        project.set_next_task(_numbered_task(1, 1))

        assert ThreadSelection(project, 2, "/ideas/x").next_task() is thread_task

    def test_report_completion_names_next_incomplete_thread(self, capsys):
        project = FakeIdeaProject()
        project.set_thread(1, "Setup", None)
        project.set_next_task(_numbered_task(3, 1))

        ThreadSelection(project, 1, "/ideas/x").report_completion()

        lines = capsys.readouterr().out.splitlines()
        assert lines[0].endswith("Thread 1 (Setup) is complete.")
        assert lines[1].endswith("Next: i2code implement --trunk --thread 3 /ideas/x")

    def test_report_completion_prints_only_all_tasks_completed_when_no_tasks_remain(self, capsys):
        project = FakeIdeaProject()
        project.set_thread(3, "Finish", None)
        project.set_next_task(None)

        ThreadSelection(project, 3, "/ideas/x").report_completion()

        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1
        assert lines[0].endswith("All tasks completed!")

    @pytest.mark.parametrize("thread", [0, 4])
    def test_validate_rejects_thread_outside_plan(self, thread):
        project = FakeIdeaProject()
        for thread_number in [1, 2, 3]:
            project.set_thread(thread_number, f"Thread {thread_number}", None)

        with pytest.raises(click.UsageError, match="^--thread must be between 1 and 3$"):
            ThreadSelection(project, thread, "/ideas/x").validate()

    def test_validate_exits_when_earlier_threads_are_incomplete(self, capsys):
        project = FakeIdeaProject()
        for thread_number in [1, 2, 3]:
            project.set_thread(thread_number, f"Thread {thread_number}", _numbered_task(thread_number, 1))

        with pytest.raises(SystemExit) as exit_info:
            ThreadSelection(project, 3, "/ideas/x").validate()

        assert exit_info.value.code == 1
        assert capsys.readouterr().err == (
            "Error: Cannot run thread 3: earlier threads have incomplete tasks: 1, 2\n")
