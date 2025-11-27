/**
 * Tests for session-recorder.js
 * Run with: node hooks/session-recorder.test.js
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Test utilities
const TEST_DIR = path.join(__dirname, '..', '.test-sessions');
const SESSIONS_DIR = path.join(TEST_DIR, '.claude', 'sessions');

// Suppress stderr during error tests
const originalStderr = console.error;
function suppressErrors() {
  console.error = () => {};
}
function restoreErrors() {
  console.error = originalStderr;
}

function cleanup() {
  if (fs.existsSync(TEST_DIR)) {
    fs.rmSync(TEST_DIR, { recursive: true, force: true });
  }
}

function setup() {
  cleanup();
  fs.mkdirSync(TEST_DIR, { recursive: true });
}

// Import the module under test (will be created next)
const sessionRecorder = require('./session-recorder.js');

// Test suite
const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

async function runTests() {
  let passed = 0;
  let failed = 0;

  for (const { name, fn } of tests) {
    setup();
    try {
      await fn();
      console.log(`✓ ${name}`);
      passed++;
    } catch (error) {
      console.log(`✗ ${name}`);
      console.log(`  Error: ${error.message}`);
      failed++;
    } finally {
      cleanup();
    }
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

// --- Tests for directory creation ---

test('createSessionsDirectory creates .claude/sessions/ if missing', () => {
  const result = sessionRecorder.createSessionsDirectory(TEST_DIR);
  assert.strictEqual(fs.existsSync(SESSIONS_DIR), true, 'Sessions directory should exist');
  assert.strictEqual(result, SESSIONS_DIR, 'Should return the sessions directory path');
});

test('createSessionsDirectory succeeds if directory already exists', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  const result = sessionRecorder.createSessionsDirectory(TEST_DIR);
  assert.strictEqual(result, SESSIONS_DIR, 'Should return the sessions directory path');
});

// --- Tests for filename generation ---

test('generateSessionFilename returns correct format', () => {
  const filename = sessionRecorder.generateSessionFilename();
  const pattern = /^session-\d{4}-\d{2}-\d{2}-\d{6}\.md$/;
  assert.match(filename, pattern, `Filename "${filename}" should match pattern session-YYYY-MM-DD-HHMMSS.md`);
});

test('generateSessionFilename uses current timestamp', () => {
  const before = new Date();
  const filename = sessionRecorder.generateSessionFilename();
  const after = new Date();

  // Extract date parts from filename
  const match = filename.match(/session-(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})\.md/);
  assert.ok(match, 'Filename should match expected pattern');

  const fileDate = new Date(
    parseInt(match[1]), // year
    parseInt(match[2]) - 1, // month (0-indexed)
    parseInt(match[3]), // day
    parseInt(match[4]), // hour
    parseInt(match[5]), // minute
    parseInt(match[6])  // second
  );

  // File date should be between before and after (with 1 second tolerance)
  assert.ok(fileDate >= new Date(before.getTime() - 1000), 'Timestamp should not be in the past');
  assert.ok(fileDate <= new Date(after.getTime() + 1000), 'Timestamp should not be in the future');
});

// --- Tests for session file creation ---

test('createSessionFile creates file with correct header', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  const filePath = sessionRecorder.createSessionFile(SESSIONS_DIR);

  assert.ok(fs.existsSync(filePath), 'Session file should exist');

  const content = fs.readFileSync(filePath, 'utf8');
  const headerPattern = /^# Session: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\n\n$/;
  assert.match(content, headerPattern, `Header "${content}" should match expected format`);
});

test('createSessionFile returns full path to created file', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  const filePath = sessionRecorder.createSessionFile(SESSIONS_DIR);

  assert.ok(filePath.startsWith(SESSIONS_DIR), 'Path should be in sessions directory');
  assert.ok(filePath.endsWith('.md'), 'Path should end with .md');
});

// --- Tests for session tracking ---

test('getOrCreateSession creates new session on first call', () => {
  sessionRecorder.resetSession(); // Ensure clean state
  const filePath = sessionRecorder.getOrCreateSession(TEST_DIR);

  assert.ok(filePath, 'Should return a file path');
  assert.ok(fs.existsSync(filePath), 'Session file should exist');
});

test('getOrCreateSession reuses existing session on subsequent calls', () => {
  sessionRecorder.resetSession();
  const filePath1 = sessionRecorder.getOrCreateSession(TEST_DIR);
  const filePath2 = sessionRecorder.getOrCreateSession(TEST_DIR);

  assert.strictEqual(filePath1, filePath2, 'Should return same file path');
});

test('resetSession clears the current session', async () => {
  sessionRecorder.resetSession(TEST_DIR);
  const filePath1 = sessionRecorder.getOrCreateSession(TEST_DIR);

  // Wait 1 second to ensure different timestamp
  await new Promise(resolve => setTimeout(resolve, 1100));

  sessionRecorder.resetSession(TEST_DIR);
  const filePath2 = sessionRecorder.getOrCreateSession(TEST_DIR);

  assert.notStrictEqual(filePath1, filePath2, 'Should create new session after reset');
});

// --- Tests for user prompt formatting ---

test('formatUserPrompt formats single line prompt correctly', () => {
  const prompt = 'Help me add a new feature';
  const result = sessionRecorder.formatUserPrompt(prompt);
  assert.strictEqual(result, '**User:**\n> Help me add a new feature\n\n');
});

test('formatUserPrompt formats multi-line prompt correctly', () => {
  const prompt = 'First line\nSecond line\nThird line';
  const result = sessionRecorder.formatUserPrompt(prompt);
  assert.strictEqual(result, '**User:**\n> First line\n> Second line\n> Third line\n\n');
});

test('formatUserPrompt handles empty prompt', () => {
  const result = sessionRecorder.formatUserPrompt('');
  assert.strictEqual(result, '**User:**\n> \n\n');
});

test('formatUserPrompt handles prompt with special markdown characters', () => {
  const prompt = 'Use `code` and **bold** text';
  const result = sessionRecorder.formatUserPrompt(prompt);
  assert.strictEqual(result, '**User:**\n> Use `code` and **bold** text\n\n');
});

// --- Tests for appendToSession ---

test('appendToSession appends content to session file', () => {
  sessionRecorder.resetSession();
  const filePath = sessionRecorder.getOrCreateSession(TEST_DIR);

  const content = '**User:**\n> Test prompt\n\n';
  const result = sessionRecorder.appendToSession(content);

  assert.strictEqual(result, true, 'Should return true on success');

  const fileContent = fs.readFileSync(filePath, 'utf8');
  assert.ok(fileContent.includes('Test prompt'), 'File should contain appended content');
});

test('appendToSession preserves existing content', () => {
  sessionRecorder.resetSession();
  const filePath = sessionRecorder.getOrCreateSession(TEST_DIR);

  sessionRecorder.appendToSession('First append\n');
  sessionRecorder.appendToSession('Second append\n');

  const fileContent = fs.readFileSync(filePath, 'utf8');
  assert.ok(fileContent.includes('First append'), 'File should contain first append');
  assert.ok(fileContent.includes('Second append'), 'File should contain second append');
});

test('appendToSession returns false when no active session', () => {
  sessionRecorder.resetSession();
  suppressErrors();
  try {
    // Don't create a session, just try to append
    sessionRecorder.resetSession();
    const result = sessionRecorder.appendToSession('test');
    assert.strictEqual(result, false, 'Should return false when no session');
  } finally {
    restoreErrors();
  }
});

// --- Tests for handleUserPromptSubmit ---

test('handleUserPromptSubmit records user prompt to session file', () => {
  sessionRecorder.resetSession();

  const hookInput = {
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'Help me write a function'
  };

  sessionRecorder.handleUserPromptSubmit(hookInput);

  const sessionPath = sessionRecorder.getCurrentSessionPath();
  assert.ok(sessionPath, 'Session should be created');

  const content = fs.readFileSync(sessionPath, 'utf8');
  assert.ok(content.includes('**User:**'), 'Should contain User label');
  assert.ok(content.includes('Help me write a function'), 'Should contain prompt text');
});

test('handleUserPromptSubmit handles missing prompt gracefully', () => {
  sessionRecorder.resetSession();
  suppressErrors();
  try {
    const hookInput = {
      session_id: 'test-session-123',
      cwd: TEST_DIR,
      hook_event_name: 'UserPromptSubmit'
      // prompt is missing
    };

    // Should not throw
    sessionRecorder.handleUserPromptSubmit(hookInput);
  } finally {
    restoreErrors();
  }
});

test('handleUserPromptSubmit handles missing cwd gracefully', () => {
  sessionRecorder.resetSession();
  suppressErrors();
  try {
    const hookInput = {
      session_id: 'test-session-123',
      hook_event_name: 'UserPromptSubmit',
      prompt: 'Test prompt'
      // cwd is missing
    };

    // Should not throw
    sessionRecorder.handleUserPromptSubmit(hookInput);
  } finally {
    restoreErrors();
  }
});

// --- Tests for Claude response formatting ---

test('formatClaudeResponse formats single line response correctly', () => {
  const response = "I'd be happy to help!";
  const result = sessionRecorder.formatClaudeResponse(response);
  assert.strictEqual(result, "**Claude:**\n> I'd be happy to help!\n\n");
});

test('formatClaudeResponse formats multi-line response correctly', () => {
  const response = 'First line\nSecond line\nThird line';
  const result = sessionRecorder.formatClaudeResponse(response);
  assert.strictEqual(result, '**Claude:**\n> First line\n> Second line\n> Third line\n\n');
});

test('formatClaudeResponse handles empty response', () => {
  const result = sessionRecorder.formatClaudeResponse('');
  assert.strictEqual(result, '**Claude:**\n> \n\n');
});

// --- Tests for transcript parsing ---

test('parseTranscript extracts assistant message from JSON transcript', () => {
  const transcript = JSON.stringify([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'Hi there! How can I help?' }
  ]);

  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, transcript);

  const result = sessionRecorder.parseTranscript(transcriptPath);
  assert.strictEqual(result, 'Hi there! How can I help?');
});

test('parseTranscript returns last assistant message', () => {
  const transcript = JSON.stringify([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'First response' },
    { role: 'user', content: 'Thanks' },
    { role: 'assistant', content: 'Second response' }
  ]);

  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, transcript);

  const result = sessionRecorder.parseTranscript(transcriptPath);
  assert.strictEqual(result, 'Second response');
});

test('parseTranscript handles nested content array', () => {
  const transcript = JSON.stringify([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: [{ type: 'text', text: 'Response with nested content' }] }
  ]);

  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, transcript);

  const result = sessionRecorder.parseTranscript(transcriptPath);
  assert.strictEqual(result, 'Response with nested content');
});

test('parseTranscript returns null for missing file', () => {
  suppressErrors();
  try {
    const result = sessionRecorder.parseTranscript('/nonexistent/transcript.json');
    assert.strictEqual(result, null);
  } finally {
    restoreErrors();
  }
});

test('parseTranscript returns null for invalid JSON', () => {
  const transcriptPath = path.join(TEST_DIR, 'invalid.json');
  fs.writeFileSync(transcriptPath, 'not valid json');

  suppressErrors();
  try {
    const result = sessionRecorder.parseTranscript(transcriptPath);
    assert.strictEqual(result, null);
  } finally {
    restoreErrors();
  }
});

test('parseTranscript returns null when no assistant message', () => {
  const transcript = JSON.stringify([
    { role: 'user', content: 'Hello' }
  ]);

  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, transcript);

  const result = sessionRecorder.parseTranscript(transcriptPath);
  assert.strictEqual(result, null);
});

// --- Tests for handleStop ---

test('handleStop records Claude response to session file', () => {
  sessionRecorder.resetSession();

  // First create a session via user prompt
  const userHookInput = {
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'Hello'
  };
  sessionRecorder.handleUserPromptSubmit(userHookInput);

  // Create a transcript file
  const transcript = JSON.stringify([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'Hi! How can I help you today?' }
  ]);
  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, transcript);

  // Handle Stop event
  const stopHookInput = {
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'Stop',
    transcript_path: transcriptPath
  };
  sessionRecorder.handleStop(stopHookInput);

  const sessionPath = sessionRecorder.getCurrentSessionPath();
  const content = fs.readFileSync(sessionPath, 'utf8');
  assert.ok(content.includes('**Claude:**'), 'Should contain Claude label');
  assert.ok(content.includes('Hi! How can I help you today?'), 'Should contain response text');
});

test('handleStop handles missing transcript_path gracefully', () => {
  sessionRecorder.resetSession();
  sessionRecorder.getOrCreateSession(TEST_DIR);

  suppressErrors();
  try {
    const hookInput = {
      session_id: 'test-session-123',
      cwd: TEST_DIR,
      hook_event_name: 'Stop'
      // transcript_path is missing
    };

    // Should not throw
    sessionRecorder.handleStop(hookInput);
  } finally {
    restoreErrors();
  }
});

// --- Tests for tool call formatting ---

test('formatToolCall formats Read tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Read', { file_path: '/src/app.js' });
  assert.strictEqual(result, 'Read /src/app.js');
});

test('formatToolCall formats Write tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Write', { file_path: '/src/new-file.js' });
  assert.strictEqual(result, 'Write /src/new-file.js');
});

test('formatToolCall formats Edit tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Edit', { file_path: '/src/config.json' });
  assert.strictEqual(result, 'Edit /src/config.json');
});

test('formatToolCall formats Bash tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Bash', { command: 'npm test' });
  assert.strictEqual(result, 'Bash: npm test');
});

test('formatToolCall formats Grep tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Grep', { pattern: 'TODO' });
  assert.strictEqual(result, "Grep 'TODO'");
});

test('formatToolCall formats Glob tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Glob', { pattern: '**/*.ts' });
  assert.strictEqual(result, "Glob '**/*.ts'");
});

test('formatToolCall formats Task tool correctly', () => {
  const result = sessionRecorder.formatToolCall('Task', { description: 'Search for patterns' });
  assert.strictEqual(result, 'Task: Search for patterns');
});

test('formatToolCall handles unknown tools', () => {
  const result = sessionRecorder.formatToolCall('UnknownTool', { some: 'data' });
  assert.strictEqual(result, 'UnknownTool');
});

test('formatToolCall handles missing tool_input', () => {
  const result = sessionRecorder.formatToolCall('Read', null);
  assert.strictEqual(result, 'Read');
});

// --- Tests for handlePostToolUse ---

test('handlePostToolUse records tool call to session file', () => {
  sessionRecorder.resetSession(TEST_DIR);

  // First create a session via user prompt
  const userHookInput = {
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'Read a file'
  };
  sessionRecorder.handleUserPromptSubmit(userHookInput);

  // Handle PostToolUse event
  const toolHookInput = {
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'PostToolUse',
    tool_name: 'Read',
    tool_input: { file_path: '/src/test.js' }
  };
  sessionRecorder.handlePostToolUse(toolHookInput);

  const sessionPath = sessionRecorder.getCurrentSessionPath();
  const content = fs.readFileSync(sessionPath, 'utf8');
  assert.ok(content.includes('**Tools Used:**'), 'Should contain Tools Used label');
  assert.ok(content.includes('Read /src/test.js'), 'Should contain tool call');
});

test('handlePostToolUse handles missing tool_name gracefully', () => {
  sessionRecorder.resetSession(TEST_DIR);
  sessionRecorder.getOrCreateSession(TEST_DIR);

  suppressErrors();
  try {
    const hookInput = {
      session_id: 'test-session-123',
      cwd: TEST_DIR,
      hook_event_name: 'PostToolUse'
      // tool_name is missing
    };

    // Should not throw
    sessionRecorder.handlePostToolUse(hookInput);
  } finally {
    restoreErrors();
  }
});

test('handlePostToolUse aggregates multiple tool calls', () => {
  sessionRecorder.resetSession(TEST_DIR);

  // Create session
  const userHookInput = {
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'Do some work'
  };
  sessionRecorder.handleUserPromptSubmit(userHookInput);

  // Multiple tool calls
  sessionRecorder.handlePostToolUse({
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'PostToolUse',
    tool_name: 'Read',
    tool_input: { file_path: '/file1.js' }
  });

  sessionRecorder.handlePostToolUse({
    session_id: 'test-session-123',
    cwd: TEST_DIR,
    hook_event_name: 'PostToolUse',
    tool_name: 'Edit',
    tool_input: { file_path: '/file2.js' }
  });

  const sessionPath = sessionRecorder.getCurrentSessionPath();
  const content = fs.readFileSync(sessionPath, 'utf8');
  assert.ok(content.includes('Read /file1.js'), 'Should contain first tool call');
  assert.ok(content.includes('Edit /file2.js'), 'Should contain second tool call');
});

// --- Tests for error handling ---

test('createSessionsDirectory handles permission errors gracefully', () => {
  suppressErrors();
  try {
    // Try to create in a non-existent root path (should fail gracefully)
    const result = sessionRecorder.createSessionsDirectory('/nonexistent/path/that/does/not/exist');
    assert.strictEqual(result, null, 'Should return null on error');
  } finally {
    restoreErrors();
  }
});

test('getOrCreateSession returns null on directory creation failure', () => {
  suppressErrors();
  try {
    sessionRecorder.resetSession();
    const result = sessionRecorder.getOrCreateSession('/nonexistent/path/that/does/not/exist');
    assert.strictEqual(result, null, 'Should return null on error');
  } finally {
    restoreErrors();
  }
});

// Run all tests
runTests();
