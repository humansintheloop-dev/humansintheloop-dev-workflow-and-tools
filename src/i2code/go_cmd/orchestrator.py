"""Workflow orchestrator: detects state, presents menus, dispatches steps."""

import glob
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TextIO

from i2code.go_cmd.menu import MenuConfig, get_user_choice


class WorkflowState(Enum):
    NO_IDEA = "no_idea"
    HAS_IDEA_NO_SPEC = "has_idea_no_spec"
    HAS_SPEC = "has_spec"
    HAS_PLAN = "has_plan"


_MENU_OPTIONS = {
    WorkflowState.NO_IDEA: ["Create idea"],
    WorkflowState.HAS_IDEA_NO_SPEC: [
        "Revise idea",
        "Create specification",
        "Exit",
    ],
    WorkflowState.HAS_SPEC: [
        "Revise the specification",
        "Create implementation plan",
        "Exit",
    ],
    WorkflowState.HAS_PLAN: [
        "Revise the plan",
        "Implement the entire plan",
        "Configure implement options",
        "Exit",
    ],
}

_STEP_DISPATCH = {
    WorkflowState.NO_IDEA: {
        1: ("Creating idea", "brainstorm-idea.sh"),
    },
    WorkflowState.HAS_IDEA_NO_SPEC: {
        1: ("Revising idea", "brainstorm-idea.sh"),
        2: ("Creating specification", "make-spec.sh"),
    },
    WorkflowState.HAS_SPEC: {
        1: ("Revising specification", "revise-spec.sh"),
        2: ("Creating implementation plan", "make-plan.sh"),
    },
    WorkflowState.HAS_PLAN: {
        1: ("Revising plan", "revise-plan.sh"),
    },
}

_MENU_PROMPTS = {
    WorkflowState.HAS_IDEA_NO_SPEC: "Idea exists. What would you like to do?",
    WorkflowState.HAS_SPEC: "Specification created. What would you like to do?",
    WorkflowState.HAS_PLAN: "Implementation plan exists. What would you like to do?",
}

_MENU_DEFAULTS = {
    WorkflowState.HAS_IDEA_NO_SPEC: 2,
    WorkflowState.HAS_SPEC: 2,
}


def _default_git_runner(cmd, **kwargs):
    return subprocess.run(cmd, **kwargs)


@dataclass
class OrchestratorDeps:
    """Injectable dependencies for the orchestrator."""

    script_runner: Callable = None
    menu_config: MenuConfig = field(default_factory=MenuConfig)
    output: TextIO = None
    git_runner: Callable = None

    def __post_init__(self):
        if self.output is None:
            self.output = sys.stderr
        if self.git_runner is None:
            self.git_runner = _default_git_runner


class Orchestrator:

    def __init__(self, project, *, deps=None, **kwargs):
        self._project = project
        if deps is not None:
            self._deps = deps
        else:
            self._deps = OrchestratorDeps(
                script_runner=kwargs.get("script_runner"),
                menu_config=kwargs.get("menu_config") or MenuConfig(),
                output=kwargs.get("output"),
                git_runner=kwargs.get("git_runner"),
            )

    def detect_state(self) -> WorkflowState:
        project = self._project
        idea_pattern = os.path.join(
            project.directory, f"{project.name}-idea.*"
        )
        if not glob.glob(idea_pattern):
            return WorkflowState.NO_IDEA
        if not os.path.isfile(project.spec_file):
            return WorkflowState.HAS_IDEA_NO_SPEC
        if not os.path.isfile(project.plan_file):
            return WorkflowState.HAS_SPEC
        return WorkflowState.HAS_PLAN

    @staticmethod
    def menu_options_for(state: WorkflowState) -> list[str]:
        return list(_MENU_OPTIONS[state])

    def run(self):
        try:
            self._main_loop()
        except KeyboardInterrupt:
            print("", file=self._deps.output)
            print("Workflow interrupted.", file=self._deps.output)
            sys.exit(130)

    def _main_loop(self):
        dispatchers = {
            WorkflowState.NO_IDEA: self._dispatch_no_idea,
            WorkflowState.HAS_IDEA_NO_SPEC: self._dispatch_with_menu,
            WorkflowState.HAS_SPEC: self._dispatch_with_menu,
            WorkflowState.HAS_PLAN: self._dispatch_has_plan,
        }
        while True:
            state = self.detect_state()
            if not dispatchers[state](state):
                return

    def _dispatch_no_idea(self, _state):
        desc, script = _STEP_DISPATCH[WorkflowState.NO_IDEA][1]
        self._run_step_with_retry(desc, script)
        return True

    def _dispatch_with_menu(self, state):
        options = self.menu_options_for(state)
        choice = get_user_choice(
            _MENU_PROMPTS[state], _MENU_DEFAULTS.get(state, 1),
            options, config=self._deps.menu_config,
        )
        if options[choice - 1] == "Exit":
            return False
        dispatch = _STEP_DISPATCH.get(state, {})
        if choice in dispatch:
            desc, script = dispatch[choice]
            self._run_step_with_retry(desc, script)
        return True

    def _dispatch_has_plan(self, _state):
        options = self._build_has_plan_options()
        choice = get_user_choice(
            _MENU_PROMPTS[WorkflowState.HAS_PLAN],
            self._commit_default(options), options,
            config=self._deps.menu_config,
        )
        return self._handle_has_plan_choice(options[choice - 1])

    def _handle_has_plan_choice(self, selected):
        if selected == "Exit":
            return False
        if selected == "Commit changes":
            self._commit_changes()
        elif selected == "Revise the plan":
            self._run_step_with_retry("Revising plan", "revise-plan.sh")
        return True

    def _build_has_plan_options(self):
        options = ["Revise the plan"]
        if self._has_uncommitted_changes():
            options.append("Commit changes")
        options.append("Implement the entire plan")
        options.append("Configure implement options")
        options.append("Exit")
        return options

    def _commit_default(self, options):
        if "Commit changes" in options:
            return options.index("Commit changes") + 1
        return 2

    def _has_uncommitted_changes(self):
        result = self._deps.git_runner(
            ["git", "status", "--porcelain", "--", self._project.directory],
            capture_output=True, text=True,
        )
        return bool(result.stdout.strip())

    def _commit_changes(self):
        self._deps.git_runner(
            ["git", "add", self._project.directory],
        )
        self._deps.git_runner(
            ["git", "commit", "-m",
             f"Add idea docs for {self._project.name}",
             "--", self._project.directory],
        )

    def _run_step_with_retry(self, description, script):
        while True:
            result = self._run_step(description, script)
            if result.returncode == 0:
                return
            if not self._handle_error():
                return

    def _run_step(self, description, script):
        print("", file=self._deps.output)
        print(f"{description}...", file=self._deps.output)
        print("", file=self._deps.output)
        return self._deps.script_runner(script, (self._project.directory,))

    def _handle_error(self):
        choice = get_user_choice(
            "What would you like to do?", 1,
            ["Retry", "Abort workflow"], config=self._deps.menu_config,
        )
        if choice == 1:
            return True
        sys.exit(1)
