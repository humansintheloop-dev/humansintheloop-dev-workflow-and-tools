"""Create implementation plan via Claude with validation and auto-repair."""

import sys
from dataclasses import dataclass
from typing import Callable

from i2code.implement.claude_runner import ClaudeResult
from i2code.implement.idea_project import IdeaProject


@dataclass
class PlanServices:
    """Bundle of callable dependencies for plan creation."""

    template_renderer: Callable
    plugin_skills_fn: Callable
    validator_fn: Callable

def _generate_plan(project, claude_runner, rendered_prompt):
    """Invoke Claude in batch mode to generate the plan."""
    cmd = ["claude", "-p", rendered_prompt]
    return claude_runner.run_batch(cmd, cwd=project.directory)


def _build_repair_prompt(template_renderer, plan_text, errors):
    """Build the repair prompt from the plan text and validation errors."""
    error_lines = "\n".join(errors)
    return template_renderer("repair-plan.md", {
        "VALIDATION_ERRORS": error_lines,
        "PLAN_TEXT": plan_text,
    })



def create_plan(project: IdeaProject, claude_runner, services: PlanServices) -> ClaudeResult:
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
        repair_prompt = _build_repair_prompt(services.template_renderer, plan_text, errors)
        result = _generate_plan(project, claude_runner, repair_prompt)
        plan_text = result.output.stdout

        is_valid, errors = services.validator_fn(plan_text)
        if not is_valid:
            _print_validation_errors(errors)
            print("Error: Plan still invalid after repair.", file=sys.stderr)
            sys.exit(1)

    _write_plan(project.plan_file, plan_text)
    print(f"plan written to {project.plan_file}", file=sys.stderr)
    return result


def _print_validation_errors(errors):
    """Print validation errors to stderr."""
    for error in errors:
        print(f"PLAN_VALIDATION_ERROR: {error}", file=sys.stderr)


def _write_plan(plan_file, plan_text):
    """Write the plan text to the plan file."""
    with open(plan_file, "w") as f:
        f.write(plan_text)
