"""Tests for HAS_PLAN menu lifecycle move options based on idea state."""

import os
from contextlib import contextmanager
import tempfile
from unittest.mock import MagicMock

import pytest

from conftest import menu_config_by_label
from i2code.go_cmd.orchestrator import (
    COMMIT_CHANGES, EXIT, Orchestrator, OrchestratorDeps,
)
from i2code.implement.idea_project import IdeaProject


MOVE_TO_READY = "Move idea to ready"
MOVE_TO_WIP = "Move idea to wip"


@contextmanager
def _lifecycle_project(name, state):
    """Create a TempIdeaProject whose path contains docs/ideas/{state}/{name}."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, "docs", "ideas", state, name)
        os.makedirs(idea_dir)
        yield IdeaProject(idea_dir)


def _create_file(project, filename, content=""):
    path = os.path.join(project.directory, filename)
    with open(path, "w") as f:
        f.write(content)


def _setup_has_plan(project):
    _create_file(project, f"{project.name}-idea.md")
    _create_file(project, f"{project.name}-spec.md")
    _create_file(project, f"{project.name}-plan.md")


def _clean_git():
    return MagicMock(return_value=MagicMock(stdout="", returncode=0))


def _dirty_git():
    """Git runner that reports dirty on first status check, clean on second."""
    call_count = {"status": 0}

    def runner(cmd, **kwargs):
        if "status" in cmd:
            call_count["status"] += 1
            if call_count["status"] <= 1:
                return MagicMock(stdout="M  some-file.md\n", returncode=0)
            return MagicMock(stdout="", returncode=0)
        return MagicMock(returncode=0)

    return runner


def _build_menu_options(project, *, git_runner=None):
    """Build the HAS_PLAN menu options for a project and return them as a list."""
    config = menu_config_by_label([EXIT])
    deps = OrchestratorDeps(
        menu_config=config,
        git_runner=git_runner or _clean_git(),
    )
    orch = Orchestrator(project, deps=deps)
    orch.run()
    displayed = config.output.getvalue()
    return _parse_menu_options(displayed)


def _is_menu_line(line):
    """Check if a line is a numbered menu option like '  1) Some option'."""
    return line and line[0].isdigit() and ")" in line


def _parse_menu_options(displayed):
    """Extract menu option labels from displayed output."""
    options = []
    for line in displayed.splitlines():
        stripped = line.strip()
        if _is_menu_line(stripped):
            label = stripped.split(")", 1)[1].strip()
            label = label.replace(" [default]", "")
            options.append(label)
    return options


def _find_default(displayed):
    """Find which option is marked [default] in the displayed menu."""
    for line in displayed.splitlines():
        stripped = line.strip()
        if _is_menu_line(stripped) and "[default]" in stripped:
            label = stripped.split(")", 1)[1].strip().replace(" [default]", "")
            return label
    return None


def _get_menu_display(project, *, git_runner=None):
    """Run orchestrator to Exit and return the raw menu display string."""
    config = menu_config_by_label([EXIT])
    deps = OrchestratorDeps(
        menu_config=config,
        git_runner=git_runner or _clean_git(),
    )
    orch = Orchestrator(project, deps=deps)
    orch.run()
    return config.output.getvalue()


@pytest.mark.unit
class TestDraftIdeaMenu:

    def test_draft_idea_has_move_to_ready_option(self):
        with _lifecycle_project("my-feature", "draft") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert MOVE_TO_READY in options

    def test_draft_idea_move_to_ready_is_option_2(self):
        with _lifecycle_project("my-feature", "draft") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert options[1] == MOVE_TO_READY

    def test_draft_idea_move_to_ready_is_default(self):
        with _lifecycle_project("my-feature", "draft") as project:
            _setup_has_plan(project)
            displayed = _get_menu_display(project)
            assert _find_default(displayed) == MOVE_TO_READY


@pytest.mark.unit
class TestReadyIdeaMenu:

    def test_ready_idea_has_move_to_wip_option(self):
        with _lifecycle_project("my-feature", "ready") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert MOVE_TO_WIP in options

    def test_ready_idea_move_to_wip_is_option_2(self):
        with _lifecycle_project("my-feature", "ready") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert options[1] == MOVE_TO_WIP

    def test_ready_idea_move_to_wip_is_default(self):
        with _lifecycle_project("my-feature", "ready") as project:
            _setup_has_plan(project)
            displayed = _get_menu_display(project)
            assert _find_default(displayed) == MOVE_TO_WIP


@pytest.mark.unit
class TestWipIdeaMenu:

    def test_wip_idea_has_no_move_option(self):
        with _lifecycle_project("my-feature", "wip") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert MOVE_TO_READY not in options
            assert MOVE_TO_WIP not in options

    def test_wip_idea_implement_is_default(self):
        with _lifecycle_project("my-feature", "wip") as project:
            _setup_has_plan(project)
            displayed = _get_menu_display(project)
            default = _find_default(displayed)
            assert default is not None
            assert default.startswith("Implement")


@pytest.mark.unit
class TestCommitChangesWithLifecycleMenu:

    def test_draft_commit_changes_appears_when_dirty(self):
        with _lifecycle_project("my-feature", "draft") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project, git_runner=_dirty_git())
            assert COMMIT_CHANGES in options
