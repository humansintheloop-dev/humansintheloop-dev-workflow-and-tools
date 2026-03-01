"""Tests for lifecycle move handler: selecting move option transitions idea."""

import os
from contextlib import contextmanager
import tempfile
from unittest.mock import MagicMock

import pytest

from conftest import menu_config_by_label
from i2code.go_cmd.orchestrator import (
    EXIT, MOVE_TO_READY, MOVE_TO_WIP,
    Orchestrator, OrchestratorDeps,
)
from i2code.implement.idea_project import IdeaProject


@contextmanager
def _lifecycle_project(name, state):
    """Create a TempIdeaProject whose path contains docs/ideas/{state}/{name}."""
    with tempfile.TemporaryDirectory() as tmpdir:
        idea_dir = os.path.join(tmpdir, "docs", "ideas", state, name)
        os.makedirs(idea_dir)
        yield IdeaProject(idea_dir)


def _create_has_plan_files(directory, name):
    for suffix in ["-idea.md", "-spec.md", "-plan.md"]:
        path = os.path.join(directory, f"{name}{suffix}")
        with open(path, "w") as f:
            f.write("")


def _fake_transition(name, old_path, new_state, git_root):
    """Simulate transition by creating files at the new location."""
    new_dir = os.path.join(str(git_root), "docs", "ideas", new_state, name)
    os.makedirs(new_dir, exist_ok=True)
    for f in os.listdir(str(old_path)):
        src = os.path.join(str(old_path), f)
        dst = os.path.join(new_dir, f)
        with open(src) as sf, open(dst, "w") as df:
            df.write(sf.read())
    return f"Move idea {name} to {new_state}"


@contextmanager
def _run_move_draft_to_ready(name="my-feature"):
    """Run orchestrator selecting 'Move idea to ready' then 'Exit'.

    Returns (orchestrator, transition_fn, displayed_output).
    """
    with _lifecycle_project(name, "draft") as project:
        _create_has_plan_files(project.directory, project.name)

        transition_fn = MagicMock(side_effect=_fake_transition)
        config = menu_config_by_label([MOVE_TO_READY, EXIT])
        deps = OrchestratorDeps(
            menu_config=config,
            git_runner=MagicMock(return_value=MagicMock(stdout="", returncode=0)),
            transition_fn=transition_fn,
        )
        orch = Orchestrator(project, deps=deps)
        orch.run()

        yield orch, transition_fn, config.output.getvalue()


@pytest.mark.unit
class TestMoveMenuHandler:

    def test_selecting_move_to_ready_calls_transition(self):
        with _run_move_draft_to_ready() as (_, transition_fn, _displayed):
            transition_fn.assert_called_once()
            name, _old_path, new_state, _git_root = transition_fn.call_args[0]
            assert name == "my-feature"
            assert new_state == "ready"

    def test_move_rebuilds_project_with_new_path(self):
        with _run_move_draft_to_ready() as (orch, _, _displayed):
            assert "/ready/" in orch._project.directory
            assert "/draft/" not in orch._project.directory

    def test_move_re_enters_menu_with_updated_options(self):
        with _run_move_draft_to_ready() as (_orch, _, displayed):
            assert MOVE_TO_WIP in displayed
