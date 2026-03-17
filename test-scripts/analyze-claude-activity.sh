#!/usr/bin/env bash
# ============================================================================
# analyze-claude-activity.sh
#
# PROMPT:
# Create a script test-scripts/analyze-claude-activity.sh that takes a logfile
# such as logs/i2code-test-repo-banking-needs-get-accounts-endpoint-vm-20260317075318.log
# as an argument. Identifies the separate invocations of Claude.
#
# For each invocation, converts the json-streaming logging into a readable
# format. Determines success or failure. And if there's a failure determines
# the error.
#
# The script should primarily use bash or python but if necessary invoke Claude
# to process specific parts of the log.
#
# The output should be a markdown document next to the log file with the same
# name but with a .md extension, summarizing each Claude invocation, its
# success or failure, and any errors encountered.
#
# Include this prompt as a comment at the top of the script for clarity.
# ============================================================================

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <logfile>"
    echo "  Analyzes Claude invocations in a log file and produces a .md summary."
    exit 1
fi

LOGFILE="$1"

if [[ ! -f "$LOGFILE" ]]; then
    echo "Error: File not found: $LOGFILE"
    exit 1
fi

OUTPUT_FILE="${LOGFILE%.log}.md"

python3 - "$LOGFILE" "$OUTPUT_FILE" << 'PYTHON_SCRIPT'
import json
import sys
import re
import os
from datetime import datetime

def parse_log(logfile):
    """Parse a log file containing Claude invocations with JSON streaming output.

    Each invocation spans from 'Running Claude (attempt N/M)...' to the next
    such line or end of file. After the JSON stream's {"type":"result"} line,
    there is a harness-level block that determines actual success/failure by
    checking whether HEAD advanced (a new commit was made). This harness
    verdict is authoritative — Claude may report <SUCCESS> in the JSON result
    but the harness still considers it a failure if HEAD didn't change.
    """
    invocations = []
    current_invocation = None
    current_json_lines = []
    post_result_lines = []
    seen_result = False

    with open(logfile, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        stripped = line.rstrip('\n')

        attempt_match = re.match(r'Running Claude \(attempt (\d+)/(\d+)\)\.\.\.', stripped)
        if attempt_match:
            if current_invocation:
                current_invocation['json_lines'] = current_json_lines
                current_invocation['post_result_lines'] = post_result_lines
                finalize_invocation(current_invocation)
                invocations.append(current_invocation)
            current_invocation = {
                'attempt': int(attempt_match.group(1)),
                'max_attempts': int(attempt_match.group(2)),
                'start_line': i,
                'command': '',
                'json_lines': [],
                'post_result_lines': [],
                'result': None,
                'harness_error': None,
            }
            current_json_lines = []
            post_result_lines = []
            seen_result = False
            continue

        if current_invocation and stripped.startswith('Running Claude (cwd='):
            current_invocation['command'] = stripped
            continue

        if current_invocation and stripped.startswith('{'):
            try:
                obj = json.loads(stripped)
                current_json_lines.append(obj)
                if obj.get('type') == 'result':
                    seen_result = True
            except json.JSONDecodeError:
                if seen_result:
                    post_result_lines.append(stripped)
        elif current_invocation:
            if seen_result:
                post_result_lines.append(stripped)

    if current_invocation:
        current_invocation['json_lines'] = current_json_lines
        current_invocation['post_result_lines'] = post_result_lines
        finalize_invocation(current_invocation)
        invocations.append(current_invocation)

    return invocations


def finalize_invocation(invocation):
    """Extract result, errors, and harness verdict from an invocation."""
    json_lines = invocation['json_lines']

    for obj in json_lines:
        if obj.get('type') == 'system' and obj.get('subtype') == 'init':
            invocation['session_id'] = obj.get('session_id', '')
            invocation['model'] = obj.get('model', '')
            invocation['claude_code_version'] = obj.get('claude_code_version', '')

        if obj.get('type') == 'result':
            invocation['result'] = obj

    # Parse the harness-level error block that follows the JSON result.
    # This block looks like:
    #   Error: Task execution failed.
    #     Exit code: 0
    #     HEAD before: <sha>
    #     HEAD after: <sha>
    #   ...optional details (permission denials, last messages, etc.)...
    post_lines = invocation.get('post_result_lines', [])
    harness_error = {}
    harness_error_lines = []
    for line in post_lines:
        stripped = line.strip()
        if not stripped:
            continue
        harness_error_lines.append(stripped)
        if stripped.startswith('Error: Task execution failed'):
            harness_error['failed'] = True
        elif stripped.startswith('Error: Task failed after'):
            harness_error['final_failure'] = stripped
        m = re.match(r'Exit code:\s*(\S+)', stripped)
        if m:
            harness_error['exit_code'] = m.group(1)
        m = re.match(r'HEAD before:\s*(\S+)', stripped)
        if m:
            harness_error['head_before'] = m.group(1)
        m = re.match(r'HEAD after:\s*(\S+)', stripped)
        if m:
            harness_error['head_after'] = m.group(1)
        m = re.match(r'Claude error:\s*(.*)', stripped)
        if m:
            harness_error['claude_error'] = m.group(1)
        m = re.match(r'Permission denied for (\d+) action', stripped)
        if m:
            harness_error['permission_denied_count'] = int(m.group(1))
    harness_error['lines'] = harness_error_lines
    invocation['harness_error'] = harness_error


def extract_assistant_messages(json_lines):
    """Extract readable assistant text messages from JSON streaming lines."""
    messages = []
    for obj in json_lines:
        if obj.get('type') == 'assistant':
            msg = obj.get('message', {})
            content_list = msg.get('content', [])
            for content in content_list:
                if content.get('type') == 'text':
                    text = content.get('text', '').strip()
                    if text:
                        messages.append(text)
    return messages


def extract_tool_calls(json_lines):
    """Extract tool call summaries from JSON streaming lines."""
    calls = []
    for obj in json_lines:
        if obj.get('type') == 'assistant':
            msg = obj.get('message', {})
            content_list = msg.get('content', [])
            for content in content_list:
                if content.get('type') == 'tool_use':
                    tool_name = content.get('name', '?')
                    tool_input = content.get('input', {})
                    summary = tool_name
                    if tool_name == 'Bash':
                        summary = f"Bash: `{tool_input.get('command', '?')}`"
                    elif tool_name == 'Read':
                        summary = f"Read: `{tool_input.get('file_path', '?')}`"
                    elif tool_name == 'Edit':
                        summary = f"Edit: `{tool_input.get('file_path', '?')}`"
                    elif tool_name == 'Write':
                        summary = f"Write: `{tool_input.get('file_path', '?')}`"
                    elif tool_name == 'Glob':
                        summary = f"Glob: `{tool_input.get('pattern', '?')}`"
                    elif tool_name == 'Grep':
                        summary = f"Grep: `{tool_input.get('pattern', '?')}`"
                    elif tool_name == 'Skill':
                        summary = f"Skill: `{tool_input.get('skill', '?')}`"
                    elif tool_name == 'ToolSearch':
                        summary = f"ToolSearch: `{tool_input.get('query', '?')}`"
                    calls.append(summary)
    return calls


def extract_permission_denials(result_obj):
    """Extract permission denial details from a result object."""
    denials = result_obj.get('permission_denials', [])
    summaries = []
    for d in denials:
        tool = d.get('tool_name', '?')
        inp = d.get('tool_input', {})
        if tool == 'Bash':
            summaries.append(f"Bash: `{inp.get('command', '?')}`")
        else:
            summaries.append(f"{tool}: {json.dumps(inp)[:100]}")
    return summaries


def format_duration(ms):
    """Format milliseconds as a human-readable duration."""
    if ms is None:
        return "unknown"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    hours = minutes / 60
    return f"{hours:.1f}h"


def format_cost(cost):
    """Format cost in USD."""
    if cost is None:
        return "unknown"
    return f"${cost:.4f}"


def determine_outcome(invocation):
    """Determine the outcome of an invocation.

    The harness-level verdict is authoritative. Claude may report <SUCCESS>
    in its JSON result, but the harness checks whether HEAD actually advanced
    (i.e., a new commit was made). If HEAD didn't change, the harness reports
    'Error: Task execution failed.' and that is the real outcome.
    """
    harness = invocation.get('harness_error', {})
    result = invocation.get('result')
    result_text = result.get('result', '') if result else ''

    # Extract what Claude claimed
    claude_claimed_success = '<SUCCESS>' in result_text
    claude_claimed_failure = '<FAILURE>' in result_text
    claude_failure_reason = ''
    if claude_claimed_failure:
        m = re.search(r'<FAILURE>(.*?)</FAILURE>', result_text, re.DOTALL)
        claude_failure_reason = m.group(1).strip() if m else result_text

    # Harness says it failed
    if harness.get('failed'):
        head_before = harness.get('head_before', '')
        head_after = harness.get('head_after', '')
        claude_error = harness.get('claude_error', '')

        # Build a reason from multiple sources
        reasons = []
        if head_before and head_after and head_before == head_after:
            reasons.append(f"HEAD unchanged ({head_before[:7]}) — no commit was made")
        if claude_error:
            reasons.append(f"Harness error: {claude_error}")
        if claude_claimed_failure:
            reasons.append(f"Claude reported: {claude_failure_reason}")
        elif claude_claimed_success:
            reasons.append(f"Claude claimed SUCCESS but harness rejected it (HEAD unchanged)")

        return 'failure', '; '.join(reasons) if reasons else 'Task execution failed (harness)'

    # No harness error — check Claude's own report
    if not result:
        return 'unknown', 'No result event found in JSON stream'
    if claude_claimed_failure:
        return 'failure', claude_failure_reason
    if result.get('is_error', False):
        return 'error', result_text

    return 'success', result_text


def generate_markdown(logfile, invocations):
    """Generate a markdown summary of all Claude invocations."""
    basename = os.path.basename(logfile)
    lines = []
    lines.append(f"# Claude Activity Report")
    lines.append(f"")
    lines.append(f"**Log file:** `{basename}`  ")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    lines.append(f"**Total invocations:** {len(invocations)}")
    lines.append(f"")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| # | Attempt | Outcome | Duration | Cost | Turns |")
    lines.append("|---|---------|---------|----------|------|-------|")
    for inv in invocations:
        result = inv.get('result', {}) or {}
        outcome, _ = determine_outcome(inv)
        icon = {'success': 'PASS', 'failure': 'FAIL', 'error': 'ERROR', 'unknown': '?'}[outcome]
        duration = format_duration(result.get('duration_ms'))
        cost = format_cost(result.get('total_cost_usd'))
        turns = result.get('num_turns', '?')
        lines.append(f"| {inv['attempt']} | {inv['attempt']}/{inv['max_attempts']} | {icon} | {duration} | {cost} | {turns} |")
    lines.append("")

    # Detailed sections
    for inv in invocations:
        result = inv.get('result', {}) or {}
        outcome, outcome_detail = determine_outcome(inv)
        icon = {'success': 'PASS', 'failure': 'FAIL', 'error': 'ERROR', 'unknown': '?'}[outcome]

        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## Invocation {inv['attempt']}/{inv['max_attempts']} — {icon}")
        lines.append(f"")

        # Metadata
        lines.append(f"**Model:** {inv.get('model', 'unknown')}  ")
        lines.append(f"**Session:** `{inv.get('session_id', 'unknown')}`  ")
        lines.append(f"**Duration:** {format_duration(result.get('duration_ms'))}  ")
        lines.append(f"**API Duration:** {format_duration(result.get('duration_api_ms'))}  ")
        lines.append(f"**Cost:** {format_cost(result.get('total_cost_usd'))}  ")
        lines.append(f"**Turns:** {result.get('num_turns', '?')}  ")
        lines.append(f"**Stop reason:** {result.get('stop_reason', '?')}  ")
        lines.append(f"")

        # Token usage
        usage = result.get('usage', {})
        if usage:
            lines.append("### Token Usage")
            lines.append("")
            lines.append(f"| Metric | Count |")
            lines.append(f"|--------|-------|")
            lines.append(f"| Input tokens | {usage.get('input_tokens', '?')} |")
            lines.append(f"| Output tokens | {usage.get('output_tokens', '?')} |")
            lines.append(f"| Cache read | {usage.get('cache_read_input_tokens', '?')} |")
            lines.append(f"| Cache creation | {usage.get('cache_creation_input_tokens', '?')} |")
            lines.append(f"")

        # Outcome
        lines.append("### Outcome")
        lines.append("")
        if outcome == 'success':
            lines.append(f"**Result:** {outcome_detail}")
        elif outcome == 'failure':
            lines.append(f"**Failure reason:**")
            lines.append(f"")
            # Split multiple reasons on semicolons for readability
            for reason_part in outcome_detail.split('; '):
                lines.append(f"> {reason_part}")
        elif outcome == 'error':
            lines.append(f"**Error:** {outcome_detail}")
        else:
            lines.append(f"**Status:** {outcome_detail}")
        lines.append("")

        # Harness error details
        harness = inv.get('harness_error', {})
        harness_lines = harness.get('lines', [])
        if harness_lines:
            lines.append("### Harness Verdict")
            lines.append("")
            lines.append("```")
            for hl in harness_lines:
                lines.append(hl)
            lines.append("```")
            lines.append("")

        # Permission denials
        denials = extract_permission_denials(result)
        if denials:
            lines.append("### Permission Denials")
            lines.append("")
            for d in denials:
                lines.append(f"- {d}")
            lines.append("")

        # Tool calls
        tool_calls = extract_tool_calls(inv['json_lines'])
        if tool_calls:
            lines.append("### Tool Calls")
            lines.append("")
            for tc in tool_calls:
                lines.append(f"- {tc}")
            lines.append("")

        # Assistant messages (conversation flow)
        messages = extract_assistant_messages(inv['json_lines'])
        if messages:
            lines.append("### Conversation")
            lines.append("")
            for msg in messages:
                # Truncate very long messages
                if len(msg) > 500:
                    msg = msg[:500] + "..."
                lines.append(f"> {msg}")
                lines.append(f">")
            lines.append("")

    return '\n'.join(lines)


def main():
    logfile = sys.argv[1]
    output_file = sys.argv[2]

    invocations = parse_log(logfile)

    if not invocations:
        print(f"No Claude invocations found in {logfile}")
        with open(output_file, 'w') as f:
            f.write(f"# Claude Activity Report\n\n**Log file:** `{os.path.basename(logfile)}`\n\nNo Claude invocations found.\n")
        print(f"Output written to {output_file}")
        return

    markdown = generate_markdown(logfile, invocations)

    with open(output_file, 'w') as f:
        f.write(markdown)

    print(f"Analyzed {len(invocations)} Claude invocation(s)")
    for inv in invocations:
        outcome, detail = determine_outcome(inv)
        result = inv.get('result', {}) or {}
        print(f"  Attempt {inv['attempt']}/{inv['max_attempts']}: {outcome.upper()} "
              f"({format_duration(result.get('duration_ms'))}, {format_cost(result.get('total_cost_usd'))})")
    print(f"Output written to {output_file}")


if __name__ == '__main__':
    main()
PYTHON_SCRIPT
