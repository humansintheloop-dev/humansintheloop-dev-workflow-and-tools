"""Tests for IsolateMode class using fakes — zero @patch decorators."""

import pytest

from i2code.implement.isolate_mode import IsolateMode, IsolateOptions
from i2code.implement.project_setup import ProjectInitializer

from fake_claude_runner import FakeClaudeRunner
from fake_git_repository import FakeGitRepository
from fake_idea_project import FakeIdeaProject


def _make_fake_project_initializer(setup_success=True):
    """Build a ProjectInitializer with fakes and a controllable ensure_project_setup."""
    from i2code.implement.command_builder import CommandBuilder
    initializer = ProjectInitializer(
        claude_runner=FakeClaudeRunner(),
        command_builder=CommandBuilder(),
        git_repo=FakeGitRepository(),
        build_fixer=None,
        push_fn=lambda branch: True,
    )
    # Monkey-patch ensure_project_setup to record calls and return canned result
    initializer._setup_success = setup_success
    initializer._setup_calls = []

    def fake_ensure_project_setup(**kwargs):
        initializer._setup_calls.append(("ensure_project_setup", kwargs))
        return initializer._setup_success

    initializer.ensure_project_setup = fake_ensure_project_setup
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


def _make_mode(project=None, git_repo=None, setup_success=True):
    """Build an IsolateMode with fakes, returning (mode, initializer, subprocess_runner)."""
    initializer = _make_fake_project_initializer(setup_success)
    subprocess_runner = FakeSubprocessRunner()
    mode = IsolateMode(
        git_repo=git_repo or FakeGitRepository(),
        project=project or FakeIdeaProject(),
        project_initializer=initializer,
        subprocess_runner=subprocess_runner,
    )
    return mode, initializer, subprocess_runner


def _execute_and_get_cmd(options=None, project=None, git_repo=None):
    """Execute IsolateMode and return the subprocess command."""
    mode, _, subprocess_runner = _make_mode(project=project, git_repo=git_repo)
    mode.execute(options)
    return subprocess_runner.calls[0][1]


@pytest.mark.unit
class TestIsolateModeExecute:
    """IsolateMode.execute() runs project setup then delegates to isolarium."""

    def test_calls_ensure_project_setup_then_runs_subprocess(self):
        mode, initializer, subprocess_runner = _make_mode()
        returncode = mode.execute()

        assert any(c[0] == "ensure_project_setup" for c in initializer._setup_calls)
        assert len(subprocess_runner.calls) == 1
        assert returncode == 0

    def test_exits_when_project_setup_fails(self):
        mode, _, subprocess_runner = _make_mode(setup_success=False)

        with pytest.raises(SystemExit) as exc_info:
            mode.execute()

        assert exc_info.value.code == 1
        assert len(subprocess_runner.calls) == 0

    def test_forwards_options_to_isolarium_command(self):
        options = IsolateOptions(
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
        options = IsolateOptions(
            non_interactive=True,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
            ci_timeout=900,
            skip_ci_wait=True,
        )
        mode, initializer, _ = _make_mode()
        mode.execute(options)

        setup_calls = [c for c in initializer._setup_calls if c[0] == "ensure_project_setup"]
        assert len(setup_calls) == 1
        kwargs = setup_calls[0][1]
        assert kwargs["idea_directory"] == "/tmp/fake-idea"
        assert kwargs["branch"] == "idea/test-feature"
        assert kwargs["interactive"] is False
        assert kwargs["mock_claude"] == "/mock.sh"
        assert kwargs["ci_timeout"] == 900
        assert kwargs["skip_ci_wait"] is True

    def test_interactive_mode_passes_interactive_flag_to_isolarium(self):
        cmd = _execute_and_get_cmd(IsolateOptions(non_interactive=False))

        assert "--interactive" in cmd
        assert "--non-interactive" not in cmd

    def test_non_interactive_omits_interactive_flag(self):
        cmd = _execute_and_get_cmd(IsolateOptions(non_interactive=True))

        assert "--interactive" not in cmd


@pytest.mark.unit
class TestIsolateModeIsolationType:
    """IsolateMode inserts --type TYPE into isolarium global args when isolation_type is provided."""

    def test_includes_type_in_isolarium_global_args(self):
        cmd = _execute_and_get_cmd(IsolateOptions(isolation_type="docker"))

        name_idx = cmd.index("--name")
        run_idx = cmd.index("run")
        type_idx = cmd.index("--type")
        assert cmd[type_idx + 1] == "docker"
        assert type_idx > name_idx
        assert type_idx < run_idx

    def test_omits_type_when_isolation_type_is_none(self):
        cmd = _execute_and_get_cmd(IsolateOptions())

        assert "--type" not in cmd

    def test_isolation_type_not_forwarded_to_inner_command(self):
        cmd = _execute_and_get_cmd(IsolateOptions(isolation_type="docker"))

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
        git_repo = FakeGitRepository(main_repo_dir=str(main_repo))

        cmd = _execute_and_get_cmd(git_repo=git_repo)

        assert "--env-file" in cmd
        env_idx = cmd.index("--env-file")
        assert cmd[env_idx + 1] == str(env_file)
        run_idx = cmd.index("run")
        assert env_idx < run_idx

    def test_omits_env_file_when_not_present(self, tmp_path):
        main_repo = tmp_path / "main-repo"
        main_repo.mkdir()
        git_repo = FakeGitRepository(main_repo_dir=str(main_repo))

        cmd = _execute_and_get_cmd(git_repo=git_repo)
        assert "--env-file" not in cmd


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
