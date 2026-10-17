"""Tests for CommandBuilder: consolidates all Claude command-building functions."""

import pytest

from i2code.implement.claude_runner import ClaudeCodeCommand
from i2code.implement.command_builder import (
    CiFixRequest,
    CommandBuilder,
    FixRequest,
    TaskCommandOpts,
)


def _build_task_cmd(**overrides):
    defaults = dict(
        idea_directory="docs/features/my-feature",
        task_description="Task 1.1: Create config file",
        cwd="/cwd",
    )
    defaults.update(overrides)
    return CommandBuilder().build_task_command(**defaults)


def _build_scaffolding_cmd(**overrides):
    defaults = dict(
        idea_directory="docs/features/my-feature",
        cwd="/cwd",
        interactive=True,
    )
    defaults.update(overrides)
    return CommandBuilder().build_scaffolding_command(**defaults)


def _build_triage_cmd(**overrides):
    defaults = dict(
        feedback_content="Please fix the typo",
        cwd="/cwd",
        interactive=True,
    )
    defaults.update(overrides)
    return CommandBuilder().build_triage_command(**defaults)


def _build_fix_cmd(**overrides):
    request_fields = {
        "pr_url": "https://github.com/owner/repo/pull/123",
        "feedback_content": "Fix the typo",
        "fix_description": "Fix typo in README",
    }
    for key in list(request_fields):
        if key in overrides:
            request_fields[key] = overrides.pop(key)
    defaults = dict(
        request=FixRequest(**request_fields),
        cwd="/cwd",
        interactive=True,
    )
    defaults.update(overrides)
    return CommandBuilder().build_fix_command(**defaults)


def _build_recovery_cmd(**overrides):
    defaults = dict(
        plan_file="docs/features/my-feature/my-feature-plan.md",
        diff_summary="some diff output",
        cwd="/cwd",
        interactive=True,
    )
    defaults.update(overrides)
    return CommandBuilder().build_recovery_command(**defaults)


def _build_ci_fix_cmd(**overrides):
    request_fields = {
        "run_id": 12345,
        "workflow_name": "CI Build",
        "failure_logs": "Error: test failed",
    }
    for key in list(request_fields):
        if key in overrides:
            request_fields[key] = overrides.pop(key)
    defaults = dict(
        request=CiFixRequest(**request_fields),
        cwd="/cwd",
        interactive=True,
    )
    defaults.update(overrides)
    return CommandBuilder().build_ci_fix_command(**defaults)


@pytest.mark.unit
class TestCommandBuilderTaskCommand:
    """Test building task execution commands."""

    def test_build_task_command_returns_dataclass(self):
        cmd = _build_task_cmd(cwd="/work/tree")
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == "/work/tree"
        assert cmd.interactive is True
        assert cmd.prompt is not None
        assert cmd.allowed_tools is None
        assert cmd.add_dirs == []
        assert cmd.extra_args == []

    def test_interactive_flag_mapped_from_opts(self):
        cmd = _build_task_cmd(opts=TaskCommandOpts(interactive=False))
        assert cmd.interactive is False

    def test_includes_idea_directory_in_prompt(self):
        cmd = _build_task_cmd()
        assert "docs/features/my-feature" in cmd.prompt

    def test_includes_task_description_in_prompt(self):
        cmd = _build_task_cmd()
        assert "Task 1.1" in cmd.prompt

    def test_build_task_command_splits_allowed_tools_from_extra_cli_args(self):
        cmd = _build_task_cmd(opts=TaskCommandOpts(
            extra_cli_args=["--allowedTools", "Bash(git commit:*)", "--debug"],
        ))
        assert cmd.allowed_tools == "Bash(git commit:*)"
        assert cmd.extra_args == ["--debug"]
        assert cmd.add_dirs == []

    def test_build_task_command_splits_add_dir_from_extra_cli_args(self):
        cmd = _build_task_cmd(opts=TaskCommandOpts(
            extra_cli_args=[
                "--add-dir", "/repo/a",
                "--allowedTools", "Read",
                "--add-dir", "/repo/b",
                "--foo",
            ],
        ))
        assert cmd.add_dirs == ["/repo/a", "/repo/b"]
        assert cmd.allowed_tools == "Read"
        assert cmd.extra_args == ["--foo"]

    def test_claude_prompt_uses_worktree_idea_directory(self):
        """Prompt should reference worktree idea dir, not main repo."""
        from i2code.implement.idea_project import IdeaProject

        main_repo_root = "/home/user/my-repo"
        worktree_path = "/tmp/my-repo-wt-kafka-security-poc"

        project = IdeaProject("/home/user/my-repo/kafka-security-poc")
        worktree_idea_dir = project.worktree_idea_project(worktree_path, main_repo_root).directory

        cmd = _build_task_cmd(idea_directory=worktree_idea_dir, task_description="Task 1.1: Create project")

        assert worktree_path in cmd.prompt, f"Prompt should use worktree path. Got: {cmd.prompt}"
        assert main_repo_root not in cmd.prompt, f"Prompt should NOT use main repo path. Got: {cmd.prompt}"


@pytest.mark.unit
class TestCommandBuilderScaffoldingCommand:
    """Test building scaffolding commands."""

    def test_build_scaffolding_command_returns_dataclass(self):
        cmd = _build_scaffolding_cmd(cwd="/work/tree", interactive=False)
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == "/work/tree"
        assert cmd.interactive is False
        assert cmd.prompt is not None

    def test_interactive_flag_mapped_from_parameter(self):
        cmd = _build_scaffolding_cmd(interactive=True)
        assert cmd.interactive is True

    def test_non_interactive_sets_allowed_tools(self):
        cmd = _build_scaffolding_cmd(interactive=False)
        assert cmd.allowed_tools == "Write,Read,Edit,Bash(gradle --version),Bash(mkdir -p:*)"

    def test_interactive_omits_allowed_tools(self):
        cmd = _build_scaffolding_cmd(interactive=True)
        assert cmd.allowed_tools is None

    def test_includes_idea_directory_in_prompt(self):
        cmd = _build_scaffolding_cmd()
        assert "docs/features/my-feature" in cmd.prompt

    def test_build_scaffolding_command_no_longer_accepts_mock_claude(self):
        with pytest.raises(TypeError):
            CommandBuilder().build_scaffolding_command(
                idea_directory="docs/features/my-feature",
                cwd="/cwd",
                interactive=True,
                mock_claude="/path/to/mock",
            )


@pytest.mark.unit
class TestCommandBuilderTriageCommand:
    """Test building triage feedback commands."""

    def test_build_triage_command_returns_dataclass(self):
        cmd = _build_triage_cmd(cwd="/work/tree", interactive=False)
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == "/work/tree"
        assert cmd.interactive is False
        assert cmd.prompt is not None

    def test_interactive_flag_mapped_from_parameter(self):
        cmd = _build_triage_cmd(interactive=True)
        assert cmd.interactive is True

    def test_includes_feedback_content_in_prompt(self):
        cmd = _build_triage_cmd()
        assert "Please fix the typo" in cmd.prompt

    def test_requests_json_output(self):
        cmd = _build_triage_cmd()
        assert "json" in cmd.prompt.lower()
        assert "comment_ids" in cmd.prompt


@pytest.mark.unit
class TestCommandBuilderFixCommand:
    """Test building fix feedback commands."""

    def test_build_fix_command_returns_dataclass(self):
        cmd = _build_fix_cmd(cwd="/work/tree", interactive=False)
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == "/work/tree"
        assert cmd.interactive is False
        assert cmd.prompt is not None

    def test_interactive_flag_mapped_from_parameter(self):
        cmd = _build_fix_cmd(interactive=True)
        assert cmd.interactive is True

    def test_includes_pr_url_in_prompt(self):
        cmd = _build_fix_cmd()
        assert "https://github.com/owner/repo/pull/123" in cmd.prompt

    def test_includes_feedback_and_description_in_prompt(self):
        cmd = _build_fix_cmd(feedback_content="Please add tests", fix_description="Add unit tests")
        assert "Please add tests" in cmd.prompt
        assert "Add unit tests" in cmd.prompt


@pytest.mark.unit
class TestCommandBuilderRecoveryCommand:
    """Test building commit-recovery commands."""

    def test_build_recovery_command_returns_dataclass(self):
        cmd = _build_recovery_cmd(cwd="/work/tree", interactive=False)
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == "/work/tree"
        assert cmd.interactive is False
        assert cmd.prompt is not None

    def test_interactive_flag_mapped_from_parameter(self):
        cmd = _build_recovery_cmd(interactive=True)
        assert cmd.interactive is True

    def test_includes_plan_file_in_prompt(self):
        cmd = _build_recovery_cmd(plan_file="docs/features/my-feature/my-feature-plan.md")
        assert "docs/features/my-feature/my-feature-plan.md" in cmd.prompt

    def test_includes_diff_summary_in_prompt(self):
        cmd = _build_recovery_cmd(diff_summary="diff --git a/foo b/foo")
        assert "diff --git a/foo b/foo" in cmd.prompt


@pytest.mark.unit
class TestCommandBuilderCiFixCommand:
    """Test building CI fix commands."""

    def test_build_ci_fix_command_returns_dataclass(self):
        cmd = _build_ci_fix_cmd(cwd="/work/tree", interactive=False)
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == "/work/tree"
        assert cmd.interactive is False
        assert cmd.prompt is not None

    def test_interactive_flag_mapped_from_parameter(self):
        cmd = _build_ci_fix_cmd(interactive=True)
        assert cmd.interactive is True

    def test_includes_workflow_info_in_prompt(self):
        """Prompt should include run_id and workflow_name."""
        cmd = _build_ci_fix_cmd()
        assert "12345" in cmd.prompt
        assert "CI Build" in cmd.prompt
        assert "Error: test failed" in cmd.prompt

    def test_truncates_long_logs(self):
        """Should truncate logs longer than 5000 chars."""
        cmd = _build_ci_fix_cmd(failure_logs="x" * 6000)
        assert "truncated" in cmd.prompt.lower()

    def test_renders_ci_fix_template(self, mocker):
        """Should render prompt from ci_fix.j2 template."""
        mock_render = mocker.patch("i2code.implement.command_builder.render_template", return_value="rendered prompt")
        _build_ci_fix_cmd()
        mock_render.assert_called_once_with(
            "ci_fix.j2",
            package="i2code.implement",
            run_id=12345,
            workflow_name="CI Build",
            failure_logs="Error: test failed",
        )

