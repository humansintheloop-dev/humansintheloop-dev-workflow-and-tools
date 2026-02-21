"""Temporary test: run real Claude triage against PR #6 fixture data.

Runs Claude for real and writes prompt + response to a log file.

Usage:
    uv run --with pytest pytest tests/implement/test_triage_real_claude.py -v -s
"""

import json
import os

import pytest

from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.pull_request_review_processor import PullRequestReviewProcessor

FIXTURE_FILE = os.path.join(os.path.dirname(__file__), "fixtures", "pr6_feedback.json")


@pytest.mark.manual
def test_real_claude_triage_pr6(tmp_path):
    """Run real Claude triage on PR #6 feedback, print prompt and response."""
    assert os.path.exists(FIXTURE_FILE), (
        f"Fixture not found: {FIXTURE_FILE}\n"
        f"Run: uv run --with pytest pytest tests/implement/test_triage_failure_logging.py -m gather_fixtures"
    )

    with open(FIXTURE_FILE) as f:
        data = json.load(f)

    feedback_content = PullRequestReviewProcessor._format_all_feedback(
        data["review_comments"], data["reviews"], data["conversation_comments"],
    )

    triage_cmd = CommandBuilder().build_triage_command(feedback_content, interactive=False)

    # Extract prompt
    prompt_idx = triage_cmd.index("-p")
    prompt = triage_cmd[prompt_idx + 1]

    print("\n" + "=" * 80)
    print("(1) PROMPT PASSED TO CLAUDE")
    print("=" * 80)
    print(prompt)
    print()

    # Run real Claude
    runner = ClaudeRunner()
    result = runner.run_with_capture(triage_cmd, cwd=os.getcwd())

    print("=" * 80)
    print("(2) CLAUDE'S RESPONSE")
    print("=" * 80)
    print(f"Return code: {result.returncode}")
    print(f"Stdout:\n{result.stdout}")
    if result.stderr:
        print(f"Stderr:\n{result.stderr}")

    # Also write to a file for easy review
    log_file = tmp_path / "triage_debug.log"
    log_file.write_text(
        f"=== PROMPT ===\n{prompt}\n\n"
        f"=== RESPONSE (stdout) ===\n{result.stdout}\n\n"
        f"=== STDERR ===\n{result.stderr}\n"
    )
    print(f"\nFull log written to: {log_file}")

    # Try to parse the triage result
    triage = PullRequestReviewProcessor._parse_triage_result(result.stdout)
    print(f"\nParsed triage result: {json.dumps(triage, indent=2) if triage else 'PARSE FAILED (None)'}")
