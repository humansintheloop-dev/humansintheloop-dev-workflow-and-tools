"""Tests for IdeaProject derived path properties and validation methods."""

import os

import pytest

from conftest import TempIdeaProject


@pytest.mark.unit
class TestIdeaProjectDerivedPaths:

    def test_spec_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.spec_file == os.path.join(
                project.directory, "my-feature-spec.md"
            )

    def test_discussion_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.discussion_file == os.path.join(
                project.directory, "my-feature-discussion.md"
            )

    def test_design_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.design_file == os.path.join(
                project.directory, "my-feature-design.md"
            )

    def test_story_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.story_file == os.path.join(
                project.directory, "my-feature-stories.md"
            )

    def test_plan_with_stories_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.plan_with_stories_file == os.path.join(
                project.directory, "my-feature-story-plan.md"
            )

    def test_session_id_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.session_id_file == os.path.join(
                project.directory, "my-feature-sessionID.txt"
            )

    def test_implement_config_file(self):
        with TempIdeaProject("my-feature") as project:
            assert project.implement_config_file == os.path.join(
                project.directory, "my-feature-implement-config.yaml"
            )

    def test_idea_file_returns_existing_md(self):
        with TempIdeaProject("my-feature") as project:
            md_path = os.path.join(project.directory, "my-feature-idea.md")
            with open(md_path, "w") as f:
                f.write("# Idea")
            assert project.idea_file == md_path

    def test_idea_file_returns_existing_txt(self):
        with TempIdeaProject("my-feature") as project:
            txt_path = os.path.join(project.directory, "my-feature-idea.txt")
            with open(txt_path, "w") as f:
                f.write("Idea")
            assert project.idea_file == txt_path

    def test_idea_file_defaults_to_txt_when_none_exists(self):
        with TempIdeaProject("my-feature") as project:
            expected = os.path.join(project.directory, "my-feature-idea.txt")
            assert project.idea_file == expected


@pytest.mark.unit
class TestIdeaProjectValidateIdea:

    def test_validate_idea_succeeds_when_idea_exists(self):
        with TempIdeaProject("my-feature") as project:
            with open(os.path.join(project.directory, "my-feature-idea.md"), "w") as f:
                f.write("# Idea")
            project.validate_idea()

    def test_validate_idea_raises_when_missing(self):
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit) as exc_info:
                project.validate_idea()
            assert exc_info.value.code == 1

    def test_validate_idea_prints_error_to_stderr(self, capsys):
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit):
                project.validate_idea()
            captured = capsys.readouterr()
            assert "idea" in captured.err.lower()


@pytest.mark.unit
class TestIdeaProjectValidateSpec:

    def test_validate_spec_succeeds_when_spec_exists(self):
        with TempIdeaProject("my-feature") as project:
            with open(os.path.join(project.directory, "my-feature-spec.md"), "w") as f:
                f.write("# Spec")
            project.validate_spec()

    def test_validate_spec_raises_when_missing(self):
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit) as exc_info:
                project.validate_spec()
            assert exc_info.value.code == 1

    def test_validate_spec_prints_error_to_stderr(self, capsys):
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit):
                project.validate_spec()
            captured = capsys.readouterr()
            assert "spec" in captured.err.lower()


@pytest.mark.unit
class TestIdeaProjectValidatePlan:

    def test_validate_plan_succeeds_when_plan_exists(self):
        with TempIdeaProject("my-feature") as project:
            with open(os.path.join(project.directory, "my-feature-plan.md"), "w") as f:
                f.write("# Plan")
            project.validate_plan()

    def test_validate_plan_raises_when_missing(self):
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit) as exc_info:
                project.validate_plan()
            assert exc_info.value.code == 1

    def test_validate_plan_prints_error_to_stderr(self, capsys):
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit):
                project.validate_plan()
            captured = capsys.readouterr()
            assert "plan" in captured.err.lower()
