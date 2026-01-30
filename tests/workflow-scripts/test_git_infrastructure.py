"""Tests for Git infrastructure setup in implement-with-worktree."""

import os
import sys
import tempfile
import pytest

from git import Repo

# Add workflow-scripts to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../workflow-scripts'))


@pytest.mark.unit
class TestIntegrationBranch:
    """Test integration branch creation and reuse."""

    def test_create_integration_branch_when_not_exists(self):
        """Should create integration branch if it doesn't exist."""
        from implement_with_worktree import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repo.init(tmpdir)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit so we have a HEAD
            test_file = os.path.join(tmpdir, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            branch_name = ensure_integration_branch(repo, "my-feature")

            assert branch_name == "idea/my-feature/integration"
            assert "idea/my-feature/integration" in [b.name for b in repo.branches]

    def test_reuse_existing_integration_branch(self):
        """Should reuse integration branch if it already exists."""
        from implement_with_worktree import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repo.init(tmpdir)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(tmpdir, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create the integration branch manually
            repo.create_head("idea/my-feature/integration")

            # Call ensure_integration_branch - should reuse, not error
            branch_name = ensure_integration_branch(repo, "my-feature")

            assert branch_name == "idea/my-feature/integration"
            # Should still have exactly one branch with that name
            matching = [b for b in repo.branches if b.name == "idea/my-feature/integration"]
            assert len(matching) == 1

    def test_integration_branch_naming_pattern(self):
        """Integration branch should follow idea/<idea-name>/integration pattern."""
        from implement_with_worktree import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repo.init(tmpdir)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(tmpdir, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            branch_name = ensure_integration_branch(repo, "wt-pr-based-development")

            assert branch_name == "idea/wt-pr-based-development/integration"
