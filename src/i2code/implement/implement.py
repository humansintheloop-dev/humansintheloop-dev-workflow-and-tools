"""Claude result diagnostics and success checking.

This module contains check_claude_success and print_task_failure_diagnostics.

All other functions have been extracted to dedicated modules:
- git_setup: branch creation, worktree management, permissions
- pr_helpers: PR title/body, feedback helpers, push commands
- branch_lifecycle: rebase, cleanup, interrupt handling
- project_setup: scaffolding and integration branch setup
- github_actions_build_fixer: CI failure detection and auto-fix
- claude_runner: Claude invocation (interactive and captured)
- pull_request_review_processor: PR feedback triage and fix loop
"""

import sys


def print_task_failure_diagnostics(
    claude_result,
    head_before: str,
    head_after: str,
) -> None:
    """Print diagnostic information when a Claude task execution fails."""
    print("\nError: Task execution failed.", file=sys.stderr)
    print(f"  Exit code: {claude_result.returncode}", file=sys.stderr)
    print(f"  HEAD before: {head_before}", file=sys.stderr)
    print(f"  HEAD after: {head_after}", file=sys.stderr)

    if claude_result.permission_denials:
        print(f"\nPermission denied for {len(claude_result.permission_denials)} action(s):", file=sys.stderr)
        for denial in claude_result.permission_denials:
            tool_name = denial.get('tool_name', 'Unknown')
            tool_input = denial.get('tool_input', {})
            cmd = tool_input.get('command', tool_input.get('description', 'N/A'))
            print(f"  - {tool_name}: {cmd}", file=sys.stderr)
        print("\nAdd missing permissions to .claude/settings.local.json", file=sys.stderr)

    if claude_result.error_message:
        print(f"\nClaude error: {claude_result.error_message}", file=sys.stderr)

    if claude_result.last_messages:
        print(f"\nLast {len(claude_result.last_messages)} messages from Claude:", file=sys.stderr)
        for msg in claude_result.last_messages:
            msg_type = msg.get('type', 'unknown')
            if msg_type == 'assistant':
                content = msg.get('message', {}).get('content', [])
                for item in content:
                    if item.get('type') == 'text':
                        text = item.get('text', '')[:200]
                        print(f"  [{msg_type}] {text}...", file=sys.stderr)
            elif msg_type == 'result':
                result = msg.get('result', '')[:200]
                print(f"  [{msg_type}] {result}...", file=sys.stderr)
            else:
                print(f"  [{msg_type}]", file=sys.stderr)


def check_claude_success(exit_code: int, head_before: str, head_after: str) -> bool:
    """Check if Claude invocation was successful.

    Success requires:
    1. Exit code of 0
    2. HEAD advanced (a commit was made)
    """
    return exit_code == 0 and head_before != head_after
