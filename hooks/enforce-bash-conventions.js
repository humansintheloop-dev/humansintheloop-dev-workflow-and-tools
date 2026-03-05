#!/usr/bin/env node
const fs = require('fs');

/**
 * PreToolUse hook that blocks certain Bash command patterns:
 * - `git -C <directory>` — use cd + git instead
 * - `cd <dir> && git ...` — run git from the project root
 * - `git commit` with heredoc — use simple `git commit -m "..."`
 * - `python -m pytest` — use `uv run python -m pytest` instead
 * - bare `pytest` — use `uv run python -m pytest` instead
 * - `bash script.sh` / `sh script.sh` — run directly when script is executable with shebang
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
  'Do not use `cd <directory> && git ...` - cd to the top-level directory and run git commands from there';

/**
 * Checks whether a Bash command uses a heredoc for git commit messages.
 * @param {string} command - The shell command to inspect
 * @returns {boolean} True if the command contains `git commit` with `<<`
 */
function isGitCommitHeredoc(command) {
  return /\bgit\s+commit\b.*<</.test(command);
}

const GIT_COMMIT_HEREDOC_MESSAGE =
  'Do not use heredoc with git commit - use `git commit -m "message"` instead';

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

/**
 * Checks whether a Bash command unnecessarily prefixes an executable shebang
 * script with `bash` or `sh`. Blocks when the script file exists, is
 * executable, and has a shebang line. If filesystem access is denied
 * (e.g., sandbox EPERM), allows the command through.
 * @param {string} command - The shell command to inspect
 * @param {Object} [fsModule] - Optional fs module for dependency injection in tests
 * @returns {boolean} True if bash/sh prefix is redundant
 */
function isBashPrefixedScript(command, fsModule) {
  const match = command.match(/^(?:ba)?sh\s+(\S+)/);
  if (!match) return false;

  const _fs = fsModule || fs;
  const scriptPath = match[1];
  try {
    _fs.accessSync(scriptPath, _fs.constants.X_OK);
  } catch {
    return false;
  }

  try {
    const fd = _fs.openSync(scriptPath, 'r');
    const buf = Buffer.alloc(2);
    _fs.readSync(fd, buf, 0, 2, 0);
    _fs.closeSync(fd);
    return buf.toString() === '#!';
  } catch {
    return false;
  }
}

const BASH_PREFIXED_SCRIPT_MESSAGE =
  'Do not prefix scripts with `bash` or `sh` - run them directly: `./script.sh`';

const BASH_RULES = [
  { test: isGitDashC, message: GIT_DASH_C_MESSAGE },
  { test: isCdAndGit, message: CD_AND_GIT_MESSAGE },
  { test: isGitCommitHeredoc, message: GIT_COMMIT_HEREDOC_MESSAGE },
  { test: isPythonMPytest, message: PYTHON_M_PYTEST_MESSAGE },
  { test: isBarePytest, message: BARE_PYTEST_MESSAGE },
  { test: isBashPrefixedScript, message: BASH_PREFIXED_SCRIPT_MESSAGE },
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
  isBashPrefixedScript,
  handlePreToolUse,
  GIT_DASH_C_MESSAGE,
  CD_AND_GIT_MESSAGE,
  GIT_COMMIT_HEREDOC_MESSAGE,
  PYTHON_M_PYTEST_MESSAGE,
  BARE_PYTEST_MESSAGE,
  BASH_PREFIXED_SCRIPT_MESSAGE
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
