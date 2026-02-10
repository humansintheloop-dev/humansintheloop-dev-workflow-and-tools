"""Tests for idea directory validation in implement-with-worktree."""

import os
import tempfile
import pytest


@pytest.mark.unit
class TestIdeaDirectoryValidation:
    """Test validation of idea directory existence."""

    def test_validate_nonexistent_directory_raises_error(self):
        """Script should raise error for non-existent directory."""
        from i2code.implement.implement import validate_idea_directory

        with pytest.raises(SystemExit) as exc_info:
            validate_idea_directory("/nonexistent/path/to/idea")

        assert exc_info.value.code != 0

    def test_validate_existing_directory_returns_idea_name(self):
        """Script should return idea name extracted from directory path."""
        from i2code.implement.implement import validate_idea_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-test-feature")
            os.makedirs(idea_dir)

            idea_name = validate_idea_directory(idea_dir)

            assert idea_name == "my-test-feature"

    def test_idea_name_extracted_from_last_path_component(self):
        """Idea name should be the last component of the path."""
        from i2code.implement.implement import validate_idea_directory

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            idea_dir = os.path.join(tmpdir, "docs", "features", "wt-pr-based-development")
            os.makedirs(idea_dir)

            idea_name = validate_idea_directory(idea_dir)

            assert idea_name == "wt-pr-based-development"


@pytest.mark.unit
class TestIdeaFilesValidation:
    """Test validation of required idea files."""

    def test_validate_missing_all_files_raises_error(self):
        """Script should raise error when all required files are missing."""
        from i2code.implement.implement import validate_idea_files

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            with pytest.raises(SystemExit) as exc_info:
                validate_idea_files(idea_dir, "my-feature")

            assert exc_info.value.code != 0

    def test_validate_missing_some_files_lists_missing(self, capsys):
        """Error message should list which files are missing."""
        from i2code.implement.implement import validate_idea_files

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)
            # Create only the idea file
            with open(os.path.join(idea_dir, "my-feature-idea.md"), "w") as f:
                f.write("# My Feature Idea")

            with pytest.raises(SystemExit):
                validate_idea_files(idea_dir, "my-feature")

            captured = capsys.readouterr()
            # Should mention the missing files
            assert "discussion" in captured.err.lower()
            assert "spec" in captured.err.lower()
            assert "plan" in captured.err.lower()

    def test_validate_all_files_present_succeeds(self):
        """Validation should pass when all required files exist."""
        from i2code.implement.implement import validate_idea_files

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)
            # Create all required files
            for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
                with open(os.path.join(idea_dir, f"my-feature-{suffix}"), "w") as f:
                    f.write(f"# {suffix}")

            # Should not raise
            validate_idea_files(idea_dir, "my-feature")

    def test_validate_accepts_txt_idea_file(self):
        """Validation should accept .txt extension for idea file."""
        from i2code.implement.implement import validate_idea_files

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)
            # Create idea as .txt, others as .md
            with open(os.path.join(idea_dir, "my-feature-idea.txt"), "w") as f:
                f.write("My Feature Idea")
            for suffix in ["discussion.md", "spec.md", "plan.md"]:
                with open(os.path.join(idea_dir, f"my-feature-{suffix}"), "w") as f:
                    f.write(f"# {suffix}")

            # Should not raise
            validate_idea_files(idea_dir, "my-feature")


@pytest.mark.unit
class TestIdeaFilesCommitValidation:
    """Test validation that idea files are committed to Git."""

    def test_uncommitted_changes_raises_error(self, capsys):
        """Script should raise error when idea files have uncommitted changes."""
        from git import Repo
        from i2code.implement.implement import validate_idea_files_committed

        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo using GitPython
            repo = Repo.init(tmpdir)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            # Create and commit all idea files
            for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
                filepath = os.path.join(idea_dir, f"my-feature-{suffix}")
                with open(filepath, "w") as f:
                    f.write(f"# {suffix}")

            repo.index.add([os.path.join("my-feature", f"my-feature-{s}")
                           for s in ["idea.md", "discussion.md", "spec.md", "plan.md"]])
            repo.index.commit("Initial")

            # Modify a file (uncommitted change)
            with open(os.path.join(idea_dir, "my-feature-plan.md"), "a") as f:
                f.write("\nNew content")

            with pytest.raises(SystemExit) as exc_info:
                validate_idea_files_committed(idea_dir, "my-feature")

            assert exc_info.value.code != 0
            captured = capsys.readouterr()
            assert "uncommitted" in captured.err.lower() or "not committed" in captured.err.lower()

    def test_untracked_files_raises_error(self):
        """Script should raise error when idea files are untracked."""
        from git import Repo
        from i2code.implement.implement import validate_idea_files_committed

        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo using GitPython
            Repo.init(tmpdir)

            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            # Create idea files but don't add them
            for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
                filepath = os.path.join(idea_dir, f"my-feature-{suffix}")
                with open(filepath, "w") as f:
                    f.write(f"# {suffix}")

            with pytest.raises(SystemExit) as exc_info:
                validate_idea_files_committed(idea_dir, "my-feature")

            assert exc_info.value.code != 0

    def test_committed_files_pass(self):
        """Validation should pass when all idea files are committed."""
        from git import Repo
        from i2code.implement.implement import validate_idea_files_committed

        with tempfile.TemporaryDirectory() as tmpdir:
            # Initialize a git repo using GitPython
            repo = Repo.init(tmpdir)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            idea_dir = os.path.join(tmpdir, "my-feature")
            os.makedirs(idea_dir)

            # Create and commit all idea files
            for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
                filepath = os.path.join(idea_dir, f"my-feature-{suffix}")
                with open(filepath, "w") as f:
                    f.write(f"# {suffix}")

            repo.index.add([os.path.join("my-feature", f"my-feature-{s}")
                           for s in ["idea.md", "discussion.md", "spec.md", "plan.md"]])
            repo.index.commit("Initial")

            # Should not raise
            validate_idea_files_committed(idea_dir, "my-feature")
