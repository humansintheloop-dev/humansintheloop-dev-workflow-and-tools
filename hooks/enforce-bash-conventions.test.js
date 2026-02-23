/**
 * Tests for enforce-bash-conventions.js
 * Run with: node hooks/enforce-bash-conventions.test.js
 */

const assert = require('assert');

const { isGitDashC, isPythonMPytest, handlePreToolUse, GIT_DASH_C_MESSAGE, PYTHON_M_PYTEST_MESSAGE } = require('./enforce-bash-conventions.js');

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

// --- Tests for isGitDashC ---

test('detects git -C with a directory argument', () => {
  assert.strictEqual(isGitDashC('git -C /some/dir status'), true);
});

test('detects git -C at the start of the command', () => {
  assert.strictEqual(isGitDashC('git -C myrepo log'), true);
});

test('detects git -C with relative path', () => {
  assert.strictEqual(isGitDashC('git -C ../other-repo diff'), true);
});

test('allows plain git commands', () => {
  assert.strictEqual(isGitDashC('git status'), false);
});

test('allows git commit', () => {
  assert.strictEqual(isGitDashC('git commit -m "message"'), false);
});

test('allows git log with other flags', () => {
  assert.strictEqual(isGitDashC('git log --oneline -n 5'), false);
});

test('does not false-positive on -c (lowercase) config flag', () => {
  assert.strictEqual(isGitDashC('git -c user.name="Test" commit'), false);
});

test('does not false-positive on grep containing git -C in a string', () => {
  assert.strictEqual(isGitDashC('echo "do not use git -C"'), true);
});

test('allows non-git commands', () => {
  assert.strictEqual(isGitDashC('npm test'), false);
});

test('allows empty command', () => {
  assert.strictEqual(isGitDashC(''), false);
});

// --- Tests for handlePreToolUse ---

test('blocks Bash tool with git -C command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'git -C /some/dir status' }
  });
  assert.strictEqual(result.blocked, true);
  assert.strictEqual(result.message, GIT_DASH_C_MESSAGE);
});

test('allows Bash tool with plain git command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'git status' }
  });
  assert.strictEqual(result.blocked, false);
});

test('ignores non-Bash tools', () => {
  const result = handlePreToolUse({
    tool_name: 'Read',
    tool_input: { file_path: '/some/file' }
  });
  assert.strictEqual(result.blocked, false);
});

test('handles missing tool_input gracefully', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash'
  });
  assert.strictEqual(result.blocked, false);
});

test('handles missing command gracefully', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: {}
  });
  assert.strictEqual(result.blocked, false);
});

// --- Tests for isPythonMPytest ---

test('detects python -m pytest', () => {
  assert.strictEqual(isPythonMPytest('python -m pytest tests/'), true);
});

test('detects python -m pytest with flags', () => {
  assert.strictEqual(isPythonMPytest('python -m pytest -v tests/'), true);
});

test('detects python3 -m pytest', () => {
  assert.strictEqual(isPythonMPytest('python3 -m pytest tests/'), true);
});

test('allows uv run pytest', () => {
  assert.strictEqual(isPythonMPytest('uv run pytest tests/'), false);
});

test('allows plain pytest', () => {
  assert.strictEqual(isPythonMPytest('pytest tests/'), false);
});

test('blocks Bash tool with python -m pytest command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'python -m pytest tests/ -v' }
  });
  assert.strictEqual(result.blocked, true);
  assert.strictEqual(result.message, PYTHON_M_PYTEST_MESSAGE);
});

test('allows Bash tool with uv run pytest command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'uv run pytest tests/ -v' }
  });
  assert.strictEqual(result.blocked, false);
});

// Run all tests
runTests();
