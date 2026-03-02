/**
 * Tests for session-recorder.js
 * Run with: node hooks/session-recorder.test.js
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

// Test utilities
const TEST_DIR = path.join(__dirname, '..', '.test-sessions');
const SESSIONS_DIR = path.join(TEST_DIR, '.hitl', 'sessions');

// Suppress stderr during error tests
const originalStderr = console.error;
function suppressErrors() {
  console.error = () => {};
}
function restoreErrors() {
  console.error = originalStderr;
}

function runGracefully(fn) {
  suppressErrors();
  try {
    fn();
  } finally {
    restoreErrors();
  }
}

function writeTranscriptAndParse(messages) {
  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, JSON.stringify(messages));
  return sessionRecorder.parseTranscript(transcriptPath);
}

function startSession(sessionId, prompt) {
  sessionRecorder.resetSession();
  sessionRecorder.handleUserPromptSubmit({
    session_id: sessionId,
    cwd: TEST_DIR,
    hook_event_name: 'UserPromptSubmit',
    prompt
  });
}

function readSessionContent() {
  return fs.readFileSync(sessionRecorder.getCurrentSessionPath(), 'utf8');
}

function hookInput(eventName, sessionId, extra) {
  return { session_id: sessionId, cwd: TEST_DIR, hook_event_name: eventName, ...extra };
}

function assertHandlesGracefully(handler, eventName, sessionId, extra) {
  sessionRecorder.resetSession();
  if (handler !== sessionRecorder.handleUserPromptSubmit) {
    sessionRecorder.getOrCreateSession(TEST_DIR, sessionId);
  }
  runGracefully(() => handler(hookInput(eventName, sessionId, extra)));
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

test('createSessionsDirectory creates .hitl/sessions/ if missing', () => {
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
  const sessionId = 'test-session-abc123';
  const filename = sessionRecorder.generateSessionFilename(sessionId);
  const pattern = /^session-\d{4}-\d{2}-\d{2}-\d{6}-test-session-abc123\.md$/;
  assert.match(filename, pattern, `Filename "${filename}" should match pattern session-YYYY-MM-DD-HHMMSS-{sessionId}.md`);
});

test('generateSessionFilename uses current timestamp', () => {
  const sessionId = 'test-session-xyz789';
  const before = new Date();
  const filename = sessionRecorder.generateSessionFilename(sessionId);
  const after = new Date();

  // Extract date parts from filename
  const match = filename.match(/session-(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})(\d{2})-test-session-xyz789\.md/);
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

// --- Tests for findSessionFile ---

test('findSessionFile finds existing session file by session ID', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  const sessionId = 'find-test-session';

  // Create a session file manually
  const filename = `session-2025-01-01-120000-${sessionId}.md`;
  const filePath = path.join(SESSIONS_DIR, filename);
  fs.writeFileSync(filePath, '# Test session\n');

  const result = sessionRecorder.findSessionFile(SESSIONS_DIR, sessionId);
  assert.strictEqual(result, filePath, 'Should find the session file');
});

test('findSessionFile returns null when no matching session exists', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });

  const result = sessionRecorder.findSessionFile(SESSIONS_DIR, 'nonexistent-session');
  assert.strictEqual(result, null, 'Should return null when no match');
});

test('findSessionFile returns null when directory does not exist', () => {
  const result = sessionRecorder.findSessionFile('/nonexistent/path', 'any-session');
  assert.strictEqual(result, null, 'Should return null for nonexistent directory');
});

// --- Tests for session file creation ---

test('createSessionFile creates file with correct header', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  const sessionId = 'test-session-header';
  const filePath = sessionRecorder.createSessionFile(SESSIONS_DIR, sessionId);

  assert.ok(fs.existsSync(filePath), 'Session file should exist');

  const content = fs.readFileSync(filePath, 'utf8');
  const headerPattern = /^# Session: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\n\n$/;
  assert.match(content, headerPattern, `Header "${content}" should match expected format`);
});

test('createSessionFile returns full path to created file', () => {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  const sessionId = 'test-session-path';
  const filePath = sessionRecorder.createSessionFile(SESSIONS_DIR, sessionId);

  assert.ok(filePath.startsWith(SESSIONS_DIR), 'Path should be in sessions directory');
  assert.ok(filePath.endsWith('.md'), 'Path should end with .md');
  assert.ok(filePath.includes(sessionId), 'Path should include session ID');
});

// --- Tests for session tracking ---

test('getOrCreateSession creates new session on first call', () => {
  sessionRecorder.resetSession(); // Ensure clean state
  const sessionId = 'test-session-create';
  const filePath = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId);

  assert.ok(filePath, 'Should return a file path');
  assert.ok(fs.existsSync(filePath), 'Session file should exist');
  assert.ok(filePath.includes(sessionId), 'Path should include session ID');
});

test('getOrCreateSession reuses existing session on subsequent calls', () => {
  sessionRecorder.resetSession();
  const sessionId = 'test-session-reuse';
  const filePath1 = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId);
  const filePath2 = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId);

  assert.strictEqual(filePath1, filePath2, 'Should return same file path');
});

test('getOrCreateSession creates different sessions for different session IDs', () => {
  sessionRecorder.resetSession();
  const filePath1 = sessionRecorder.getOrCreateSession(TEST_DIR, 'session-id-1');
  sessionRecorder.resetSession();
  const filePath2 = sessionRecorder.getOrCreateSession(TEST_DIR, 'session-id-2');

  assert.notStrictEqual(filePath1, filePath2, 'Should create different sessions for different IDs');
  assert.ok(filePath1.includes('session-id-1'), 'First path should include first session ID');
  assert.ok(filePath2.includes('session-id-2'), 'Second path should include second session ID');
});

test('resetSession clears the current session', async () => {
  const sessionId1 = 'test-session-reset-1';
  const sessionId2 = 'test-session-reset-2';

  sessionRecorder.resetSession();
  const filePath1 = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId1);

  sessionRecorder.resetSession();
  const filePath2 = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId2);

  assert.notStrictEqual(filePath1, filePath2, 'Should create new session after reset with different ID');
});

// --- Tests for user prompt formatting ---

test('formatUserPrompt formats single line prompt correctly', () => {
  const prompt = 'Help me add a new feature';
  const result = sessionRecorder.formatUserPrompt(prompt);
  const pattern = /^\*\*User:\*\* \[\d{2}:\d{2}:\d{2}\]\n> Help me add a new feature\n\n$/;
  assert.match(result, pattern, `Result "${result}" should match pattern with timestamp`);
});

test('formatUserPrompt formats multi-line prompt correctly', () => {
  const prompt = 'First line\nSecond line\nThird line';
  const result = sessionRecorder.formatUserPrompt(prompt);
  const pattern = /^\*\*User:\*\* \[\d{2}:\d{2}:\d{2}\]\n> First line\n> Second line\n> Third line\n\n$/;
  assert.match(result, pattern, `Result "${result}" should match pattern with timestamp`);
});

test('formatUserPrompt handles empty prompt', () => {
  const result = sessionRecorder.formatUserPrompt('');
  const pattern = /^\*\*User:\*\* \[\d{2}:\d{2}:\d{2}\]\n> \n\n$/;
  assert.match(result, pattern, `Result "${result}" should match pattern with timestamp`);
});

test('formatUserPrompt handles prompt with special markdown characters', () => {
  const prompt = 'Use `code` and **bold** text';
  const result = sessionRecorder.formatUserPrompt(prompt);
  assert.ok(result.includes('> Use `code` and **bold** text'), 'Should contain prompt text');
  assert.ok(result.includes('**User:**'), 'Should contain User label');
});

// --- Tests for appendToSession ---

test('appendToSession appends content to session file', () => {
  sessionRecorder.resetSession();
  const sessionId = 'test-session-append';
  const filePath = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId);

  const content = '**User:**\n> Test prompt\n\n';
  const result = sessionRecorder.appendToSession(content);

  assert.strictEqual(result, true, 'Should return true on success');

  const fileContent = fs.readFileSync(filePath, 'utf8');
  assert.ok(fileContent.includes('Test prompt'), 'File should contain appended content');
});

test('appendToSession preserves existing content', () => {
  sessionRecorder.resetSession();
  const sessionId = 'test-session-preserve';
  const filePath = sessionRecorder.getOrCreateSession(TEST_DIR, sessionId);

  sessionRecorder.appendToSession('First append\n');
  sessionRecorder.appendToSession('Second append\n');

  const fileContent = fs.readFileSync(filePath, 'utf8');
  assert.ok(fileContent.includes('First append'), 'File should contain first append');
  assert.ok(fileContent.includes('Second append'), 'File should contain second append');
});

test('appendToSession returns false when no active session', () => {
  sessionRecorder.resetSession();
  runGracefully(() => {
    sessionRecorder.resetSession();
    const result = sessionRecorder.appendToSession('test');
    assert.strictEqual(result, false, 'Should return false when no session');
  });
});

// --- Tests for handleUserPromptSubmit ---

test('handleUserPromptSubmit records user prompt to session file', () => {
  startSession('test-session-123', 'Help me write a function');

  assert.ok(sessionRecorder.getCurrentSessionPath(), 'Session should be created');

  const content = readSessionContent();
  assert.ok(content.includes('**User:**'), 'Should contain User label');
  assert.ok(content.includes('Help me write a function'), 'Should contain prompt text');
});

test('handleUserPromptSubmit handles missing prompt gracefully', () => {
  assertHandlesGracefully(sessionRecorder.handleUserPromptSubmit, 'UserPromptSubmit', 'test-session-123', {});
});

test('handleUserPromptSubmit handles missing cwd gracefully', () => {
  sessionRecorder.resetSession();
  runGracefully(() => {
    sessionRecorder.handleUserPromptSubmit({
      session_id: 'test-session-123',
      hook_event_name: 'UserPromptSubmit',
      prompt: 'Test prompt'
    });
  });
});

// --- Tests for Claude response formatting ---

test('formatClaudeResponse formats single line response correctly', () => {
  const response = "I'd be happy to help!";
  const result = sessionRecorder.formatClaudeResponse(response);
  const pattern = /^\*\*Claude:\*\* \[\d{2}:\d{2}:\d{2}\]\n> I'd be happy to help!\n\n$/;
  assert.match(result, pattern, `Result "${result}" should match pattern with timestamp`);
});

test('formatClaudeResponse formats multi-line response correctly', () => {
  const response = 'First line\nSecond line\nThird line';
  const result = sessionRecorder.formatClaudeResponse(response);
  const pattern = /^\*\*Claude:\*\* \[\d{2}:\d{2}:\d{2}\]\n> First line\n> Second line\n> Third line\n\n$/;
  assert.match(result, pattern, `Result "${result}" should match pattern with timestamp`);
});

test('formatClaudeResponse handles empty response', () => {
  const result = sessionRecorder.formatClaudeResponse('');
  const pattern = /^\*\*Claude:\*\* \[\d{2}:\d{2}:\d{2}\]\n> \n\n$/;
  assert.match(result, pattern, `Result "${result}" should match pattern with timestamp`);
});

// --- Tests for transcript parsing ---

test('parseTranscript extracts assistant message from JSON transcript', () => {
  const result = writeTranscriptAndParse([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'Hi there! How can I help?' }
  ]);
  assert.strictEqual(result, 'Hi there! How can I help?');
});

test('parseTranscript returns last assistant message', () => {
  const result = writeTranscriptAndParse([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'First response' },
    { role: 'user', content: 'Thanks' },
    { role: 'assistant', content: 'Second response' }
  ]);
  assert.strictEqual(result, 'Second response');
});

test('parseTranscript handles nested content array', () => {
  const result = writeTranscriptAndParse([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: [{ type: 'text', text: 'Response with nested content' }] }
  ]);
  assert.strictEqual(result, 'Response with nested content');
});

test('parseTranscript returns null for missing file', () => {
  runGracefully(() => {
    const result = sessionRecorder.parseTranscript('/nonexistent/transcript.json');
    assert.strictEqual(result, null);
  });
});

test('parseTranscript returns null for invalid JSON', () => {
  const transcriptPath = path.join(TEST_DIR, 'invalid.json');
  fs.writeFileSync(transcriptPath, 'not valid json');

  runGracefully(() => {
    const result = sessionRecorder.parseTranscript(transcriptPath);
    assert.strictEqual(result, null);
  });
});

test('parseTranscript returns null when no assistant message', () => {
  const result = writeTranscriptAndParse([{ role: 'user', content: 'Hello' }]);
  assert.strictEqual(result, null);
});

// --- Tests for handleStop ---

test('handleStop records Claude response to session file', () => {
  startSession('test-session-123', 'Hello');

  // Create a transcript file
  const transcriptPath = path.join(TEST_DIR, 'transcript.json');
  fs.writeFileSync(transcriptPath, JSON.stringify([
    { role: 'user', content: 'Hello' },
    { role: 'assistant', content: 'Hi! How can I help you today?' }
  ]));

  sessionRecorder.handleStop(hookInput('Stop', 'test-session-123', {
    transcript_path: transcriptPath
  }));

  const content = readSessionContent();
  assert.ok(content.includes('**Claude:**'), 'Should contain Claude label');
  assert.ok(content.includes('Hi! How can I help you today?'), 'Should contain response text');
});

test('handleStop handles missing transcript_path gracefully', () => {
  assertHandlesGracefully(sessionRecorder.handleStop, 'Stop', 'test-session-stop', {});
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
  startSession('test-session-123', 'Read a file');

  sessionRecorder.handlePostToolUse(hookInput('PostToolUse', 'test-session-123', {
    tool_name: 'Read',
    tool_input: { file_path: '/src/test.js' }
  }));

  const content = readSessionContent();
  assert.ok(content.includes('**Tools Used:**'), 'Should contain Tools Used label');
  assert.ok(content.includes('Read /src/test.js'), 'Should contain tool call');
});

test('handlePostToolUse handles missing tool_name gracefully', () => {
  assertHandlesGracefully(sessionRecorder.handlePostToolUse, 'PostToolUse', 'test-session-tool', {});
});

test('handlePostToolUse aggregates multiple tool calls', () => {
  startSession('test-session-123', 'Do some work');

  sessionRecorder.handlePostToolUse(hookInput('PostToolUse', 'test-session-123', {
    tool_name: 'Read',
    tool_input: { file_path: '/file1.js' }
  }));

  sessionRecorder.handlePostToolUse(hookInput('PostToolUse', 'test-session-123', {
    tool_name: 'Edit',
    tool_input: { file_path: '/file2.js' }
  }));

  const content = readSessionContent();
  assert.ok(content.includes('Read /file1.js'), 'Should contain first tool call');
  assert.ok(content.includes('Edit /file2.js'), 'Should contain second tool call');
});

// --- Tests for error handling ---

test('createSessionsDirectory handles permission errors gracefully', () => {
  runGracefully(() => {
    const result = sessionRecorder.createSessionsDirectory('/nonexistent/path/that/does/not/exist');
    assert.strictEqual(result, null, 'Should return null on error');
  });
});

test('getOrCreateSession returns null on directory creation failure', () => {
  sessionRecorder.resetSession();
  runGracefully(() => {
    const result = sessionRecorder.getOrCreateSession('/nonexistent/path/that/does/not/exist', 'test-session-fail');
    assert.strictEqual(result, null, 'Should return null on error');
  });
});

test('getOrCreateSession returns null when sessionId is missing', () => {
  sessionRecorder.resetSession();
  runGracefully(() => {
    const result = sessionRecorder.getOrCreateSession(TEST_DIR, null);
    assert.strictEqual(result, null, 'Should return null when sessionId is missing');
  });
});

// --- Tests for git commit tracking ---

test('captureCommitInfo returns SHA and remote in a git repo', () => {
  // This test runs in the project root which is a git repo
  const projectRoot = path.join(__dirname, '..');
  const result = sessionRecorder.captureCommitInfo(projectRoot);

  assert.ok(result, 'Should return commit info');
  assert.ok(result.sha, 'Should have sha property');
  assert.ok(result.sha.match(/^[a-f0-9]{40}$/), 'SHA should be a 40-char hex string');
  // remote may or may not exist depending on repo setup
});

test('captureCommitInfo returns null for non-git directory', () => {
  // Use /tmp which is outside any git repo
  const tempDir = fs.mkdtempSync(path.join('/tmp', 'session-recorder-test-'));
  try {
    const result = sessionRecorder.captureCommitInfo(tempDir);
    assert.strictEqual(result, null, 'Should return null for non-git directory');
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

test('handlePostToolUse records git commit SHA on successful commit', () => {
  startSession('test-git-commit-success', 'Commit the changes');

  const projectRoot = path.join(__dirname, '..');
  sessionRecorder.handlePostToolUse({
    session_id: 'test-git-commit-success',
    cwd: projectRoot,
    hook_event_name: 'PostToolUse',
    tool_name: 'Bash',
    tool_input: { command: 'git commit -m "Test commit"' },
    tool_response: { stdout: '[master abc123] Test commit', stderr: '', interrupted: false }
  });

  const content = readSessionContent();

  assert.ok(content.match(/\*\*Git Commit:\*\* \[\d{2}:\d{2}:\d{2}\]/), 'Should contain Git Commit label with timestamp');
  assert.ok(content.includes('- SHA:'), 'Should contain SHA');
  assert.ok(content.match(/[a-f0-9]{40}/), 'Should contain a valid SHA');
});

test('handlePostToolUse records git commit failure', () => {
  startSession('test-git-commit-failure', 'Commit the changes');

  sessionRecorder.handlePostToolUse({
    session_id: 'test-git-commit-failure',
    cwd: TEST_DIR,
    hook_event_name: 'PostToolUse',
    tool_name: 'Bash',
    tool_input: { command: 'git commit -m "Test commit"' },
    tool_response: { stdout: '', stderr: 'nothing to commit, working tree clean', interrupted: false }
  });

  const content = readSessionContent();

  assert.ok(content.match(/\*\*Git Commit Failed:\*\* \[\d{2}:\d{2}:\d{2}\]/), 'Should contain Git Commit Failed label with timestamp');
});

test('handlePostToolUse does not record git info for non-commit commands', () => {
  startSession('test-non-commit', 'Run git status');

  sessionRecorder.handlePostToolUse(hookInput('PostToolUse', 'test-non-commit', {
    tool_name: 'Bash',
    tool_input: { command: 'git status' },
    tool_response: { stdout: 'On branch master', stderr: '', interrupted: false }
  }));

  const content = readSessionContent();

  assert.ok(!content.includes('**Git Commit:**'), 'Should not contain Git Commit label');
  assert.ok(!content.includes('**Git Commit Failed:**'), 'Should not contain Git Commit Failed');
});

// --- Tests for handlePermissionRequest ---

test('handlePermissionRequest records permission request to session file', () => {
  startSession('test-session-perm', 'Delete old files');

  sessionRecorder.handlePermissionRequest(hookInput('PermissionRequest', 'test-session-perm', {
    tool_name: 'Bash',
    tool_input: { command: 'rm -rf node_modules' }
  }));

  const content = readSessionContent();
  assert.ok(content.includes('**Permission Requested:**'), 'Should contain Permission Requested label');
  assert.ok(content.includes('Bash: rm -rf node_modules'), 'Should contain tool call summary');
});

test('handleHookEvent routes PermissionRequest to handlePermissionRequest', () => {
  startSession('test-session-route', 'Do something');

  sessionRecorder.handleHookEvent(hookInput('PermissionRequest', 'test-session-route', {
    tool_name: 'Write',
    tool_input: { file_path: '/src/secret.js' }
  }));

  const content = readSessionContent();
  assert.ok(content.includes('**Permission Requested:**'), 'Should contain Permission Requested label');
  assert.ok(content.includes('Write /src/secret.js'), 'Should contain tool call summary');
});

test('handlePermissionRequest handles missing tool_name gracefully', () => {
  assertHandlesGracefully(sessionRecorder.handlePermissionRequest, 'PermissionRequest', 'test-session-perm-no-tool', {});
  const content = readSessionContent();
  assert.ok(!content.includes('**Permission Requested:**'), 'Should not record when tool_name is missing');
});

// Run all tests
runTests();
