"""Task selections: which plan tasks TrunkMode runs and how it reports completion."""

import sys

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

    def is_already_complete(self):
        return False

    def next_task(self):
        return self._project.get_next_task()

    def report_completion(self):
        _report_all_tasks_completed()

    def report_already_complete(self):
        _report_all_tasks_completed()


class ThreadSelection:
    """Selects the incomplete tasks of one thread."""

    def __init__(self, project, thread, idea_directory):
        self._project = project
        self._thread = thread
        self._idea_directory = idea_directory

    def validate(self):
        self._validate_thread_in_range()
        self._validate_earlier_threads_complete()

    def _validate_thread_in_range(self):
        thread_count = self._project.thread_count()
        if not 1 <= self._thread <= thread_count:
            raise click.UsageError(f"--thread must be between 1 and {thread_count}")

    def _validate_earlier_threads_complete(self):
        incomplete_threads = self._project.incomplete_threads_before(self._thread)
        if incomplete_threads:
            thread_list = ", ".join(str(thread) for thread in incomplete_threads)
            print(f"Error: Cannot run thread {self._thread}: earlier threads have incomplete tasks: {thread_list}",
                  file=sys.stderr)
            sys.exit(1)

    def is_already_complete(self):
        return self.next_task() is None

    def next_task(self):
        return self._project.get_next_task_in_thread(self._thread)

    def report_completion(self):
        if self._project.get_next_task() is None:
            _report_all_tasks_completed()
            return
        print_message(f"Thread {self._thread} ({self._title()}) is complete.")
        self._report_next_thread()

    def report_already_complete(self):
        print_message(f"Thread {self._thread} ({self._title()}) is already complete.")
        self._report_next_thread()

    def _title(self):
        return self._project.thread_title(self._thread)

    def _report_next_thread(self):
        next_task = self._project.get_next_task()
        if next_task is None:
            _report_all_tasks_completed()
            return
        print_message(f"Next: i2code implement --trunk --thread {next_task.number.thread} {self._idea_directory}")
