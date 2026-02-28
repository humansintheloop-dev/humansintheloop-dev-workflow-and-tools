#!/usr/bin/env node
/**
 * Session Recorder for Claude Code
 *
 * Records all Claude Code interactions (prompts, responses, tool calls)
 * to markdown files in .hitl/sessions/
 *
 * This script is invoked by Claude Code hooks:
 * - UserPromptSubmit: Captures user prompts
 * - PostToolUse: Captures tool calls
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Current session state
let currentSessionPath = null;

/**
 * Finds the project root by traversing up from the given directory
 * looking for .claude/ or .git/ directories.
 * @param {string} startDir - The directory to start searching from
 * @returns {string} The project root, or startDir if not found
 */
function findProjectRoot(startDir) {
  if (!startDir) {
    return startDir;
  }

  let dir = path.resolve(startDir);
  const root = path.parse(dir).root;

  while (dir !== root) {
    // Check for .claude/ directory (preferred marker for this plugin)
    const claudeDir = path.join(dir, '.claude');
    if (fs.existsSync(claudeDir) && fs.statSync(claudeDir).isDirectory()) {
      return dir;
    }

    // Check for .git/ directory (common project root marker)
    const gitDir = path.join(dir, '.git');
    if (fs.existsSync(gitDir)) {
      return dir;
    }

    // Move up one directory
    const parentDir = path.dirname(dir);
    if (parentDir === dir) {
      break; // Reached filesystem root
    }
    dir = parentDir;
  }

  // If no markers found, return the original directory
  return startDir;
}

/**
 * Finds an existing session file for the given session ID
 * @param {string} sessionsDir - The sessions directory path
 * @param {string} sessionId - The Claude session ID
 * @returns {string|null} The session file path, or null if not found
 */
function findSessionFile(sessionsDir, sessionId) {
  try {
    const files = fs.readdirSync(sessionsDir);
    const pattern = new RegExp(`^session-.*-${sessionId}\\.md$`);
    const match = files.find(f => pattern.test(f));
    if (match) {
      return path.join(sessionsDir, match);
    }
  } catch (error) {
    // Directory doesn't exist or can't be read
  }
  return null;
}

/**
 * Writes debug log to .hitl/sessions/debug.log
 * @param {string} workspaceDir - The workspace directory path (from hook input cwd)
 * @param {string} message - The message to log
 * @param {Object} data - Optional data to log as JSON
 */
function debugLog(workspaceDir, message, data = null) {
  try {
    // Use workspaceDir if provided, otherwise fall back to process.cwd()
    const baseDir = workspaceDir || process.cwd();
    const debugFile = path.join(baseDir, '.hitl', 'sessions', 'debug.log');
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
 * Creates the .hitl/sessions/ directory if it doesn't exist
 * @param {string} workspaceDir - The workspace directory path
 * @returns {string|null} The sessions directory path, or null on error
 */
function createSessionsDirectory(workspaceDir) {
  const sessionsDir = path.join(workspaceDir, '.hitl', 'sessions');
  try {
    fs.mkdirSync(sessionsDir, { recursive: true });
    return sessionsDir;
  } catch (error) {
    console.error(`[session-recorder] Failed to create sessions directory: ${error.message}`);
    return null;
  }
}

/**
 * Generates a session filename with timestamp and session ID: session-YYYY-MM-DD-HHMMSS-{sessionId}.md
 * @param {string} sessionId - The Claude session ID
 * @returns {string} The generated filename
 */
function generateSessionFilename(sessionId) {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `session-${year}-${month}-${day}-${hours}${minutes}${seconds}-${sessionId}.md`;
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
 * Formats a timestamp for entry headers: HH:MM:SS
 * @returns {string} The formatted timestamp
 */
function formatEntryTimestamp() {
  const now = new Date();
  const hours = String(now.getHours()).padStart(2, '0');
  const minutes = String(now.getMinutes()).padStart(2, '0');
  const seconds = String(now.getSeconds()).padStart(2, '0');

  return `${hours}:${minutes}:${seconds}`;
}

/**
 * Creates a new session file with the header
 * @param {string} sessionsDir - The sessions directory path
 * @param {string} sessionId - The Claude session ID
 * @returns {string} The full path to the created session file
 */
function createSessionFile(sessionsDir, sessionId) {
  const filename = generateSessionFilename(sessionId);
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

function hasActiveSession(sessionId) {
  return currentSessionPath && fs.existsSync(currentSessionPath) && currentSessionPath.includes(sessionId);
}

/**
 * Gets the current session file path, creating a new session if needed
 * @param {string} workspaceDir - The workspace directory path
 * @param {string} sessionId - The Claude session ID
 * @returns {string|null} The session file path, or null on error
 */
function getOrCreateSession(workspaceDir, sessionId) {
  if (!sessionId) {
    console.error('[session-recorder] Missing sessionId');
    return null;
  }

  // Return existing session if we have one in memory for this session
  if (hasActiveSession(sessionId)) {
    return currentSessionPath;
  }

  // Create sessions directory
  const sessionsDir = createSessionsDirectory(workspaceDir);
  if (!sessionsDir) {
    return null;
  }

  // Try to find existing session file for this session ID
  const existingSession = findSessionFile(sessionsDir, sessionId);
  if (existingSession) {
    currentSessionPath = existingSession;
    return currentSessionPath;
  }

  // Create new session file
  currentSessionPath = createSessionFile(sessionsDir, sessionId);

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
  const timestamp = formatEntryTimestamp();
  const lines = prompt.split('\n');
  const quotedLines = lines.map(line => `> ${line}`).join('\n');
  return `**User:** [${timestamp}]\n${quotedLines}\n\n`;
}

/**
 * Formats a Claude response as markdown with blockquote
 * @param {string} response - Claude's response text
 * @returns {string} Formatted markdown string
 */
function formatClaudeResponse(response) {
  const timestamp = formatEntryTimestamp();
  const lines = response.split('\n');
  const quotedLines = lines.map(line => `> ${line}`).join('\n');
  return `**Claude:** [${timestamp}]\n${quotedLines}\n\n`;
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

function isJsonlFormat(transcriptPath, content) {
  return transcriptPath.endsWith('.jsonl') || content.trim().startsWith('{');
}

function findLastAssistantInJsonl(content) {
  const lines = content.trim().split('\n').filter(line => line.trim());
  for (let i = lines.length - 1; i >= 0; i--) {
    try {
      const entry = JSON.parse(lines[i]);
      if (entry.type === 'assistant' && entry.message) {
        return extractTextFromContent(entry.message.content);
      }
    } catch (lineError) {
      continue;
    }
  }
  return null;
}

function findLastAssistantInArray(content) {
  const transcript = JSON.parse(content);
  if (!Array.isArray(transcript)) {
    console.error('[session-recorder] Transcript is not an array');
    return null;
  }
  for (let i = transcript.length - 1; i >= 0; i--) {
    if (transcript[i].role === 'assistant') {
      return extractTextFromContent(transcript[i].content);
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
    if (isJsonlFormat(transcriptPath, content)) {
      return findLastAssistantInJsonl(content);
    }
    return findLastAssistantInArray(content);
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
const TOOL_FORMAT_RULES = {
  Read:  { key: 'file_path', fmt: v => `Read ${v}` },
  Write: { key: 'file_path', fmt: v => `Write ${v}` },
  Edit:  { key: 'file_path', fmt: v => `Edit ${v}` },
  Bash:  { key: 'command',   fmt: v => `Bash: ${v}` },
  Grep:  { key: 'pattern',   fmt: v => `Grep '${v}'` },
  Glob:  { key: 'pattern',   fmt: v => `Glob '${v}'` },
  Task:  { key: 'description', fmt: v => `Task: ${v}` },
};

function formatToolCall(toolName, toolInput) {
  if (!toolInput) {
    return toolName;
  }
  const rule = TOOL_FORMAT_RULES[toolName];
  if (rule && toolInput[rule.key]) {
    return rule.fmt(toolInput[rule.key]);
  }
  return toolName;
}

/**
 * Captures git commit info (SHA and remote URL) from the current directory
 * @param {string} workspaceDir - The workspace directory path
 * @returns {Object|null} Object with sha and remote, or null on error
 */
function captureCommitInfo(workspaceDir) {
  try {
    const sha = execSync('git rev-parse HEAD', {
      cwd: workspaceDir,
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe']
    }).trim();

    let remote = null;
    try {
      remote = execSync('git remote get-url origin', {
        cwd: workspaceDir,
        encoding: 'utf8',
        stdio: ['pipe', 'pipe', 'pipe']
      }).trim();
    } catch (remoteError) {
      // No remote configured, that's okay
    }

    return { sha, remote };
  } catch (error) {
    return null;
  }
}

function needsSessionCreation(projectRoot, sessionId) {
  return !currentSessionPath && projectRoot && sessionId;
}

function isGitCommitCommand(toolName, toolInput) {
  return toolName === 'Bash' && toolInput?.command && /git\s+commit/.test(toolInput.command);
}

/**
 * Handles the PostToolUse hook event
 * @param {Object} hookInput - The hook input data
 * @param {string} hookInput.session_id - The Claude session ID
 * @param {string} hookInput.tool_name - The name of the tool
 * @param {Object} hookInput.tool_input - The tool input parameters
 * @param {Object} hookInput.tool_response - The tool response (includes success field)
 * @param {string} hookInput.cwd - The current working directory
 */
function handlePostToolUse(hookInput) {
  const { session_id, tool_name, tool_input, tool_response, cwd } = hookInput;

  // Find the project root (in case cwd has changed during the session)
  const projectRoot = findProjectRoot(cwd);

  debugLog(projectRoot, 'handlePostToolUse called', hookInput);

  if (!tool_name) {
    debugLog(projectRoot, 'Missing tool_name in PostToolUse hook input');
    console.error('[session-recorder] Missing tool_name in PostToolUse hook input');
    return;
  }

  // Ensure we have a session
  if (needsSessionCreation(projectRoot, session_id)) {
    getOrCreateSession(projectRoot, session_id);
  }

  if (!currentSessionPath) {
    debugLog(projectRoot, 'No active session for PostToolUse event');
    console.error('[session-recorder] No active session for PostToolUse event');
    return;
  }

  // Format the tool call
  const toolSummary = formatToolCall(tool_name, tool_input);
  const timestamp = formatEntryTimestamp();
  debugLog(projectRoot, `Tool summary: ${toolSummary}`);

  // Append tool call to session (each tool call gets its own "Tools Used" section for simplicity)
  const formatted = `**Tools Used:** [${timestamp}]\n- ${toolSummary}\n\n`;
  appendToSession(formatted);
  debugLog(projectRoot, 'Tool call appended successfully');

  // Track git commits
  if (isGitCommitCommand(tool_name, tool_input)) {
    recordGitCommit(projectRoot, tool_response);
  }
}

function recordGitCommit(projectRoot, tool_response) {
  const bashSuccess = tool_response && !tool_response.interrupted && !tool_response.stderr;
  const commitTimestamp = formatEntryTimestamp();
  if (!bashSuccess) {
    appendToSession(`**Git Commit Failed:** [${commitTimestamp}]\n\n`);
    debugLog(projectRoot, 'Git commit failure recorded');
    return;
  }
  const gitInfo = captureCommitInfo(projectRoot);
  if (!gitInfo) {
    return;
  }
  let commitFormatted = `**Git Commit:** [${commitTimestamp}]\n- SHA: ${gitInfo.sha}\n`;
  if (gitInfo.remote) {
    commitFormatted += `- Repository: ${gitInfo.remote}\n`;
  }
  commitFormatted += '\n';
  appendToSession(commitFormatted);
  debugLog(projectRoot, 'Git commit info appended successfully');
}

/**
 * Handles the UserPromptSubmit hook event
 * @param {Object} hookInput - The hook input data
 * @param {string} hookInput.session_id - The Claude session ID
 * @param {string} hookInput.cwd - The current working directory
 * @param {string} hookInput.hook_event_name - The hook event name
 * @param {string} hookInput.prompt - The user's prompt text
 */
function handleUserPromptSubmit(hookInput) {
  const { session_id, cwd, prompt } = hookInput;

  if (!cwd) {
    console.error('[session-recorder] Missing cwd in hook input');
    return;
  }

  if (!session_id) {
    console.error('[session-recorder] Missing session_id in hook input');
    return;
  }

  if (prompt === undefined || prompt === null) {
    console.error('[session-recorder] Missing prompt in hook input');
    return;
  }

  // Find the project root (in case cwd has changed during the session)
  const projectRoot = findProjectRoot(cwd);

  // Get or create session file
  const sessionPath = getOrCreateSession(projectRoot, session_id);
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
 * @param {string} hookInput.session_id - The Claude session ID
 * @param {string} hookInput.transcript_path - Path to the transcript file
 * @param {string} hookInput.cwd - The current working directory
 */
function handleStop(hookInput) {
  const { session_id, transcript_path, cwd } = hookInput;

  // Find the project root (in case cwd has changed during the session)
  const projectRoot = findProjectRoot(cwd);

  debugLog(projectRoot, 'handleStop called', hookInput);

  if (!transcript_path) {
    debugLog(projectRoot, 'Missing transcript_path in Stop hook input');
    console.error('[session-recorder] Missing transcript_path in Stop hook input');
    return;
  }

  debugLog(projectRoot, `transcript_path: ${transcript_path}, cwd: ${cwd}, projectRoot: ${projectRoot}, currentSessionPath: ${currentSessionPath}`);

  // If no session exists, we can't record the response
  if (!currentSessionPath) {
    debugLog(projectRoot, 'No currentSessionPath, trying to create session');
    // Try to create session if we have projectRoot and session_id
    if (projectRoot && session_id) {
      getOrCreateSession(projectRoot, session_id);
    }
    if (!currentSessionPath) {
      debugLog(projectRoot, 'Failed to create session');
      console.error('[session-recorder] No active session for Stop event');
      return;
    }
  }

  // Parse transcript to get Claude's response
  debugLog(projectRoot, `Parsing transcript from: ${transcript_path}`);
  const response = parseTranscript(transcript_path);
  debugLog(projectRoot, `Parsed response: ${response ? response.slice(0, 200) + '...' : 'null'}`);

  if (!response) {
    debugLog(projectRoot, 'Could not extract response from transcript');
    console.error('[session-recorder] Could not extract response from transcript');
    return;
  }

  // Format and append the response
  const formatted = formatClaudeResponse(response);
  debugLog(projectRoot, `Appending to session: ${currentSessionPath}`);
  appendToSession(formatted);
  debugLog(projectRoot, 'Response appended successfully');
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
  findProjectRoot,
  createSessionsDirectory,
  generateSessionFilename,
  createSessionFile,
  findSessionFile,
  getOrCreateSession,
  resetSession,
  appendToSession,
  getCurrentSessionPath,
  formatUserPrompt,
  formatClaudeResponse,
  formatToolCall,
  formatEntryTimestamp,
  captureCommitInfo,
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
