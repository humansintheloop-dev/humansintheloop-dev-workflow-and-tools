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
        from i2code.implement.claude_runner import ClaudeResult

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=1, stdout="error", stderr="fail"))
        result = fake.run_interactive(["claude", "x"], cwd="/repo")
        assert result.returncode == 1
        assert result.stdout == "error"

    def test_returns_sequence_of_results(self):
        from i2code.implement.claude_runner import ClaudeResult

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
        from i2code.implement.claude_runner import ClaudeResult

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


@pytest.mark.unit
class TestRunClaudeWithOutputCapture:
    """Test running Claude with output capture and real-time display."""

    def test_run_claude_captures_stdout(self, mocker):
        """Should capture stdout from Claude process."""
        from i2code.implement.claude_runner import run_claude_with_output_capture

        # Mock Popen with pipe-like objects
        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        # read1() returns data then empty bytes (EOF) to stop the reader thread
        mock_stdout.read1.side_effect = [b"line1\n", b"line2\n", b""]
        mock_stderr.read1.side_effect = [b""]  # No stderr

        mock_process = mocker.MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.returncode = 0
        mocker.patch('i2code.implement.claude_runner.subprocess.Popen', return_value=mock_process)

        result = run_claude_with_output_capture(["claude", "test"], cwd="/tmp")

        assert "line1" in result.stdout
        assert "line2" in result.stdout
        assert result.returncode == 0

    def test_run_claude_captures_stderr(self, mocker):
        """Should capture stderr from Claude process."""
        from i2code.implement.claude_runner import run_claude_with_output_capture

        mock_stdout = mocker.MagicMock()
        mock_stderr = mocker.MagicMock()

        # read1() returns data then empty bytes (EOF)
        mock_stdout.read1.side_effect = [b""]  # No stdout
        mock_stderr.read1.side_effect = [b"error1\n", b""]

        mock_process = mocker.MagicMock()
        mock_process.stdout = mock_stdout
        mock_process.stderr = mock_stderr
        mock_process.returncode = 1
        mocker.patch('i2code.implement.claude_runner.subprocess.Popen', return_value=mock_process)

        result = run_claude_with_output_capture(["claude", "test"], cwd="/tmp")

        assert "error1" in result.stderr
        assert result.returncode == 1


@pytest.mark.unit
class TestClaudeInvocationResult:
    """Test handling of Claude invocation results."""

    def test_check_claude_success_with_zero_exit(self):
        """Should return True for exit code 0."""
        from i2code.implement.claude_runner import check_claude_success

        assert check_claude_success(exit_code=0, head_before="abc123", head_after="def456") is True

    def test_check_claude_success_fails_with_nonzero_exit(self):
        """Should return False for non-zero exit code."""
        from i2code.implement.claude_runner import check_claude_success

        assert check_claude_success(exit_code=1, head_before="abc123", head_after="def456") is False

    def test_check_claude_success_fails_if_head_unchanged(self):
        """Should return False if HEAD didn't advance (no commit made)."""
        from i2code.implement.claude_runner import check_claude_success

        assert check_claude_success(exit_code=0, head_before="abc123", head_after="abc123") is False

    def test_check_claude_success_requires_both_conditions(self):
        """Success requires exit code 0 AND HEAD advancement."""
        from i2code.implement.claude_runner import check_claude_success

        # Exit 0 but no commit
        assert check_claude_success(exit_code=0, head_before="abc", head_after="abc") is False
        # Commit made but exit failed
        assert check_claude_success(exit_code=1, head_before="abc", head_after="def") is False
        # Both conditions met
        assert check_claude_success(exit_code=0, head_before="abc", head_after="def") is True
