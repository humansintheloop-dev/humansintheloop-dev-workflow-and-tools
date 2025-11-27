#!/usr/bin/env node
/**
 * Session Recorder for Claude Code
 *
 * Records all Claude Code interactions (prompts, responses, tool calls)
 * to markdown files in .claude/sessions/
 *
 * This script is invoked by Claude Code hooks:
 * - UserPromptSubmit: Captures user prompts
 * - PostToolUse: Captures tool calls
 */

const fs = require('fs');
const path = require('path');

// Current session state
let currentSessionPath = null;

/**
 * Creates the .claude/sessions/ directory if it doesn't exist
 * @param {string} workspaceDir - The workspace directory path
 * @returns {string|null} The sessions directory path, or null on error
 */
function createSessionsDirectory(workspaceDir) {
  const sessionsDir = path.join(workspaceDir, '.claude', 'sessions');
  try {
    fs.mkdirSync(sessionsDir, { recursive: true });
    return sessionsDir;
  } catch (error) {
    console.error(`[session-recorder] Failed to create sessions directory: ${error.message}`);
    return null;
  }
}

/**
 * Generates a session filename with timestamp format: session-YYYY-MM-DD-HHMMSS.md
 * @returns {string} The generated filename
 */
function generateSessionFilename() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `session-${year}-${month}-${day}-${hours}${minutes}${seconds}.md`;
}

/**
 * Formats a timestamp for the session header: YYYY-MM-DD HH:MM:SS
 * @returns {string} The formatted timestamp
 */
function formatHeaderTimestamp() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * Creates a new session file with the header
 * @param {string} sessionsDir - The sessions directory path
 * @returns {string} The full path to the created session file
 */
function createSessionFile(sessionsDir) {
  const filename = generateSessionFilename();
  const filePath = path.join(sessionsDir, filename);
  const header = `# Session: ${formatHeaderTimestamp()}\n\n`;

  try {
    fs.writeFileSync(filePath, header, { encoding: 'utf8', flag: 'wx' });
    return filePath;
  } catch (error) {
    console.error(`[session-recorder] Failed to create session file: ${error.message}`);
    return null;
  }
}

/**
 * Gets the current session file path, creating a new session if needed
 * @param {string} workspaceDir - The workspace directory path
 * @returns {string|null} The session file path, or null on error
 */
function getOrCreateSession(workspaceDir) {
  // Return existing session if we have one
  if (currentSessionPath && fs.existsSync(currentSessionPath)) {
    return currentSessionPath;
  }

  // Create sessions directory
  const sessionsDir = createSessionsDirectory(workspaceDir);
  if (!sessionsDir) {
    return null;
  }

  // Create new session file
  currentSessionPath = createSessionFile(sessionsDir);
  return currentSessionPath;
}

/**
 * Resets the current session (for testing)
 */
function resetSession() {
  currentSessionPath = null;
}

/**
 * Appends content to the current session file
 * @param {string} content - The content to append
 * @returns {boolean} True if successful, false otherwise
 */
function appendToSession(content) {
  if (!currentSessionPath) {
    console.error('[session-recorder] No active session');
    return false;
  }

  try {
    fs.appendFileSync(currentSessionPath, content, { encoding: 'utf8' });
    return true;
  } catch (error) {
    console.error(`[session-recorder] Failed to append to session: ${error.message}`);
    return false;
  }
}

// Export functions for testing
module.exports = {
  createSessionsDirectory,
  generateSessionFilename,
  createSessionFile,
  getOrCreateSession,
  resetSession,
  appendToSession
};

// Main entry point when run as a script
if (require.main === module) {
  // Read JSON input from stdin
  let input = '';
  process.stdin.setEncoding('utf8');

  process.stdin.on('data', (chunk) => {
    input += chunk;
  });

  process.stdin.on('end', () => {
    try {
      const data = JSON.parse(input);
      // Hook handling will be implemented in Steel Thread 2
      console.error('[session-recorder] Received hook data:', JSON.stringify(data, null, 2));
    } catch (error) {
      console.error(`[session-recorder] Failed to parse input: ${error.message}`);
    }
  });
}
