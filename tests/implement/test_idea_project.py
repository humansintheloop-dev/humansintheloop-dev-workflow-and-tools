"""Tests for IdeaProject value object."""

import os

import pytest

from conftest import TempIdeaProject


@pytest.mark.unit
class TestIdeaProjectConstruction:
    """Test constructing IdeaProject from a directory path."""

    def test_name_extracted_from_directory_basename(self):
        """IdeaProject.name should be the last component of the directory path."""
        with TempIdeaProject("my-feature") as project:
            assert project.name == "my-feature"

    def test_directory_is_stored(self):
        """IdeaProject.directory should return the directory path."""
        with TempIdeaProject("my-feature") as project:
            assert project.directory.endswith("my-feature")

    def test_plan_file_path(self):
        """IdeaProject.plan_file should return <dir>/<name>-plan.md."""
        with TempIdeaProject("my-feature") as project:
            assert project.plan_file == os.path.join(
                project.directory, "my-feature-plan.md"
            )

    def test_state_file_path(self):
        """IdeaProject.state_file should return <dir>/<name>-wt-state.json."""
        with TempIdeaProject("my-feature") as project:
            assert project.state_file == os.path.join(
                project.directory, "my-feature-wt-state.json"
            )


@pytest.mark.unit
class TestIdeaProjectValidation:
    """Test IdeaProject.validate() method."""

    def test_validate_nonexistent_directory_raises_error(self):
        """validate() should raise SystemExit for non-existent directory."""
        from i2code.implement.idea_project import IdeaProject

        project = IdeaProject("/nonexistent/path/to/idea")

        with pytest.raises(SystemExit) as exc_info:
            project.validate()

        assert exc_info.value.code != 0

    def test_validate_existing_directory_returns_self(self):
        """validate() should return self when directory exists."""
        with TempIdeaProject("my-feature") as project:
            result = project.validate()

            assert result is project


@pytest.mark.unit
class TestIdeaProjectValidateFiles:
    """Test IdeaProject.validate_files() method."""

    def test_validate_files_missing_all_raises_error(self):
        """validate_files() should raise SystemExit when all files missing."""
        with TempIdeaProject("my-feature") as project:
            with pytest.raises(SystemExit) as exc_info:
                project.validate_files()

            assert exc_info.value.code != 0

    def test_validate_files_lists_missing_files(self, capsys):
        """Error message should list which files are missing."""
        with TempIdeaProject("my-feature") as project:
            # Create only the idea file
            with open(os.path.join(project.directory, "my-feature-idea.md"), "w") as f:
                f.write("# My Feature Idea")

            with pytest.raises(SystemExit):
                project.validate_files()

            captured = capsys.readouterr()
            assert "discussion" in captured.err.lower()
            assert "spec" in captured.err.lower()
            assert "plan" in captured.err.lower()

    def test_validate_files_all_present_succeeds(self):
        """validate_files() should succeed when all files exist."""
        with TempIdeaProject("my-feature") as project:
            for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
                with open(
                    os.path.join(project.directory, f"my-feature-{suffix}"), "w"
                ) as f:
                    f.write(f"# {suffix}")

            project.validate_files()  # Should not raise

    def test_validate_files_accepts_txt_idea(self):
        """validate_files() should accept .txt extension for idea file."""
        with TempIdeaProject("my-feature") as project:
            with open(
                os.path.join(project.directory, "my-feature-idea.txt"), "w"
            ) as f:
                f.write("My Feature Idea")
            for suffix in ["discussion.md", "spec.md", "plan.md"]:
                with open(
                    os.path.join(project.directory, f"my-feature-{suffix}"), "w"
                ) as f:
                    f.write(f"# {suffix}")

            project.validate_files()  # Should not raise
