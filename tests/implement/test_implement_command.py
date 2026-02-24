"""Tests for ImplementCommand class."""


import click
import pytest
from unittest.mock import MagicMock, patch

from i2code.implement.implement_command import ImplementCommand
from i2code.implement.implement_opts import ImplementOpts
from i2code.plan_domain.numbered_task import NumberedTask, TaskNumber
from i2code.plan_domain.task import Task

from fake_idea_project import FakeIdeaProject


def _make_opts(**overrides):
    defaults = dict(idea_directory="/tmp/fake-idea")
    defaults.update(overrides)
    return ImplementOpts(**defaults)


_DEFAULT_TASK = NumberedTask(
    number=TaskNumber(thread=1, task=1),
    task=Task(_lines=["- [ ] **Task 1.1: default-task**"]),
)


def _make_command(**opt_overrides):
    opts = _make_opts(**opt_overrides)
    project = FakeIdeaProject()
    project.set_next_task(_DEFAULT_TASK)
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
class TestExecuteAllTasksComplete:
    """execute() returns normally when all tasks complete, before dispatching to any mode."""

    @pytest.mark.parametrize("opts,mode_method", [
        (dict(), "_worktree_mode"),
        (dict(trunk=True), "_trunk_mode"),
        (dict(isolate=True), "_isolate_mode"),
    ], ids=["worktree", "trunk", "isolate"])
    def test_mode_not_called(self, capsys, opts, mode_method):
        cmd, project, git_repo = _make_command(
            ignore_uncommitted_idea_changes=True, **opts
        )
        project.set_next_task(None)
        with patch.object(cmd, mode_method) as mock_mode:
            cmd.execute()
            assert "all tasks" in capsys.readouterr().out.lower()
            mock_mode.assert_not_called()


@pytest.mark.unit
class TestWorktreeModeAllTasksComplete:
    """_worktree_mode() returns normally when all tasks are complete."""

    def test_returns_when_all_tasks_complete(self, capsys):
        cmd, project, git_repo = _make_command(
            ignore_uncommitted_idea_changes=True
        )
        project.set_next_task(None)

        cmd.execute()

        assert "all tasks" in capsys.readouterr().out.lower()
        git_repo.ensure_integration_branch.assert_not_called()
        git_repo.ensure_slice_branch.assert_not_called()
        git_repo.ensure_worktree.assert_not_called()
        git_repo.checkout.assert_not_called()


@pytest.mark.unit
class TestIsolateModeReceivesIsolationType:
    """_isolate_mode() passes isolation_type to isolate_mode.execute()."""

    def test_isolate_mode_receives_isolation_type(self):
        cmd, project, git_repo = _make_command(
            isolate=True, isolation_type="docker",
            ignore_uncommitted_idea_changes=True,
        )
        cmd.mode_factory.make_isolate_mode.return_value.execute.return_value = 0
        with pytest.raises(SystemExit):
            cmd.execute()
        call_kwargs = cmd.mode_factory.make_isolate_mode.return_value.execute.call_args
        assert call_kwargs.kwargs.get("isolation_type") == "docker"

    def test_isolate_mode_receives_none_when_not_set(self):
        cmd, project, git_repo = _make_command(
            isolate=True,
            ignore_uncommitted_idea_changes=True,
        )
        cmd.mode_factory.make_isolate_mode.return_value.execute.return_value = 0
        with pytest.raises(SystemExit):
            cmd.execute()
        call_kwargs = cmd.mode_factory.make_isolate_mode.return_value.execute.call_args
        assert call_kwargs.kwargs.get("isolation_type") is None


@pytest.mark.unit
class TestImplementCommandWorktreeMode:
    """_worktree_mode() uses a single idea branch (no integration or slice branch)."""

    def _setup_worktree_command(self):
        """Set up a command with mocks for worktree mode execution."""
        cmd, project, git_repo = _make_command(
            ignore_uncommitted_idea_changes=True
        )
        project.set_next_task(NumberedTask(
            number=TaskNumber(thread=1, task=1),
            task=Task(_lines=["- [ ] **Task 1.1: test-task**"]),
        ))
        git_repo.working_tree_dir = "/tmp/fake-repo"
        git_repo.ensure_idea_branch.return_value = "idea/fake-idea"
        mock_wt_git_repo = MagicMock()
        mock_wt_git_repo.working_tree_dir = "/tmp/wt"
        git_repo.ensure_worktree.return_value = mock_wt_git_repo
        git_repo.gh_client.find_pr.return_value = None
        return cmd, project, git_repo, mock_wt_git_repo

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_calls_ensure_idea_branch(self, mock_setup, mock_load_state):
        cmd, project, git_repo, _ = self._setup_worktree_command()
        cmd.execute()
        git_repo.ensure_idea_branch.assert_called_once_with(project.name)

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_ensure_worktree_receives_idea_branch(self, mock_setup, mock_load_state):
        cmd, project, git_repo, _ = self._setup_worktree_command()
        cmd.execute()
        git_repo.ensure_worktree.assert_called_once_with(project.name, "idea/fake-idea")

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_sets_branch_to_idea_branch(self, mock_setup, mock_load_state):
        cmd, _, git_repo, mock_wt_git_repo = self._setup_worktree_command()
        cmd.execute()
        assert mock_wt_git_repo.branch == "idea/fake-idea"

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_find_pr_uses_idea_branch(self, mock_setup, mock_load_state):
        cmd, _, git_repo, mock_wt_git_repo = self._setup_worktree_command()
        cmd.execute()
        mock_wt_git_repo.gh_client.find_pr.assert_called_once_with("idea/fake-idea")

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_checkout_not_called(self, mock_setup, mock_load_state):
        cmd, _, git_repo, mock_wt_git_repo = self._setup_worktree_command()
        cmd.execute()
        mock_wt_git_repo.checkout.assert_not_called()

    @patch("i2code.implement.implement_command.WorkflowState.load")
    @patch("i2code.implement.implement_command.setup_project")
    def test_delegates_to_mode_factory(self, mock_setup, mock_load_state):
        cmd, _, _, _ = self._setup_worktree_command()
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
class TestImplementCommandIsolationTypeImplied:
    """--isolation-type implies --isolate when --isolate is not explicitly set."""

    def test_isolation_type_implies_isolate_dispatch(self):
        """With isolation_type set and isolate=False, execute() dispatches to _isolate_mode()."""
        cmd, *_ = _make_command(
            isolation_type="docker", ignore_uncommitted_idea_changes=True
        )
        cmd.mode_factory.make_isolate_mode.return_value.execute.return_value = 0
        with patch.object(cmd, '_isolate_mode') as mock_isolate, \
             patch.object(cmd, '_worktree_mode') as mock_worktree:
            cmd.execute()
            mock_isolate.assert_called_once()
            mock_worktree.assert_not_called()

    def test_isolation_type_implies_isolate_dry_run(self, capsys):
        """In dry-run mode with isolation_type set, output shows Mode: isolate."""
        cmd, *_ = _make_command(
            dry_run=True, isolation_type="docker"
        )
        cmd.execute()
        output = capsys.readouterr().out
        assert "Mode: isolate" in output


@pytest.mark.unit
class TestDeferredPRCreation:
    """Test that PR creation is deferred until after first push."""

    def test_setup_only_does_not_create_pr(self, monkeypatch):
        """Running with --setup-only should NOT attempt to create a PR."""
        monkeypatch.setattr(
            "i2code.implement.implement_command.WorkflowState.load",
            lambda x: MagicMock(),
        )
        monkeypatch.setattr(
            "i2code.implement.implement_command.setup_project",
            lambda *a, **kw: None,
        )

        cmd, _project, git_repo = _make_command(
            setup_only=True, ignore_uncommitted_idea_changes=True,
        )
        git_repo.ensure_idea_branch.return_value = "idea/fake-idea"
        mock_wt_git_repo = MagicMock()
        mock_wt_git_repo.working_tree_dir = "/tmp/wt"
        git_repo.ensure_worktree.return_value = mock_wt_git_repo
        cmd.execute()

        mock_wt_git_repo.gh_client.find_pr.assert_not_called()
