"""Tests for CommandBuilder: consolidates all Claude command-building functions."""

import os
import pytest

from i2code.implement.command_builder import CommandBuilder, TaskCommandOpts


def _build_task_cmd(**overrides):
    defaults = dict(idea_directory="docs/features/my-feature", task_description="Task 1.1: Create config file")
    defaults.update(overrides)
    return CommandBuilder().build_task_command(**defaults)


def _build_scaffolding_cmd(**overrides):
    defaults = dict(idea_directory="docs/features/my-feature", interactive=True)
    defaults.update(overrides)
    return CommandBuilder().build_scaffolding_command(**defaults)


def _build_triage_cmd(**overrides):
    defaults = dict(feedback_content="Please fix the typo", interactive=True)
    defaults.update(overrides)
    return CommandBuilder().build_triage_command(**defaults)


def _build_fix_cmd(**overrides):
    defaults = dict(
        pr_url="https://github.com/owner/repo/pull/123",
        feedback_content="Fix the typo",
        fix_description="Fix typo in README",
        interactive=True,
    )
    defaults.update(overrides)
    return CommandBuilder().build_fix_command(**defaults)


def _build_ci_fix_cmd(**overrides):
    defaults = dict(run_id=12345, workflow_name="CI Build", failure_logs="Error: test failed", interactive=True)
    defaults.update(overrides)
    return CommandBuilder().build_ci_fix_command(**defaults)


def _build_feedback_cmd(**overrides):
    defaults = dict(
        pr_url="https://github.com/owner/repo/pull/123",
        feedback_type="review_comment",
        feedback_content="Please fix the typo",
    )
    defaults.update(overrides)
    return CommandBuilder().build_feedback_command(**defaults)


FEEDBACK_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), '../../prompt-templates/wt-handle-feedback.md')


def _read_feedback_template():
    with open(FEEDBACK_TEMPLATE_PATH, 'r') as f:
        return f.read()


@pytest.mark.unit
class TestCommandBuilderTaskCommand:
    """Test building task execution commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive command should be ['claude', prompt]."""
        cmd = _build_task_cmd()
        assert cmd[0] == "claude"
        assert len(cmd) == 2
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive command should include -p flag."""
        cmd = _build_task_cmd(opts=TaskCommandOpts(interactive=False))
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert "--verbose" in cmd
        assert "--output-format=stream-json" in cmd

    def test_includes_idea_directory_in_prompt(self):
        """Prompt should reference the idea directory."""
        cmd = _build_task_cmd()
        assert "docs/features/my-feature" in cmd[1]

    def test_includes_task_description_in_prompt(self):
        """Prompt should include the task description."""
        cmd = _build_task_cmd()
        assert "Task 1.1" in cmd[1]

    def test_extra_cli_args_in_interactive(self):
        """Interactive command should include extra_cli_args."""
        cmd = _build_task_cmd(opts=TaskCommandOpts(extra_cli_args=["--allowedTools", "Bash(git commit:*)"]))
        assert "--allowedTools" in cmd
        assert cmd[0] == "claude"

    def test_extra_cli_args_in_non_interactive(self):
        """Non-interactive command should include extra_cli_args before -p."""
        cmd = _build_task_cmd(opts=TaskCommandOpts(
            interactive=False,
            extra_cli_args=["--allowedTools", "Bash(git commit:*),Write(/repo/)"],
        ))
        assert "--allowedTools" in cmd
        assert "-p" in cmd

    def test_claude_prompt_uses_worktree_idea_directory(self):
        """Claude command prompt should reference worktree idea dir, not main repo."""
        from i2code.implement.idea_project import IdeaProject

        main_repo_root = "/home/user/my-repo"
        worktree_path = "/tmp/my-repo-wt-kafka-security-poc"

        project = IdeaProject("/home/user/my-repo/kafka-security-poc")
        worktree_idea_dir = project.worktree_idea_project(worktree_path, main_repo_root).directory

        cmd = _build_task_cmd(idea_directory=worktree_idea_dir, task_description="Task 1.1: Create project")

        prompt = cmd[1]
        assert worktree_path in prompt, f"Prompt should use worktree path. Got: {prompt}"
        assert main_repo_root not in prompt, f"Prompt should NOT use main repo path. Got: {prompt}"


@pytest.mark.unit
class TestCommandBuilderScaffoldingCommand:
    """Test building scaffolding commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive scaffolding should be ['claude', prompt]."""
        cmd = _build_scaffolding_cmd()
        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_allowed_tools(self):
        """Non-interactive scaffolding includes specific --allowed-tools."""
        cmd = _build_scaffolding_cmd(interactive=False)
        assert "--allowed-tools" in cmd
        assert "-p" in cmd

    def test_mock_claude_returns_mock_script_command(self):
        """Mock mode should return [mock_script, 'setup']."""
        cmd = _build_scaffolding_cmd(mock_claude="/path/to/mock")
        assert cmd == ["/path/to/mock", "setup"]

    def test_includes_idea_directory_in_prompt(self):
        """Prompt should reference the idea directory."""
        cmd = _build_scaffolding_cmd()
        assert "docs/features/my-feature" in cmd[1]


@pytest.mark.unit
class TestCommandBuilderTriageCommand:
    """Test building triage feedback commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive triage should be ['claude', prompt]."""
        cmd = _build_triage_cmd()
        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive triage should include -p flag."""
        cmd = _build_triage_cmd(interactive=False)
        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_includes_feedback_content_in_prompt(self):
        """Prompt should include the feedback content."""
        cmd = _build_triage_cmd()
        assert "Please fix the typo" in cmd[1]

    def test_requests_json_output(self):
        """Should request JSON output format."""
        cmd = _build_triage_cmd()
        prompt = cmd[1]
        assert "json" in prompt.lower()
        assert "comment_ids" in prompt


@pytest.mark.unit
class TestCommandBuilderFixCommand:
    """Test building fix feedback commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive fix should be ['claude', prompt]."""
        cmd = _build_fix_cmd()
        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive fix should include -p flag."""
        cmd = _build_fix_cmd(interactive=False)
        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_includes_pr_url_in_prompt(self):
        """Prompt should include the PR URL."""
        cmd = _build_fix_cmd()
        assert "https://github.com/owner/repo/pull/123" in cmd[1]

    def test_includes_feedback_and_description_in_prompt(self):
        """Should include feedback content and fix description in prompt."""
        cmd = _build_fix_cmd(feedback_content="Please add tests", fix_description="Add unit tests")
        assert "Please add tests" in cmd[1]
        assert "Add unit tests" in cmd[1]


@pytest.mark.unit
class TestCommandBuilderCiFixCommand:
    """Test building CI fix commands."""

    def test_interactive_returns_claude_with_prompt(self):
        """Interactive CI fix should be ['claude', prompt]."""
        cmd = _build_ci_fix_cmd()
        assert cmd[0] == "claude"
        assert "-p" not in cmd

    def test_non_interactive_includes_p_flag(self):
        """Non-interactive CI fix should include -p flag."""
        cmd = _build_ci_fix_cmd(interactive=False)
        assert "-p" in cmd
        assert "--verbose" in cmd

    def test_includes_workflow_info_in_prompt(self):
        """Prompt should include run_id and workflow_name."""
        cmd = _build_ci_fix_cmd()
        prompt = cmd[1]
        assert "12345" in prompt
        assert "CI Build" in prompt
        assert "Error: test failed" in prompt

    def test_truncates_long_logs(self):
        """Should truncate logs longer than 5000 chars."""
        cmd = _build_ci_fix_cmd(failure_logs="x" * 6000)
        assert "truncated" in cmd[1].lower()

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


@pytest.mark.unit
class TestCommandBuilderFeedbackCommand:
    """Test building feedback commands."""

    def test_uses_print_flag(self):
        """Feedback command should use --print flag."""
        cmd = _build_feedback_cmd()
        assert "--print" in cmd or "-p" in cmd

    def test_includes_pr_url_in_prompt(self):
        """Command should include PR URL in prompt."""
        cmd = _build_feedback_cmd()
        assert "https://github.com/owner/repo/pull/123" in " ".join(cmd)

    def test_includes_feedback_content_in_prompt(self):
        """Command should include feedback content."""
        cmd = _build_feedback_cmd()
        assert "Please fix the typo" in " ".join(cmd)

    def test_uses_feedback_template(self):
        """Should use wt-handle-feedback.md template."""
        cmd = _build_feedback_cmd()
        assert "wt-handle-feedback.md" in " ".join(cmd)


@pytest.mark.unit
class TestFeedbackTemplate:
    """Test wt-handle-feedback.md prompt template."""

    def test_feedback_template_exists(self):
        """Template file should exist in prompt-templates directory."""
        assert os.path.exists(FEEDBACK_TEMPLATE_PATH), f"Template not found at {FEEDBACK_TEMPLATE_PATH}"

    def test_feedback_template_has_pr_url_placeholder(self):
        """Template should have placeholder for PR URL."""
        assert 'PR_URL' in _read_feedback_template(), "Template should have PR_URL placeholder"

    def test_feedback_template_has_feedback_content_placeholder(self):
        """Template should have placeholder for feedback content."""
        assert 'FEEDBACK_CONTENT' in _read_feedback_template(), "Template should have FEEDBACK_CONTENT placeholder"

    def test_feedback_template_has_feedback_type_placeholder(self):
        """Template should have placeholder for feedback type."""
        assert 'FEEDBACK_TYPE' in _read_feedback_template(), "Template should have FEEDBACK_TYPE placeholder"
