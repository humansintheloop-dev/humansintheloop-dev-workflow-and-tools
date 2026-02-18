"""Tests for Git infrastructure setup in implement-with-worktree."""

import os
import tempfile
import pytest

from git import Repo


@pytest.mark.unit
class TestIntegrationBranch:
    """Test integration branch creation and reuse."""

    def test_create_integration_branch_when_not_exists(self):
        """Should create integration branch if it doesn't exist."""
        from i2code.implement.git_setup import ensure_integration_branch

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
        from i2code.implement.git_setup import ensure_integration_branch

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
        from i2code.implement.git_setup import ensure_integration_branch

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

    def test_isolated_tracks_remote_branch_when_exists(self):
        """When isolated=True and remote branch exists, should create local tracking branch from remote."""
        from i2code.implement.git_setup import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a "remote" bare repo
            remote_path = os.path.join(tmpdir, "remote.git")
            Repo.init(remote_path, bare=True)

            # Create a local repo that pushes to the remote
            origin_path = os.path.join(tmpdir, "origin")
            origin_repo = Repo.init(origin_path)
            origin_repo.config_writer().set_value("user", "email", "test@test.com").release()
            origin_repo.config_writer().set_value("user", "name", "Test").release()

            # Add initial commit and push to remote
            readme = os.path.join(origin_path, "README.md")
            with open(readme, "w") as f:
                f.write("# Test")
            origin_repo.index.add(["README.md"])
            origin_repo.index.commit("Initial commit")
            origin_repo.create_remote("origin", remote_path)
            origin_repo.remotes.origin.push(origin_repo.active_branch.name)

            # Create integration branch with scaffolding and push it
            origin_repo.create_head("idea/my-feature/integration")
            origin_repo.heads["idea/my-feature/integration"].checkout()
            scaffold_file = os.path.join(origin_path, "scaffold.txt")
            with open(scaffold_file, "w") as f:
                f.write("scaffolding")
            origin_repo.index.add(["scaffold.txt"])
            origin_repo.index.commit("Add scaffolding")
            origin_repo.remotes.origin.push("idea/my-feature/integration")

            # Now clone to simulate the VM's fresh clone
            vm_path = os.path.join(tmpdir, "vm-clone")
            vm_repo = Repo.clone_from(remote_path, vm_path)
            vm_repo.config_writer().set_value("user", "email", "test@test.com").release()
            vm_repo.config_writer().set_value("user", "name", "Test").release()

            # The VM clone should NOT have the local branch yet
            assert "idea/my-feature/integration" not in [b.name for b in vm_repo.branches]

            # But the remote ref should exist
            remote_refs = [r.name for r in vm_repo.remotes.origin.refs]
            assert "origin/idea/my-feature/integration" in remote_refs

            # Call with isolated=True — should create local tracking branch from remote
            branch_name = ensure_integration_branch(vm_repo, "my-feature", isolated=True)

            assert branch_name == "idea/my-feature/integration"
            assert "idea/my-feature/integration" in [b.name for b in vm_repo.branches]

            # The local branch should point to the same commit as the remote
            local_commit = vm_repo.heads["idea/my-feature/integration"].commit.hexsha
            remote_commit = vm_repo.remotes.origin.refs["idea/my-feature/integration"].commit.hexsha
            assert local_commit == remote_commit

    def test_isolated_creates_from_head_when_no_remote(self):
        """When isolated=True but no remote branch exists, should fall back to creating from HEAD."""
        from i2code.implement.git_setup import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a bare remote
            remote_path = os.path.join(tmpdir, "remote.git")
            Repo.init(remote_path, bare=True)

            # Create local repo with remote
            local_path = os.path.join(tmpdir, "local")
            repo = Repo.init(local_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            readme = os.path.join(local_path, "README.md")
            with open(readme, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")
            repo.create_remote("origin", remote_path)
            repo.remotes.origin.push(repo.active_branch.name)

            # No integration branch on remote — isolated should fall back to HEAD
            branch_name = ensure_integration_branch(repo, "my-feature", isolated=True)

            assert branch_name == "idea/my-feature/integration"
            assert "idea/my-feature/integration" in [b.name for b in repo.branches]

            # Should point to HEAD since there's no remote branch
            assert repo.heads["idea/my-feature/integration"].commit == repo.head.commit

    def test_isolated_reuses_existing_local_branch(self):
        """When isolated=True and local branch already exists, should reuse it."""
        from i2code.implement.git_setup import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Repo.init(tmpdir)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            readme = os.path.join(tmpdir, "README.md")
            with open(readme, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create the integration branch manually
            repo.create_head("idea/my-feature/integration")

            branch_name = ensure_integration_branch(repo, "my-feature", isolated=True)

            assert branch_name == "idea/my-feature/integration"
            matching = [b for b in repo.branches if b.name == "idea/my-feature/integration"]
            assert len(matching) == 1

    def test_non_isolated_default_creates_from_head(self):
        """Default (isolated=False) behavior is unchanged — always creates from HEAD."""
        from i2code.implement.git_setup import ensure_integration_branch

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create bare remote with integration branch
            remote_path = os.path.join(tmpdir, "remote.git")
            Repo.init(remote_path, bare=True)

            origin_path = os.path.join(tmpdir, "origin")
            origin_repo = Repo.init(origin_path)
            origin_repo.config_writer().set_value("user", "email", "test@test.com").release()
            origin_repo.config_writer().set_value("user", "name", "Test").release()

            readme = os.path.join(origin_path, "README.md")
            with open(readme, "w") as f:
                f.write("# Test")
            origin_repo.index.add(["README.md"])
            origin_repo.index.commit("Initial commit")
            origin_repo.create_remote("origin", remote_path)
            origin_repo.remotes.origin.push(origin_repo.active_branch.name)

            # Push an integration branch with extra content
            origin_repo.create_head("idea/my-feature/integration")
            origin_repo.heads["idea/my-feature/integration"].checkout()
            scaffold = os.path.join(origin_path, "scaffold.txt")
            with open(scaffold, "w") as f:
                f.write("scaffolding")
            origin_repo.index.add(["scaffold.txt"])
            origin_repo.index.commit("Add scaffolding")
            origin_repo.remotes.origin.push("idea/my-feature/integration")

            # Clone it
            vm_path = os.path.join(tmpdir, "vm-clone")
            vm_repo = Repo.clone_from(remote_path, vm_path)
            vm_repo.config_writer().set_value("user", "email", "test@test.com").release()
            vm_repo.config_writer().set_value("user", "name", "Test").release()

            # Default call (isolated=False) — should create from HEAD, NOT track remote
            branch_name = ensure_integration_branch(vm_repo, "my-feature")

            assert branch_name == "idea/my-feature/integration"
            assert "idea/my-feature/integration" in [b.name for b in vm_repo.branches]

            # Should point to HEAD (master), not the remote integration branch
            assert vm_repo.heads["idea/my-feature/integration"].commit == vm_repo.head.commit


@pytest.mark.unit
class TestWorktree:
    """Test worktree creation and reuse."""

    def test_create_worktree_when_not_exists(self):
        """Should create worktree if it doesn't exist."""
        from i2code.implement.git_setup import ensure_integration_branch
        from i2code.implement.git_repository import GitRepository
        from fake_github_client import FakeGitHubClient

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo
            repo_path = os.path.join(tmpdir, "my-repo")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create integration branch
            integration_branch = ensure_integration_branch(repo, "my-feature")

            # Create worktree
            wt_repo = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("my-feature", integration_branch)

            expected_path = os.path.join(tmpdir, "my-repo-wt-my-feature")
            assert wt_repo.working_tree_dir == expected_path
            assert os.path.isdir(wt_repo.working_tree_dir)

    def test_reuse_existing_worktree(self):
        """Should reuse worktree if it already exists."""
        from i2code.implement.git_setup import ensure_integration_branch
        from i2code.implement.git_repository import GitRepository
        from fake_github_client import FakeGitHubClient

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo
            repo_path = os.path.join(tmpdir, "my-repo")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create integration branch
            integration_branch = ensure_integration_branch(repo, "my-feature")

            # Create worktree first time
            wt1 = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("my-feature", integration_branch)

            # Call again - should reuse, not error
            wt2 = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("my-feature", integration_branch)

            assert wt1.working_tree_dir == wt2.working_tree_dir

    def test_worktree_naming_pattern(self):
        """Worktree path should follow ../<repo-name>-wt-<idea-name> pattern."""
        from i2code.implement.git_setup import ensure_integration_branch
        from i2code.implement.git_repository import GitRepository
        from fake_github_client import FakeGitHubClient

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo with specific name
            repo_path = os.path.join(tmpdir, "genai-development-workflow")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create integration branch
            integration_branch = ensure_integration_branch(repo, "wt-pr-based-development")

            # Create worktree
            wt_repo = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("wt-pr-based-development", integration_branch)

            expected_path = os.path.join(tmpdir, "genai-development-workflow-wt-wt-pr-based-development")
            assert wt_repo.working_tree_dir == expected_path

    def test_copies_settings_local_json_to_worktree(self):
        """Should copy .claude/settings.local.json to worktree if it exists."""
        from i2code.implement.git_setup import ensure_integration_branch
        from i2code.implement.git_repository import GitRepository
        from fake_github_client import FakeGitHubClient

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo
            repo_path = os.path.join(tmpdir, "my-repo")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create .claude/settings.local.json in main repo
            claude_dir = os.path.join(repo_path, ".claude")
            os.makedirs(claude_dir)
            settings_file = os.path.join(claude_dir, "settings.local.json")
            with open(settings_file, "w") as f:
                f.write('{"permissions": {"allow": ["Bash(*)"]}}')

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create integration branch and worktree
            integration_branch = ensure_integration_branch(repo, "my-feature")
            wt_repo = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("my-feature", integration_branch)

            # Check that settings.local.json was copied to worktree
            worktree_settings = os.path.join(wt_repo.working_tree_dir, ".claude", "settings.local.json")
            assert os.path.isfile(worktree_settings), \
                f"settings.local.json should be copied to worktree at {worktree_settings}"

            # Verify content matches
            with open(worktree_settings, "r") as f:
                content = f.read()
            assert '"permissions"' in content

    def test_does_not_fail_if_settings_local_json_missing(self):
        """Should not fail if .claude/settings.local.json does not exist."""
        from i2code.implement.git_setup import ensure_integration_branch
        from i2code.implement.git_repository import GitRepository
        from fake_github_client import FakeGitHubClient

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main repo WITHOUT .claude/settings.local.json
            repo_path = os.path.join(tmpdir, "my-repo")
            os.makedirs(repo_path)
            repo = Repo.init(repo_path)
            repo.config_writer().set_value("user", "email", "test@test.com").release()
            repo.config_writer().set_value("user", "name", "Test").release()

            # Create an initial commit
            test_file = os.path.join(repo_path, "README.md")
            with open(test_file, "w") as f:
                f.write("# Test")
            repo.index.add(["README.md"])
            repo.index.commit("Initial commit")

            # Create integration branch and worktree - should not fail
            integration_branch = ensure_integration_branch(repo, "my-feature")
            wt_repo = GitRepository(repo, gh_client=FakeGitHubClient()).ensure_worktree("my-feature", integration_branch)

            # Worktree should exist
            assert os.path.isdir(wt_repo.working_tree_dir)


@pytest.mark.unit
class TestSliceBranch:
    """Test slice branch creation and naming."""

    def test_create_slice_branch(self):
        """Should create slice branch with correct naming."""
        from i2code.implement.git_setup import ensure_slice_branch

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

            # Create integration branch
            repo.create_head("idea/my-feature/integration")

            branch_name = ensure_slice_branch(
                repo,
                "my-feature",
                slice_number=1,
                slice_name="project-setup",
                integration_branch="idea/my-feature/integration"
            )

            assert branch_name == "idea/my-feature/01-project-setup"
            assert "idea/my-feature/01-project-setup" in [b.name for b in repo.branches]

    def test_slice_branch_zero_padded_number(self):
        """Slice number should be zero-padded to 2 digits."""
        from i2code.implement.git_setup import ensure_slice_branch

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

            repo.create_head("idea/my-feature/integration")

            branch_name = ensure_slice_branch(
                repo,
                "my-feature",
                slice_number=5,
                slice_name="feedback-handling",
                integration_branch="idea/my-feature/integration"
            )

            assert branch_name == "idea/my-feature/05-feedback-handling"

    def test_reuse_existing_slice_branch(self):
        """Should reuse slice branch if it already exists."""
        from i2code.implement.git_setup import ensure_slice_branch

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

            repo.create_head("idea/my-feature/integration")
            # Create slice branch manually
            repo.create_head("idea/my-feature/01-project-setup")

            branch_name = ensure_slice_branch(
                repo,
                "my-feature",
                slice_number=1,
                slice_name="project-setup",
                integration_branch="idea/my-feature/integration"
            )

            assert branch_name == "idea/my-feature/01-project-setup"
            # Should still have exactly one branch with that name
            matching = [b for b in repo.branches if b.name == "idea/my-feature/01-project-setup"]
            assert len(matching) == 1


@pytest.mark.unit
class TestSliceNameSanitization:
    """Test sanitizing task names for branch names."""

    def test_sanitize_simple_name(self):
        """Simple names should pass through with lowercase."""
        from i2code.implement.git_setup import sanitize_branch_name

        assert sanitize_branch_name("Project Setup") == "project-setup"

    def test_sanitize_removes_special_chars(self):
        """Special characters should be removed or replaced."""
        from i2code.implement.git_setup import sanitize_branch_name

        assert sanitize_branch_name("Task 1.1: Create files") == "task-1-1-create-files"

    def test_sanitize_collapses_multiple_dashes(self):
        """Multiple dashes should be collapsed to one."""
        from i2code.implement.git_setup import sanitize_branch_name

        assert sanitize_branch_name("foo---bar") == "foo-bar"

    def test_sanitize_strips_leading_trailing_dashes(self):
        """Leading and trailing dashes should be stripped."""
        from i2code.implement.git_setup import sanitize_branch_name

        assert sanitize_branch_name("--foo-bar--") == "foo-bar"
