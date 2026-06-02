"""Resolve the plan-file text that the implement subprocess actually edited.

The orchestrator's post-implement check needs to read the plan file from the
location that the implement subprocess wrote to (main repo, worktree sibling,
clone sibling, or PR branch). This module centralises that resolution so the
orchestrator can stay focused on banner logic.
"""

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TextIO

from i2code.implement.git_repository import GitRepository
from i2code.implement.idea_project import IdeaProject


sibling_path = GitRepository._sibling_path


@dataclass
class ResolverDeps:
    """Injectable IO for `resolve_plan_text` — currently used by the VM branch."""

    gh_runner: Callable[..., Any] | None = None
    output: TextIO | None = None


def _is_worktree_pr_mode(config: dict[str, Any] | None) -> bool:
    if config is None:
        return False
    return not config["trunk"] and config["isolation_type"] == "none"


def _is_host_clone_mode(config: dict[str, Any] | None) -> bool:
    if config is None:
        return False
    return not config["trunk"] and config["isolation_type"] in ("nono", "container")


def _is_vm_mode(config: dict[str, Any] | None) -> bool:
    if config is None:
        return False
    return not config["trunk"] and config["isolation_type"] == "vm"


def _read_sibling_plan_text(
    project: IdeaProject, git_root: str, suffix: str,
) -> str:
    sibling = sibling_path(git_root, suffix, project.name)
    sibling_project = project.worktree_idea_project(sibling, git_root)
    return Path(sibling_project.plan_file).read_text(encoding="utf-8")


def derive_origin_owner_repo(git_root: str) -> str:
    """Return `<owner>/<repo>` parsed from the `origin` remote of `git_root`.

    Reads the origin URL with `git -C <git_root> remote get-url origin`
    (read-only inspection) and accepts both `https://github.com/<owner>/<repo>(.git)`
    and `git@github.com:<owner>/<repo>(.git)` URL forms.
    """
    result = subprocess.run(
        ["git", "-C", git_root, "remote", "get-url", "origin"],
        capture_output=True, text=True, check=True,
    )
    url = result.stdout.strip()
    if url.endswith(".git"):
        url = url[:-len(".git")]
    if url.startswith("git@"):
        _, _, path = url.partition(":")
    else:
        _, _, path = url.partition("://")
        _, _, path = path.partition("/")
    return path


def _read_vm_plan_text(
    project: IdeaProject,
    git_root: str,
    gh_runner: Callable[..., Any],
    output: TextIO | None,
) -> str | None:
    owner_repo = derive_origin_owner_repo(git_root)
    idea_relpath = os.path.relpath(project.directory, git_root)
    content_path = f"{idea_relpath}/{project.name}-plan.md"
    api_path = (
        f"repos/{owner_repo}/contents/{content_path}"
        f"?ref=idea/{project.name}"
    )
    argv = [
        "gh", "api", api_path,
        "-H", "Accept: application/vnd.github.raw",
    ]
    try:
        result = gh_runner(argv)
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        _emit_gh_failure(output, str(exc))
        return None
    if result.returncode != 0:
        _emit_gh_failure(output, _first_non_empty_line(result.stderr))
        return None
    return result.stdout


def _first_non_empty_line(text: str | None) -> str:
    if not text:
        return ""
    for line in text.splitlines():
        if line.strip():
            return line
    return ""


def _emit_gh_failure(output: TextIO | None, reason: str) -> None:
    if output is None:
        return
    print(f"Could not check plan completion: {reason}", file=output)


def _default_gh_runner(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def resolve_plan_text(
    project: IdeaProject,
    config: dict[str, Any] | None,
    git_root: str,
    deps: ResolverDeps | None = None,
) -> str | None:
    """Return the plan file's text for the mode recorded in `config`.

    Worktree+PR mode (`trunk=false`, `isolation_type=none`) reads the plan
    file at `<git-parent>/<repo>-wt-<idea>/<idea-relpath>/<idea>-plan.md`.
    Host clone isolation (`trunk=false`, `isolation_type` in `nono`/`container`)
    reads the host clone sibling at
    `<git-parent>/<repo>-cl-<idea>/<idea-relpath>/<idea>-plan.md`.
    VM isolation (`trunk=false`, `isolation_type=vm`) fetches the plan file
    from the `idea/<name>` branch on `origin` via `gh api`. If the `gh`
    invocation raises or returns a non-zero exit, a single
    `Could not check plan completion: <reason>` line is written to `output`
    and `None` is returned so the caller suppresses both banners.
    Trunk mode (`trunk=true`) and missing config both read the main repo's
    plan file directly.
    """
    if _is_worktree_pr_mode(config):
        return _read_sibling_plan_text(project, git_root, "wt")
    if _is_host_clone_mode(config):
        return _read_sibling_plan_text(project, git_root, "cl")
    if _is_vm_mode(config):
        effective = deps if deps is not None else ResolverDeps()
        runner = effective.gh_runner if effective.gh_runner is not None else _default_gh_runner
        return _read_vm_plan_text(project, git_root, runner, effective.output)
    if config is None or config["trunk"]:
        return Path(project.plan_file).read_text(encoding="utf-8")
    return None
