"""Tests for the task selections that TrunkMode iterates over."""

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
