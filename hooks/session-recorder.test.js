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
  sessionRecorder.resetSession();
  const filePath1 = sessionRecorder.getOrCreateSession(TEST_DIR);

  // Wait 1 second to ensure different timestamp
  await new Promise(resolve => setTimeout(resolve, 1100));

  sessionRecorder.resetSession();
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
