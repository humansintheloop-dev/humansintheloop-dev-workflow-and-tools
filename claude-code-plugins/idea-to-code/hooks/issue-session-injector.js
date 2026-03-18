#!/usr/bin/env node

/**
 * PreToolUse hook that appends --session-id to i2code issue create commands.
 *
 * When the hook input contains a Bash command with `i2code issue create`
 * and a `session_id` field, it appends `--session-id <id>` to the command.
 *
 * Returns modified tool_input JSON on stdout when the command is modified.
 * Exits 0 silently when no modification is needed.
 */

/**
 * Handles a PreToolUse hook event.
 * @param {Object} hookInput - The hook input data
 * @returns {Object|null} Modified tool_input or null if no change needed
 */
function handlePreToolUse(hookInput) {
  const { tool_name, tool_input, session_id } = hookInput;

  if (tool_name !== 'Bash') return null;

  const command = tool_input?.command;
  if (!command) return null;
  if (!session_id) return null;
  if (!command.includes('i2code issue create')) return null;
  if (command.includes('--session-id')) return null;

  return {
    tool_input: {
      command: `${command} --session-id ${session_id}`
    }
  };
}

// Export for testing
module.exports = { handlePreToolUse };

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

      if (result) {
        process.stdout.write(JSON.stringify(result.tool_input));
      }

      process.exit(0);
    } catch (error) {
      // Don't modify on parse errors - allow the command through
      process.exit(0);
    }
  });
}
