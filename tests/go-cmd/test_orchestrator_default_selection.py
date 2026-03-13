"""Tests for HAS_PLAN menu default selection based on config file existence."""

import os
from contextlib import contextmanager
import tempfile
from unittest.mock import MagicMock

import pytest

from conftest import menu_config_by_label
from i2code.go_cmd.orchestrator import (
    COMMIT_CHANGES, CONFIGURE_IMPLEMENT, EXIT, Orchestrator, OrchestratorDeps,
    REVISE_IMPLEMENT,
)
from i2code.implement.idea_project import IdeaProject


@contextmanager
def _wip_project(name):
    """Create a TempIdeaProject in a wip directory (no lifecycle move option)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, "docs", "ideas", "wip", name)
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


def _is_default_menu_line(line):
    stripped = line.strip()
    return stripped[:1].isdigit() and ")" in stripped and "[default]" in stripped


def _find_default(displayed):
    """Find which option is marked [default] in the displayed menu."""
    for line in displayed.splitlines():
        if _is_default_menu_line(line):
            label = line.strip().split(")", 1)[1].strip().replace(" [default]", "")
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
class TestDefaultSelectionByConfig:

    def test_no_config_defaults_to_configure(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            # No config file created
            displayed = _get_menu_display(project)
            assert _find_default(displayed) == CONFIGURE_IMPLEMENT

    def test_config_exists_with_uncommitted_changes_defaults_to_commit(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            _create_file(project, f"{project.name}-implement-config.yaml", "model: opus")
            displayed = _get_menu_display(project, git_runner=_dirty_git())
            assert _find_default(displayed) == COMMIT_CHANGES

    def test_config_exists_no_changes_defaults_to_revise(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            _create_file(project, f"{project.name}-implement-config.yaml", "model: opus")
            displayed = _get_menu_display(project)
            assert _find_default(displayed) == REVISE_IMPLEMENT
