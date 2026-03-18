/**
 * Tests for issue-session-injector.js
 * Run with: node hooks/issue-session-injector.test.js
 */

const assert = require('assert');

const { handlePreToolUse } = require('./issue-session-injector.js');

// Test suite
const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

async function runTests() {
  let passed = 0;
  let failed = 0;

  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log(`✓ ${name}`);
      passed++;
    } catch (error) {
      console.log(`✗ ${name}`);
      console.log(`  Error: ${error.message}`);
      failed++;
    }
  }

  console.log(`\n${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

// --- Tests for session ID injection ---

test('injects session ID into matching i2code issue create command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'echo \'{"title":"bug"}\' | i2code issue create' },
    session_id: 'abc123'
  });
  assert.deepStrictEqual(result, {
    tool_input: { command: 'echo \'{"title":"bug"}\' | i2code issue create --session-id abc123' }
  });
});

test('no session_id passes through unchanged', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'echo \'{"title":"bug"}\' | i2code issue create' }
  });
  assert.strictEqual(result, null);
});

test('non-matching command passes through unchanged', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'git status' },
    session_id: 'abc123'
  });
  assert.strictEqual(result, null);
});

test('already has --session-id not appended twice', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'echo \'{"title":"bug"}\' | i2code issue create --session-id existing' },
    session_id: 'abc123'
  });
  assert.strictEqual(result, null);
});

test('non-Bash tool passes through unchanged', () => {
  const result = handlePreToolUse({
    tool_name: 'Read',
    tool_input: { file_path: '/some/file' },
    session_id: 'abc123'
  });
  assert.strictEqual(result, null);
});

test('handles missing tool_input gracefully', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    session_id: 'abc123'
  });
  assert.strictEqual(result, null);
});

test('handles missing command gracefully', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: {},
    session_id: 'abc123'
  });
  assert.strictEqual(result, null);
});

// Run all tests
runTests();
