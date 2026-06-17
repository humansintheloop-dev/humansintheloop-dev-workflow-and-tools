"""Tests for PullRequestReviewProcessor triage flow.

Covers triage execute() dispatch, JSON parsing of triage output, and prompt /
response logging on parse failure.
"""

import json
import os

import pytest

from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor
from i2code.implement.claude_runner import (
    CapturedOutput,
    ClaudeCodeCommand,
    ClaudeResult,
    _parse_stream_json_output,
)
from i2code.implement.command_builder import CommandBuilder

from fake_git_repository import FakeGitRepository
from fake_github_client import FakeGitHubClient
from fake_workflow_state import FakeWorkflowState
from fake_claude_runner import FakeClaudeRunner
from i2code.implement.implement_opts import ImplementOpts

from pull_request_review_processor_helpers import make_processor

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
PR6_FEEDBACK_FILE = os.path.join(FIXTURE_DIR, "pr6_feedback.json")
PR6_TRIAGE_STDOUT_FILE = os.path.join(FIXTURE_DIR, "pr6_triage_stdout.txt")

PR6_REPO = "humansintheloop-dev/humansintheloop-dev-workflow-and-tools"
PR6_NUMBER = 6


@pytest.mark.unit
class TestProcessPrFeedbackTriage:
    """process_pr_feedback triages feedback using claude_runner.execute()."""

    def test_triage_uses_execute_with_command_dataclass(self):
        """Non-mock triage dispatches execute() with the CommandBuilder triage command."""
        triage_json = json.dumps({"will_fix": [], "needs_clarification": []})
        triage_result = ClaudeResult(
            returncode=0,
            output=CapturedOutput(triage_json),
            result_text=triage_json,
        )

        feedback_comment = {"id": 1, "body": "fix this", "user": {"login": "u"}}
        processor, _, fake_repo, _, fake_claude = make_processor(
            comments=[feedback_comment],
        )
        fake_claude.set_result(triage_result)

        processor.process_pr_feedback()

        assert len(fake_claude.calls) == 1
        method, cmd, cwd = fake_claude.calls[0]
        assert method == "execute"
        assert isinstance(cmd, ClaudeCodeCommand)
        feedback_content = PullRequestReviewProcessor._format_all_feedback(
            [feedback_comment], [], [],
        )
        expected = CommandBuilder().build_triage_command(
            feedback_content,
            cwd=fake_repo.working_tree_dir,
            interactive=False,
        )
        assert cmd == expected
        assert cwd == fake_repo.working_tree_dir

    def test_triage_with_mock_claude_uses_execute_with_mock_command(self):
        """When mock_claude is set, triage execute() receives a ClaudeCodeCommand with mock_command."""
        triage_json = json.dumps({"will_fix": [], "needs_clarification": []})
        triage_result = ClaudeResult(
            returncode=0,
            output=CapturedOutput(triage_json),
            result_text=triage_json,
        )

        mock_path = "/path/to/mock-claude"
        processor, _, fake_repo, _, fake_claude = make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
            mock_claude=mock_path,
        )
        fake_claude.set_result(triage_result)

        processor.process_pr_feedback()

        assert len(fake_claude.calls) == 1
        method, cmd, cwd = fake_claude.calls[0]
        assert method == "execute"
        assert isinstance(cmd, ClaudeCodeCommand)
        assert cmd.cwd == fake_repo.working_tree_dir
        assert cmd.mock_command == [mock_path, "triage-42"]
        assert cwd == fake_repo.working_tree_dir

    def test_triage_reads_from_result_text(self):
        """Triage parses will_fix from result.result_text, not output.stdout."""
        triage_json = json.dumps({
            "will_fix": [{"comment_ids": [1], "description": "fix"}],
            "needs_clarification": [],
        })
        triage_result = ClaudeResult(
            returncode=0,
            output=CapturedOutput("ignored raw stdout"),
            result_text=triage_json,
        )
        fix_result = ClaudeResult(returncode=0)

        processor, _, fake_repo, _, fake_claude = make_processor(
            comments=[{"id": 1, "body": "fix this", "user": {"login": "u"}}],
        )
        fake_repo.set_head_sha("aaa111")

        def advance_head():
            fake_repo.set_head_sha("bbb222")

        fake_claude.set_results([triage_result, fix_result])
        fake_claude.set_side_effects([lambda: None, advance_head])

        had_feedback, made_changes = processor.process_pr_feedback()
        assert had_feedback is True
        assert made_changes is True

    def test_extract_result_text_no_longer_defined(self):
        """_extract_result_text private function is removed from the processor."""
        assert not hasattr(PullRequestReviewProcessor, "_extract_result_text")


@pytest.mark.unit
class TestParseTriageResult:
    """Test parsing JSON triage result from Claude."""

    def test_parse_triage_result_with_json_code_block(self):
        """Should parse JSON from markdown code block."""
        output = '''Here's the triage:
```json
{
  "will_fix": [{"comment_ids": [1, 2], "description": "Fix typo"}],
  "needs_clarification": []
}
```
'''
        result = PullRequestReviewProcessor._parse_triage_result(output)
        assert result is not None
        assert len(result["will_fix"]) == 1
        assert result["will_fix"][0]["comment_ids"] == [1, 2]

    def test_parse_triage_result_with_plain_json(self):
        """Should parse plain JSON output."""
        output = '{"will_fix": [], "needs_clarification": [{"comment_id": 5, "question": "What?"}]}'
        result = PullRequestReviewProcessor._parse_triage_result(output)
        assert result is not None
        assert len(result["needs_clarification"]) == 1
        assert result["needs_clarification"][0]["comment_id"] == 5

    def test_parse_triage_result_returns_none_on_invalid(self):
        """Should return None for invalid JSON."""
        assert PullRequestReviewProcessor._parse_triage_result("This is not JSON at all") is None


@pytest.mark.unit
class TestTriageFeedbackLogging:
    """Test that _triage_feedback logs prompt and response to file."""

    @pytest.fixture
    def pr6_feedback(self):
        assert os.path.exists(PR6_FEEDBACK_FILE), (
            f"Fixture not found: {PR6_FEEDBACK_FILE}\n"
            f"Run: uv run --with pytest pytest tests/implement/test_triage_failure_logging.py -m gather_fixtures"
        )
        with open(PR6_FEEDBACK_FILE) as f:
            return json.load(f)

    @pytest.fixture
    def home_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", classmethod(lambda cls: tmp_path))
        return tmp_path

    def _make_triage_processor(self, claude_stdout):
        worktree_name = "myrepo-wt-improve-modularity"

        fake_gh = FakeGitHubClient()
        fake_gh.set_pr_url(PR6_NUMBER, f"https://github.com/{PR6_REPO}/pull/{PR6_NUMBER}")

        fake_repo = FakeGitRepository(
            working_tree_dir=f"/worktrees/{worktree_name}", gh_client=fake_gh,
        )
        fake_repo.pr_number = PR6_NUMBER
        fake_repo.branch = "idea/improve-modularity/01-extract-ideaproject-class"
        fake_repo.set_pushed(True)

        fake_claude = FakeClaudeRunner()
        _diagnostics, result_text = _parse_stream_json_output(claude_stdout)
        fake_claude.set_result(ClaudeResult(
            returncode=0,
            output=CapturedOutput(claude_stdout),
            result_text=result_text,
        ))

        processor = PullRequestReviewProcessor(
            opts=ImplementOpts(idea_directory="/tmp/idea", non_interactive=True, skip_ci_wait=True),
            git_repo=fake_repo, state=FakeWorkflowState(), claude_runner=fake_claude,
        )

        return processor, worktree_name

    def test_logs_feedback_content_on_triage_parse_failure(self, pr6_feedback, home_dir):
        processor, worktree_name = self._make_triage_processor("not json at all")

        review_comments = pr6_feedback["review_comments"]
        feedback_content = PullRequestReviewProcessor._format_all_feedback(
            review_comments, pr6_feedback["reviews"], pr6_feedback["conversation_comments"],
        )

        result = processor._triage_feedback(feedback_content, PR6_NUMBER)
        assert result is None

        log_file = home_dir / ".hitl" / worktree_name / "logs" / "log.log"
        assert log_file.exists(), f"Expected log file at {log_file}"

        log_content = log_file.read_text()
        assert "--- prompt ---" in log_content
        assert "--- claude response ---" in log_content
        assert "not json at all" in log_content

        for comment in review_comments:
            body = comment.get("body", "").strip()
            if body:
                assert body in log_content, f"Expected review comment body in log: {body[:60]}..."
                break

    def test_parses_real_claude_triage_response(self, pr6_feedback, home_dir):
        with open(PR6_TRIAGE_STDOUT_FILE) as f:
            triage_stdout = f.read()

        processor, _ = self._make_triage_processor(triage_stdout)

        feedback_content = PullRequestReviewProcessor._format_all_feedback(
            pr6_feedback["review_comments"], pr6_feedback["reviews"], pr6_feedback["conversation_comments"],
        )

        result = processor._triage_feedback(feedback_content, PR6_NUMBER)
        assert result is not None, "Expected triage to parse successfully"
        assert "will_fix" in result
        assert "needs_clarification" in result
        assert len(result["will_fix"]) > 0
