"""Tests for IsolateMode class using fakes — zero @patch decorators."""

import pytest

from i2code.implement.isolate_mode import IsolateMode
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

    def run(self, cmd):
        self.calls.append(("run", cmd))
        return self._returncode


@pytest.mark.unit
class TestIsolateModeExecute:
    """IsolateMode.execute() runs project setup then delegates to isolarium."""

    def test_calls_ensure_project_setup_then_runs_subprocess(self):
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        returncode = mode.execute()

        assert any(c[0] == "ensure_project_setup" for c in fake_initializer._setup_calls)
        assert len(fake_subprocess.calls) == 1
        assert returncode == 0

    def test_exits_when_project_setup_fails(self):
        fake_initializer = _make_fake_project_initializer(setup_success=False)
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )

        with pytest.raises(SystemExit) as exc_info:
            mode.execute()

        assert exc_info.value.code == 1
        assert len(fake_subprocess.calls) == 0

    def test_forwards_options_to_isolarium_command(self):
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        mode.execute(
            non_interactive=True,
            mock_claude="/mock.sh",
            cleanup=True,
            setup_only=True,
            extra_prompt="extra text",
            skip_ci_wait=True,
            ci_fix_retries=5,
            ci_timeout=900,
        )

        cmd = fake_subprocess.calls[0][1]
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
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject(directory="/home/user/project/docs/features/test-feature")

        mode = IsolateMode(
            git_repo=FakeGitRepository(working_tree_dir="/home/user/project"),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        mode.execute()

        cmd = fake_subprocess.calls[0][1]
        assert "isolarium" in cmd
        assert "--name" in cmd
        assert "i2code-test-feature" in cmd
        assert "--isolated" in cmd

    def test_returns_subprocess_returncode(self):
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        fake_subprocess.set_returncode(42)
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        returncode = mode.execute()

        assert returncode == 42

    def test_forwards_setup_parameters(self):
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        mode.execute(
            non_interactive=True,
            mock_claude="/mock.sh",
            ci_fix_retries=5,
            ci_timeout=900,
            skip_ci_wait=True,
        )

        setup_calls = [c for c in fake_initializer._setup_calls if c[0] == "ensure_project_setup"]
        assert len(setup_calls) == 1
        kwargs = setup_calls[0][1]
        assert kwargs["idea_directory"] == "/tmp/fake-idea"
        assert kwargs["interactive"] is False
        assert kwargs["mock_claude"] == "/mock.sh"
        assert kwargs["ci_timeout"] == 900
        assert kwargs["skip_ci_wait"] is True

    def test_interactive_mode_passes_interactive_flag_to_isolarium(self):
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        mode.execute(non_interactive=False)

        cmd = fake_subprocess.calls[0][1]
        assert "--interactive" in cmd
        assert "--non-interactive" not in cmd

    def test_non_interactive_omits_interactive_flag(self):
        fake_initializer = _make_fake_project_initializer()
        fake_subprocess = FakeSubprocessRunner()
        project = FakeIdeaProject()

        mode = IsolateMode(
            git_repo=FakeGitRepository(),
            project=project,
            project_initializer=fake_initializer,
            subprocess_runner=fake_subprocess,
        )
        mode.execute(non_interactive=True)

        cmd = fake_subprocess.calls[0][1]
        assert "--interactive" not in cmd
