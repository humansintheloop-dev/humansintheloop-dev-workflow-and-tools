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


def _menu_config(choices):
    it = iter(choices)
    return MenuConfig(input_fn=lambda _: next(it), output=io.StringIO())


def _success_result():
    return MagicMock(returncode=0)


def _clean_git():
    return MagicMock(return_value=MagicMock(stdout="", returncode=0))


def _setup_has_plan(project, plan_content="- [ ] **Task 1.1: Do something**\n"):
    _create_file(project, "my-feature-idea.md")
    _create_file(project, "my-feature-spec.md")
    _create_file(project, "my-feature-plan.md", plan_content)


# ---------------------------------------------------------------------------
# Implement menu label shows build_implement_label
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementMenuLabel:

    def test_has_plan_menu_shows_implement_label_without_flags(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            menu_output = io.StringIO()
            config = MenuConfig(input_fn=lambda _: "3", output=menu_output)
            orch = Orchestrator(
                project, script_runner=MagicMock(), menu_config=config,
                git_runner=_clean_git(),
            )
            orch.run()
            displayed = menu_output.getvalue()
            assert "Implement the entire plan: i2code implement" in displayed

    def test_has_plan_menu_shows_flags_when_config_exists(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file, interactive=False, trunk=True,
            )
            menu_output = io.StringIO()
            config = MenuConfig(input_fn=lambda _: "4", output=menu_output)
            orch = Orchestrator(
                project, script_runner=MagicMock(), menu_config=config,
                git_runner=_clean_git(),
            )
            orch.run()
            displayed = menu_output.getvalue()
            assert "i2code implement --non-interactive --trunk" in displayed


# ---------------------------------------------------------------------------
# "Configure implement options" visibility
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureOptionVisibility:

    def test_configure_option_hidden_when_no_config_file(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            menu_output = io.StringIO()
            config = MenuConfig(input_fn=lambda _: "3", output=menu_output)
            orch = Orchestrator(
                project, script_runner=MagicMock(), menu_config=config,
                git_runner=_clean_git(),
            )
            orch.run()
            displayed = menu_output.getvalue()
            assert "Configure implement options" not in displayed

    def test_configure_option_shown_when_config_file_exists(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file, interactive=True, trunk=False,
            )
            menu_output = io.StringIO()
            config = MenuConfig(input_fn=lambda _: "4", output=menu_output)
            orch = Orchestrator(
                project, script_runner=MagicMock(), menu_config=config,
                git_runner=_clean_git(),
            )
            orch.run()
            displayed = menu_output.getvalue()
            assert "Configure implement options" in displayed


# ---------------------------------------------------------------------------
# Implement selection: prompts for config when missing, runs implement
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementSelectionPromptsWhenNoConfig:

    def test_implement_prompts_for_config_then_runs(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            mock_implement = MagicMock(return_value=_success_result())
            # Menu choices: "2" = Implement, then "1" = Interactive, "1" = Worktree,
            # then "4" = Exit (config now exists so menu has 4 items)
            config = _menu_config(["2", "1", "1", "4"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
                implement_runner=mock_implement,
            )
            orch.run()
            mock_implement.assert_called_once()
            assert os.path.isfile(project.implement_config_file)


@pytest.mark.unit
class TestImplementSelectionReusesConfig:

    def test_implement_reuses_existing_config(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file, interactive=False, trunk=True,
            )
            mock_implement = MagicMock(return_value=_success_result())
            # "2" = Implement, then "4" = Exit
            config = _menu_config(["2", "4"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
                implement_runner=mock_implement,
            )
            orch.run()
            call_args = mock_implement.call_args
            flags = call_args[0][0]
            assert "--non-interactive" in flags
            assert "--trunk" in flags


# ---------------------------------------------------------------------------
# Implement runner receives correct flags and directory
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestImplementRunnerArgs:

    def test_implement_runner_receives_flags_and_directory(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file, interactive=False, trunk=False,
            )
            mock_implement = MagicMock(return_value=_success_result())
            config = _menu_config(["2", "4"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
                implement_runner=mock_implement,
            )
            orch.run()
            call_args = mock_implement.call_args
            flags, directory = call_args[0]
            assert "--non-interactive" in flags
            assert directory == project.directory


# ---------------------------------------------------------------------------
# Configure implement options re-prompts and overwrites
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConfigureImplementOptions:

    def test_configure_reprompts_and_overwrites_config(self):
        from i2code.go_cmd.implement_config import (
            read_implement_config,
            write_implement_config,
        )

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file, interactive=True, trunk=False,
            )
            # "3" = Configure, "2" = Non-interactive, "2" = Trunk, "4" = Exit
            config = _menu_config(["3", "2", "2", "4"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
            )
            orch.run()
            updated = read_implement_config(project.implement_config_file)
            assert updated["interactive"] is False
            assert updated["trunk"] is True


# ---------------------------------------------------------------------------
# Display implement config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDisplayImplementConfig:

    def test_displays_config_before_running_implement(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            write_implement_config(
                project.implement_config_file, interactive=True, trunk=False,
            )
            mock_implement = MagicMock(return_value=_success_result())
            output = io.StringIO()
            config = _menu_config(["2", "4"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
                implement_runner=mock_implement, output=output,
            )
            orch.run()
            displayed = output.getvalue()
            assert "Implementation options:" in displayed
            assert "Mode: interactive" in displayed
            assert "Branch: worktree" in displayed


# ---------------------------------------------------------------------------
# Plan completion detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPlanCompletionAllDone:

    def test_all_tasks_complete_prints_workflow_complete_and_exits(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(
                project,
                "- [x] **Task 1.1: Done**\n- [x] **Task 1.2: Also done**\n",
            )
            write_implement_config(
                project.implement_config_file, interactive=True, trunk=False,
            )
            mock_implement = MagicMock(return_value=_success_result())
            output = io.StringIO()
            config = _menu_config(["2"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
                implement_runner=mock_implement, output=output,
            )
            with pytest.raises(SystemExit) as exc_info:
                orch.run()
            assert exc_info.value.code == 0
            assert "Workflow Complete!" in output.getvalue()


@pytest.mark.unit
class TestPlanCompletionIncomplete:

    def test_incomplete_tasks_continues_loop(self):
        from i2code.go_cmd.implement_config import write_implement_config

        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(
                project,
                "- [x] **Task 1.1: Done**\n- [ ] **Task 1.2: Not done**\n",
            )
            write_implement_config(
                project.implement_config_file, interactive=True, trunk=False,
            )
            mock_implement = MagicMock(return_value=_success_result())
            output = io.StringIO()
            # "2" = Implement, then "4" = Exit
            config = _menu_config(["2", "4"])
            orch = Orchestrator(
                project, script_runner=MagicMock(),
                menu_config=config, git_runner=_clean_git(),
                implement_runner=mock_implement, output=output,
            )
            orch.run()
            assert "Plan has uncompleted tasks" in output.getvalue()
            assert "Workflow Complete!" not in output.getvalue()
