"""Tests for ImplementCommand class."""


import click
import pytest
from unittest.mock import MagicMock, patch

from i2code.implement.implement_command import ImplementCommand
from i2code.implement.implement_opts import ImplementOpts

from fake_idea_project import FakeIdeaProject


def _make_opts(**overrides):
    defaults = dict(idea_directory="/tmp/fake-idea")
    defaults.update(overrides)
    return ImplementOpts(**defaults)


def _make_command(**opt_overrides):
    opts = _make_opts(**opt_overrides)
    project = FakeIdeaProject()
    git_repo = MagicMock()
    mode_factory = MagicMock()
    cmd = ImplementCommand(opts, project, git_repo, mode_factory)
    return cmd, project, git_repo


@pytest.mark.unit
class TestImplementCommandDryRun:
    """execute() in dry-run prints mode and exits without dispatching."""

    def test_dry_run_trunk_mode(self, capsys):
        cmd, *_ = _make_command(dry_run=True, trunk=True)
        cmd.execute()
        assert "trunk" in capsys.readouterr().out.lower()

    def test_dry_run_isolate_mode(self, capsys):
        cmd, *_ = _make_command(dry_run=True, isolate=True)
        cmd.execute()
        assert "isolate" in capsys.readouterr().out.lower()

    def test_dry_run_worktree_mode(self, capsys):
        cmd, *_ = _make_command(dry_run=True)
        cmd.execute()
        assert "worktree" in capsys.readouterr().out.lower()

    def test_dry_run_does_not_execute(self):
        cmd, *_ = _make_command(dry_run=True, trunk=True)
        with patch.object(cmd, '_trunk_mode') as mock_trunk:
            cmd.execute()
            mock_trunk.assert_not_called()


@pytest.mark.unit
class TestImplementCommandTrunkDispatch:
    """execute() dispatches to _trunk_mode() for --trunk."""

    def test_dispatches_to_trunk_mode(self):
        cmd, project, *_ = _make_command(trunk=True, ignore_uncommitted_idea_changes=True)
        with patch.object(cmd, '_trunk_mode') as mock_trunk:
            cmd.execute()
            mock_trunk.assert_called_once()

    def test_trunk_calls_validate_trunk_options(self):
        cmd, *_ = _make_command(trunk=True, ignore_uncommitted_idea_changes=True)
        cmd.opts.validate_trunk_options = MagicMock(side_effect=click.UsageError("stopped"))
        with pytest.raises(click.UsageError):
            cmd.execute()


@pytest.mark.unit
class TestImplementCommandIsolateDispatch:
    """execute() dispatches to _isolate_mode() for --isolate."""

    def test_dispatches_to_isolate_mode(self):
        cmd, *_ = _make_command(isolate=True, ignore_uncommitted_idea_changes=True)
        with patch.object(cmd, '_isolate_mode') as mock_isolate:
            cmd.execute()
            mock_isolate.assert_called_once()


@pytest.mark.unit
class TestImplementCommandWorktreeDispatch:
    """execute() dispatches to _worktree_mode() by default."""

    def test_dispatches_to_worktree_mode(self):
        cmd, *_ = _make_command(ignore_uncommitted_idea_changes=True)
        with patch.object(cmd, '_worktree_mode') as mock_wt:
            cmd.execute()
            mock_wt.assert_called_once()


@pytest.mark.unit
class TestImplementCommandValidation:
    """execute() validates idea files committed unless skipped."""

    @patch("i2code.implement.implement_command.validate_idea_files_committed")
    def test_validates_idea_files_committed(self, mock_validate):
        cmd, *_ = _make_command(trunk=True)
        with patch.object(cmd, '_trunk_mode'):
            cmd.execute()
        mock_validate.assert_called_once()

    @patch("i2code.implement.implement_command.validate_idea_files_committed")
    def test_skips_validation_when_isolated(self, mock_validate):
        cmd, *_ = _make_command(trunk=True, isolated=True)
        # isolated=True with trunk=True will fail validate_trunk_options,
        # so use ignore_uncommitted_idea_changes instead
        cmd2, *_ = _make_command(trunk=True, ignore_uncommitted_idea_changes=True)
        with patch.object(cmd2, '_trunk_mode'):
            cmd2.execute()
        mock_validate.assert_not_called()

    @patch("i2code.implement.implement_command.validate_idea_files_committed")
    def test_skips_validation_when_ignore_uncommitted(self, mock_validate):
        cmd, *_ = _make_command(trunk=True, ignore_uncommitted_idea_changes=True)
        with patch.object(cmd, '_trunk_mode'):
            cmd.execute()
        mock_validate.assert_not_called()


@pytest.mark.unit
class TestImplementCommandTrunkMode:
    """_trunk_mode() delegates to mode_factory.make_trunk_mode()."""

    def test_trunk_mode_delegates_to_mode_factory(self):
        cmd, project, git_repo = _make_command(
            trunk=True, ignore_uncommitted_idea_changes=True
        )
        cmd.execute()
        cmd.mode_factory.make_trunk_mode.assert_called_once_with(
            git_repo=git_repo,
            project=project,
        )
        cmd.mode_factory.make_trunk_mode.return_value.execute.assert_called_once_with(
            non_interactive=False,
            mock_claude=None,
            extra_prompt=None,
        )


@pytest.mark.unit
class TestImplementCommandIsolateMode:
    """_isolate_mode() delegates to mode_factory.make_isolate_mode()."""

    def test_isolate_mode_delegates_to_mode_factory(self):
        cmd, project, git_repo = _make_command(
            isolate=True, ignore_uncommitted_idea_changes=True
        )
        cmd.mode_factory.make_isolate_mode.return_value.execute.return_value = 0
        with pytest.raises(SystemExit) as exc_info:
            cmd.execute()
        assert exc_info.value.code == 0
        cmd.mode_factory.make_isolate_mode.assert_called_once_with(
            git_repo=git_repo,
            project=project,
        )
        cmd.mode_factory.make_isolate_mode.return_value.execute.assert_called_once()


@pytest.mark.unit
class TestWorktreeModeAllTasksComplete:
    """_worktree_mode() exits with error when all tasks are complete."""

    def test_exits_with_error_when_all_tasks_complete(self, capsys):
        cmd, project, git_repo = _make_command(
            ignore_uncommitted_idea_changes=True
        )

        with pytest.raises(SystemExit) as exc_info:
            cmd.execute()

        assert exc_info.value.code == 1
        assert "all tasks" in capsys.readouterr().err.lower()
        git_repo.ensure_integration_branch.assert_not_called()
        git_repo.ensure_slice_branch.assert_not_called()
        git_repo.ensure_worktree.assert_not_called()
        git_repo.checkout.assert_not_called()


@pytest.mark.unit
class TestImplementCommandWorktreeMode:
    """_worktree_mode() delegates to mode_factory.make_worktree_mode()."""

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_worktree_mode_delegates_to_mode_factory(
        self, mock_setup, mock_load_state,
    ):
        mock_load_state.return_value = MagicMock(slice_number=1)

        cmd, project, git_repo = _make_command(
            ignore_uncommitted_idea_changes=True
        )
        project.set_next_task(NumberedTask(
            number=TaskNumber(thread=1, task=1),
            task=Task(_lines=["- [ ] **Task 1.1: test-task**"]),
        ))
        git_repo.working_tree_dir = "/tmp/fake-repo"
        mock_wt_git_repo = MagicMock()
        mock_wt_git_repo.working_tree_dir = "/tmp/wt"
        git_repo.ensure_worktree.return_value = mock_wt_git_repo
        git_repo.gh_client.find_pr.return_value = None

        cmd.execute()

        cmd.mode_factory.make_worktree_mode.assert_called_once()
        cmd.mode_factory.make_worktree_mode.return_value.execute.assert_called_once()


@pytest.mark.unit
class TestNoModuleLevelFunctions:
    """cli.py should not have module-level implement functions."""

    def test_no_implement_function_in_cli(self):
        import i2code.implement.cli as cli_module
        assert not hasattr(cli_module, 'implement'), \
            "cli.py should not have module-level implement()"

    def test_no_implement_trunk_mode_in_cli(self):
        import i2code.implement.cli as cli_module
        assert not hasattr(cli_module, 'implement_trunk_mode'), \
            "cli.py should not have module-level implement_trunk_mode()"

    def test_no_implement_isolate_mode_in_cli(self):
        import i2code.implement.cli as cli_module
        assert not hasattr(cli_module, 'implement_isolate_mode'), \
            "cli.py should not have module-level implement_isolate_mode()"

    def test_no_implement_worktree_mode_in_cli(self):
        import i2code.implement.cli as cli_module
        assert not hasattr(cli_module, 'implement_worktree_mode'), \
            "cli.py should not have module-level implement_worktree_mode()"


@pytest.mark.unit
class TestImplementCmd:
    """Test implement CLI command uses command_factory from context."""

    def test_uses_command_factory_and_forwards_opts(self):
        from click.testing import CliRunner
        from i2code.implement.cli import implement_cmd

        mock_command = MagicMock()
        received_opts = []

        def fake_factory(opts):
            received_opts.append(opts)
            return mock_command

        runner = CliRunner(catch_exceptions=False)
        runner.invoke(
            implement_cmd, ["/tmp/fake-idea", "--setup-only", "--trunk"],
            obj={"command_factory": fake_factory},
        )

        assert received_opts[0].idea_directory == "/tmp/fake-idea"
        assert received_opts[0].setup_only is True
        assert received_opts[0].trunk is True
        mock_command.execute.assert_called_once()


@pytest.mark.unit
class TestDeferredPRCreation:
    """Test that PR creation is deferred until after first push."""

    def test_setup_only_does_not_create_pr(self, monkeypatch):
        """Running with --setup-only should NOT attempt to create a PR."""
        monkeypatch.setattr(
            "i2code.implement.implement_command.WorkflowState.load",
            lambda x: MagicMock(slice_number=1),
        )
        monkeypatch.setattr(
            "i2code.implement.implement_command.setup_project",
            lambda *a, **kw: None,
        )

        cmd, _project, git_repo = _make_command(
            setup_only=True, ignore_uncommitted_idea_changes=True,
        )
        cmd.execute()

        git_repo.gh_client.find_pr.assert_not_called()
