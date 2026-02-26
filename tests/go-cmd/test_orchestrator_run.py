"""Tests for orchestrator.run() — step dispatch, error handling, and git integration."""

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


def _failure_result():
    return MagicMock(returncode=1)


def _setup_has_idea(project):
    _create_file(project, "my-feature-idea.md")


def _setup_has_spec(project):
    _setup_has_idea(project)
    _create_file(project, "my-feature-spec.md")


def _setup_has_plan(project):
    _setup_has_spec(project)
    _create_file(project, "my-feature-plan.md")


def _run_dispatch_test(setup_fn, choices, expected_script):
    with TempIdeaProject("my-feature") as project:
        setup_fn(project)
        mock_runner = MagicMock(return_value=_success_result())
        config = _menu_config(choices)
        orch = Orchestrator(project, script_runner=mock_runner, menu_config=config)
        orch.run()
        mock_runner.assert_called_once_with(expected_script, (project.directory,))


def _git_result(stdout):
    return MagicMock(stdout=stdout, returncode=0)


def _run_has_plan_with_git(project, exit_choice, git_stdout):
    menu_output = io.StringIO()
    config = MenuConfig(input_fn=lambda _: exit_choice, output=menu_output)
    mock_git = MagicMock(return_value=_git_result(git_stdout))
    orch = Orchestrator(
        project, script_runner=MagicMock(), menu_config=config,
        git_runner=mock_git,
    )
    orch.run()
    return menu_output.getvalue()


# ---------------------------------------------------------------------------
# Step dispatch: each menu selection invokes the correct script
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDispatchNoIdea:

    def test_no_idea_runs_brainstorm_script(self):
        with TempIdeaProject("my-feature") as project:
            mock_runner = MagicMock()
            mock_runner.side_effect = lambda script, args=(): (
                _create_file(project, "my-feature-idea.md", "idea"),
                _success_result(),
            )[-1]
            config = _menu_config(["3"])
            orch = Orchestrator(project, script_runner=mock_runner, menu_config=config)
            orch.run()
            mock_runner.assert_called_once_with(
                "brainstorm-idea.sh", (project.directory,)
            )


@pytest.mark.unit
class TestDispatchHasIdeaNoSpec:

    def test_revise_idea_runs_brainstorm_script(self):
        _run_dispatch_test(_setup_has_idea, ["1", "3"], "brainstorm-idea.sh")

    def test_create_spec_runs_make_spec_script(self):
        _run_dispatch_test(_setup_has_idea, ["2", "3"], "make-spec.sh")

    def test_exit_does_not_run_any_script(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_idea(project)
            mock_runner = MagicMock()
            config = _menu_config(["3"])
            orch = Orchestrator(project, script_runner=mock_runner, menu_config=config)
            orch.run()
            mock_runner.assert_not_called()


@pytest.mark.unit
class TestDispatchHasSpec:

    def test_revise_spec_runs_revise_spec_script(self):
        _run_dispatch_test(_setup_has_spec, ["1", "3"], "revise-spec.sh")

    def test_create_plan_runs_make_plan_script(self):
        _run_dispatch_test(_setup_has_spec, ["2", "3"], "make-plan.sh")


@pytest.mark.unit
class TestDispatchHasPlan:

    def test_revise_plan_runs_revise_plan_script(self):
        _run_dispatch_test(_setup_has_plan, ["1", "3"], "revise-plan.sh")


# ---------------------------------------------------------------------------
# run_step: prints description and calls callback
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRunStep:

    def test_run_step_prints_description(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_idea(project)
            mock_runner = MagicMock(return_value=_success_result())
            output = io.StringIO()
            config = _menu_config(["1", "3"])
            orch = Orchestrator(
                project, script_runner=mock_runner, menu_config=config,
                output=output,
            )
            orch.run()
            assert "Revising idea" in output.getvalue()


# ---------------------------------------------------------------------------
# Error handling: retry and abort
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestErrorHandlingRetry:

    def test_retry_reruns_failed_step(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_spec(project)
            results = iter([_failure_result(), _success_result()])
            mock_runner = MagicMock(side_effect=lambda *a, **kw: next(results))
            config = _menu_config(["2", "1", "3"])
            orch = Orchestrator(project, script_runner=mock_runner, menu_config=config)
            orch.run()
            assert mock_runner.call_count == 2


@pytest.mark.unit
class TestErrorHandlingAbort:

    def test_abort_exits_with_code_1(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_spec(project)
            mock_runner = MagicMock(return_value=_failure_result())
            config = _menu_config(["2", "2"])
            orch = Orchestrator(project, script_runner=mock_runner, menu_config=config)
            with pytest.raises(SystemExit) as exc_info:
                orch.run()
            assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# KeyboardInterrupt
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeyboardInterrupt:

    def test_keyboard_interrupt_exits_with_130(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_idea(project)
            mock_runner = MagicMock(side_effect=KeyboardInterrupt)
            config = _menu_config(["1"])
            output = io.StringIO()
            orch = Orchestrator(
                project, script_runner=mock_runner, menu_config=config,
                output=output,
            )
            with pytest.raises(SystemExit) as exc_info:
                orch.run()
            assert exc_info.value.code == 130
            assert "Workflow interrupted" in output.getvalue()


# ---------------------------------------------------------------------------
# Git dirty detection and commit
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitDirtyDetection:

    def test_dirty_adds_commit_option_to_has_plan_menu(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            displayed = _run_has_plan_with_git(project, "4", "M  some-file.md\n")
            assert "Commit changes" in displayed

    def test_clean_repo_does_not_add_commit_option(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            displayed = _run_has_plan_with_git(project, "3", "")
            assert "Commit changes" not in displayed


@pytest.mark.unit
class TestCommitAction:

    def test_commit_runs_git_add_and_commit(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            git_calls = []

            def mock_git(cmd, **kwargs):
                git_calls.append(cmd)
                status_calls = [c for c in git_calls if "status" in c]
                if "status" in cmd:
                    if len(status_calls) <= 1:
                        return _git_result("M file\n")
                    return _git_result("")
                return MagicMock(returncode=0)

            config = _menu_config(["2", "3"])
            orch = Orchestrator(
                project, script_runner=MagicMock(), menu_config=config,
                git_runner=mock_git,
            )
            orch.run()

            add_calls = [c for c in git_calls if "add" in c]
            commit_calls = [c for c in git_calls if "commit" in c]
            assert len(add_calls) == 1
            assert project.directory in add_calls[0]
            assert len(commit_calls) == 1
            assert "Add idea docs for my-feature" in " ".join(commit_calls[0])
