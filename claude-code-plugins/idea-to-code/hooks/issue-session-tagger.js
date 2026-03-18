#!/usr/bin/env node
/**
 * Issue Session Tagger for Claude Code
 *
 * Automatically fills in the claude_session_id field in issue reports
 * when Claude writes to .hitl/issues/active/*.md
 *
 * This script is invoked by Claude Code hooks:
 * - PostToolUse: Detects Write operations to issue files
 */

const fs = require('fs');

/**
 * Checks if a file path is an issue report in .hitl/issues/active/
 * @param {string} filePath - The file path to check
 * @returns {boolean} True if this is an active issue file
 */
function isActiveIssueFile(filePath) {
  if (!filePath) return false;
  return filePath.includes('.hitl/issues/active/') && filePath.endsWith('.md');
}

/**
 * Fills in the claude_session_id field in an issue file
 * @param {string} filePath - Path to the issue file
 * @param {string} sessionId - The Claude session ID to insert
 * @returns {boolean} True if the file was updated
 */
function tagIssueWithSessionId(filePath, sessionId) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');

    // Check if it has the placeholder
    if (!content.includes('claude_session_id: unknown')) {
      return false;
    }

    // Replace the placeholder with the actual session ID
    const updated = content.replace(
      'claude_session_id: unknown',
      `claude_session_id: ${sessionId}`
    );

    fs.writeFileSync(filePath, updated, 'utf8');
    return true;
  } catch (error) {
    // Silently fail - this is a best-effort enhancement
    return false;
  }
}

/**
 * Handles the PostToolUse hook event
 * @param {Object} hookInput - The hook input data
 */
function handlePostToolUse(hookInput) {
  const { session_id, tool_name, tool_input } = hookInput;

  // Only process Write operations
  if (tool_name !== 'Write') {
    return;
  }

  // Check if this is an issue file
  const filePath = tool_input?.file_path;
  if (!isActiveIssueFile(filePath)) {
    return;
  }

  // Tag the issue with the session ID
  if (session_id) {
    tagIssueWithSessionId(filePath, session_id);
  }
}

/**
 * Main hook handler
 * @param {Object} hookInput - The hook input data
 */
function handleHookEvent(hookInput) {
  const { hook_event_name } = hookInput;

  if (hook_event_name === 'PostToolUse') {
    handlePostToolUse(hookInput);
  }
}

// Export for testing
module.exports = {
  isActiveIssueFile,
  tagIssueWithSessionId,
  handlePostToolUse,
  handleHookEvent
};

// Main entry point when run as a script
if (require.main === module) {
  let input = '';
  process.stdin.setEncoding('utf8');

  process.stdin.on('data', (chunk) => {
    input += chunk;
  });

  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      handleHookEvent(data);
    } catch (error) {
      // Silent fail - don't disrupt Claude's workflow
    }
  });
}
