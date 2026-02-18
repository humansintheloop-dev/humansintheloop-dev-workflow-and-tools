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

    def get_next_task(self):
        return None
