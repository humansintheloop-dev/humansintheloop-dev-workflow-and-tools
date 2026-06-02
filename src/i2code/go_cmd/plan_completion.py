"""Resolve the plan-file text that the implement subprocess actually edited.

The orchestrator's post-implement check needs to read the plan file from the
location that the implement subprocess wrote to (main repo, worktree sibling,
clone sibling, or PR branch). This module centralises that resolution so the
orchestrator can stay focused on banner logic.
"""

from pathlib import Path
from typing import Any, Callable

from i2code.implement.git_repository import GitRepository
from i2code.implement.idea_project import IdeaProject


sibling_path = GitRepository._sibling_path


def _is_worktree_pr_mode(config: dict[str, Any] | None) -> bool:
    if config is None:
        return False
    return not config["trunk"] and config["isolation_type"] == "none"


def _is_host_clone_mode(config: dict[str, Any] | None) -> bool:
    if config is None:
        return False
    return not config["trunk"] and config["isolation_type"] in ("nono", "container")


def _read_sibling_plan_text(
    project: IdeaProject, git_root: str, suffix: str,
) -> str:
    sibling = sibling_path(git_root, suffix, project.name)
    sibling_project = project.worktree_idea_project(sibling, git_root)
    return Path(sibling_project.plan_file).read_text(encoding="utf-8")


def resolve_plan_text(
    project: IdeaProject,
    config: dict[str, Any] | None,
    git_root: str,
    *,
    gh_runner: Callable[..., Any] | None = None,
) -> str | None:
    """Return the plan file's text for the mode recorded in `config`.

    Worktree+PR mode (`trunk=false`, `isolation_type=none`) reads the plan
    file at `<git-parent>/<repo>-wt-<idea>/<idea-relpath>/<idea>-plan.md`.
    Host clone isolation (`trunk=false`, `isolation_type` in `nono`/`container`)
    reads the host clone sibling at
    `<git-parent>/<repo>-cl-<idea>/<idea-relpath>/<idea>-plan.md`.
    Trunk mode (`trunk=true`) and missing config both read the main repo's
    plan file directly. Other branches will be added by subsequent steel
    threads.
    """
    if _is_worktree_pr_mode(config):
        return _read_sibling_plan_text(project, git_root, "wt")
    if _is_host_clone_mode(config):
        return _read_sibling_plan_text(project, git_root, "cl")
    if config is None or config["trunk"]:
        return Path(project.plan_file).read_text(encoding="utf-8")
    return None
