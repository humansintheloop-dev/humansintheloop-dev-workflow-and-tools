"""PullRequestReviewProcessor: processes PR review feedback."""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from i2code.implement.command_builder import CommandBuilder


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

        Returns:
            Tuple of (had_feedback, made_changes):
            - had_feedback: True if there was new feedback to process
            - made_changes: True if Claude made code changes (commits)
        """
        pr_number = self._git_repo.pr_number

        new_review_comments, new_reviews, new_conversation = (
            self._fetch_unprocessed_feedback(pr_number)
        )

        if not new_review_comments and not new_reviews and not new_conversation:
            return (False, False)

        return self._triage_and_apply_feedback(
            new_review_comments, new_reviews, new_conversation, pr_number,
        )

    def _fetch_unprocessed_feedback(self, pr_number):
        """Fetch PR feedback and filter to only unprocessed items."""
        gh_client = self._git_repo.gh_client

        review_comments = gh_client.fetch_pr_comments(pr_number)
        reviews = gh_client.fetch_pr_reviews(pr_number)
        conversation_comments = gh_client.fetch_pr_conversation_comments(pr_number)

        return (
            self._get_new_feedback(review_comments, self._state.processed_comment_ids),
            self._get_new_feedback(reviews, self._state.processed_review_ids),
            self._get_new_feedback(conversation_comments, self._state.processed_conversation_ids),
        )

    def _triage_and_apply_feedback(self, new_review_comments, new_reviews, new_conversation, pr_number):
        """Triage feedback via Claude and apply the results.

        Returns:
            Tuple of (had_feedback=True, made_changes).
        """
        print(f"Found new feedback: {len(new_reviews)} review(s), "
              f"{len(new_review_comments)} review comment(s), "
              f"{len(new_conversation)} general comment(s)")

        feedback_content = self._format_all_feedback(
            new_review_comments, new_reviews, new_conversation,
        )

        triage = self._triage_feedback(feedback_content, pr_number)

        if not triage:
            self._mark_all_processed(new_review_comments, new_reviews, new_conversation)
            return (True, False)

        new_feedback = (new_review_comments, new_reviews, new_conversation)
        made_changes = self._apply_feedback(triage, new_feedback, pr_number)

        self._mark_all_processed(new_review_comments, new_reviews, new_conversation)
        return (True, made_changes)

    def _triage_feedback(self, feedback_content, pr_number):
        """Run Claude triage and parse the result.

        Returns:
            Parsed triage dict, or None if parsing failed.
        """
        triage_cmd, triage_result = self._run_triage(feedback_content, pr_number)

        prompt = self._extract_prompt_from_command(triage_cmd)
        self._log_to_file(
            f"=== Triage request ===\n"
            f"--- prompt ---\n{prompt}\n"
            f"--- claude response ---\n{triage_result.output.stdout}\n"
        )

        triage = self._parse_triage_result(triage_result.output.stdout)
        if not triage:
            print("Warning: Could not parse triage result, marking all as processed")
            return None

        return triage

    @staticmethod
    def _extract_prompt_from_command(cmd):
        """Extract the -p prompt argument from a Claude command list."""
        try:
            idx = cmd.index("-p")
            return cmd[idx + 1]
        except (ValueError, IndexError):
            return " ".join(cmd)

    def _apply_feedback(self, triage, new_feedback, pr_number):
        """Apply a parsed triage result: clarifications then fixes.

        Returns:
            True if code changes were made, False otherwise.
            Raises early (returns True) on push failure.
        """
        new_review_comments, _, new_conversation = new_feedback

        will_fix = triage.get("will_fix", [])
        needs_clarification = triage.get("needs_clarification", [])

        print(f"Triage result: {len(will_fix)} fix group(s), "
              f"{len(needs_clarification)} needing clarification")

        self._reply_with_clarifications(
            needs_clarification, pr_number, new_review_comments, new_conversation,
        )

        made_any_changes = self._apply_fix_groups(will_fix, new_feedback)
        if made_any_changes is None:
            return True

        return made_any_changes

    def _run_triage(self, feedback_content, pr_number):
        """Build and run the triage command via Claude.

        Returns:
            Tuple of (command_list, ClaudeResult).
        """
        print("Triaging feedback...")
        if self._opts.mock_claude:
            triage_cmd = [self._opts.mock_claude, f"triage-{pr_number}"]
        else:
            triage_cmd = CommandBuilder().build_triage_command(feedback_content, interactive=False)

        result = self._claude_runner.run_batch(triage_cmd, cwd=self._git_repo.working_tree_dir)
        return triage_cmd, result

    def _reply_with_clarifications(self, needs_clarification, pr_number, new_review_comments, new_conversation):
        """Reply to comments needing clarification."""
        gh_client = self._git_repo.gh_client

        for item in needs_clarification:
            comment_id = item.get("comment_id")
            question = item.get("question", "Could you please clarify?")

            comment_type = self._determine_comment_type(
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

    def _apply_fix_groups(self, will_fix, new_feedback):
        """Apply fix groups by invoking Claude, pushing, and replying.

        Returns:
            True/False for whether changes were made, or None if push failed.
        """
        made_any_changes = False

        for fix_group in will_fix:
            result = self._process_fix_group(fix_group, new_feedback)
            if result is None:
                return None
            if result:
                made_any_changes = True

        return made_any_changes

    def _process_fix_group(self, fix_group, new_feedback):
        """Process a single fix group: invoke Claude, push, reply.

        Returns:
            True if changes were made, False if not, None if push failed.
        """
        new_review_comments, new_reviews, new_conversation = new_feedback
        comment_ids = fix_group.get("comment_ids", [])
        description = fix_group.get("description", "Address feedback")

        if not comment_ids:
            return False

        print(f"\nFixing: {description}")
        print(f"  Comments: {comment_ids}")

        all_feedback = new_review_comments + new_reviews + new_conversation
        group_feedback = self._get_feedback_by_ids(all_feedback, comment_ids)
        group_content = self._format_all_feedback(
            [f for f in group_feedback if f in new_review_comments],
            [f for f in group_feedback if f in new_reviews],
            [f for f in group_feedback if f in new_conversation],
        )

        commit_sha = self._invoke_fix(group_content, description, comment_ids)
        if not commit_sha:
            return False

        if not self._push_and_reply(commit_sha, comment_ids, new_review_comments, new_conversation):
            return None

        self._wait_for_ci_if_needed(commit_sha)
        return True

    def _invoke_fix(self, group_content, description, comment_ids):
        """Invoke Claude to fix a group. Returns short commit SHA or None."""
        pr_number = self._git_repo.pr_number
        pr_url = self._git_repo.gh_client.get_pr_url(pr_number)
        interactive = not self._opts.non_interactive
        head_before = self._git_repo.head_sha

        if self._opts.mock_claude:
            fix_cmd = [self._opts.mock_claude, f"fix-{pr_number}-{comment_ids[0]}"]
        else:
            fix_cmd = CommandBuilder().build_fix_command(pr_url, group_content, description, interactive=interactive)

        print("  Invoking Claude to fix...")
        if interactive:
            self._claude_runner.run_interactive(fix_cmd, cwd=self._git_repo.working_tree_dir)
        else:
            self._claude_runner.run_batch(fix_cmd, cwd=self._git_repo.working_tree_dir)

        head_after = self._git_repo.head_sha
        if head_before == head_after:
            print("  Warning: Claude did not make any commits for this fix")
            return None

        commit_sha = head_after[:8]
        print(f"  Committed: {commit_sha}")
        return commit_sha

    def _push_and_reply(self, commit_sha, comment_ids, new_review_comments, new_conversation):
        """Push changes and reply to comments. Returns False if push fails."""
        pr_number = self._git_repo.pr_number
        gh_client = self._git_repo.gh_client

        print("  Pushing...")
        if not self._git_repo.push():
            print("  Error: Could not push fix", file=sys.stderr)
            return False

        for comment_id in comment_ids:
            comment_type = self._determine_comment_type(
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

        return True

    def _wait_for_ci_if_needed(self, commit_sha):
        """Wait for CI if configured to do so."""
        if self._opts.skip_ci_wait:
            return

        gh_client = self._git_repo.gh_client
        head_sha = self._git_repo.head_sha
        print("  Waiting for CI...")
        ci_success, failing_run = gh_client.wait_for_workflow_completion(
            self._git_repo.branch, head_sha, timeout_seconds=self._opts.ci_timeout,
        )

        if not ci_success and failing_run:
            workflow_name = failing_run.get("name", "unknown")
            print(f"  CI failed: {workflow_name}")
        elif ci_success:
            print("  CI passed!")

    def _mark_all_processed(self, new_review_comments, new_reviews, new_conversation):
        """Mark all feedback items as processed in workflow state."""
        self._state.mark_comments_processed([c["id"] for c in new_review_comments])
        self._state.mark_reviews_processed([r["id"] for r in new_reviews])
        self._state.mark_conversations_processed([c["id"] for c in new_conversation])

    @staticmethod
    def _get_new_feedback(
        all_feedback: List[Dict[str, Any]], processed_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """Filter feedback to only include items not yet processed."""
        return [f for f in all_feedback if f.get("id") not in processed_ids]

    @staticmethod
    def _format_all_feedback(
        review_comments: List[Dict[str, Any]],
        reviews: List[Dict[str, Any]],
        conversation_comments: List[Dict[str, Any]],
    ) -> str:
        """Format all feedback types into a single string for Claude."""
        sections = []

        if reviews:
            sections.append("## PR Reviews\n")
            for review in reviews:
                state = review.get("state", "COMMENTED")
                body = review.get("body", "").strip()
                user = review.get("user", {}).get("login", "unknown")
                review_id = review.get("id")
                sections.append(f"### Review by {user} (ID: {review_id}, State: {state})")
                if body:
                    sections.append(f"{body}\n")
                else:
                    sections.append("(No body text)\n")

        if review_comments:
            sections.append("## Review Comments (on specific code lines)\n")
            for comment in review_comments:
                body = comment.get("body", "").strip()
                user = comment.get("user", {}).get("login", "unknown")
                path = comment.get("path", "unknown file")
                line = comment.get("line") or comment.get("original_line", "?")
                comment_id = comment.get("id")
                sections.append(f"### Comment by {user} on {path}:{line} (ID: {comment_id})")
                sections.append(f"{body}\n")

        if conversation_comments:
            sections.append("## General PR Comments\n")
            for comment in conversation_comments:
                body = comment.get("body", "").strip()
                user = comment.get("user", {}).get("login", "unknown")
                comment_id = comment.get("id")
                sections.append(f"### Comment by {user} (ID: {comment_id})")
                sections.append(f"{body}\n")

        return "\n".join(sections)

    @staticmethod
    def _parse_triage_result(claude_output: str) -> Optional[Dict[str, Any]]:
        """Parse the JSON triage result from Claude's output."""
        text = PullRequestReviewProcessor._extract_result_text(claude_output)
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                print(f"Warning: Found ```json block but failed to parse: {e}", file=sys.stderr)
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse triage output as JSON: {e}", file=sys.stderr)
            print(f"  Output: {text.strip()}", file=sys.stderr)
        return None

    @staticmethod
    def _extract_result_text(claude_output: str) -> str:
        """Extract result text from stream-json output, or return as-is."""
        for line in claude_output.split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                if msg.get('type') == 'result' and 'result' in msg:
                    return msg['result']
            except json.JSONDecodeError:
                continue
        return claude_output

    @staticmethod
    def _get_feedback_by_ids(
        all_feedback: List[Dict[str, Any]], comment_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """Get feedback items matching the given IDs."""
        return [f for f in all_feedback if f.get("id") in comment_ids]

    @staticmethod
    def _determine_comment_type(
        comment_id: int, review_comments: List[Dict], conversation_comments: List[Dict],
    ) -> str:
        """Determine whether a comment ID is a review comment or conversation comment."""
        for c in review_comments:
            if c.get("id") == comment_id:
                return "review"
        return "conversation"

    def _log_to_file(self, message):
        worktree_name = os.path.basename(self._git_repo.working_tree_dir)
        log_dir = Path.home() / ".hitl" / worktree_name / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with open(log_dir / "log.log", "a") as f:
            timestamp = datetime.now(timezone.utc).isoformat()
            f.write(f"[{timestamp}] {message}\n")
