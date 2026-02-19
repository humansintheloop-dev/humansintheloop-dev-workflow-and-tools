#!/usr/bin/env node
/**
 * PreToolUse hook that blocks `git -C <directory>` commands.
 *
 * Responds with a message telling Claude to cd to the directory
 * and run git commands from there instead.
 *
 * Exit codes:
 *   0 - allow the command
 *   2 - block the command (stderr is fed back to Claude)
 */

/**
 * Checks whether a Bash command invokes git with the -C flag.
 * @param {string} command - The shell command to inspect
 * @returns {boolean} True if the command contains `git -C`
 */
function isGitDashC(command) {
  return /\bgit\s+-C\b/.test(command);
}

const BLOCK_MESSAGE =
  'IMPORTANT: Use simple commands that you have permission to execute. ' +
  'Avoid complex commands that may fail due to permission issues. ' +
  'Do not use `git -C directory` - cd to the top-level directory and run git commands from there';

/**
 * Handles a PreToolUse hook event for the Bash tool.
 * @param {Object} hookInput - The hook input data
 * @returns {{ blocked: boolean, message?: string }}
 */
function handlePreToolUse(hookInput) {
  const { tool_name, tool_input } = hookInput;

  if (tool_name !== 'Bash') {
    return { blocked: false };
  }

  const command = tool_input?.command || '';

  if (isGitDashC(command)) {
    return { blocked: true, message: BLOCK_MESSAGE };
  }

  return { blocked: false };
}

// Export for testing
module.exports = {
  isGitDashC,
  handlePreToolUse,
  BLOCK_MESSAGE
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
      const result = handlePreToolUse(data);

      if (result.blocked) {
        process.stderr.write(result.message);
        process.exit(2);
      }

      process.exit(0);
    } catch (error) {
      // Don't block on parse errors - allow the command
      process.exit(0);
    }
  });
}
