"""Tests for orchestrator.run() — step dispatch, error handling, and git integration."""

import io
import os
from unittest.mock import MagicMock

import pytest

from conftest import TempIdeaProject, make_mock_fn_returning, menu_config_by_label
from i2code.go_cmd.orchestrator import (
    ABORT, COMMIT_CHANGES, CREATE_PLAN, CREATE_SPEC,
    EXIT, RETRY, REVISE_IDEA, REVISE_PLAN, REVISE_SPEC,
    Orchestrator, OrchestratorDeps,
)


def _create_file(project, filename, content=""):
    path = os.path.join(project.directory, filename)
    with open(path, "w") as f:
        f.write(content)


def _success_result():
    return MagicMock(returncode=0)


def _failure_result():
    return MagicMock(returncode=1)


def _make_orchestrator(project, menu_labels, **dep_overrides):
    """Create an Orchestrator with label-based menu config and dep overrides."""
    config = menu_config_by_label(menu_labels)
    deps = OrchestratorDeps(menu_config=config, **dep_overrides)
    return Orchestrator(project, deps=deps)


def _setup_has_idea(project):
    _create_file(project, "my-feature-idea.md")


def _setup_has_spec(project):
    _setup_has_idea(project)
    _create_file(project, "my-feature-spec.md")


def _setup_has_plan(project):
    _setup_has_spec(project)
    _create_file(project, "my-feature-plan.md")


def _run_python_step_test(setup_fn, menu_labels, dep_name, side_effect=None):
    """Run a dispatch test for a Python step function.

    Creates a mock for the given dep_name, runs the orchestrator with
    the specified menu labels, and asserts the mock was called once with the project.
    """
    with TempIdeaProject("my-feature") as project:
        setup_fn(project)
        mock_fn = MagicMock(
            side_effect=side_effect,
            return_value=_success_result(),
        )
        orch = _make_orchestrator(project, menu_labels, **{dep_name: mock_fn})
        orch.run()
        mock_fn.assert_called_once_with(project)


def _git_result(stdout):
    return MagicMock(stdout=stdout, returncode=0)


def _run_has_plan_with_git(project, menu_labels, git_stdout):
    config = menu_config_by_label(menu_labels)
    mock_git = MagicMock(return_value=_git_result(git_stdout))
    deps = OrchestratorDeps(menu_config=config, git_runner=mock_git)
    orch = Orchestrator(project, deps=deps)
    orch.run()
    return config.output.getvalue()


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
            lambda _: None, [EXIT], "brainstorm_idea_fn",
            side_effect=brainstorm_side_effect,
        )


@pytest.mark.unit
class TestDispatchHasIdeaNoSpec:

    def test_revise_idea_calls_brainstorm_function(self):
        _run_python_step_test(
            _setup_has_idea, [REVISE_IDEA, EXIT], "brainstorm_idea_fn",
        )

    def test_create_spec_calls_python_function(self):
        _run_python_step_test(
            _setup_has_idea, [CREATE_SPEC, EXIT], "create_spec_fn",
        )

    def test_exit_does_not_run_any_step(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_idea(project)
            mock_fn = MagicMock()
            orch = _make_orchestrator(
                project, [EXIT],
                brainstorm_idea_fn=mock_fn,
            )
            orch.run()
            mock_fn.assert_not_called()


@pytest.mark.unit
class TestDispatchHasSpec:

    def test_revise_spec_calls_python_function(self):
        _run_python_step_test(
            _setup_has_spec, [REVISE_SPEC, EXIT], "revise_spec_fn",
        )

    def test_create_plan_calls_python_function(self):
        _run_python_step_test(
            _setup_has_spec, [CREATE_PLAN, EXIT], "create_plan_fn",
        )


@pytest.mark.unit
class TestDispatchHasPlan:

    def test_revise_plan_calls_python_function(self):
        _run_python_step_test(
            _setup_has_plan, [REVISE_PLAN, EXIT], "revise_plan_fn",
        )


# ---------------------------------------------------------------------------
# run_step: prints description and calls callback
# ---------------------------------------------------------------------------


def _run_with_python_deps(setup_fn, menu_labels, extra_deps=None):
    """Run orchestrator with OrchestratorDeps."""
    with TempIdeaProject("my-feature") as project:
        setup_fn(project)
        kwargs = {
            "brainstorm_idea_fn": MagicMock(return_value=_success_result()),
        }
        if extra_deps:
            kwargs.update(extra_deps)
        orch = _make_orchestrator(project, menu_labels, **kwargs)
        orch.run()


@pytest.mark.unit
class TestRunStep:

    def test_run_step_prints_description(self):
        output = io.StringIO()
        _run_with_python_deps(
            _setup_has_idea, [REVISE_IDEA, EXIT], {"output": output},
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
            user_choices = [CREATE_PLAN, RETRY, EXIT]
            mock_create_plan = make_mock_fn_returning(
                _failure_result(), _success_result(),
            )
            orch = _make_orchestrator(
                project, user_choices,
                create_plan_fn=mock_create_plan,
            )
            orch.run()
            assert mock_create_plan.call_count == 2


@pytest.mark.unit
class TestErrorHandlingAbort:

    def test_abort_exits_with_code_1(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_spec(project)
            mock_create_plan = MagicMock(return_value=_failure_result())
            orch = _make_orchestrator(
                project, [CREATE_PLAN, ABORT],
                create_plan_fn=mock_create_plan,
            )
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
                _setup_has_idea, [REVISE_IDEA],
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
            displayed = _run_has_plan_with_git(
                project, [EXIT], "M  some-file.md\n",
            )
            assert COMMIT_CHANGES in displayed

    def test_clean_repo_does_not_add_commit_option(self):
        with TempIdeaProject("my-feature") as project:
            _setup_has_plan(project)
            displayed = _run_has_plan_with_git(project, [EXIT], "")
            assert COMMIT_CHANGES not in displayed


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

            user_choices = [COMMIT_CHANGES, EXIT]
            orch = _make_orchestrator(
                project, user_choices,
                git_runner=mock_git,
            )
            orch.run()

            add_calls = [c for c in git_calls if "add" in c]
            commit_calls = [c for c in git_calls if "commit" in c]
            assert len(add_calls) == 1
            assert project.directory in add_calls[0]
            assert len(commit_calls) == 1
            assert "Add idea docs for my-feature" in " ".join(commit_calls[0])
