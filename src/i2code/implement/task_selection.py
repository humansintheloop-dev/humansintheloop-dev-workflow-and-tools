"""Task selections: which plan tasks TrunkMode runs and how it reports completion."""

from i2code.implement.console import print_message


class AllTasksSelection:
    """Selects every incomplete task in the plan."""

    def __init__(self, project):
        self._project = project

    def validate(self):
        pass

    def next_task(self):
        return self._project.get_next_task()

    def report_completion(self):
        print_message("All tasks completed!")


class ThreadSelection:
    """Selects the incomplete tasks of one thread."""

    def __init__(self, project, thread, idea_directory):
        self._project = project
        self._thread = thread
        self._idea_directory = idea_directory

    def validate(self):
        pass

    def next_task(self):
        return self._project.get_next_task_in_thread(self._thread)

    def report_completion(self):
        title = self._project.thread_title(self._thread)
        print_message(f"Thread {self._thread} ({title}) is complete.")
        next_thread = self._project.get_next_task().number.thread
        print_message(f"Next: i2code implement --trunk --thread {next_thread} {self._idea_directory}")
