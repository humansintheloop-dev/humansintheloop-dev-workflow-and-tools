"""Tests for orchestrator.run() — step dispatch, error handling, and git integration."""

import io
import os
from unittest.mock import MagicMock

import pytest

from conftest import TempIdeaProject
from i2code.go_cmd.menu import MenuConfig
from i2code.go_cmd.orchestrator import Orchestrator, OrchestratorDeps


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


def _run_python_step_test(setup_fn, choices, dep_name, side_effect=None):
    """Run a dispatch test for a Python step function (not a script).

    Creates a mock for the given dep_name, runs the orchestrator with
    the specified choices, and asserts the mock was called once with the project.
    """
    with TempIdeaProject("my-feature") as project:
        setup_fn(project)
        mock_fn = MagicMock(
            side_effect=side_effect,
            return_value=_success_result(),
        )
        config = _menu_config(choices)
        deps = OrchestratorDeps(
            menu_config=config,
            **{dep_name: mock_fn},
        )
        orch = Orchestrator(project, deps=deps)
        orch.run()
        mock_fn.assert_called_once_with(project)


def _git_result(stdout):
    return MagicMock(stdout=stdout, returncode=0)


def _run_has_plan_with_git(project, exit_choice, git_stdout):
    menu_output = io.StringIO()
    config = MenuConfig(input_fn=lambda _: exit_choice, output=menu_output)
    mock_git = MagicMock(return_value=_git_result(git_stdout))
    orch = Orchestrator(
        project, menu_config=config,
        git_runner=mock_git,
    )
    orch.run()
    return menu_output.getvalue()


# ---------------------------------------------------------------------------
# Step dispatch: each menu selection invokes the correct script
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDispatchNoIdea:

    def test_no_idea_calls_brainstorm_function(self):
        def brainstorm_side_effect(p):
            _create_file(p, f"{p.name}-idea.md", "idea")
            return _success_result()

        _run_python_step_test(
            lambda _: None, ["3"], "brainstorm_idea_fn",
            side_effect=brainstorm_side_effect,
        )


@pytest.mark.unit
class TestDispatchHasIdeaNoSpec:

    def test_revise_idea_calls_brainstorm_function(self):
        _run_python_step_test(
            _setup_has_idea, ["1", "3"], "brainstorm_idea_fn",
        )

    def test_create_spec_calls_python_function(self):
        _run_python_step_test(
            _setup_has_idea, ["2", "3"], "create_spec_fn",
        )

    def test_exit_does_not_run_any_step(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_idea(project)
            mock_fn = MagicMock()
            config = _menu_config(["3"])
            deps = OrchestratorDeps(
                menu_config=config,
                brainstorm_idea_fn=mock_fn,
            )
            orch = Orchestrator(project, deps=deps)
            orch.run()
            mock_fn.assert_not_called()


@pytest.mark.unit
class TestDispatchHasSpec:

    def test_revise_spec_calls_python_function(self):
        _run_python_step_test(
            _setup_has_spec, ["1", "3"], "revise_spec_fn",
        )

    def test_create_plan_calls_python_function(self):
        _run_python_step_test(
            _setup_has_spec, ["2", "3"], "create_plan_fn",
        )


@pytest.mark.unit
class TestDispatchHasPlan:

    def test_revise_plan_calls_python_function(self):
        _run_python_step_test(
            _setup_has_plan, ["1", "3"], "revise_plan_fn",
        )


# ---------------------------------------------------------------------------
# run_step: prints description and calls callback
# ---------------------------------------------------------------------------


def _run_with_python_deps(setup_fn, choices, extra_deps=None):
    """Run orchestrator with OrchestratorDeps and return the deps for assertions."""
    with TempIdeaProject("my-feature") as project:
        setup_fn(project)
        config = _menu_config(choices)
        kwargs = {
            "menu_config": config,
            "brainstorm_idea_fn": MagicMock(return_value=_success_result()),
        }
        if extra_deps:
            kwargs.update(extra_deps)
        deps = OrchestratorDeps(**kwargs)
        orch = Orchestrator(project, deps=deps)
        orch.run()
        return deps


@pytest.mark.unit
class TestRunStep:

    def test_run_step_prints_description(self):
        output = io.StringIO()
        _run_with_python_deps(
            _setup_has_idea, ["1", "3"], {"output": output},
        )
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
            mock_fn = MagicMock(side_effect=lambda _: next(results))
            config = _menu_config(["2", "1", "3"])
            deps = OrchestratorDeps(
                menu_config=config,
                create_plan_fn=mock_fn,
            )
            orch = Orchestrator(project, deps=deps)
            orch.run()
            assert mock_fn.call_count == 2


@pytest.mark.unit
class TestErrorHandlingAbort:

    def test_abort_exits_with_code_1(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_spec(project)
            mock_fn = MagicMock(return_value=_failure_result())
            config = _menu_config(["2", "2"])
            deps = OrchestratorDeps(
                menu_config=config,
                create_plan_fn=mock_fn,
            )
            orch = Orchestrator(project, deps=deps)
            with pytest.raises(SystemExit) as exc_info:
                orch.run()
            assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# KeyboardInterrupt
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeyboardInterrupt:

    def test_keyboard_interrupt_exits_with_130(self):
        output = io.StringIO()
        with pytest.raises(SystemExit) as exc_info:
            _run_with_python_deps(
                _setup_has_idea, ["1"],
                {
                    "output": output,
                    "brainstorm_idea_fn": MagicMock(side_effect=KeyboardInterrupt),
                },
            )
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
                project, menu_config=config,
                git_runner=mock_git,
            )
            orch.run()

            add_calls = [c for c in git_calls if "add" in c]
            commit_calls = [c for c in git_calls if "commit" in c]
            assert len(add_calls) == 1
            assert project.directory in add_calls[0]
            assert len(commit_calls) == 1
            assert "Add idea docs for my-feature" in " ".join(commit_calls[0])
