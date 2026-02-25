"""Workspace: bundles a git repository and idea project."""

from dataclasses import dataclass


@dataclass
class Workspace:
    """A git repository and the idea project being implemented in it."""

    git_repo: object
    project: object
