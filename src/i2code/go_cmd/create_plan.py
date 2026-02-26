"""Create implementation plan via Claude with validation and auto-repair."""

import sys
from dataclasses import dataclass
from typing import Callable

from i2code.implement.idea_project import IdeaProject


@dataclass
class PlanServices:
    """Bundle of callable dependencies for plan creation."""

    template_renderer: Callable
    plugin_skills_fn: Callable
    validator_fn: Callable

_REPAIR_PROMPT = """\
You are repairing a generated implementation plan that must follow a strict task schema.

Fix ONLY the listed validation errors.
- Do NOT add new steel threads.
- Do NOT add new tasks unless required to fix a missing contract field on an existing task (prefer rewriting titles/structure).
- Do NOT change scope or introduce new features.
- Preserve numbering and ordering of tasks as much as possible.
- Ensure every task uses this format:

- [ ] **Task X.Y: Outcome-oriented description**
  - TaskType: OUTCOME | INFRA | REFACTOR
  - Entrypoint:
  - Observable:
  - Evidence:
  - Steps:
    - [ ] ...

Return the FULL corrected plan as markdown. No commentary.

Validation errors:
"""


def _generate_plan(project, claude_runner, rendered_prompt):
    """Invoke Claude in batch mode to generate the plan."""
    cmd = ["claude", "-p", rendered_prompt]
    return claude_runner.run_batch(cmd, cwd=project.directory)


def _build_repair_prompt(plan_text, errors):
    """Build the repair prompt from the plan text and validation errors."""
    error_lines = "\n".join(errors)
    return f"{_REPAIR_PROMPT}{error_lines}\n\nPlan to repair:\n{plan_text}"


def _repair_plan(project, claude_runner, plan_text, errors):
    """Invoke Claude to repair the plan based on validation errors."""
    repair_prompt = _build_repair_prompt(plan_text, errors)
    cmd = ["claude", "-p", repair_prompt]
    return claude_runner.run_batch(cmd, cwd=project.directory)


def create_plan(project: IdeaProject, claude_runner, services: PlanServices):
    """Generate an implementation plan, validate it, and auto-repair if needed.

    Validates idea and spec exist, enumerates plugin skills, renders the
    create-implementation-plan.md template, invokes Claude in batch mode,
    validates the output, attempts one repair if invalid, and writes the
    final plan to the plan file.

    Args:
        project: The idea project containing file paths
        claude_runner: ClaudeRunner instance for invoking Claude
        services: PlanServices bundling template_renderer, plugin_skills_fn,
            and validator_fn callables

    Raises:
        SystemExit: If idea/spec missing or plan invalid after repair
    """
    project.validate_idea()
    project.validate_spec()

    skills = services.plugin_skills_fn()
    rendered_prompt = services.template_renderer("create-implementation-plan.md", {
        "IDEA_FILE": project.idea_file,
        "SPEC_FILE": project.spec_file,
        "PLAN_SKILLS": skills,
    })

    print("Generate plan", file=sys.stderr)
    result = _generate_plan(project, claude_runner, rendered_prompt)
    plan_text = result.output.stdout

    is_valid, errors = services.validator_fn(plan_text)
    if not is_valid:
        _print_validation_errors(errors)
        print("Attempting one automatic repair pass...", file=sys.stderr)
        repair_result = _repair_plan(project, claude_runner, plan_text, errors)
        plan_text = repair_result.output.stdout

        is_valid, errors = services.validator_fn(plan_text)
        if not is_valid:
            _print_validation_errors(errors)
            print("Error: Plan still invalid after repair.", file=sys.stderr)
            sys.exit(1)

    _write_plan(project.plan_file, plan_text)
    print(f"plan written to {project.plan_file}", file=sys.stderr)


def _print_validation_errors(errors):
    """Print validation errors to stderr."""
    for error in errors:
        print(f"PLAN_VALIDATION_ERROR: {error}", file=sys.stderr)


def _write_plan(plan_file, plan_text):
    """Write the plan text to the plan file."""
    with open(plan_file, "w") as f:
        f.write(plan_text)
