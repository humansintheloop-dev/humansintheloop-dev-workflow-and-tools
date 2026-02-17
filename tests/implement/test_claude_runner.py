"""Tests for ClaudeRunner strategy pattern."""

import os
import stat
import tempfile

import pytest

from fake_claude_runner import FakeClaudeRunner


@pytest.mark.unit
class TestFakeClaudeRunner:
    """FakeClaudeRunner returns canned results and records calls."""

    def test_returns_default_success_result(self):
        fake = FakeClaudeRunner()
        result = fake.run_interactive(["claude", "do task"], cwd="/repo")
        assert result.returncode == 0

    def test_records_run_interactive_call(self):
        fake = FakeClaudeRunner()
        fake.run_interactive(["claude", "do task"], cwd="/repo")
        assert fake.calls == [("run_interactive", ["claude", "do task"], "/repo")]

    def test_records_run_with_capture_call(self):
        fake = FakeClaudeRunner()
        fake.run_with_capture(["claude", "-p", "do task"], cwd="/repo")
        assert fake.calls == [("run_with_capture", ["claude", "-p", "do task"], "/repo")]

    def test_returns_configured_result(self):
        from i2code.implement.implement import ClaudeResult

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=1, stdout="error", stderr="fail"))
        result = fake.run_interactive(["claude", "x"], cwd="/repo")
        assert result.returncode == 1
        assert result.stdout == "error"

    def test_returns_sequence_of_results(self):
        from i2code.implement.implement import ClaudeResult

        fake = FakeClaudeRunner()
        fake.set_results([
            ClaudeResult(returncode=0, stdout="ok1", stderr=""),
            ClaudeResult(returncode=1, stdout="fail", stderr="err"),
        ])
        r1 = fake.run_interactive(["claude", "t1"], cwd="/r")
        r2 = fake.run_with_capture(["claude", "t2"], cwd="/r")
        assert r1.returncode == 0
        assert r2.returncode == 1

    def test_falls_back_to_default_after_sequence_exhausted(self):
        from i2code.implement.implement import ClaudeResult

        fake = FakeClaudeRunner()
        fake.set_results([ClaudeResult(returncode=42, stdout="", stderr="")])
        r1 = fake.run_interactive(["claude", "t1"], cwd="/r")
        r2 = fake.run_interactive(["claude", "t2"], cwd="/r")
        assert r1.returncode == 42
        assert r2.returncode == 0  # default


@pytest.mark.unit
class TestMockClaudeRunner:
    """MockClaudeRunner wraps a mock shell script for integration testing."""

    def test_run_interactive_invokes_mock_script(self):
        from i2code.implement.claude_runner import MockClaudeRunner, ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            script = os.path.join(tmpdir, "mock-claude.sh")
            with open(script, "w") as f:
                f.write("#!/bin/bash\nexit 0\n")
            os.chmod(script, stat.S_IRWXU)

            runner = MockClaudeRunner(script)
            result = runner.run_interactive(["claude", "do task"], cwd=tmpdir)
            assert isinstance(result, ClaudeResult)
            assert result.returncode == 0

    def test_run_with_capture_invokes_mock_script(self):
        from i2code.implement.claude_runner import MockClaudeRunner, ClaudeResult

        with tempfile.TemporaryDirectory() as tmpdir:
            script = os.path.join(tmpdir, "mock-claude.sh")
            with open(script, "w") as f:
                f.write('#!/bin/bash\necho "captured output"\nexit 0\n')
            os.chmod(script, stat.S_IRWXU)

            runner = MockClaudeRunner(script)
            result = runner.run_with_capture(["claude", "do task"], cwd=tmpdir)
            assert isinstance(result, ClaudeResult)
            assert result.returncode == 0

    def test_run_interactive_returns_nonzero_on_script_failure(self):
        from i2code.implement.claude_runner import MockClaudeRunner

        with tempfile.TemporaryDirectory() as tmpdir:
            script = os.path.join(tmpdir, "mock-claude.sh")
            with open(script, "w") as f:
                f.write("#!/bin/bash\nexit 1\n")
            os.chmod(script, stat.S_IRWXU)

            runner = MockClaudeRunner(script)
            result = runner.run_interactive(["claude", "do task"], cwd=tmpdir)
            assert result.returncode == 1


@pytest.mark.unit
class TestClaudeResultInModule:
    """ClaudeResult is accessible from claude_runner module."""

    def test_claude_result_importable_from_claude_runner(self):
        from i2code.implement.claude_runner import ClaudeResult

        result = ClaudeResult(returncode=0, stdout="hi", stderr="")
        assert result.returncode == 0
        assert result.stdout == "hi"
