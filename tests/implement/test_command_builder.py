"""Tests for CommandBuilder: consolidates all Claude command-building functions."""

import pytest


@pytest.mark.unit
class TestCommandBuilderTaskCommand:
    """Test building task execution commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive command should be ['claude', prompt]."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_task_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            interactive=True,
        )

        assert cmd[0] == "claude"
        assert len(cmd) == 2
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive command should include -p flag."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_task_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            interactive=False,
        )

        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "--verbose" in cmd
        assert "--output-format=stream-json" in cmd

    def test_includes_idea_directory_in_prompt(self):
        """Prompt should reference the idea directory."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_task_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            interactive=True,
        )

        assert "docs/features/my-feature" in cmd[1]

    def test_includes_task_description_in_prompt(self):
        """Prompt should include the task description."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_task_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            interactive=True,
        )

        assert "Task 1.1" in cmd[1]

    def test_extra_cli_args_in_interactive(self):
        """Interactive command should include extra_cli_args."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_task_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            interactive=True,
            extra_cli_args=["--allowedTools", "Bash(git commit:*)"],
        )

        assert "--allowedTools" in cmd
        assert cmd[0] == "claude"

    def test_extra_cli_args_in_non_interactive(self):
        """Non-interactive command should include extra_cli_args before -p."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_task_command(
            idea_directory="docs/features/my-feature",
            task_description="Task 1.1: Create config file",
            interactive=False,
            extra_cli_args=["--allowedTools", "Bash(git commit:*),Write(/repo/)"],
        )

        assert "--allowedTools" in cmd
        assert "-p" in cmd


@pytest.mark.unit
class TestCommandBuilderScaffoldingCommand:
    """Test building scaffolding commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive scaffolding should be ['claude', prompt]."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_scaffolding_command(
            idea_directory="docs/features/my-feature",
            interactive=True,
        )

        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_allowed_tools(self):
        """Non-interactive scaffolding includes specific --allowed-tools."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_scaffolding_command(
            idea_directory="docs/features/my-feature",
            interactive=False,
        )

        assert "--allowed-tools" in cmd
        assert "-p" in cmd

    def test_mock_claude_returns_mock_script_command(self):
        """Mock mode should return [mock_script, 'setup']."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_scaffolding_command(
            idea_directory="docs/features/my-feature",
            interactive=True,
            mock_claude="/path/to/mock",
        )

        assert cmd == ["/path/to/mock", "setup"]

    def test_includes_idea_directory_in_prompt(self):
        """Prompt should reference the idea directory."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_scaffolding_command(
            idea_directory="docs/features/my-feature",
            interactive=True,
        )

        assert "docs/features/my-feature" in cmd[1]


@pytest.mark.unit
class TestCommandBuilderTriageCommand:
    """Test building triage feedback commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive triage should be ['claude', prompt]."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_triage_command(
            feedback_content="Please fix the typo",
            interactive=True,
        )

        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive triage should include -p flag."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_triage_command(
            feedback_content="Please fix the typo",
            interactive=False,
        )

        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_includes_feedback_content_in_prompt(self):
        """Prompt should include the feedback content."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_triage_command(
            feedback_content="Please fix the typo",
            interactive=True,
        )

        assert "Please fix the typo" in cmd[1]


@pytest.mark.unit
class TestCommandBuilderFixCommand:
    """Test building fix feedback commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive fix should be ['claude', prompt]."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_fix_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_content="Fix the typo",
            fix_description="Fix typo in README",
            interactive=True,
        )

        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive fix should include -p flag."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_fix_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_content="Fix the typo",
            fix_description="Fix typo in README",
            interactive=False,
        )

        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_includes_pr_url_in_prompt(self):
        """Prompt should include the PR URL."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_fix_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_content="Fix the typo",
            fix_description="Fix typo in README",
            interactive=True,
        )

        assert "https://github.com/owner/repo/pull/123" in cmd[1]


@pytest.mark.unit
class TestCommandBuilderCiFixCommand:
    """Test building CI fix commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive CI fix should be ['claude', prompt]."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_ci_fix_command(
            run_id=12345,
            workflow_name="CI Build",
            failure_logs="Error: test failed",
            interactive=True,
        )

        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive CI fix should include -p flag."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_ci_fix_command(
            run_id=12345,
            workflow_name="CI Build",
            failure_logs="Error: test failed",
            interactive=False,
        )

        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_includes_workflow_info_in_prompt(self):
        """Prompt should include run_id and workflow_name."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_ci_fix_command(
            run_id=12345,
            workflow_name="CI Build",
            failure_logs="Error: test failed",
            interactive=True,
        )

        prompt = cmd[1]
        assert "12345" in prompt
        assert "CI Build" in prompt
        assert "Error: test failed" in prompt

    def test_truncates_long_logs(self):
        """Should truncate logs longer than 5000 chars."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        long_logs = "x" * 6000
        cmd = builder.build_ci_fix_command(
            run_id=1,
            workflow_name="Build",
            failure_logs=long_logs,
            interactive=True,
        )

        prompt = cmd[1]
        assert "truncated" in prompt.lower()

    def test_renders_ci_fix_template(self, mocker):
        """Should render prompt from ci_fix.j2 template."""
        from i2code.implement.command_builder import CommandBuilder

        mock_render = mocker.patch("i2code.implement.command_builder.render_template", return_value="rendered prompt")

        CommandBuilder().build_ci_fix_command(
            run_id=12345,
            workflow_name="CI Build",
            failure_logs="Error: test failed",
            interactive=True,
        )

        mock_render.assert_called_once_with(
            "ci_fix.j2",
            package="i2code.implement",
            run_id=12345,
            workflow_name="CI Build",
            failure_logs="Error: test failed",
        )


@pytest.mark.unit
class TestCommandBuilderFeedbackCommand:
    """Test building feedback commands."""

    def test_uses_print_flag(self):
        """Feedback command should use --print flag."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo",
        )

        assert "--print" in cmd or "-p" in cmd

    def test_includes_pr_url_in_prompt(self):
        """Command should include PR URL in prompt."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo",
        )

        cmd_str = " ".join(cmd)
        assert "https://github.com/owner/repo/pull/123" in cmd_str

    def test_includes_feedback_content_in_prompt(self):
        """Command should include feedback content."""
        from i2code.implement.command_builder import CommandBuilder

        builder = CommandBuilder()
        cmd = builder.build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo",
        )

        cmd_str = " ".join(cmd)
        assert "Please fix the typo" in cmd_str

    def test_uses_feedback_template(self):
        """Should use wt-handle-feedback.md template."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_feedback_command(
            pr_url="https://github.com/owner/repo/pull/123",
            feedback_type="review_comment",
            feedback_content="Please fix the typo",
        )

        assert "wt-handle-feedback.md" in " ".join(cmd)
