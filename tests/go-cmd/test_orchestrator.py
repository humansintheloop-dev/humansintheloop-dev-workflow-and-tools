"""Tests for go_cmd.orchestrator — state detection and menu presentation."""

import os

import pytest

from conftest import TempIdeaProject
from i2code.go_cmd.orchestrator import Orchestrator, WorkflowState


@pytest.mark.unit
class TestDetectStateNoIdea:

    def test_empty_directory_is_no_idea(self):
        with TempIdeaProject("my-feature") as project:
            orchestrator = Orchestrator(project)
            assert orchestrator.detect_state() == WorkflowState.NO_IDEA


@pytest.mark.unit
class TestDetectStateHasIdeaNoSpec:

    def test_idea_file_only_is_has_idea_no_spec(self):
        with TempIdeaProject("my-feature") as project:
            _create_file(project, "my-feature-idea.md")
            orchestrator = Orchestrator(project)
            assert orchestrator.detect_state() == WorkflowState.HAS_IDEA_NO_SPEC

    def test_idea_txt_file_is_has_idea_no_spec(self):
        with TempIdeaProject("my-feature") as project:
            _create_file(project, "my-feature-idea.txt")
            orchestrator = Orchestrator(project)
            assert orchestrator.detect_state() == WorkflowState.HAS_IDEA_NO_SPEC


@pytest.mark.unit
class TestDetectStateHasSpec:

    def test_idea_and_spec_is_has_spec(self):
        with TempIdeaProject("my-feature") as project:
            _create_file(project, "my-feature-idea.md")
            _create_file(project, "my-feature-spec.md")
            orchestrator = Orchestrator(project)
            assert orchestrator.detect_state() == WorkflowState.HAS_SPEC


@pytest.mark.unit
class TestDetectStateHasPlan:

    def test_idea_spec_and_plan_is_has_plan(self):
        with TempIdeaProject("my-feature") as project:
            _create_file(project, "my-feature-idea.md")
            _create_file(project, "my-feature-spec.md")
            _create_file(project, "my-feature-plan.md")
            orchestrator = Orchestrator(project)
            assert orchestrator.detect_state() == WorkflowState.HAS_PLAN


@pytest.mark.unit
class TestMenuOptionsForNoIdea:

    def test_no_idea_menu_has_create_idea(self):
        options = Orchestrator.menu_options_for(WorkflowState.NO_IDEA)
        assert len(options) == 1
        assert "Create idea" in options[0]


@pytest.mark.unit
class TestMenuOptionsForHasIdeaNoSpec:

    def test_has_idea_no_spec_menu_options(self):
        options = Orchestrator.menu_options_for(WorkflowState.HAS_IDEA_NO_SPEC)
        assert len(options) == 3
        assert "Revise idea" in options[0]
        assert "Create specification" in options[1]
        assert "Exit" in options[2]


@pytest.mark.unit
class TestMenuOptionsForHasSpec:

    def test_has_spec_menu_options(self):
        options = Orchestrator.menu_options_for(WorkflowState.HAS_SPEC)
        assert len(options) == 3
        assert "Revise the specification" in options[0]
        assert "Create implementation plan" in options[1]
        assert "Exit" in options[2]


@pytest.mark.unit
class TestMenuOptionsForHasPlan:

    def test_has_plan_menu_options(self):
        options = Orchestrator.menu_options_for(WorkflowState.HAS_PLAN)
        assert len(options) >= 3
        assert "Revise the plan" in options[0]
        assert "Exit" in options[-1]


def _create_file(project, filename, content=""):
    path = os.path.join(project.directory, filename)
    with open(path, "w") as f:
        f.write(content)
