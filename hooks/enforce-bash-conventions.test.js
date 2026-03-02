/**
 * Tests for enforce-bash-conventions.js
 * Run with: node hooks/enforce-bash-conventions.test.js
 */

const assert = require('assert');

const { isGitDashC, isCdAndGit, isGitCommitHeredoc, isPythonMPytest, isBarePytest, handlePreToolUse, GIT_DASH_C_MESSAGE, CD_AND_GIT_MESSAGE, GIT_COMMIT_HEREDOC_MESSAGE, PYTHON_M_PYTEST_MESSAGE, BARE_PYTEST_MESSAGE } = require('./enforce-bash-conventions.js');

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

// --- Tests for isCdAndGit ---

test('detects cd && git with absolute path', () => {
  assert.strictEqual(isCdAndGit('cd /tmp/some-repo && git status'), true);
});

test('detects cd && git with relative path', () => {
  assert.strictEqual(isCdAndGit('cd ../other-repo && git log'), true);
});

test('detects cd && git without spaces around &&', () => {
  assert.strictEqual(isCdAndGit('cd /some/dir&&git status'), true);
});

test('allows cd without git', () => {
  assert.strictEqual(isCdAndGit('cd /some/dir && npm test'), false);
});

test('allows plain git commands without cd', () => {
  assert.strictEqual(isCdAndGit('git status'), false);
});

test('allows cd alone', () => {
  assert.strictEqual(isCdAndGit('cd /some/dir'), false);
});

test('blocks Bash tool with cd && git command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'cd /tmp/eventuate-examples && git status' }
  });
  assert.strictEqual(result.blocked, true);
  assert.strictEqual(result.message, CD_AND_GIT_MESSAGE);
});

// --- Tests for isGitCommitHeredoc ---

test('detects git commit with cat heredoc', () => {
  assert.strictEqual(isGitCommitHeredoc('git commit -m "$(cat <<\'EOF\'\nmessage\nEOF\n)"'), true);
});

test('detects git commit with cat heredoc unquoted', () => {
  assert.strictEqual(isGitCommitHeredoc('git commit -m "$(cat <<EOF\nmessage\nEOF\n)"'), true);
});

test('detects git commit with cat heredoc after other flags', () => {
  assert.strictEqual(isGitCommitHeredoc('git commit --allow-empty -m "$(cat <<\'EOF\'\nmessage\nEOF\n)"'), true);
});

test('allows simple git commit -m', () => {
  assert.strictEqual(isGitCommitHeredoc('git commit -m "simple message"'), false);
});

test('allows git commit -F- heredoc', () => {
  assert.strictEqual(isGitCommitHeredoc('git commit -F- <<EOF\nmessage\nEOF'), false);
});

test('allows non-commit git commands', () => {
  assert.strictEqual(isGitCommitHeredoc('git status'), false);
});

test('blocks Bash tool with git commit cat heredoc', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'git commit -m "$(cat <<\'EOF\'\nFix bug\n\nCo-authored by Claude Code\nEOF\n)"' }
  });
  assert.strictEqual(result.blocked, true);
  assert.strictEqual(result.message, GIT_COMMIT_HEREDOC_MESSAGE);
});

test('allows Bash tool with git commit -F- heredoc', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'git commit -F- <<EOF\nFix bug\n\nCo-authored by Claude Code\nEOF' }
  });
  assert.strictEqual(result.blocked, false);
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

test('allows uv run python -m pytest', () => {
  assert.strictEqual(isPythonMPytest('uv run python -m pytest tests/ -v -m unit'), false);
});

test('isPythonMPytest does not match bare pytest', () => {
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

test('allows Bash tool with uv run python -m pytest command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'uv run python -m pytest tests/ -v -m unit' }
  });
  assert.strictEqual(result.blocked, false);
});

// --- Tests for isBarePytest ---

test('detects bare pytest', () => {
  assert.strictEqual(isBarePytest('pytest tests/'), true);
});

test('detects bare pytest with flags', () => {
  assert.strictEqual(isBarePytest('pytest -v tests/'), true);
});

test('allows uv run pytest', () => {
  assert.strictEqual(isBarePytest('uv run pytest tests/'), false);
});

test('allows uv run python -m pytest', () => {
  assert.strictEqual(isBarePytest('uv run python -m pytest tests/ -v -m unit'), false);
});

test('blocks Bash tool with bare pytest command', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'pytest tests/' }
  });
  assert.strictEqual(result.blocked, true);
  assert.strictEqual(result.message, BARE_PYTEST_MESSAGE);
});

test('blocks Bash tool with bare pytest and flags', () => {
  const result = handlePreToolUse({
    tool_name: 'Bash',
    tool_input: { command: 'pytest -v --tb=short tests/' }
  });
  assert.strictEqual(result.blocked, true);
  assert.strictEqual(result.message, BARE_PYTEST_MESSAGE);
});

// Run all tests
runTests();
