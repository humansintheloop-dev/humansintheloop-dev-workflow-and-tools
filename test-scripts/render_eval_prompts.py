"""Render the plugin eval case prompts from the current i2code prompt templates.

Usage: uv run python test-scripts/render_eval_prompts.py <out-dir>

Calls the real step functions on a copy of the eval fixture with a runner
that captures the prompt instead of starting Claude, and writes
<out-dir>/<case>/prompt.md for each case.
"""

import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from i2code.go_cmd.create_plan import PlanServices, create_plan
from i2code.go_cmd.plan_validator import validate_plan
from i2code.go_cmd.plugin_skills import list_plugin_skills
from i2code.go_cmd.revise_plan import revise_plan
from i2code.implement.idea_project import IdeaProject
from i2code.spec_cmd.create_spec import create_spec
from i2code.spec_cmd.revise_spec import revise_spec
from i2code.template_renderer import render_template

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "claude-code-plugins" / "idea-to-code" / "evals" / "fixtures" / "eval-idea"
WORKSPACE_IDEA_DIRECTORY = "docs/ideas/active/eval-idea"

CASE_FRONTMATTER = """\
---
max_turns: 40
allowed_tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
---

"""


class _PromptCaptured(Exception):
    """Raised by the capturing runner to stop the step before Claude runs."""


class _CapturingRunner:
    def __init__(self):
        self.prompt = None

    def execute(self, command):
        self.prompt = command.prompt
        raise _PromptCaptured()


@dataclass(frozen=True)
class EvalCase:
    name: str
    run_step: Callable[[IdeaProject, _CapturingRunner], object]
    appended_request: str | None = None


CASES = [
    EvalCase(
        "create-spec",
        lambda project, runner: create_spec(project, runner),
    ),
    EvalCase(
        "revise-spec",
        lambda project, runner: revise_spec(project, runner),
        "Change the specification: add a non-functional requirement that a full eval run costs at most USD 25.",
    ),
    EvalCase(
        "create-plan",
        lambda project, runner: create_plan(project, runner, PlanServices(
            template_renderer=render_template,
            plugin_skills_fn=list_plugin_skills,
            validator_fn=validate_plan,
        )),
    ),
    EvalCase(
        "revise-plan",
        lambda project, runner: revise_plan(project, runner, render_template),
        "Change the plan: add a task to the last steel thread that adds a README section describing how to run the evals.",
    ),
]


def capture_prompt(case: EvalCase, project: IdeaProject) -> str:
    runner = _CapturingRunner()
    try:
        case.run_step(project, runner)
    except _PromptCaptured:
        pass
    if runner.prompt is None:
        raise RuntimeError(f"{case.name}: the step did not invoke Claude")
    return runner.prompt


def relativize_idea_directory(prompt: str, idea_directory: str) -> str:
    for absolute in {os.path.realpath(idea_directory), idea_directory}:
        prompt = prompt.replace(absolute, WORKSPACE_IDEA_DIRECTORY)
    return prompt


def case_prompt(case: EvalCase, prompt: str) -> str:
    body = prompt.rstrip() + "\n"
    if case.appended_request:
        body += "\n" + case.appended_request + "\n"
    return CASE_FRONTMATTER + body


def write_case_prompt(out_dir: Path, case: EvalCase, content: str) -> None:
    case_dir = out_dir / case.name
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "prompt.md").write_text(content)


def copy_fixture(workspace: str) -> str:
    idea_directory = os.path.join(workspace, WORKSPACE_IDEA_DIRECTORY)
    shutil.copytree(FIXTURE_DIR, idea_directory)
    return idea_directory


def render_eval_prompts(out_dir: Path) -> None:
    with tempfile.TemporaryDirectory() as workspace:
        idea_directory = copy_fixture(workspace)
        project = IdeaProject(idea_directory)
        for case in CASES:
            prompt = relativize_idea_directory(capture_prompt(case, project), idea_directory)
            write_case_prompt(out_dir, case, case_prompt(case, prompt))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: render_eval_prompts.py <out-dir>", file=sys.stderr)
        return 2
    render_eval_prompts(Path(argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
