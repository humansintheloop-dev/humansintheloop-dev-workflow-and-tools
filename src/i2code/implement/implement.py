"""PR feedback processing and Claude result diagnostics.

This module contains process_pr_feedback (the feedback triage and fix loop),
check_claude_success, and print_task_failure_diagnostics.

All other functions have been extracted to dedicated modules:
- git_setup: branch creation, worktree management, permissions
- pr_helpers: PR title/body, feedback helpers, push commands
- branch_lifecycle: rebase, cleanup, interrupt handling
- project_setup: scaffolding and integration branch setup
- ci_fix: CI failure detection and auto-fix
- claude_runner: Claude invocation (interactive and captured)
"""

import sys
from typing import Optional

from git import Repo as GitRepo

from i2code.implement.claude_runner import (
    ClaudeResult,
    run_claude_interactive,
    run_claude_with_output_capture,
)
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.pr_helpers import (
    _default_gh_client,
    determine_comment_type,
    format_all_feedback,
    get_feedback_by_ids,
    get_new_feedback,
    parse_triage_result,
    push_branch_to_remote,
)


def process_pr_feedback(
    pr_number: int,
    pr_url: str,
    state,
    worktree_path: str,
    slice_branch: str,
    interactive: bool = True,
    mock_claude: Optional[str] = None,
    skip_ci_wait: bool = False,
    ci_timeout: int = 600,
    gh_client=None,
) -> tuple:
    """Process new PR feedback using triage-based approach.

    Flow:
    1. Fetch and filter new feedback
    2. Invoke Claude to triage (categorize as will_fix or needs_clarification)
    3. Reply to comments needing clarification
    4. For each fix group: invoke Claude, push, reply with SHA, verify CI

    Returns:
        Tuple of (had_feedback, made_changes):
        - had_feedback: True if there was new feedback to process
        - made_changes: True if Claude made code changes (commits)
    """
    if gh_client is None:
        gh_client = _default_gh_client()

    review_comments = gh_client.fetch_pr_comments(pr_number)
    reviews = gh_client.fetch_pr_reviews(pr_number)
    conversation_comments = gh_client.fetch_pr_conversation_comments(pr_number)

    new_review_comments = get_new_feedback(
        review_comments, state.processed_comment_ids,
    )
    new_reviews = get_new_feedback(
        reviews, state.processed_review_ids,
    )
    new_conversation = get_new_feedback(
        conversation_comments, state.processed_conversation_ids,
    )

    if not new_review_comments and not new_reviews and not new_conversation:
        return (False, False)

    print(f"Found new feedback: {len(new_reviews)} review(s), "
          f"{len(new_review_comments)} review comment(s), "
          f"{len(new_conversation)} general comment(s)")

    all_new_feedback = new_review_comments + new_reviews + new_conversation
    feedback_content = format_all_feedback(
        new_review_comments, new_reviews, new_conversation,
    )

    print("Triaging feedback...")
    if mock_claude:
        triage_cmd = [mock_claude, f"triage-{pr_number}"]
    else:
        triage_cmd = CommandBuilder().build_triage_command(feedback_content, interactive=False)

    triage_result = run_claude_with_output_capture(triage_cmd, cwd=worktree_path)

    triage = parse_triage_result(triage_result.stdout)
    if not triage:
        print("Warning: Could not parse triage result, marking all as processed")
        state.mark_comments_processed([c["id"] for c in new_review_comments])
        state.mark_reviews_processed([r["id"] for r in new_reviews])
        state.mark_conversations_processed([c["id"] for c in new_conversation])
        return (True, False)

    will_fix = triage.get("will_fix", [])
    needs_clarification = triage.get("needs_clarification", [])

    print(f"Triage result: {len(will_fix)} fix group(s), "
          f"{len(needs_clarification)} needing clarification")

    for item in needs_clarification:
        comment_id = item.get("comment_id")
        question = item.get("question", "Could you please clarify?")

        comment_type = determine_comment_type(
            comment_id, new_review_comments, new_conversation,
        )

        print(f"Asking for clarification on comment {comment_id}...")
        if comment_type == "review":
            success = gh_client.reply_to_review_comment(pr_number, comment_id, question)
        else:
            success = gh_client.reply_to_pr_comment(pr_number, f"Re: comment {comment_id}\n\n{question}")

        if success:
            print(f"  Replied to comment {comment_id}")
        else:
            print(f"  Warning: Failed to reply to comment {comment_id}")

    worktree_repo = GitRepo(worktree_path)
    made_any_changes = False

    for fix_group in will_fix:
        comment_ids = fix_group.get("comment_ids", [])
        description = fix_group.get("description", "Address feedback")

        if not comment_ids:
            continue

        print(f"\nFixing: {description}")
        print(f"  Comments: {comment_ids}")

        group_feedback = get_feedback_by_ids(all_new_feedback, comment_ids)
        group_content = format_all_feedback(
            [f for f in group_feedback if f in new_review_comments],
            [f for f in group_feedback if f in new_reviews],
            [f for f in group_feedback if f in new_conversation],
        )

        head_before = worktree_repo.head.commit.hexsha

        if mock_claude:
            fix_cmd = [mock_claude, f"fix-{pr_number}-{comment_ids[0]}"]
        else:
            fix_cmd = CommandBuilder().build_fix_command(pr_url, group_content, description, interactive=interactive)

        print("  Invoking Claude to fix...")
        if interactive:
            run_claude_interactive(fix_cmd, cwd=worktree_path)
        else:
            run_claude_with_output_capture(fix_cmd, cwd=worktree_path)

        head_after = worktree_repo.head.commit.hexsha

        if head_before == head_after:
            print("  Warning: Claude did not make any commits for this fix")
            continue

        made_any_changes = True
        commit_sha = head_after[:8]
        print(f"  Committed: {commit_sha}")

        print("  Pushing...")
        if not push_branch_to_remote(slice_branch):
            print("  Error: Could not push fix", file=sys.stderr)
            return (True, True)

        for comment_id in comment_ids:
            comment_type = determine_comment_type(
                comment_id, new_review_comments, new_conversation,
            )

            reply_body = f"Fixed in {commit_sha}"
            if comment_type == "review":
                success = gh_client.reply_to_review_comment(pr_number, comment_id, reply_body)
            else:
                success = gh_client.reply_to_pr_comment(pr_number, f"Re: comment {comment_id}\n\n{reply_body}")

            if success:
                print(f"  Replied to comment {comment_id}: {reply_body}")
            else:
                print(f"  Warning: Failed to reply to comment {comment_id}")

        if not skip_ci_wait:
            print("  Waiting for CI...")
            ci_success, failing_run = gh_client.wait_for_workflow_completion(
                slice_branch, head_after, timeout_seconds=ci_timeout,
            )

            if not ci_success and failing_run:
                workflow_name = failing_run.get("name", "unknown")
                print(f"  CI failed: {workflow_name}")
            elif ci_success:
                print("  CI passed!")

    state.mark_comments_processed([c["id"] for c in new_review_comments])
    state.mark_reviews_processed([r["id"] for r in new_reviews])
    state.mark_conversations_processed([c["id"] for c in new_conversation])

    return (True, made_any_changes)


def print_task_failure_diagnostics(
    claude_result: 'ClaudeResult',
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
