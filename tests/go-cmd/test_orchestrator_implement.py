"""Tests for orchestrator implement config integration and plan completion."""

import io
import os
from unittest.mock import MagicMock

import pytest

from conftest import TempIdeaProject
from i2code.go_cmd.menu import MenuConfig
from i2code.go_cmd.orchestrator import Orchestrator


def _create_file(project, filename, content=""):
    path = os.path.join(project.directory, filename)
    with open(path, "w") as f:
        f.write(content)


def _success_result():
    return MagicMock(returncode=0)


def _clean_git():
    return MagicMock(return_value=MagicMock(stdout="", returncode=0))


def _setup_has_plan(project, plan_content="- [ ] **Task 1.1: Do something**\n"):
    _create_file(project, "my-feature-idea.md")
    _create_file(project, "my-feature-spec.md")
    _create_file(project, "my-feature-plan.md", plan_content)


class _OrchestratorRun:
    """Captured output from an orchestrator run."""

    def __init__(self):
        self.menu_displayed = ""
        self.output_displayed = ""
        self.exit_code = None


def _run_has_plan_orchestrator(project, choices, *,
                               config_kwargs=None, implement_runner=None):
    """Setup a has-plan project, run an orchestrator, and return captured output.

    Callers needing custom plan content should call _setup_has_plan() before
    this function; default plan files are created automatically when absent.

    Returns:
        _OrchestratorRun with menu_displayed, output_displayed, and exit_code.
    """
    if not os.path.exists(project.plan_file):
        _setup_has_plan(project)

    if config_kwargs is not None:
        from i2code.go_cmd.implement_config import write_implement_config
        write_implement_config(project.implement_config_file, **config_kwargs)

    menu_output = io.StringIO()
    output = io.StringIO()
    it = iter(choices)
    menu_config = MenuConfig(input_fn=lambda _: next(it), output=menu_output)
    orch = Orchestrator(
        project, script_runner=MagicMock(), menu_config=menu_config,
        git_runner=_clean_git(),
        implement_runner=implement_runner, output=output,
    )

    result = _OrchestratorRun()
    try:
        orch.run()
    except SystemExit as e:
        result.exit_code = e.code
    result.menu_displayed = menu_output.getvalue()
    result.output_displayed = output.getvalue()
    return result


# ---------------------------------------------------------------------------
# Implement menu label shows build_implement_label
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementMenuLabel:

    @pytest.mark.parametrize("config_kwargs,exit_choice,expected_text", [
        (None, "3", "Implement the entire plan: i2code implement"),
        (dict(interactive=False, trunk=True), "4",
         "i2code implement --non-interactive --trunk"),
    ])
    def test_has_plan_menu_shows_implement_label(self, config_kwargs,
                                                 exit_choice, expected_text):
        with TempIdeaProject("my-feature") as project:
            result = _run_has_plan_orchestrator(
                project, [exit_choice], config_kwargs=config_kwargs,
            )
            assert expected_text in result.menu_displayed


# ---------------------------------------------------------------------------
# "Configure implement options" visibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureOptionVisibility:

    @pytest.mark.parametrize("config_kwargs,exit_choice,should_show", [
        (None, "3", False),
        (dict(interactive=True, trunk=False), "4", True),
    ])
    def test_configure_option_visibility(self, config_kwargs, exit_choice,
                                         should_show):
        with TempIdeaProject("my-feature") as project:
            result = _run_has_plan_orchestrator(
                project, [exit_choice], config_kwargs=config_kwargs,
            )
            if should_show:
                assert "Configure implement options" in result.menu_displayed
            else:
                assert "Configure implement options" not in result.menu_displayed


# ---------------------------------------------------------------------------
# Implement selection: prompts for config when missing, runs implement
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementSelectionPromptsWhenNoConfig:

    def test_implement_prompts_for_config_then_runs(self):
        with TempIdeaProject("my-feature") as project:
            mock_implement = MagicMock(return_value=_success_result())
            # Menu choices: "2" = Implement, then "1" = Interactive, "1" = Worktree,
            # then "4" = Exit (config now exists so menu has 4 items)
            _run_has_plan_orchestrator(
                project, ["2", "1", "1", "4"],
                implement_runner=mock_implement,
            )
            mock_implement.assert_called_once()
            assert os.path.isfile(project.implement_config_file)


@pytest.mark.unit
class TestImplementSelectionReusesConfig:

    def test_implement_reuses_existing_config(self):
        with TempIdeaProject("my-feature") as project:
            mock_implement = MagicMock(return_value=_success_result())
            # "2" = Implement, then "4" = Exit
            _run_has_plan_orchestrator(
                project, ["2", "4"],
                config_kwargs=dict(interactive=False, trunk=True),
                implement_runner=mock_implement,
            )
            flags = mock_implement.call_args[0][0]
            assert "--non-interactive" in flags
            assert "--trunk" in flags


# ---------------------------------------------------------------------------
# Implement runner receives correct flags and directory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementRunnerArgs:

    def test_implement_runner_receives_flags_and_directory(self):
        with TempIdeaProject("my-feature") as project:
            mock_implement = MagicMock(return_value=_success_result())
            _run_has_plan_orchestrator(
                project, ["2", "4"],
                config_kwargs=dict(interactive=False, trunk=False),
                implement_runner=mock_implement,
            )
            flags, directory = mock_implement.call_args[0]
            assert "--non-interactive" in flags
            assert directory == project.directory


# ---------------------------------------------------------------------------
# Configure implement options re-prompts and overwrites
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureImplementOptions:

    def test_configure_reprompts_and_overwrites_config(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            # "3" = Configure, "2" = Non-interactive, "2" = Trunk, "4" = Exit
            _run_has_plan_orchestrator(
                project, ["3", "2", "2", "4"],
                config_kwargs=dict(interactive=True, trunk=False),
            )
            updated = read_implement_config(project.implement_config_file)
            assert updated["interactive"] is False
            assert updated["trunk"] is True


# ---------------------------------------------------------------------------
# Display implement config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDisplayImplementConfig:

    def test_displays_config_before_running_implement(self):
        with TempIdeaProject("my-feature") as project:
            mock_implement = MagicMock(return_value=_success_result())
            result = _run_has_plan_orchestrator(
                project, ["2", "4"],
                config_kwargs=dict(interactive=True, trunk=False),
                implement_runner=mock_implement,
            )
            assert "Implementation options:" in result.output_displayed
            assert "Mode: interactive" in result.output_displayed
            assert "Branch: worktree" in result.output_displayed


# ---------------------------------------------------------------------------
# Plan completion detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlanCompletionAllDone:

    def test_all_tasks_complete_prints_workflow_complete_and_exits(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(
                project,
                "- [x] **Task 1.1: Done**\n- [x] **Task 1.2: Also done**\n",
            )
            result = _run_has_plan_orchestrator(
                project, ["2"],
                config_kwargs=dict(interactive=True, trunk=False),
                implement_runner=MagicMock(return_value=_success_result()),
            )
            assert result.exit_code == 0
            assert "Workflow Complete!" in result.output_displayed


@pytest.mark.unit
class TestPlanCompletionIncomplete:

    def test_incomplete_tasks_continues_loop(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(
                project,
                "- [x] **Task 1.1: Done**\n- [ ] **Task 1.2: Not done**\n",
            )
            result = _run_has_plan_orchestrator(
                project, ["2", "4"],
                config_kwargs=dict(interactive=True, trunk=False),
                implement_runner=MagicMock(return_value=_success_result()),
            )
            assert "Plan has uncompleted tasks" in result.output_displayed
            assert "Workflow Complete!" not in result.output_displayed
