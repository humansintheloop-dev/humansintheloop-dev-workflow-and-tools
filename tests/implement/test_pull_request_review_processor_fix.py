"""Tests for PullRequestReviewProcessor fix-group processing.

Covers fix-group dispatch via claude_runner.execute(), git_repo head-SHA
tracking, push behavior, and state marking after a successful fix.
"""

import json

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.claude_runner import (
    CapturedOutput,
    ClaudeCodeCommand,
    ClaudeResult,
)
from i2code.implement.command_builder import CommandBuilder, FixRequest

from pull_request_review_processor_helpers import make_processor


SINGLE_COMMENT = [{"id": 1, "body": "fix this", "user": {"login": "u"}}]


def _triage_with_fix(comment_ids, description="Fix issue"):
    return json.dumps({
        "will_fix": [{"comment_ids": comment_ids, "description": description}],
        "needs_clarification": [],
    })


def _make_fix_processor(comments, triage_json, non_interactive=True, **extra):
    """Create a processor configured for fix-group tests with head SHA advancement."""
    triage_result = ClaudeResult(
        returncode=0,
        output=CapturedOutput(triage_json),
        result_text=triage_json,
    )
    fix_result = ClaudeResult(returncode=0)

    processor, _, fake_repo, fake_state, fake_claude = make_processor(
        comments=comments, non_interactive=non_interactive, **extra,
    )
    fake_repo.set_head_sha("aaa111")

    def advance_head():
        fake_repo.set_head_sha("bbb222")

    fake_claude.set_results([triage_result, fix_result])
    fake_claude.set_side_effects([lambda: None, advance_head])

    return processor, fake_repo, fake_state, fake_claude


@pytest.mark.unit
class TestProcessPrFeedbackFixGroup:
    """process_pr_feedback processes fix groups using injected collaborators."""

    def test_fix_uses_git_repo_head_sha_not_gitrepo(self):
        """HEAD tracking uses self._git_repo.head_sha, not GitRepo(worktree_path)."""
        processor, _, _, _ = _make_fix_processor(SINGLE_COMMENT, _triage_with_fix([1]))
        had_feedback, made_changes = processor.process_pr_feedback()
        assert had_feedback is True
        assert made_changes is True

    def test_fix_uses_git_repo_push_not_push_branch_to_remote(self):
        """Push uses self._git_repo.push(), not push_branch_to_remote()."""
        processor, fake_repo, _, _ = _make_fix_processor(SINGLE_COMMENT, _triage_with_fix([1]))
        processor.process_pr_feedback()
        push_calls = [c for c in fake_repo.calls if c[0] == "push"]
        assert len(push_calls) == 1

    def test_fix_uses_execute_with_command_dataclass(self):
        """Non-mock fix dispatches execute() with the CommandBuilder fix command."""
        processor, fake_repo, _, fake_claude = _make_fix_processor(
            SINGLE_COMMENT, _triage_with_fix([1]),
        )
        processor.process_pr_feedback()

        assert len(fake_claude.calls) == 2
        triage_method, _, _ = fake_claude.calls[0]
        fix_method, fix_cmd, fix_cwd = fake_claude.calls[1]
        assert triage_method == "execute"
        assert fix_method == "execute"
        assert isinstance(fix_cmd, ClaudeCodeCommand)
        feedback_content = PullRequestReviewProcessor._format_all_feedback(
            SINGLE_COMMENT, [], [],
        )
        expected = CommandBuilder().build_fix_command(
            FixRequest(
                pr_url="https://github.com/org/repo/pull/42",
                feedback_content=feedback_content,
                fix_description="Fix issue",
            ),
            cwd=fake_repo.working_tree_dir,
            interactive=False,
        )
        assert fix_cmd == expected
        assert fix_cwd == fake_repo.working_tree_dir

    def test_fix_with_mock_claude_uses_execute_with_mock_command(self):
        """When mock_claude is set, fix execute() receives a ClaudeCodeCommand with mock_command."""
        mock_path = "/path/to/mock-claude"
        processor, fake_repo, _, fake_claude = _make_fix_processor(
            SINGLE_COMMENT, _triage_with_fix([1]), mock_claude=mock_path,
        )
        processor.process_pr_feedback()

        assert len(fake_claude.calls) == 2
        fix_method, fix_cmd, fix_cwd = fake_claude.calls[1]
        assert fix_method == "execute"
        assert isinstance(fix_cmd, ClaudeCodeCommand)
        assert fix_cmd.cwd == fake_repo.working_tree_dir
        assert fix_cmd.mock_command == [mock_path, "fix-42-1"]
        assert fix_cwd == fake_repo.working_tree_dir

    def test_fix_marks_all_feedback_processed(self):
        """After processing, all feedback IDs are marked processed in state."""
        processor, _, fake_state, _ = _make_fix_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
            triage_json=_triage_with_fix([1]),
            reviews=[{"id": 10, "body": "looks bad", "state": "CHANGES_REQUESTED", "user": {"login": "u"}}],
            conversation_comments=[{"id": 20, "body": "general note", "user": {"login": "u"}}],
        )
        processor.process_pr_feedback()
        assert 1 in fake_state.processed_comment_ids
        assert 10 in fake_state.processed_review_ids
        assert 20 in fake_state.processed_conversation_ids
