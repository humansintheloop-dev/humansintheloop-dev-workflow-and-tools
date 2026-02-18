"""Tests for FakeIdeaProject test double."""

import pytest

from fake_idea_project import FakeIdeaProject


@pytest.mark.unit
class TestFakeIdeaProjectDefaults:
    """FakeIdeaProject provides sensible defaults matching IdeaProject conventions."""

    def test_default_name(self):
        project = FakeIdeaProject()
        assert project.name == "test-feature"

    def test_default_directory(self):
        project = FakeIdeaProject()
        assert project.directory == "/tmp/fake-idea"

    def test_plan_file_derived_from_name_and_directory(self):
        project = FakeIdeaProject()
        assert project.plan_file == "/tmp/fake-idea/test-feature-plan.md"

    def test_state_file_derived_from_name_and_directory(self):
        project = FakeIdeaProject()
        assert project.state_file == "/tmp/fake-idea/test-feature-wt-state.json"

    def test_custom_name_and_directory(self):
        project = FakeIdeaProject(name="my-idea", directory="/home/user/ideas/my-idea")
        assert project.name == "my-idea"
        assert project.directory == "/home/user/ideas/my-idea"
        assert project.plan_file == "/home/user/ideas/my-idea/my-idea-plan.md"


@pytest.mark.unit
class TestFakeIdeaProjectMethods:
    """FakeIdeaProject methods behave like no-ops or return configurable values."""

    def test_validate_returns_self(self):
        project = FakeIdeaProject()
        assert project.validate() is project

    def test_validate_files_is_noop(self):
        project = FakeIdeaProject()
        assert project.validate_files() is None

    def test_find_missing_files_returns_empty(self):
        project = FakeIdeaProject()
        assert project.find_missing_files() == []

    def test_find_idea_files_returns_empty_by_default(self):
        project = FakeIdeaProject()
        assert project.find_idea_files() == []

    def test_find_idea_files_returns_configured_files(self):
        project = FakeIdeaProject()
        project.set_idea_files(["/tmp/a.md", "/tmp/b.md"])
        assert project.find_idea_files() == ["/tmp/a.md", "/tmp/b.md"]

    def test_worktree_idea_project_returns_new_fake(self):
        project = FakeIdeaProject(name="feat", directory="/repo/docs/feat")
        wt = project.worktree_idea_project("/wt", "/repo")
        assert isinstance(wt, FakeIdeaProject)
        assert wt.directory == "/wt/docs/feat"
        assert wt.name == "feat"

    def test_worktree_idea_project_returns_configured_project(self):
        project = FakeIdeaProject()
        custom_wt = FakeIdeaProject(name="wt-feat", directory="/wt/idea")
        project.set_worktree_project(custom_wt)
        assert project.worktree_idea_project("/wt", "/repo") is custom_wt
