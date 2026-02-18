"""IdeaProject value object: encapsulates idea directory, name, and derived paths."""

import glob
import os
import sys

from i2code.plan.plan_file_io import with_plan_file


class IdeaProject:
    """Value object representing an idea project directory.

    Encapsulates the (idea_directory, idea_name) pair and derived paths
    like plan_file and state_file.
    """

    def __init__(self, directory: str):
        self._directory = directory
        self._name = os.path.basename(os.path.normpath(directory))

    @property
    def directory(self) -> str:
        return self._directory

    @property
    def name(self) -> str:
        return self._name

    @property
    def plan_file(self) -> str:
        return os.path.join(self._directory, f"{self._name}-plan.md")

    @property
    def state_file(self) -> str:
        return os.path.join(self._directory, f"{self._name}-wt-state.json")

    def validate(self) -> "IdeaProject":
        """Validate that the idea directory exists.

        Returns:
            self, for method chaining

        Raises:
            SystemExit: If the directory does not exist
        """
        if not os.path.isdir(self._directory):
            print(f"Error: Directory not found: {self._directory}", file=sys.stderr)
            sys.exit(1)
        return self

    @property
    def file_patterns(self) -> list[str]:
        """Glob patterns for all idea files in this project."""
        return [
            f"{self._name}-idea.*",
            f"{self._name}-discussion.md",
            f"{self._name}-spec.md",
            f"{self._name}-plan.md",
        ]

    def find_idea_files(self) -> list[str]:
        """Return absolute paths of all idea files found in the directory."""
        files = []
        for pattern in self.file_patterns:
            files.extend(glob.glob(os.path.join(self._directory, pattern)))
        return files

    def find_missing_files(self) -> list[str]:
        """Return list of required idea files that are missing from the directory."""
        missing = []

        idea_pattern = os.path.join(self._directory, f"{self._name}-idea.*")
        if not glob.glob(idea_pattern):
            missing.append(f"{self._name}-idea.md (or .txt)")

        for suffix in ["discussion.md", "spec.md", "plan.md"]:
            filepath = os.path.join(self._directory, f"{self._name}-{suffix}")
            if not os.path.isfile(filepath):
                missing.append(f"{self._name}-{suffix}")

        return missing

    def worktree_idea_project(self, worktree_path: str, main_repo_root: str) -> "IdeaProject":
        """Return an IdeaProject for the corresponding path within a worktree."""
        idea_relpath = os.path.relpath(self._directory, main_repo_root)
        return IdeaProject(os.path.join(worktree_path, idea_relpath))

    def get_next_task(self):
        with with_plan_file(self.plan_file) as plan:
            return plan.get_next_task()

    def is_task_completed(self, thread: int, task: int) -> bool:
        with with_plan_file(self.plan_file) as plan:
            return plan.is_task_completed(thread, task)

    def validate_files(self) -> None:
        """Validate that all required idea files exist.

        Raises:
            SystemExit: If any required files are missing
        """
        missing_files = self.find_missing_files()
        if missing_files:
            print(
                f"Error: Missing required idea files in {self._directory}:",
                file=sys.stderr,
            )
            for f in missing_files:
                print(f"  - {f}", file=sys.stderr)
            sys.exit(1)
