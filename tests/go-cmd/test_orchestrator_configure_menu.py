"""Tests for HAS_PLAN menu configure/revise implement options."""

import os
from contextlib import contextmanager
import tempfile
from unittest.mock import MagicMock

import pytest

from conftest import menu_config_by_label
from i2code.go_cmd.orchestrator import (
    EXIT, Orchestrator, OrchestratorDeps,
)
from i2code.go_cmd.implement_config import write_implement_config
from i2code.implement.idea_project import IdeaProject


CONFIGURE_IMPLEMENT = "Configure implement options"
REVISE_IMPLEMENT = "Revise implement options"
REVISE_PLAN = "Revise the plan"


@contextmanager
def _wip_project(name):
    """Create a project in wip state (no move option) for simpler menu testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, "docs", "ideas", "wip", name)
        os.makedirs(idea_dir)
        yield IdeaProject(idea_dir)


def _setup_has_plan(project):
    for suffix in ("idea.md", "spec.md", "plan.md"):
        path = os.path.join(project.directory, f"{project.name}-{suffix}")
        with open(path, "w") as f:
            f.write("")


def _clean_git():
    return MagicMock(return_value=MagicMock(stdout="", returncode=0))


def _build_menu_options(project):
    config = menu_config_by_label([EXIT])
    deps = OrchestratorDeps(
        menu_config=config,
        git_runner=_clean_git(),
    )
    orch = Orchestrator(project, deps=deps)
    orch.run()
    displayed = config.output.getvalue()
    return _parse_menu_options(displayed)


def _parse_menu_options(displayed):
    return [
        line.strip().split(")", 1)[1].strip().replace(" [default]", "")
        for line in displayed.splitlines()
        if _is_menu_line(line.strip())
    ]


def _is_menu_line(stripped):
    return stripped and stripped[0].isdigit() and ")" in stripped


@pytest.mark.unit
class TestConfigureOptionWhenNoConfig:

    def test_configure_implement_at_index_1_when_no_config(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert options[1] == CONFIGURE_IMPLEMENT

    def test_menu_order_without_config(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            assert options[0] == REVISE_PLAN
            assert options[1] == CONFIGURE_IMPLEMENT
            assert options[-2].startswith("Implement")
            assert options[-1] == "Exit"


@pytest.mark.unit
class TestReviseOptionWhenConfigExists:

    def test_revise_implement_at_index_1_when_config_exists(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file,
                interactive=True, isolation_type="none", trunk=False,
            )
            options = _build_menu_options(project)
            assert options[1] == REVISE_IMPLEMENT

    def test_menu_order_with_config(self):
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file,
                interactive=True, isolation_type="none", trunk=False,
            )
            options = _build_menu_options(project)
            assert options[0] == REVISE_PLAN
            assert options[1] == REVISE_IMPLEMENT
            assert options[-2].startswith("Implement")
            assert options[-1] == "Exit"


@pytest.mark.unit
class TestMenuOrderingWithAllConditionalItems:

    def test_full_ordering_revise_plan_configure_implement_exit(self):
        """Verify relative ordering: Revise plan, Configure/Revise options, Implement, Exit."""
        with _wip_project("my-feature") as project:
            _setup_has_plan(project)
            options = _build_menu_options(project)
            revise_idx = options.index(REVISE_PLAN)
            configure_idx = options.index(CONFIGURE_IMPLEMENT)
            implement_idx = next(
                i for i, o in enumerate(options) if o.startswith("Implement")
            )
            exit_idx = options.index("Exit")
            assert revise_idx < configure_idx < implement_idx < exit_idx
