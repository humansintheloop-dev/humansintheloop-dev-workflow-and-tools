"""Task selections: which plan tasks TrunkMode runs and how it reports completion."""

import click

from i2code.implement.console import print_message


def _report_all_tasks_completed():
    print_message("All tasks completed!")


class AllTasksSelection:
    """Selects every incomplete task in the plan."""

    def __init__(self, project):
        self._project = project

    def validate(self):
        pass

    def next_task(self):
        return self._project.get_next_task()

    def report_completion(self):
        _report_all_tasks_completed()


class ThreadSelection:
    """Selects the incomplete tasks of one thread."""

    def __init__(self, project, thread, idea_directory):
        self._project = project
        self._thread = thread
        self._idea_directory = idea_directory

    def validate(self):
        thread_count = self._project.thread_count()
        if not 1 <= self._thread <= thread_count:
            raise click.UsageError(f"--thread must be between 1 and {thread_count}")

    def next_task(self):
        return self._project.get_next_task_in_thread(self._thread)

    def report_completion(self):
        next_task = self._project.get_next_task()
        if next_task is None:
            _report_all_tasks_completed()
            return
        title = self._project.thread_title(self._thread)
        print_message(f"Thread {self._thread} ({title}) is complete.")
        print_message(f"Next: i2code implement --trunk --thread {next_task.number.thread} {self._idea_directory}")
