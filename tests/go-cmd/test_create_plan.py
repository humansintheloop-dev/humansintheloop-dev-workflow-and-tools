"""Tests for create_plan: generates, validates, and auto-repairs plan via Claude."""

import os
import sys

import pytest

from conftest import TempIdeaProject
from i2code.claude.permissions import build_read_only_tools_flag
from i2code.implement.claude_runner import ClaudeCodeCommand, ClaudeResult
from i2code.implement.idea_project import IdeaProject
from i2code.go_cmd.create_plan import PlanServices, create_plan
from i2code.go_cmd.plan_validator import validate_plan
from i2code.template_renderer import render_template

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner


VALID_PLAN = """\
# Implementation Plan

## Steel Thread 1: Feature

- [ ] **Task 1.1: Do something useful**
  - TaskType: OUTCOME
  - Entrypoint: `uv run python3 -m pytest tests/ -v`
  - Observable: Something observable happens
  - Evidence: Tests pass
  - Steps:
    - [ ] Step one
"""

INVALID_PLAN = """\
# Implementation Plan

## Steel Thread 1: Feature

- [ ] **Task 1.1: Missing Evidence**
  - TaskType: OUTCOME
  - Entrypoint: `command`
  - Observable: Something
"""


def _create_idea_and_spec(project):
    """Create idea and spec files so validation passes."""
    idea_path = os.path.join(project.directory, f"{project.name}-idea.md")
    spec_path = os.path.join(project.directory, f"{project.name}-spec.md")
    with open(idea_path, "w") as f:
        f.write("My idea")
    with open(spec_path, "w") as f:
        f.write("My spec")


def _valid_result():
    return ClaudeResult(returncode=0, result_text=VALID_PLAN)


def _invalid_result():
    return ClaudeResult(returncode=0, result_text=INVALID_PLAN)


def _fake_renderer(template_name, variables):
    parts = [f"template={template_name}"]
    for key, value in sorted(variables.items()):
        parts.append(f"{key}={value}")
    return " | ".join(parts)


def _pass_services():
    return PlanServices(
        template_renderer=_fake_renderer,
        plugin_skills_fn=lambda: "idea-to-code:tdd, idea-to-code:commit-guidelines",
        validator_fn=lambda text: (True, []),
    )


def _fail_services():
    return PlanServices(
        template_renderer=_fake_renderer,
        plugin_skills_fn=lambda: "idea-to-code:tdd",
        validator_fn=lambda text: (False, ["Missing Evidence in Task 1.1"]),
    )


def _counting_validator_services():
    """Return services with a validator that fails on first call, passes on second."""
    call_count = [0]

    def validator(text):
        call_count[0] += 1
        if call_count[0] == 1:
            return (False, ["Missing Evidence in Task 1.1"])
        return (True, [])

    return PlanServices(
        template_renderer=_fake_renderer,
        plugin_skills_fn=lambda: "idea-to-code:tdd",
        validator_fn=validator,
    )


def _run_create_plan(project, runner=None, services=None):
    """Run create_plan with a ready project and sensible defaults."""
    _create_idea_and_spec(project)
    if runner is None:
        runner = FakeClaudeRunner()
    if services is None:
        services = _pass_services()
    runner.set_result(_valid_result())
    create_plan(project, runner, services)
    return runner


@pytest.mark.unit
class TestCreatePlanValidation:

    def test_exits_when_idea_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            with open(os.path.join(project.directory, f"{project.name}-spec.md"), "w") as f:
                f.write("spec")
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                create_plan(project, runner, _pass_services())
            assert len(runner.calls) == 0

    def test_exits_when_spec_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            with open(os.path.join(project.directory, f"{project.name}-idea.md"), "w") as f:
                f.write("idea")
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                create_plan(project, runner, _pass_services())
            assert len(runner.calls) == 0


PLUGIN_SKILLS = "idea-to-code:tdd, idea-to-code:commit-guidelines"


def _real_renderer_services():
    return PlanServices(
        template_renderer=render_template,
        plugin_skills_fn=lambda: PLUGIN_SKILLS,
        validator_fn=lambda text: (True, []),
    )


@pytest.mark.unit
class TestCreatePlanTemplateRendering:

    def _rendered_prompt(self, project):
        runner = _run_create_plan(project, services=_real_renderer_services())
        command = runner.calls[0][1]
        assert isinstance(command, ClaudeCodeCommand)
        return command.prompt or ""

    def test_prompt_names_idea_directory_skills_and_stdout_mechanics(self):
        with TempIdeaProject("my-feature") as project:
            prompt = self._rendered_prompt(project)
            assert project.directory in prompt
            assert "idea-to-code:idea-organization" in prompt
            assert "idea-to-code:create-plan" in prompt
            assert "idea-to-code:plan-format" in prompt
            assert "## Skills to Follow" in prompt
            assert PLUGIN_SKILLS in prompt
            assert "Output the plan to stdout in MARKDOWN format only." in prompt
            assert "DO NOT use the Write tool or Edit tool" in prompt

    def test_prompt_omits_planning_method_moved_to_skills(self):
        with TempIdeaProject("my-feature") as project:
            prompt = self._rendered_prompt(project)
            assert "@" not in prompt
            assert "## General principles" not in prompt
            assert "## Task 1.1 Requirements" not in prompt
            assert "TaskType: OUTCOME | INFRA | REFACTOR" not in prompt
            assert "Architecture POC" not in prompt


@pytest.mark.unit
class TestCreatePlanClaudeInvocation:

    def test_invokes_claude_via_execute(self):
        with TempIdeaProject("my-feature") as project:
            runner = _run_create_plan(project)
            assert runner.calls[0][0] == "execute"

    def test_command_is_non_interactive_batch(self):
        with TempIdeaProject("my-feature") as project:
            runner = _run_create_plan(project)
            command = runner.calls[0][1]
            assert isinstance(command, ClaudeCodeCommand)
            assert command.interactive is False


@pytest.mark.unit
class TestCreatePlanWritesPlanFile:

    def test_writes_plan_to_plan_file(self):
        with TempIdeaProject("my-feature") as project:
            _run_create_plan(project)
            assert os.path.isfile(project.plan_file)
            with open(project.plan_file) as f:
                assert f.read() == VALID_PLAN


@pytest.mark.unit
class TestCreatePlanRepairOnValidationFailure:

    def test_invokes_claude_again_when_validation_fails(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_results([_invalid_result(), _valid_result()])
            create_plan(project, runner, _counting_validator_services())
            assert len(runner.calls) == 2

    def test_repair_prompt_includes_errors_and_plan(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_results([_invalid_result(), _valid_result()])
            create_plan(project, runner, _counting_validator_services())
            repair_command = runner.calls[1][1]
            assert isinstance(repair_command, ClaudeCodeCommand)
            assert "Missing Evidence in Task 1.1" in (repair_command.prompt or "")

    def test_writes_repaired_plan_when_repair_succeeds(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_results([_invalid_result(), _valid_result()])
            create_plan(project, runner, _counting_validator_services())
            with open(project.plan_file) as f:
                assert f.read() == VALID_PLAN


TEST_TASK_TYPE_PLAN = """\
# Implementation Plan

## Steel Thread 1: Setup

- [ ] **Task 1.1: Set up**
  - TaskType: INFRA
  - Entrypoint: `command`
  - Observable: Something
  - Evidence: Something
  - Steps:
    - [ ] Step one

## Steel Thread 2: Feature

- [ ] **Task 2.1: Test something**
  - TaskType: TEST
  - Entrypoint: `command`
  - Observable: Something
  - Evidence: Something
  - Steps:
    - [ ] Step one
"""


@pytest.mark.unit
class TestCreatePlanRepairsInvalidTaskType:

    def _run_with_test_task_type_then_valid(self, project, template_renderer=_fake_renderer):
        _create_idea_and_spec(project)
        runner = FakeClaudeRunner()
        runner.set_results([
            ClaudeResult(returncode=0, result_text=TEST_TASK_TYPE_PLAN),
            _valid_result(),
        ])
        services = PlanServices(
            template_renderer=template_renderer,
            plugin_skills_fn=lambda: "idea-to-code:tdd",
            validator_fn=validate_plan,
        )
        create_plan(project, runner, services)
        return runner

    def test_rendered_repair_prompt_names_plan_format_instead_of_restating_task_format(self):
        with TempIdeaProject("my-feature") as project:
            runner = self._run_with_test_task_type_then_valid(project, template_renderer=render_template)
            repair_command = runner.calls[1][1]
            assert isinstance(repair_command, ClaudeCodeCommand)
            prompt = repair_command.prompt or ""
            assert "idea-to-code:plan-format" in prompt
            assert "Invalid TaskType 'TEST'" in prompt
            assert TEST_TASK_TYPE_PLAN in prompt
            assert "Fix ONLY the listed validation errors." in prompt
            assert "TaskType: OUTCOME | INFRA | REFACTOR" not in prompt
            with open(project.plan_file) as f:
                assert f.read() == VALID_PLAN

    def test_repair_prompt_contains_invalid_task_type_error(self):
        with TempIdeaProject("my-feature") as project:
            runner = self._run_with_test_task_type_then_valid(project)
            assert len(runner.calls) == 2
            repair_command = runner.calls[1][1]
            assert isinstance(repair_command, ClaudeCodeCommand)
            assert "Invalid TaskType 'TEST' in Task 2.1" in (repair_command.prompt or "")

    def test_prints_invalid_task_type_error_to_stderr(self, capsys):
        with TempIdeaProject("my-feature") as project:
            self._run_with_test_task_type_then_valid(project)
            assert (
                "PLAN_VALIDATION_ERROR: Invalid TaskType 'TEST' in Task 2.1"
                " (expected OUTCOME, INFRA or REFACTOR)"
            ) in capsys.readouterr().err

    def test_writes_repaired_plan(self):
        with TempIdeaProject("my-feature") as project:
            self._run_with_test_task_type_then_valid(project)
            with open(project.plan_file) as f:
                assert f.read() == VALID_PLAN


@pytest.mark.unit
class TestCreatePlanAllowedTools:

    def test_allowed_tools_is_read_only_when_repo_root_provided(self, tmp_path):
        repo_root = str(tmp_path / "repo")
        os.makedirs(repo_root)
        idea_dir = str(tmp_path / "repo" / "docs" / "ideas" / "my-idea")
        os.makedirs(idea_dir)
        project = IdeaProject(idea_dir)
        _create_idea_and_spec(project)
        runner = FakeClaudeRunner()
        runner.set_result(_valid_result())

        create_plan(project, runner, _pass_services(), repo_root=repo_root)

        kind, command, cwd = runner.calls[0]
        assert kind == "execute"
        assert isinstance(command, ClaudeCodeCommand)
        assert command.allowed_tools == build_read_only_tools_flag(repo_root)
        assert command.cwd == repo_root
        assert cwd == repo_root

    def test_standalone_no_allowed_tools(self):
        """Standalone create_plan (no repo_root) omits allowed_tools and uses project.directory as cwd."""
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_result(_valid_result())
            create_plan(project, runner, _pass_services())
            kind, command, cwd = runner.calls[0]
            assert kind == "execute"
            assert isinstance(command, ClaudeCodeCommand)
            assert command.allowed_tools is None
            assert command.cwd == project.directory
            assert cwd == project.directory


@pytest.mark.unit
class TestCreatePlanRepairFails:

    def test_raises_when_repair_still_invalid(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_results([_invalid_result(), _invalid_result()])
            with pytest.raises(SystemExit):
                create_plan(project, runner, _fail_services())

    def test_does_not_write_plan_when_repair_fails(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_results([_invalid_result(), _invalid_result()])
            with pytest.raises(SystemExit):
                create_plan(project, runner, _fail_services())
            assert not os.path.isfile(project.plan_file)

    def test_writes_broken_plan_when_repair_fails(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_and_spec(project)
            runner = FakeClaudeRunner()
            runner.set_results([_invalid_result(), _invalid_result()])
            with pytest.raises(SystemExit):
                create_plan(project, runner, _fail_services())
            assert os.path.isfile(project.broken_plan_file)
            with open(project.broken_plan_file) as f:
                assert f.read() == INVALID_PLAN
