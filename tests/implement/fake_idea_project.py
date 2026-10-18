"""FakeIdeaProject: test double for IdeaProject.

Separated into its own module so tests can import it unambiguously
regardless of pytest's conftest resolution order.
"""

import os


class FakeIdeaProject:
    """Test double for IdeaProject that returns canned responses."""

    def __init__(self, name="test-feature", directory="/tmp/fake-idea"):
        self._name = name
        self._directory = directory
        self._idea_files = []
        self._worktree_project = None
        self._next_task = None
        self._threads = {}

    @property
    def name(self):
        return self._name

    @property
    def directory(self):
        return self._directory

    @property
    def plan_file(self):
        return os.path.join(self._directory, f"{self._name}-plan.md")

    @property
    def state_file(self):
        return os.path.join(self._directory, f"{self._name}-wt-state.json")

    def validate(self):
        return self

    def validate_files(self):
        return None

    def find_idea_files(self):
        return self._idea_files

    def set_idea_files(self, files):
        self._idea_files = files

    def find_missing_files(self):
        return []

    def worktree_idea_project(self, worktree_path, main_repo_root):
        if self._worktree_project is not None:
            return self._worktree_project
        idea_relpath = os.path.relpath(self._directory, main_repo_root)
        return FakeIdeaProject(
            name=self._name,
            directory=os.path.join(worktree_path, idea_relpath),
        )

    def set_worktree_project(self, project):
        self._worktree_project = project

    def set_next_task(self, task):
        self._next_task = task

    def get_next_task(self):
        return self._next_task

    def set_thread(self, thread, title, next_task):
        self._threads[thread] = (title, next_task)

    def get_next_task_in_thread(self, thread):
        return self._threads[thread][1]

    def thread_title(self, thread):
        return self._threads[thread][0]

    def thread_count(self):
        return max(self._threads, default=0)

    def incomplete_threads_before(self, thread):
        return [number for number, (_, next_task) in sorted(self._threads.items())
                if number < thread and next_task is not None]
