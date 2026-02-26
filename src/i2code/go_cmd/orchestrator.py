"""Workflow orchestrator: detects state and presents menus."""

import glob
import os
from enum import Enum


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


class Orchestrator:

    def __init__(self, project):
        self._project = project

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
