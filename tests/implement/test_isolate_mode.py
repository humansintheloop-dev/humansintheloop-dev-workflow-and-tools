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
from fake_repo_cloner import FakeRepoCloner


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


def _noop_project_setup(git_repo):
    pass


def _make_mode(project=None, git_repo=None, setup_success=True, clone_creator=None):
    """Build an IsolateMode with fakes, returning (mode, initializer, subprocess_runner, clone_creator).

    Default paths place the project directory inside the git repo so that
    worktree_idea_project computes sensible relative paths.
    """
    git_repo = git_repo or FakeGitRepository()
    project = project or FakeIdeaProject(
        directory=os.path.join(git_repo.working_tree_dir, "docs/features/test-feature"),
    )
    initializer = _make_fake_project_scaffolder(setup_success)
    subprocess_runner = FakeSubprocessRunner()
    clone_creator = clone_creator or FakeRepoCloner()
    workspace = Workspace(git_repo=git_repo, project=project)

    def scaffolder_factory(wt_git_repo):
        return initializer

    worktree_setup = WorktreeSetupDeps(
        scaffolder_factory=scaffolder_factory,
        clone_creator=clone_creator,
        project_setup_fn=_noop_project_setup,
    )
    mode = IsolateMode(
        workspace=workspace,
        worktree_setup=worktree_setup,
        subprocess_runner=subprocess_runner,
    )
    return mode, initializer, subprocess_runner, clone_creator


def _opts(**kwargs):
    """Build ImplementOpts with defaults suitable for IsolateMode tests."""
    kwargs.setdefault("idea_directory", "/tmp/fake-idea")
    return ImplementOpts(**kwargs)


def _execute_and_get_cmd(options=None, project=None, git_repo=None):
    """Execute IsolateMode and return the subprocess command."""
    if options is None:
        options = _opts()
    mode, _, subprocess_runner, _ = _make_mode(project=project, git_repo=git_repo)
    mode.execute(options)
    return subprocess_runner.calls[0][1]


@pytest.mark.unit
class TestIsolateModeExecute:
    """IsolateMode.execute() runs project setup then delegates to isolarium."""

    def test_calls_ensure_scaffolding_setup_then_runs_subprocess(self):
        mode, initializer, subprocess_runner, _ = _make_mode()
        returncode = mode.execute(_opts())

        assert any(c[0] == "ensure_scaffolding_setup" for c in initializer._setup_calls)
        assert len(subprocess_runner.calls) == 1
        assert returncode == 0

    def test_exits_when_project_setup_fails(self):
        mode, _, subprocess_runner, _ = _make_mode(setup_success=False)

        with pytest.raises(SystemExit) as exc_info:
            mode.execute(_opts())

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
        mode, _, subprocess_runner, _ = _make_mode()
        subprocess_runner.set_returncode(42)
        returncode = mode.execute(_opts())

        assert returncode == 42

    def test_forwards_setup_parameters(self):
        options = _opts(
            non_interactive=True,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
            ci_timeout=900,
            skip_ci_wait=True,
        )
        mode, initializer, _, _ = _make_mode()
        mode.execute(options)

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
    """IsolateMode calls clone_creator after scaffolding and uses clone path as subprocess cwd."""

    def test_clone_named_relative_to_original_repo_not_worktree(self):
        """Clone dir should be <original_repo>-cl-<idea>, not <worktree>-cl-<idea>."""
        git_repo = FakeGitRepository(working_tree_dir="/home/user/project")
        project = FakeIdeaProject(
            name="my-feature",
            directory="/home/user/project/docs/features/my-feature",
        )
        clone_creator = FakeRepoCloner(clone_path="/home/user/project-cl-my-feature")
        mode, _, _, _ = _make_mode(
            git_repo=git_repo, project=project, clone_creator=clone_creator,
        )

        mode.execute(_opts())

        assert len(clone_creator.calls) == 1
        call = clone_creator.calls[0]
        # source is worktree, but clone_base is original repo
        assert call == (
            "create_clone",
            "/home/user/project-wt-my-feature",
            "my-feature",
            "https://github.com/test/repo.git",
            "/home/user/project",
        )

    def test_subprocess_cwd_is_clone_path(self):
        clone_creator = FakeRepoCloner(clone_path="/tmp/clone-dir")
        mode, _, subprocess_runner, _ = _make_mode(clone_creator=clone_creator)

        mode.execute(_opts())

        assert len(subprocess_runner.calls) == 1
        _, _, cwd = subprocess_runner.calls[0]
        assert cwd == "/tmp/clone-dir"

    def test_create_clone_not_called_when_scaffolding_fails(self):
        clone_creator = FakeRepoCloner()
        mode, _, _, _ = _make_mode(setup_success=False, clone_creator=clone_creator)

        with pytest.raises(SystemExit):
            mode.execute(_opts())

        assert len(clone_creator.calls) == 0


@pytest.mark.unit
class TestIsolateModeSkipsWorktreeWhenCloneExists:
    """execute() skips worktree and scaffolding when clone directory already exists."""

    def _make_mode_with_clone(self, tmp_path):
        repo_dir = str(tmp_path / "my-repo")
        os.makedirs(repo_dir)
        clone_dir = str(tmp_path / "my-repo-cl-test-feature")
        os.makedirs(clone_dir)

        git_repo = FakeGitRepository(working_tree_dir=repo_dir)
        project = FakeIdeaProject(
            name="test-feature",
            directory=os.path.join(repo_dir, "docs/features/test-feature"),
        )
        mode, initializer, subprocess_runner, clone_creator = _make_mode(
            git_repo=git_repo, project=project,
        )
        return mode, git_repo, initializer, subprocess_runner, clone_creator

    def test_worktree_not_created(self, tmp_path):
        mode, git_repo, _, _, _ = self._make_mode_with_clone(tmp_path)
        mode.execute(_opts())
        assert not any(c[0] == "ensure_worktree" for c in git_repo.calls)

    def test_scaffolding_not_called(self, tmp_path):
        mode, _, initializer, _, _ = self._make_mode_with_clone(tmp_path)
        mode.execute(_opts())
        assert len(initializer._setup_calls) == 0

    def test_clone_not_created(self, tmp_path):
        mode, _, _, _, clone_creator = self._make_mode_with_clone(tmp_path)
        mode.execute(_opts())
        assert len(clone_creator.calls) == 0

    def test_subprocess_still_runs(self, tmp_path):
        mode, _, _, subprocess_runner, _ = self._make_mode_with_clone(tmp_path)
        mode.execute(_opts())
        assert len(subprocess_runner.calls) == 1

    def test_subprocess_runs_in_clone_directory(self, tmp_path):
        mode, _, _, subprocess_runner, _ = self._make_mode_with_clone(tmp_path)
        mode.execute(_opts())
        clone_dir = str(tmp_path / "my-repo-cl-test-feature")
        _, _, cwd = subprocess_runner.calls[0]
        assert cwd == clone_dir, (
            f"Expected isolarium to run in clone {clone_dir}, got {cwd}"
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
        mode, _, _, _ = _make_mode(git_repo=git_repo, project=project)
        mode.execute(_opts())

        branch_calls = [c for c in git_repo.calls if c[0] == "ensure_branch"]
        assert len(branch_calls) == 1
        assert branch_calls[0][1] == "idea/my-feature"

        wt_calls = [c for c in git_repo.calls if c[0] == "ensure_worktree"]
        assert len(wt_calls) == 1
        assert wt_calls[0] == ("ensure_worktree", "my-feature", "idea/my-feature")

    def test_calls_project_setup_fn_with_worktree_git_repo(self):
        setup_calls = []

        def tracking_setup(git_repo):
            setup_calls.append(git_repo)

        mode, _, _, _ = _make_mode()
        mode._project_setup_fn = tracking_setup
        mode.execute(_opts())

        assert len(setup_calls) == 1
        assert setup_calls[0].is_worktree


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
