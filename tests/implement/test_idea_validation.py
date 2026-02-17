"""Tests for idea file commit validation in implement-with-worktree."""

import os
import tempfile
import pytest


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
