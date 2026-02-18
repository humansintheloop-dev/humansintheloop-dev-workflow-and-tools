"""PullRequestReviewProcessor: processes PR review feedback."""

import sys

from i2code.implement.command_builder import CommandBuilder
from i2code.implement.pr_helpers import (
    determine_comment_type,
    format_all_feedback,
    get_feedback_by_ids,
    get_new_feedback,
    parse_triage_result,
)


class PullRequestReviewProcessor:
    """Processes PR review feedback for a worktree-based workflow.

    Args:
        opts: ImplementOpts with execution parameters.
        git_repo: GitRepository (or FakeGitRepository) for branch/push/PR/CI operations.
        state: WorkflowState (or FakeWorkflowState) for tracking processed feedback.
        claude_runner: ClaudeRunner (or FakeClaudeRunner) for invoking Claude.
    """

    def __init__(self, opts, git_repo, state, claude_runner):
        self._opts = opts
        self._git_repo = git_repo
        self._state = state
        self._claude_runner = claude_runner

    def process_feedback(self):
        """Process PR feedback if any exists.

        Returns True if feedback was found (caller should loop back).
        """
        if not self._git_repo.pr_number or not self._git_repo.branch_has_been_pushed():
            return False

        had_feedback, _made_changes = self.process_pr_feedback()

        if had_feedback:
            self._state.save()
            return True

        return False

    def process_pr_feedback(self):
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
        pr_number = self._git_repo.pr_number
        pr_url = self._git_repo.gh_client.get_pr_url(pr_number)
        gh_client = self._git_repo.gh_client

        review_comments = gh_client.fetch_pr_comments(pr_number)
        reviews = gh_client.fetch_pr_reviews(pr_number)
        conversation_comments = gh_client.fetch_pr_conversation_comments(pr_number)

        new_review_comments = get_new_feedback(
            review_comments, self._state.processed_comment_ids,
        )
        new_reviews = get_new_feedback(
            reviews, self._state.processed_review_ids,
        )
        new_conversation = get_new_feedback(
            conversation_comments, self._state.processed_conversation_ids,
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
        if self._opts.mock_claude:
            triage_cmd = [self._opts.mock_claude, f"triage-{pr_number}"]
        else:
            triage_cmd = CommandBuilder().build_triage_command(feedback_content, interactive=False)

        triage_result = self._claude_runner.run_with_capture(triage_cmd, cwd=self._git_repo.working_tree_dir)

        triage = parse_triage_result(triage_result.stdout)
        if not triage:
            print("Warning: Could not parse triage result, marking all as processed")
            self._state.mark_comments_processed([c["id"] for c in new_review_comments])
            self._state.mark_reviews_processed([r["id"] for r in new_reviews])
            self._state.mark_conversations_processed([c["id"] for c in new_conversation])
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

        interactive = not self._opts.non_interactive
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

            head_before = self._git_repo.head_sha

            if self._opts.mock_claude:
                fix_cmd = [self._opts.mock_claude, f"fix-{pr_number}-{comment_ids[0]}"]
            else:
                fix_cmd = CommandBuilder().build_fix_command(pr_url, group_content, description, interactive=interactive)

            print("  Invoking Claude to fix...")
            if interactive:
                self._claude_runner.run_interactive(fix_cmd, cwd=self._git_repo.working_tree_dir)
            else:
                self._claude_runner.run_with_capture(fix_cmd, cwd=self._git_repo.working_tree_dir)

            head_after = self._git_repo.head_sha

            if head_before == head_after:
                print("  Warning: Claude did not make any commits for this fix")
                continue

            made_any_changes = True
            commit_sha = head_after[:8]
            print(f"  Committed: {commit_sha}")

            print("  Pushing...")
            if not self._git_repo.push():
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

            if not self._opts.skip_ci_wait:
                print("  Waiting for CI...")
                ci_success, failing_run = gh_client.wait_for_workflow_completion(
                    self._git_repo.branch, head_after, timeout_seconds=self._opts.ci_timeout,
                )

                if not ci_success and failing_run:
                    workflow_name = failing_run.get("name", "unknown")
                    print(f"  CI failed: {workflow_name}")
                elif ci_success:
                    print("  CI passed!")

        self._state.mark_comments_processed([c["id"] for c in new_review_comments])
        self._state.mark_reviews_processed([r["id"] for r in new_reviews])
        self._state.mark_conversations_processed([c["id"] for c in new_conversation])

        return (True, made_any_changes)
