"""Workspace: bundles a git repository and idea project."""

from dataclasses import dataclass

from i2code.implement.git_repository import GitRepository
from i2code.implement.idea_project import IdeaProject


@dataclass
class Workspace:
    """A git repository and the idea project being implemented in it."""

    git_repo: GitRepository
    project: IdeaProject
