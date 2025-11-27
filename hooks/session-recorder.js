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
 * Gets the path to the session state file for a given workspace
 * @param {string} workspaceDir - The workspace directory
 * @returns {string} Path to the state file
 */
function getStateFilePath(workspaceDir) {
  return path.join(workspaceDir, '.claude', 'sessions', '.current-session');
}

/**
 * Loads the current session path from the state file
 * @param {string} workspaceDir - The workspace directory
 * @returns {string|null} The session path, or null if not found
 */
function loadSessionState(workspaceDir) {
  try {
    const stateFile = getStateFilePath(workspaceDir);
    if (fs.existsSync(stateFile)) {
      const sessionPath = fs.readFileSync(stateFile, 'utf8').trim();
      if (sessionPath && fs.existsSync(sessionPath)) {
        return sessionPath;
      }
    }
  } catch (error) {
    // Ignore errors reading state file
  }
  return null;
}

/**
 * Saves the current session path to the state file
 * @param {string} workspaceDir - The workspace directory
 * @param {string} sessionPath - The session file path to save
 */
function saveSessionState(workspaceDir, sessionPath) {
  try {
    const stateFile = getStateFilePath(workspaceDir);
    fs.writeFileSync(stateFile, sessionPath, 'utf8');
  } catch (error) {
    // Ignore errors writing state file
  }
}

/**
 * Writes debug log to .claude/sessions/debug.log
 * @param {string} message - The message to log
 * @param {Object} data - Optional data to log as JSON
 */
function debugLog(message, data = null) {
  try {
    const debugFile = path.join(process.cwd(), '.claude', 'sessions', 'debug.log');
    const timestamp = new Date().toISOString();
    let logEntry = `[${timestamp}] ${message}`;
    if (data) {
      logEntry += `\n${JSON.stringify(data, null, 2)}`;
    }
    logEntry += '\n\n';
    fs.appendFileSync(debugFile, logEntry);
  } catch (error) {
    // Silently ignore debug logging errors
  }
}

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
  // Return existing session if we have one in memory
  if (currentSessionPath && fs.existsSync(currentSessionPath)) {
    return currentSessionPath;
  }

  // Try to load from state file (for cross-process persistence)
  const savedSession = loadSessionState(workspaceDir);
  if (savedSession) {
    currentSessionPath = savedSession;
    return currentSessionPath;
  }

  // Create sessions directory
  const sessionsDir = createSessionsDirectory(workspaceDir);
  if (!sessionsDir) {
    return null;
  }

  // Create new session file
  currentSessionPath = createSessionFile(sessionsDir);

  // Save to state file for other hook processes
  if (currentSessionPath) {
    saveSessionState(workspaceDir, currentSessionPath);
  }

  return currentSessionPath;
}

/**
 * Resets the current session (for testing)
 * @param {string} workspaceDir - Optional workspace directory to clear state file
 */
function resetSession(workspaceDir = null) {
  currentSessionPath = null;
  // Also clear state file if workspace provided
  if (workspaceDir) {
    try {
      const stateFile = getStateFilePath(workspaceDir);
      if (fs.existsSync(stateFile)) {
        fs.unlinkSync(stateFile);
      }
    } catch (error) {
      // Ignore errors
    }
  }
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

/**
 * Gets the current session file path (for testing)
 * @returns {string|null} The current session path
 */
function getCurrentSessionPath() {
  return currentSessionPath;
}

/**
 * Formats a user prompt as markdown with blockquote
 * @param {string} prompt - The user's prompt text
 * @returns {string} Formatted markdown string
 */
function formatUserPrompt(prompt) {
  const lines = prompt.split('\n');
  const quotedLines = lines.map(line => `> ${line}`).join('\n');
  return `**User:**\n${quotedLines}\n\n`;
}

/**
 * Formats a Claude response as markdown with blockquote
 * @param {string} response - Claude's response text
 * @returns {string} Formatted markdown string
 */
function formatClaudeResponse(response) {
  const lines = response.split('\n');
  const quotedLines = lines.map(line => `> ${line}`).join('\n');
  return `**Claude:**\n${quotedLines}\n\n`;
}

/**
 * Extracts text content from a message content field
 * Content can be a string or an array of content blocks
 * @param {string|Array} content - The message content
 * @returns {string|null} The extracted text, or null if not found
 */
function extractTextFromContent(content) {
  if (typeof content === 'string') {
    return content;
  }

  if (Array.isArray(content)) {
    // Find text blocks and concatenate them
    const textBlocks = content
      .filter(block => block.type === 'text' && block.text)
      .map(block => block.text);

    if (textBlocks.length > 0) {
      return textBlocks.join('\n');
    }
  }

  return null;
}

/**
 * Parses a transcript file to extract the last assistant message
 * Supports both JSON array format and JSONL (JSON Lines) format
 * @param {string} transcriptPath - Path to the transcript file
 * @returns {string|null} The last assistant response text, or null on error
 */
function parseTranscript(transcriptPath) {
  try {
    const content = fs.readFileSync(transcriptPath, 'utf8');

    // Try JSONL format first (one JSON object per line)
    if (transcriptPath.endsWith('.jsonl') || content.trim().startsWith('{')) {
      const lines = content.trim().split('\n').filter(line => line.trim());

      // Find the last assistant message (iterate backwards)
      for (let i = lines.length - 1; i >= 0; i--) {
        try {
          const entry = JSON.parse(lines[i]);

          // JSONL format: {type: "assistant", message: {role: "assistant", content: [...]}}
          if (entry.type === 'assistant' && entry.message) {
            return extractTextFromContent(entry.message.content);
          }
        } catch (lineError) {
          // Skip malformed lines
          continue;
        }
      }
      return null;
    }

    // Try JSON array format
    const transcript = JSON.parse(content);

    if (!Array.isArray(transcript)) {
      console.error('[session-recorder] Transcript is not an array');
      return null;
    }

    // Find the last assistant message
    for (let i = transcript.length - 1; i >= 0; i--) {
      const message = transcript[i];
      if (message.role === 'assistant') {
        return extractTextFromContent(message.content);
      }
    }

    return null;
  } catch (error) {
    console.error(`[session-recorder] Failed to parse transcript: ${error.message}`);
    return null;
  }
}

/**
 * Formats a tool call into a minimal summary string
 * @param {string} toolName - The name of the tool
 * @param {Object} toolInput - The tool input parameters
 * @returns {string} Formatted tool call summary
 */
function formatToolCall(toolName, toolInput) {
  if (!toolInput) {
    return toolName;
  }

  switch (toolName) {
    case 'Read':
      return toolInput.file_path ? `Read ${toolInput.file_path}` : 'Read';

    case 'Write':
      return toolInput.file_path ? `Write ${toolInput.file_path}` : 'Write';

    case 'Edit':
      return toolInput.file_path ? `Edit ${toolInput.file_path}` : 'Edit';

    case 'Bash':
      return toolInput.command ? `Bash: ${toolInput.command}` : 'Bash';

    case 'Grep':
      return toolInput.pattern ? `Grep '${toolInput.pattern}'` : 'Grep';

    case 'Glob':
      return toolInput.pattern ? `Glob '${toolInput.pattern}'` : 'Glob';

    case 'Task':
      return toolInput.description ? `Task: ${toolInput.description}` : 'Task';

    default:
      return toolName;
  }
}

/**
 * Handles the PostToolUse hook event
 * @param {Object} hookInput - The hook input data
 * @param {string} hookInput.tool_name - The name of the tool
 * @param {Object} hookInput.tool_input - The tool input parameters
 * @param {string} hookInput.cwd - The current working directory
 */
function handlePostToolUse(hookInput) {
  debugLog('handlePostToolUse called', hookInput);

  const { tool_name, tool_input, cwd } = hookInput;

  if (!tool_name) {
    debugLog('Missing tool_name in PostToolUse hook input');
    console.error('[session-recorder] Missing tool_name in PostToolUse hook input');
    return;
  }

  // Ensure we have a session
  if (!currentSessionPath && cwd) {
    getOrCreateSession(cwd);
  }

  if (!currentSessionPath) {
    debugLog('No active session for PostToolUse event');
    console.error('[session-recorder] No active session for PostToolUse event');
    return;
  }

  // Format the tool call
  const toolSummary = formatToolCall(tool_name, tool_input);
  debugLog(`Tool summary: ${toolSummary}`);

  // Append tool call to session (each tool call gets its own "Tools Used" section for simplicity)
  const formatted = `**Tools Used:**\n- ${toolSummary}\n\n`;
  appendToSession(formatted);
  debugLog('Tool call appended successfully');
}

/**
 * Handles the UserPromptSubmit hook event
 * @param {Object} hookInput - The hook input data
 * @param {string} hookInput.session_id - The session ID
 * @param {string} hookInput.cwd - The current working directory
 * @param {string} hookInput.hook_event_name - The hook event name
 * @param {string} hookInput.prompt - The user's prompt text
 */
function handleUserPromptSubmit(hookInput) {
  const { cwd, prompt } = hookInput;

  if (!cwd) {
    console.error('[session-recorder] Missing cwd in hook input');
    return;
  }

  if (prompt === undefined || prompt === null) {
    console.error('[session-recorder] Missing prompt in hook input');
    return;
  }

  // Get or create session file
  const sessionPath = getOrCreateSession(cwd);
  if (!sessionPath) {
    console.error('[session-recorder] Failed to get or create session');
    return;
  }

  // Format and append the prompt
  const formatted = formatUserPrompt(prompt);
  appendToSession(formatted);
}

/**
 * Handles the Stop hook event (when Claude finishes responding)
 * @param {Object} hookInput - The hook input data
 * @param {string} hookInput.transcript_path - Path to the transcript file
 * @param {string} hookInput.cwd - The current working directory
 */
function handleStop(hookInput) {
  debugLog('handleStop called', hookInput);

  const { transcript_path, cwd } = hookInput;

  if (!transcript_path) {
    debugLog('Missing transcript_path in Stop hook input');
    console.error('[session-recorder] Missing transcript_path in Stop hook input');
    return;
  }

  debugLog(`transcript_path: ${transcript_path}, cwd: ${cwd}, currentSessionPath: ${currentSessionPath}`);

  // If no session exists, we can't record the response
  if (!currentSessionPath) {
    debugLog('No currentSessionPath, trying to create session');
    // Try to create session if we have cwd
    if (cwd) {
      getOrCreateSession(cwd);
    }
    if (!currentSessionPath) {
      debugLog('Failed to create session');
      console.error('[session-recorder] No active session for Stop event');
      return;
    }
  }

  // Parse transcript to get Claude's response
  debugLog(`Parsing transcript from: ${transcript_path}`);
  const response = parseTranscript(transcript_path);
  debugLog(`Parsed response: ${response ? response.slice(0, 200) + '...' : 'null'}`);

  if (!response) {
    debugLog('Could not extract response from transcript');
    console.error('[session-recorder] Could not extract response from transcript');
    return;
  }

  // Format and append the response
  const formatted = formatClaudeResponse(response);
  debugLog(`Appending to session: ${currentSessionPath}`);
  appendToSession(formatted);
  debugLog('Response appended successfully');
}

/**
 * Main hook handler - routes to appropriate handler based on event type
 * @param {Object} hookInput - The hook input data
 */
function handleHookEvent(hookInput) {
  const { hook_event_name } = hookInput;

  switch (hook_event_name) {
    case 'UserPromptSubmit':
      handleUserPromptSubmit(hookInput);
      break;
    case 'PostToolUse':
      handlePostToolUse(hookInput);
      break;
    case 'Stop':
      handleStop(hookInput);
      break;
    default:
      console.error(`[session-recorder] Unknown hook event: ${hook_event_name}`);
  }
}

// Export functions for testing
module.exports = {
  createSessionsDirectory,
  generateSessionFilename,
  createSessionFile,
  getOrCreateSession,
  resetSession,
  appendToSession,
  getCurrentSessionPath,
  formatUserPrompt,
  formatClaudeResponse,
  formatToolCall,
  parseTranscript,
  handleUserPromptSubmit,
  handlePostToolUse,
  handleStop,
  handleHookEvent
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
      handleHookEvent(data);
    } catch (error) {
      console.error(`[session-recorder] Failed to parse input: ${error.message}`);
    }
  });
}
