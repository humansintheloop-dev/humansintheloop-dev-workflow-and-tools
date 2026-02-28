"""Tests for orchestrator implement config integration and plan completion."""

import io
import os
from unittest.mock import MagicMock

import pytest

from conftest import TempIdeaProject, menu_config_by_label
from i2code.go_cmd.implement_config import (
    INTERACTIVE, NON_INTERACTIVE, TRUNK_MODE, WORKTREE_MODE,
)
from i2code.go_cmd.orchestrator import (
    CONFIGURE_IMPLEMENT, EXIT, IMPLEMENT_PLAN,
    Orchestrator, OrchestratorDeps,
)


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


def _run_has_plan_orchestrator(project, menu_labels, *,
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

    config = menu_config_by_label(menu_labels)
    output = io.StringIO()
    deps = OrchestratorDeps(
        menu_config=config,
        git_runner=_clean_git(),
        implement_runner=implement_runner,
        output=output,
    )
    orch = Orchestrator(project, deps=deps)

    result = _OrchestratorRun()
    try:
        orch.run()
    except SystemExit as e:
        result.exit_code = e.code
    result.menu_displayed = config.output.getvalue()
    result.output_displayed = output.getvalue()
    return result


# ---------------------------------------------------------------------------
# Implement menu label shows build_implement_label
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementMenuLabel:

    @pytest.mark.parametrize("config_kwargs,expected_text", [
        (None, "Implement the entire plan: i2code implement"),
        (dict(interactive=False, trunk=True),
         "i2code implement --non-interactive --trunk"),
    ])
    def test_has_plan_menu_shows_implement_label(self, config_kwargs,
                                                 expected_text):
        with TempIdeaProject("my-feature") as project:
            result = _run_has_plan_orchestrator(
                project, [EXIT], config_kwargs=config_kwargs,
            )
            assert expected_text in result.menu_displayed


# ---------------------------------------------------------------------------
# "Configure implement options" visibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureOptionVisibility:

    @pytest.mark.parametrize("config_kwargs,should_show", [
        (None, False),
        (dict(interactive=True, trunk=False), True),
    ])
    def test_configure_option_visibility(self, config_kwargs, should_show):
        with TempIdeaProject("my-feature") as project:
            result = _run_has_plan_orchestrator(
                project, [EXIT], config_kwargs=config_kwargs,
            )
            if should_show:
                assert CONFIGURE_IMPLEMENT in result.menu_displayed
            else:
                assert CONFIGURE_IMPLEMENT not in result.menu_displayed


# ---------------------------------------------------------------------------
# Implement selection: prompts for config when missing, runs implement
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementSelectionPromptsWhenNoConfig:

    def test_implement_prompts_for_config_then_runs(self):
        with TempIdeaProject("my-feature") as project:
            mock_implement = MagicMock(return_value=_success_result())
            user_choices = [IMPLEMENT_PLAN, INTERACTIVE, WORKTREE_MODE, EXIT]
            _run_has_plan_orchestrator(
                project, user_choices,
                implement_runner=mock_implement,
            )
            mock_implement.assert_called_once()
            assert os.path.isfile(project.implement_config_file)


# ---------------------------------------------------------------------------
# Implement runner receives correct flags and directory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementRunnerReceivesConfig:

    @pytest.mark.parametrize("config_kwargs,expected_flags", [
        (dict(interactive=False, trunk=True), ["--non-interactive", "--trunk"]),
        (dict(interactive=False, trunk=False), ["--non-interactive"]),
    ])
    def test_implement_runner_receives_expected_flags(self, config_kwargs,
                                                      expected_flags):
        with TempIdeaProject("my-feature") as project:
            mock_implement = MagicMock(return_value=_success_result())
            _run_has_plan_orchestrator(
                project, [IMPLEMENT_PLAN, EXIT],
                config_kwargs=config_kwargs,
                implement_runner=mock_implement,
            )
            flags, directory = mock_implement.call_args[0]
            for flag in expected_flags:
                assert flag in flags
            assert directory == project.directory


# ---------------------------------------------------------------------------
# Configure implement options re-prompts and overwrites
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureImplementOptions:

    def test_configure_reprompts_and_overwrites_config(self):
        from i2code.go_cmd.implement_config import read_implement_config

        with TempIdeaProject("my-feature") as project:
            user_choices = [
                CONFIGURE_IMPLEMENT, NON_INTERACTIVE, TRUNK_MODE, EXIT,
            ]
            _run_has_plan_orchestrator(
                project, user_choices,
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
                project, [IMPLEMENT_PLAN, EXIT],
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
class TestPlanCompletion:

    @pytest.mark.parametrize("plan_content,user_choices,expect_complete", [
        (
            "## Steel Thread 1: Feature\n\n"
            "- [x] **Task 1.1: Done**\n- [x] **Task 1.2: Also done**\n",
            [IMPLEMENT_PLAN],
            True,
        ),
        (
            "## Steel Thread 1: Feature\n\n"
            "- [x] **Task 1.1: Done**\n- [ ] **Task 1.2: Not done**\n",
            [IMPLEMENT_PLAN, EXIT],
            False,
        ),
    ])
    def test_plan_completion_detection(self, plan_content, user_choices,
                                       expect_complete):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project, plan_content)
            result = _run_has_plan_orchestrator(
                project, user_choices,
                config_kwargs=dict(interactive=True, trunk=False),
                implement_runner=MagicMock(return_value=_success_result()),
            )
            if expect_complete:
                assert result.exit_code == 0
                assert "Workflow Complete!" in result.output_displayed
            else:
                assert "Plan has uncompleted tasks" in result.output_displayed
                assert "Workflow Complete!" not in result.output_displayed
