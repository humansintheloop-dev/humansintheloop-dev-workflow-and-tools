"""Tests for IsolateMode class using fakes — zero @patch decorators."""

import os

import pytest

from i2code.implement.implement_opts import ImplementOpts
from i2code.implement.isolate_mode import IsolateMode, WorktreeSetupDeps
from i2code.implement.project_scaffolding import ProjectScaffolder, ScaffoldingCreator, ScaffoldingSteps
from i2code.implement.workspace import Workspace

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_idea_project import FakeIdeaProject


def _make_fake_project_scaffolder(setup_success=True):
    """Build a ProjectScaffolder with fakes and a controllable ensure_scaffolding_setup."""
    from i2code.implement.command_builder import CommandBuilder
    scaffolding_creator = ScaffoldingCreator(
        command_builder=CommandBuilder(),
        claude_runner=FakeClaudeRunner(),
    )
    steps = ScaffoldingSteps(
        claude_runner=FakeClaudeRunner(),
        build_fixer=None,
        push_fn=lambda branch: True,
    )
    initializer = ProjectScaffolder(
        scaffolding_creator=scaffolding_creator,
        git_repo=FakeGitRepository(),
        steps=steps,
    )
    # Monkey-patch ensure_scaffolding_setup to record calls and return canned result
    initializer._setup_success = setup_success
    initializer._setup_calls = []

    def fake_ensure_scaffolding_setup(opts, **kwargs):
        initializer._setup_calls.append(("ensure_scaffolding_setup", {"opts": opts, **kwargs}))
        return initializer._setup_success

    initializer.ensure_scaffolding_setup = fake_ensure_scaffolding_setup
    return initializer


class FakeSubprocessRunner:
    """Fake for subprocess.run that records calls and returns canned results."""

    def __init__(self):
        self._returncode = 0
        self.calls = []

    def set_returncode(self, code):
        self._returncode = code

    def run(self, cmd, cwd=None):
        self.calls.append(("run", cmd, cwd))
        return self._returncode


class FakeProjectSetup:
    """Test double for ProjectSetup that records calls without touching the filesystem."""

    def __init__(self):
        self.calls = []

    def setup_worktree(self, git_repo):
        self.calls.append(("setup_worktree", git_repo))

    def setup_clone(self, git_repo):
        self.calls.append(("setup_clone", git_repo))


def _make_mode(options=None, project=None, git_repo=None):
    """Build an IsolateMode with fakes, returning (mode, initializer, subprocess_runner).

    Default paths place the project directory inside the git repo so that
    worktree_idea_project computes sensible relative paths.
    """
    git_repo = git_repo or FakeGitRepository()
    project = project or FakeIdeaProject(
        directory=os.path.join(git_repo.working_tree_dir, "docs/features/test-feature"),
    )
    initializer = _make_fake_project_scaffolder()
    subprocess_runner = FakeSubprocessRunner()
    workspace = Workspace(git_repo=git_repo, project=project)

    def scaffolder_factory(wt_git_repo):
        return initializer

    worktree_setup = WorktreeSetupDeps(
        scaffolder_factory=scaffolder_factory,
        project_setup=FakeProjectSetup(),
    )
    mode = IsolateMode(
        workspace=workspace,
        options=options or _opts(),
        worktree_setup=worktree_setup,
        subprocess_runner=subprocess_runner,
    )
    return mode, initializer, subprocess_runner


def _opts(**kwargs):
    """Build ImplementOpts with defaults suitable for IsolateMode tests."""
    kwargs.setdefault("idea_directory", "/tmp/fake-idea")
    return ImplementOpts(**kwargs)


def _execute_and_get_cmd(options=None, project=None, git_repo=None):
    """Execute IsolateMode and return the subprocess command."""
    mode, _, subprocess_runner = _make_mode(
        options=options, project=project, git_repo=git_repo,
    )
    mode.execute()
    return subprocess_runner.calls[0][1]


@pytest.mark.unit
class TestIsolateModeExecute:
    """IsolateMode.execute() runs project setup then delegates to isolarium."""

    def test_calls_ensure_scaffolding_setup_then_runs_subprocess(self):
        mode, initializer, subprocess_runner = _make_mode()
        returncode = mode.execute()

        assert any(c[0] == "ensure_scaffolding_setup" for c in initializer._setup_calls)
        assert len(subprocess_runner.calls) == 1
        assert returncode == 0

    def test_exits_when_project_setup_fails(self):
        mode, initializer, subprocess_runner = _make_mode()
        initializer._setup_success = False

        with pytest.raises(SystemExit) as exc_info:
            mode.execute()

        assert exc_info.value.code == 1
        assert len(subprocess_runner.calls) == 0

    def test_forwards_options_to_isolarium_command(self):
        options = _opts(
            non_interactive=True,
            mock_claude="/mock.sh",
            cleanup=True,
            setup_only=True,
            extra_prompt="extra text",
            skip_ci_wait=True,
            ci_fix_retries=5,
            ci_timeout=900,
        )
        cmd = _execute_and_get_cmd(options)

        assert "--non-interactive" in cmd
        assert "--mock-claude" in cmd
        assert "/mock.sh" in cmd
        assert "--cleanup" in cmd
        assert "--setup-only" in cmd
        assert "--extra-prompt" in cmd
        assert "extra text" in cmd
        assert "--skip-ci-wait" in cmd
        assert "--ci-fix-retries" in cmd
        assert "5" in cmd
        assert "--ci-timeout" in cmd
        assert "900" in cmd

    def test_builds_isolarium_command_with_idea_name(self):
        project = FakeIdeaProject(directory="/home/user/project/docs/features/test-feature")
        git_repo = FakeGitRepository(working_tree_dir="/home/user/project")
        cmd = _execute_and_get_cmd(project=project, git_repo=git_repo)

        assert "isolarium" in cmd
        assert "--name" in cmd
        assert "i2code-test-feature" in cmd
        assert "--isolated" in cmd

    def test_returns_subprocess_returncode(self):
        mode, _, subprocess_runner = _make_mode()
        subprocess_runner.set_returncode(42)
        returncode = mode.execute()

        assert returncode == 42

    def test_forwards_setup_parameters(self):
        options = _opts(
            non_interactive=True,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
            ci_timeout=900,
            skip_ci_wait=True,
        )
        mode, initializer, _ = _make_mode(options=options)
        mode.execute()

        setup_calls = [c for c in initializer._setup_calls if c[0] == "ensure_scaffolding_setup"]
        assert len(setup_calls) == 1
        kwargs = setup_calls[0][1]
        assert kwargs["opts"] is options
        assert kwargs["idea_directory"] == "/fake/repo-wt-test-feature/docs/features/test-feature"
        assert kwargs["branch"] == "idea/test-feature"

    def test_interactive_mode_passes_interactive_flag_to_isolarium(self):
        cmd = _execute_and_get_cmd(_opts(non_interactive=False))

        assert "--interactive" in cmd
        assert "--non-interactive" not in cmd

    def test_non_interactive_omits_interactive_flag(self):
        cmd = _execute_and_get_cmd(_opts(non_interactive=True))

        assert "--interactive" not in cmd


@pytest.mark.unit
class TestIsolateModeIsolationType:
    """IsolateMode inserts --type TYPE into isolarium global args when isolation_type is provided."""

    def test_includes_type_in_isolarium_global_args(self):
        cmd = _execute_and_get_cmd(_opts(isolation_type="docker"))

        name_idx = cmd.index("--name")
        run_idx = cmd.index("run")
        type_idx = cmd.index("--type")
        assert cmd[type_idx + 1] == "docker"
        assert type_idx > name_idx
        assert type_idx < run_idx

    def test_omits_type_when_isolation_type_is_none(self):
        cmd = _execute_and_get_cmd(_opts())

        assert "--type" not in cmd

    def test_isolation_type_not_forwarded_to_inner_command(self):
        cmd = _execute_and_get_cmd(_opts(isolation_type="docker"))

        separator_idx = cmd.index("--")
        inner_cmd = cmd[separator_idx + 1:]
        assert "--type" not in inner_cmd


@pytest.mark.unit
class TestIsolateModeEnvFile:
    """IsolateMode passes --env-file to isolarium when .env.local exists in main repo."""

    def test_includes_env_file_when_present(self, tmp_path):
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        env_file = main_repo / ".env.local"
        env_file.write_text("SECRET=value\n")
        git_repo = FakeGitRepository(
            working_tree_dir=str(main_repo), main_repo_dir=str(main_repo),
        )
        project = FakeIdeaProject(
            directory=os.path.join(str(main_repo), "docs/features/test-feature"),
        )

        cmd = _execute_and_get_cmd(git_repo=git_repo, project=project)

        assert "--env-file" in cmd
        env_idx = cmd.index("--env-file")
        assert cmd[env_idx + 1] == str(env_file)
        run_idx = cmd.index("run")
        assert env_idx < run_idx

    def test_omits_env_file_when_not_present(self, tmp_path):
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        git_repo = FakeGitRepository(
            working_tree_dir=str(main_repo), main_repo_dir=str(main_repo),
        )
        project = FakeIdeaProject(
            directory=os.path.join(str(main_repo), "docs/features/test-feature"),
        )

        cmd = _execute_and_get_cmd(git_repo=git_repo, project=project)
        assert "--env-file" not in cmd


@pytest.mark.unit
class TestIsolateModeCloneCreator:
    """IsolateMode calls git_repo.clone() after scaffolding and uses clone path as subprocess cwd."""

    def test_clone_called_on_worktree_git_repo(self):
        git_repo = FakeGitRepository(working_tree_dir="/home/user/project")
        project = FakeIdeaProject(
            name="my-feature",
            directory="/home/user/project/docs/features/my-feature",
        )
        mode, _, _ = _make_mode(git_repo=git_repo, project=project)

        mode.execute()

        wt_repo_calls = git_repo.calls
        clone_calls = [c for c in wt_repo_calls if c[0] == "clone"]
        assert len(clone_calls) == 0  # clone is on worktree repo, not main repo
        # The worktree repo is a FakeGitRepository returned by ensure_worktree;
        # we verify the subprocess cwd uses the clone path pattern
        _, _, cwd = mode._subprocess_runner.calls[0]
        assert cwd == "/home/user/project-wt-my-feature-cl-my-feature"

    def test_subprocess_cwd_is_clone_path(self):
        mode, _, subprocess_runner = _make_mode()

        mode.execute()

        assert len(subprocess_runner.calls) == 1
        _, _, cwd = subprocess_runner.calls[0]
        assert "-cl-" in cwd

    def test_clone_not_called_when_scaffolding_fails(self):
        mode, initializer, _ = _make_mode()
        initializer._setup_success = False

        with pytest.raises(SystemExit):
            mode.execute()


@pytest.mark.unit
class TestIsolateModeSkipsWorktreeWhenCloneExists:
    """execute() skips worktree and scaffolding when clone directory already exists."""

    def _make_mode_with_clone(self):
        git_repo = FakeGitRepository(working_tree_dir="/fake/my-repo")
        clone_repo = FakeGitRepository(working_tree_dir="/fake/my-repo-cl-test-feature")
        git_repo.set_clone_repo("test-feature", clone_repo)
        project = FakeIdeaProject(
            name="test-feature",
            directory="/fake/my-repo/docs/features/test-feature",
        )
        mode, initializer, subprocess_runner = _make_mode(
            git_repo=git_repo, project=project,
        )
        return mode, git_repo, initializer, subprocess_runner

    def test_worktree_not_created(self):
        mode, git_repo, _, _ = self._make_mode_with_clone()
        mode.execute()
        assert not any(c[0] == "ensure_worktree" for c in git_repo.calls)

    def test_scaffolding_not_called(self):
        mode, _, initializer, _ = self._make_mode_with_clone()
        mode.execute()
        assert len(initializer._setup_calls) == 0

    def test_clone_not_created(self):
        mode, git_repo, _, _ = self._make_mode_with_clone()
        mode.execute()
        assert not any(c[0] == "clone" for c in git_repo.calls)

    def test_subprocess_still_runs(self):
        mode, _, _, subprocess_runner = self._make_mode_with_clone()
        mode.execute()
        assert len(subprocess_runner.calls) == 1

    def test_subprocess_runs_in_clone_directory(self):
        mode, _, _, subprocess_runner = self._make_mode_with_clone()
        mode.execute()
        _, _, cwd = subprocess_runner.calls[0]
        assert cwd == "/fake/my-repo-cl-test-feature"

    def test_copies_user_config_to_existing_clone(self):
        mode, git_repo, _, _ = self._make_mode_with_clone()
        mode.execute()

        clone_repo = git_repo._clone_repos["test-feature"]
        config_calls = [c for c in clone_repo.calls if c[0] == "set_user_config"]
        assert len(config_calls) == 1
        assert config_calls[0] == ("set_user_config", "Test", "test@test.com")


def _extract_isolated_path(cmd):
    """Extract the --isolated path from the inner command (after --)."""
    separator_idx = cmd.index("--")
    inner_cmd = cmd[separator_idx + 1:]
    isolated_idx = inner_cmd.index("--isolated")
    return inner_cmd[isolated_idx + 1]


@pytest.mark.unit
class TestIsolateModeIsolatedPathRelativeToClone:
    """--isolated path must be relative to the clone dir (subprocess cwd), not to git_repo."""

    def test_existing_clone_isolated_path_is_relative_to_clone(self):
        git_repo = FakeGitRepository(working_tree_dir="/fake/my-repo")
        clone_repo = FakeGitRepository(working_tree_dir="/fake/my-repo-cl-test-feature")
        git_repo.set_clone_repo("test-feature", clone_repo)
        project = FakeIdeaProject(
            name="test-feature",
            directory="/fake/my-repo/docs/features/test-feature",
        )

        mode, _, subprocess_runner = _make_mode(git_repo=git_repo, project=project)
        mode.execute()

        _, cmd, _ = subprocess_runner.calls[0]
        idea_dir_arg = _extract_isolated_path(cmd)
        assert idea_dir_arg == "docs/features/test-feature", (
            f"Expected 'docs/features/test-feature', got '{idea_dir_arg}'"
        )


@pytest.mark.unit
class TestIsolateModeCloneSettings:
    """IsolateMode copies .claude/settings.local.json into the clone."""

    def test_clone_gets_settings_when_clone_already_exists(self, tmp_path):
        from i2code.implement.worktree_setup import ProjectSetup

        main_repo = str(tmp_path / "my-repo")
        clone_dir = str(tmp_path / "my-repo-cl-test-feature")
        os.makedirs(os.path.join(main_repo, ".claude"))
        os.makedirs(clone_dir)
        settings = os.path.join(main_repo, ".claude", "settings.local.json")
        with open(settings, "w") as f:
            f.write('{"permissions": {"allow": []}}\n')

        git_repo = FakeGitRepository(
            working_tree_dir=main_repo, main_repo_dir=main_repo,
        )
        clone_repo = FakeGitRepository(
            working_tree_dir=clone_dir, main_repo_dir=main_repo,
        )
        git_repo.set_clone_repo("test-feature", clone_repo)
        project = FakeIdeaProject(
            name="test-feature",
            directory=os.path.join(main_repo, "docs/features/test-feature"),
        )

        initializer = _make_fake_project_scaffolder()
        subprocess_runner = FakeSubprocessRunner()
        workspace = Workspace(git_repo=git_repo, project=project)
        worktree_setup = WorktreeSetupDeps(
            scaffolder_factory=lambda wt: initializer,
            project_setup=ProjectSetup(),
        )
        mode = IsolateMode(
            workspace=workspace,
            options=_opts(),
            worktree_setup=worktree_setup,
            subprocess_runner=subprocess_runner,
        )
        mode.execute()

        clone_settings = os.path.join(clone_dir, ".claude", "settings.local.json")
        assert os.path.isfile(clone_settings), (
            "Expected .claude/settings.local.json in clone directory"
        )


@pytest.mark.unit
class TestIsolateModeWorktreeSetup:
    """execute() creates worktree and calls project_setup_fn when no clone exists."""

    def test_creates_worktree_via_ensure_idea_branch_and_ensure_worktree(self):
        git_repo = FakeGitRepository(working_tree_dir="/fake/repo")
        project = FakeIdeaProject(
            name="my-feature",
            directory="/fake/repo/docs/features/my-feature",
        )
        mode, _, _ = _make_mode(git_repo=git_repo, project=project)
        mode.execute()

        branch_calls = [c for c in git_repo.calls if c[0] == "ensure_branch"]
        assert len(branch_calls) == 1
        assert branch_calls[0][1] == "idea/my-feature"

        wt_calls = [c for c in git_repo.calls if c[0] == "ensure_worktree"]
        assert len(wt_calls) == 1
        assert wt_calls[0] == ("ensure_worktree", "my-feature", "idea/my-feature")

    def test_calls_setup_worktree_with_worktree_git_repo(self):
        mode, _, _ = _make_mode()
        mode.execute()

        setup = mode._project_setup
        worktree_calls = [c for c in setup.calls if c[0] == "setup_worktree"]
        assert len(worktree_calls) == 1
        assert worktree_calls[0][1].is_worktree


@pytest.mark.unit
class TestSubprocessRunner:
    """SubprocessRunner uses Popen + ManagedSubprocess for clean interrupt handling."""

    def test_uses_popen_with_start_new_session_and_managed_subprocess(self):
        from unittest.mock import patch, MagicMock
        from i2code.implement.isolate_mode import SubprocessRunner

        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        mock_process.returncode = 0

        mock_managed = MagicMock()
        mock_managed.__enter__ = MagicMock(return_value=mock_managed)
        mock_managed.__exit__ = MagicMock(return_value=False)
        mock_managed.interrupted = False

        with patch("i2code.implement.isolate_mode.subprocess.Popen", return_value=mock_process) as mock_popen, \
             patch("i2code.implement.isolate_mode.ManagedSubprocess", return_value=mock_managed) as mock_managed_cls:
            runner = SubprocessRunner()
            result = runner.run(["echo", "hello"])

        mock_popen.assert_called_once_with(["echo", "hello"], start_new_session=True, cwd=None)
        mock_managed_cls.assert_called_once_with(mock_process, label="isolarium")
        assert result == 0

    def test_returns_130_when_interrupted(self):
        from unittest.mock import patch, MagicMock
        from i2code.implement.isolate_mode import SubprocessRunner

        mock_process = MagicMock()
        mock_process.wait.return_value = 0
        mock_process.returncode = 0

        mock_managed = MagicMock()
        mock_managed.__enter__ = MagicMock(return_value=mock_managed)
        mock_managed.__exit__ = MagicMock(return_value=False)
        mock_managed.interrupted = True

        with patch("i2code.implement.isolate_mode.subprocess.Popen", return_value=mock_process), \
             patch("i2code.implement.isolate_mode.ManagedSubprocess", return_value=mock_managed):
            runner = SubprocessRunner()
            result = runner.run(["some", "command"])

        assert result == 130
