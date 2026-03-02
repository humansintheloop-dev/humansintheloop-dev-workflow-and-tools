#!/usr/bin/env node
/**
 * PreToolUse hook that blocks certain Bash command patterns:
 * - `git -C <directory>` — use cd + git instead
 * - `cd <dir> && git ...` — run git from the project root
 * - `git commit -m "$(cat <<'EOF'...` — use simple `git commit -m "..."`
 * - `python -m pytest` — use `uv run python -m pytest` instead
 * - bare `pytest` — use `uv run python -m pytest` instead
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

const GIT_DASH_C_MESSAGE =
  'IMPORTANT: Use simple commands that you have permission to execute. ' +
  'Avoid complex commands that may fail due to permission issues. ' +
  'Do not use `git -C directory` - cd to the top-level directory and run git commands from there';

/**
 * Checks whether a Bash command uses `cd <dir> && git ...`.
 * @param {string} command - The shell command to inspect
 * @returns {boolean} True if the command contains `cd <dir> && git`
 */
function isCdAndGit(command) {
  return /\bcd\s+\S+\s*&&\s*git\b/.test(command);
}

const CD_AND_GIT_MESSAGE =
  'Do not use `cd <directory> && git ...` - run git commands from the project root directory';

/**
 * Checks whether a Bash command uses a HEREDOC for git commit messages.
 * @param {string} command - The shell command to inspect
 * @returns {boolean} True if the command contains `git commit -m "$(cat <<`
 */
function isGitCommitHeredoc(command) {
  return /\bgit\s+commit\b.*\$\(cat\s*<</.test(command);
}

const GIT_COMMIT_HEREDOC_MESSAGE =
  'Do not use `git commit -m "$(cat <<EOF ..."` - use `git commit -F- <<EOF` instead';

function isPythonMPytest(command) {
  return /^python3?\s+-m\s+pytest\b/.test(command);
}

const PYTHON_M_PYTEST_MESSAGE =
  'Do not use `python -m pytest` - use `uv run python -m pytest` instead';

/**
 * Checks whether a Bash command runs pytest without `uv run`.
 * @param {string} command - The shell command to inspect
 * @returns {boolean} True if the command runs bare pytest (not via uv run)
 */
function isBarePytest(command) {
  return /^pytest\b/.test(command);
}

const BARE_PYTEST_MESSAGE =
  'Do not run `pytest` directly - use `uv run python -m pytest` instead';

const BASH_RULES = [
  { test: isGitDashC, message: GIT_DASH_C_MESSAGE },
  { test: isCdAndGit, message: CD_AND_GIT_MESSAGE },
  { test: isGitCommitHeredoc, message: GIT_COMMIT_HEREDOC_MESSAGE },
  { test: isPythonMPytest, message: PYTHON_M_PYTEST_MESSAGE },
  { test: isBarePytest, message: BARE_PYTEST_MESSAGE },
];

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
  const violated = BASH_RULES.find(rule => rule.test(command));

  if (violated) {
    return { blocked: true, message: violated.message };
  }

  return { blocked: false };
}

// Export for testing
module.exports = {
  isGitDashC,
  isCdAndGit,
  isGitCommitHeredoc,
  isPythonMPytest,
  isBarePytest,
  handlePreToolUse,
  GIT_DASH_C_MESSAGE,
  CD_AND_GIT_MESSAGE,
  GIT_COMMIT_HEREDOC_MESSAGE,
  PYTHON_M_PYTEST_MESSAGE,
  BARE_PYTEST_MESSAGE
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
