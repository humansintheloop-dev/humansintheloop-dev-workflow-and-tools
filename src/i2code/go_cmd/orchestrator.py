"""Workflow orchestrator: detects state, presents menus, dispatches steps."""

import glob
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TextIO

from i2code.go_cmd.create_plan import PlanServices, create_plan
from i2code.go_cmd.implement_config import (
    build_implement_flags,
    build_implement_label,
    prompt_implement_config,
    read_implement_config,
    write_implement_config,
)
from i2code.go_cmd.menu import MenuConfig, get_user_choice
from i2code.go_cmd.plan_validator import validate_plan
from i2code.go_cmd.plugin_skills import list_plugin_skills
from i2code.go_cmd.revise_plan import revise_plan
from i2code.idea_cmd.brainstorm import brainstorm_idea
from i2code.implement.claude_runner import ClaudeRunner
from i2code.spec_cmd.create_spec import create_spec
from i2code.spec_cmd.revise_spec import revise_spec
from i2code.template_renderer import render_template


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
        1: ("Creating idea", "brainstorm_idea"),
    },
    WorkflowState.HAS_IDEA_NO_SPEC: {
        1: ("Revising idea", "brainstorm_idea"),
        2: ("Creating specification", "create_spec"),
    },
    WorkflowState.HAS_SPEC: {
        1: ("Revising specification", "revise_spec"),
        2: ("Creating implementation plan", "create_plan"),
    },
    WorkflowState.HAS_PLAN: {
        1: ("Revising plan", "revise_plan"),
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


def _default_implement_runner(flags, directory):
    cmd = ["i2code", "implement"] + flags + [directory]
    return subprocess.run(cmd)


def _default_brainstorm_idea(project):
    return brainstorm_idea(project, ClaudeRunner())


def _default_create_spec(project):
    return create_spec(project, ClaudeRunner())


def _default_revise_spec(project):
    return revise_spec(project, ClaudeRunner())


def _default_create_plan(project):
    runner = ClaudeRunner()
    services = PlanServices(
        template_renderer=render_template,
        plugin_skills_fn=list_plugin_skills,
        validator_fn=validate_plan,
    )
    return create_plan(project, runner, services)


def _default_revise_plan(project):
    return revise_plan(project, ClaudeRunner(), render_template)


_CALLABLE_DEFAULTS = {
    "git_runner": _default_git_runner,
    "implement_runner": _default_implement_runner,
    "brainstorm_idea_fn": _default_brainstorm_idea,
    "create_spec_fn": _default_create_spec,
    "revise_spec_fn": _default_revise_spec,
    "create_plan_fn": _default_create_plan,
    "revise_plan_fn": _default_revise_plan,
}


@dataclass
class OrchestratorDeps:
    """Injectable dependencies for the orchestrator."""

    menu_config: MenuConfig = field(default_factory=MenuConfig)
    output: TextIO = None
    git_runner: Callable = None
    implement_runner: Callable = None
    brainstorm_idea_fn: Callable = None
    create_spec_fn: Callable = None
    revise_spec_fn: Callable = None
    create_plan_fn: Callable = None
    revise_plan_fn: Callable = None

    def __post_init__(self):
        if self.output is None:
            self.output = sys.stderr
        for attr, default in _CALLABLE_DEFAULTS.items():
            if getattr(self, attr) is None:
                setattr(self, attr, default)


class Orchestrator:

    def __init__(self, project, *, deps=None, **kwargs):
        self._project = project
        if deps is not None:
            self._deps = deps
        else:
            self._deps = OrchestratorDeps(
                menu_config=kwargs.get("menu_config") or MenuConfig(),
                output=kwargs.get("output"),
                git_runner=kwargs.get("git_runner"),
                implement_runner=kwargs.get("implement_runner"),
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
            self._run_step_with_retry("Revising plan", "revise_plan")
        elif selected == "Configure implement options":
            self._configure_implement()
        elif selected.startswith("Implement the entire plan"):
            self._run_implement()
        return True

    def _build_has_plan_options(self):
        config_path = self._project.implement_config_file
        options = ["Revise the plan"]
        if self._has_uncommitted_changes():
            options.append("Commit changes")
        options.append(build_implement_label(config_path))
        if os.path.isfile(config_path):
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

    def _ensure_implement_config(self):
        config_path = self._project.implement_config_file
        config = read_implement_config(config_path)
        if config is None:
            menu_fn = self._menu_fn_for_prompts()
            interactive, trunk = prompt_implement_config(menu_fn)
            write_implement_config(config_path, interactive, trunk)
        return read_implement_config(config_path)

    def _menu_fn_for_prompts(self):
        def menu_fn(prompt, default, options):
            return get_user_choice(
                prompt, default, options, config=self._deps.menu_config,
            )
        return menu_fn

    def _display_implement_config(self, config):
        output = self._deps.output
        print("Implementation options:", file=output)
        mode = "interactive" if config["interactive"] else "non-interactive"
        print(f"  Mode: {mode}", file=output)
        branch = "trunk" if config["trunk"] else "worktree"
        print(f"  Branch: {branch}", file=output)

    def _run_implement(self):
        config = self._ensure_implement_config()
        self._display_implement_config(config)
        flags = build_implement_flags(config)
        print("", file=self._deps.output)
        print("Implementing plan...", file=self._deps.output)
        print("", file=self._deps.output)
        result = self._deps.implement_runner(flags, self._project.directory)
        if result.returncode == 0:
            self._check_plan_completion()
        else:
            self._handle_error()

    def _configure_implement(self):
        menu_fn = self._menu_fn_for_prompts()
        interactive, trunk = prompt_implement_config(menu_fn)
        write_implement_config(
            self._project.implement_config_file, interactive, trunk,
        )

    def _check_plan_completion(self):
        plan_path = self._project.plan_file
        if not os.path.isfile(plan_path):
            return
        with open(plan_path) as f:
            content = f.read()
        output = self._deps.output
        if "[ ]" in content:
            print("", file=output)
            print("================================================", file=output)
            print("  Plan has uncompleted tasks", file=output)
            print("================================================", file=output)
            print("", file=output)
        else:
            print("", file=output)
            print("================================================", file=output)
            print("  Workflow Complete!", file=output)
            print("================================================", file=output)
            sys.exit(0)

    def _run_step_with_retry(self, description, step_key):
        while True:
            result = self._run_step(description, step_key)
            if result.returncode == 0:
                return
            if not self._handle_error():
                return

    def _run_step(self, description, step_key):
        print("", file=self._deps.output)
        print(f"{description}...", file=self._deps.output)
        print("", file=self._deps.output)
        return self._run_python_step(step_key)

    def _run_python_step(self, step_key):
        step_fns = {
            "brainstorm_idea": self._deps.brainstorm_idea_fn,
            "create_spec": self._deps.create_spec_fn,
            "revise_spec": self._deps.revise_spec_fn,
            "create_plan": self._deps.create_plan_fn,
            "revise_plan": self._deps.revise_plan_fn,
        }
        return step_fns[step_key](self._project)

    def _handle_error(self):
        choice = get_user_choice(
            "What would you like to do?", 1,
            ["Retry", "Abort workflow"], config=self._deps.menu_config,
        )
        if choice == 1:
            return True
        sys.exit(1)
