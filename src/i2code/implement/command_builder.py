"""CommandBuilder: builds all Claude command lists.

Consolidates the interactive/non-interactive branching into a single
_with_mode() helper so the if interactive: ... else: ... pattern
exists in one place.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from i2code.implement.claude_runner import ClaudeCodeCommand
from i2code.templates.template_renderer import render_template


@dataclass
class TaskCommandOpts:
    """Optional execution modifiers for build_task_command."""
    interactive: bool = True
    extra_prompt: Optional[str] = None
    extra_cli_args: Optional[List[str]] = None


class CommandBuilder:
    """Builds Claude CLI commands for all invocation types.

    The interactive/non-interactive branching is handled once in
    ``_with_mode()``.  Each public method renders its template and
    delegates to that helper.
    """

    def _with_mode(
        self,
        prompt: str,
        interactive: bool,
        extra_cli_args: Optional[List[str]] = None,
    ) -> List[str]:
        """Apply interactive/non-interactive flags to a prompt.

        Args:
            prompt: The rendered prompt string.
            interactive: True for interactive, False for -p mode.
            extra_cli_args: Optional extra CLI arguments.

        Returns:
            Command list suitable for subprocess.
        """
        extra = extra_cli_args or []
        if interactive:
            return ["claude"] + extra + [prompt]
        else:
            return ["claude"] + extra + [
                "--verbose", "--output-format=stream-json", "-p", prompt
            ]

    def build_recovery_command(
        self,
        plan_file: str,
        diff_summary: str,
        interactive: bool = True,
    ) -> List[str]:
        """Build command to invoke Claude for committing recovered changes.

        Args:
            plan_file: Path to the plan file.
            diff_summary: Summary of uncommitted changes (git diff output).
            interactive: If True, run Claude interactively.

        Returns:
            Command list suitable for subprocess.
        """
        prompt = render_template(
            "commit_recovery.j2",
            package="i2code.implement",
            plan_file=plan_file,
            diff_summary=diff_summary,
            interactive=interactive,
        )

        return self._with_mode(prompt, interactive)

    def build_task_command(
        self,
        idea_directory: str,
        task_description: str,
        opts: Optional[TaskCommandOpts] = None,
        cwd: str = "",
    ) -> ClaudeCodeCommand:
        opts = opts or TaskCommandOpts()
        prompt = render_template(
            "task_execution.j2",
            package="i2code.implement",
            idea_directory=idea_directory,
            task_description=task_description,
            extra_prompt=opts.extra_prompt,
            interactive=opts.interactive,
        )

        allowed_tools, add_dirs, extra_args = self._split_extra_cli_args(
            opts.extra_cli_args,
        )

        return ClaudeCodeCommand(
            cwd=cwd,
            prompt=prompt,
            interactive=opts.interactive,
            allowed_tools=allowed_tools,
            add_dirs=add_dirs,
            extra_args=extra_args,
        )

    def _split_extra_cli_args(
        self, extra_cli_args: Optional[List[str]],
    ) -> Tuple[Optional[str], List[str], List[str]]:
        allowed_tools: Optional[str] = None
        add_dirs: List[str] = []
        extra_args: List[str] = []

        tokens = list(extra_cli_args or [])
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == "--allowedTools" and i + 1 < len(tokens):
                allowed_tools = tokens[i + 1]
                i += 2
            elif token == "--add-dir" and i + 1 < len(tokens):
                add_dirs.append(tokens[i + 1])
                i += 2
            else:
                extra_args.append(token)
                i += 1

        return allowed_tools, add_dirs, extra_args

    def build_scaffolding_command(
        self,
        idea_directory: str,
        interactive: bool = True,
        mock_claude: Optional[str] = None,
    ) -> List[str]:
        """Build the Claude command for project scaffolding.

        Args:
            idea_directory: Path to the idea directory.
            interactive: If True, run Claude interactively.
            mock_claude: Optional path to mock script for testing.

        Returns:
            Command list suitable for subprocess.
        """
        if mock_claude:
            return [mock_claude, "setup"]

        prompt = render_template(
            "scaffolding.j2",
            package="i2code.implement",
            idea_directory=idea_directory,
        )

        if interactive:
            return ["claude", prompt]
        else:
            return [
                "claude",
                "--allowed-tools",
                "Write,Read,Edit,Bash(gradle --version),Bash(mkdir -p:*)",
                "--verbose", "--output-format=stream-json", "-p", prompt,
            ]

    def build_triage_command(
        self,
        feedback_content: str,
        cwd: str = "",
        interactive: bool = True,
    ) -> ClaudeCodeCommand:
        prompt = render_template(
            "triage_feedback.j2",
            package="i2code.implement",
            feedback_content=feedback_content,
        )

        return ClaudeCodeCommand(
            cwd=cwd,
            prompt=prompt,
            interactive=interactive,
        )

    def build_fix_command(
        self,
        pr_url: str,
        feedback_content: str,
        fix_description: str,
        interactive: bool = True,
    ) -> List[str]:
        """Build command to invoke Claude for fixing a group of comments.

        Args:
            pr_url: The PR URL.
            feedback_content: The specific feedback to address.
            fix_description: Description of what to fix.
            interactive: If True, run Claude interactively.

        Returns:
            Command list suitable for subprocess.
        """
        prompt = render_template(
            "fix_feedback.j2",
            package="i2code.implement",
            pr_url=pr_url,
            feedback_content=feedback_content,
            fix_description=fix_description,
        )

        return self._with_mode(prompt, interactive)

    def build_ci_fix_command(
        self,
        run_id: int,
        workflow_name: str,
        failure_logs: str,
        interactive: bool = True,
    ) -> List[str]:
        """Build command to invoke Claude for fixing CI failures.

        Args:
            run_id: The workflow run database ID.
            workflow_name: Name of the failing workflow.
            failure_logs: The failure logs from the workflow.
            interactive: If True, run Claude interactively.

        Returns:
            Command list suitable for subprocess.
        """
        max_log_length = 5000
        if len(failure_logs) > max_log_length:
            failure_logs = f"... (truncated)\n{failure_logs[-max_log_length:]}"

        prompt = render_template(
            "ci_fix.j2",
            package="i2code.implement",
            run_id=run_id,
            workflow_name=workflow_name,
            failure_logs=failure_logs,
        )

        return self._with_mode(prompt, interactive)

    def build_feedback_command(
        self,
        pr_url: str,
        feedback_type: str,
        feedback_content: str,
    ) -> List[str]:
        """Build the command to invoke Claude for handling feedback.

        Args:
            pr_url: The PR URL.
            feedback_type: Type of feedback (review_comment, review, etc.).
            feedback_content: The feedback content to address.

        Returns:
            Command list suitable for subprocess.
        """
        prompt = render_template(
            "address_feedback.j2",
            package="i2code.implement",
            pr_url=pr_url,
            feedback_type=feedback_type,
            feedback_content=feedback_content,
        )

        return [
            "claude",
            "--print", "wt-handle-feedback.md",
            "-p", prompt,
        ]
