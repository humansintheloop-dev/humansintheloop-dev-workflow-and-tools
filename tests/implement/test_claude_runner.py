"""Tests for ClaudeRunner strategy pattern."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from fake_claude_runner import FakeClaudeRunner
from i2code.implement.claude_runner import (
    CapturedOutput,
    ClaudeCodeCommand,
    ClaudeResult,
    ClaudeRunner,
    SessionId,
    _parse_stream_json_output,
    run_claude_with_output_capture,
)


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

    def test_records_run_batch_call(self):
        fake = FakeClaudeRunner()
        fake.run_batch(["claude", "-p", "do task"], cwd="/repo")
        assert fake.calls == [("run_batch", ["claude", "-p", "do task"], "/repo")]

    def test_returns_configured_result(self):

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=1, output=CapturedOutput("error", "fail")))
        result = fake.run_interactive(["claude", "x"], cwd="/repo")
        assert result.returncode == 1
        assert result.output.stdout == "error"

    def test_returns_sequence_of_results(self):

        fake = FakeClaudeRunner()
        fake.set_results([
            ClaudeResult(returncode=0, output=CapturedOutput("ok1")),
            ClaudeResult(returncode=1, output=CapturedOutput("fail", "err")),
        ])
        r1 = fake.run_interactive(["claude", "t1"], cwd="/r")
        r2 = fake.run_batch(["claude", "t2"], cwd="/r")
        assert r1.returncode == 0
        assert r2.returncode == 1

    def test_records_run_call(self):
        fake = FakeClaudeRunner()
        fake.run(["claude", "do task"], cwd="/repo")
        assert fake.calls == [("run", ["claude", "do task"], "/repo")]

    def test_falls_back_to_default_after_sequence_exhausted(self):

        fake = FakeClaudeRunner()
        fake.set_results([ClaudeResult(returncode=42)])
        r1 = fake.run_interactive(["claude", "t1"], cwd="/r")
        r2 = fake.run_interactive(["claude", "t2"], cwd="/r")
        assert r1.returncode == 42
        assert r2.returncode == 0  # default

    def test_records_execute_call(self):
        fake = FakeClaudeRunner()
        command = ClaudeCodeCommand(prompt="x", cwd="/r", interactive=False)
        fake.execute(command)
        assert fake.calls == [("execute", command, "/r")]
        assert fake.calls[0][1] is command

    def test_execute_returns_configured_result(self):
        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=7, result_text="done"))
        command = ClaudeCodeCommand(prompt="x", cwd="/r", interactive=False)
        result = fake.execute(command)
        assert result.returncode == 7
        assert result.result_text == "done"


@pytest.mark.unit
class TestClaudeResultInModule:
    """ClaudeResult is accessible from claude_runner module."""

    def test_claude_result_importable_from_claude_runner(self):

        result = ClaudeResult(returncode=0, output=CapturedOutput(stdout="hi"))
        assert result.returncode == 0
        assert result.output.stdout == "hi"


def _run_with_mocked_pipes(mocker, stdout_chunks, stderr_chunks, returncode=0):
    """Patch Popen with pipes producing the given chunks and run the capture helper."""
    mock_stdout = mocker.MagicMock()
    mock_stderr = mocker.MagicMock()
    mock_stdout.read1.side_effect = [*stdout_chunks, b""]
    mock_stderr.read1.side_effect = [*stderr_chunks, b""]

    mock_process = mocker.MagicMock()
    mock_process.stdout = mock_stdout
    mock_process.stderr = mock_stderr
    mock_process.returncode = returncode
    mocker.patch(
        'i2code.implement.claude_runner.subprocess.Popen',
        return_value=mock_process,
    )

    return run_claude_with_output_capture(["claude", "test"], cwd="/tmp")


@pytest.mark.unit
class TestRunClaudeWithOutputCapture:
    """Test running Claude with output capture and real-time display."""

    def test_run_claude_captures_stdout(self, mocker):
        result = _run_with_mocked_pipes(mocker, [b"line1\n", b"line2\n"], [])

        assert "line1" in result.output.stdout
        assert "line2" in result.output.stdout
        assert result.returncode == 0

    def test_run_claude_captures_stderr(self, mocker):
        result = _run_with_mocked_pipes(mocker, [], [b"error1\n"], returncode=1)

        assert "error1" in result.output.stderr
        assert result.returncode == 1


def _make_mock_popen():
    """Create a mock Popen that simulates a process with empty pipes."""
    mock_process = MagicMock()
    mock_process.stdout.read1.return_value = b""
    mock_process.stderr.read1.return_value = b""
    mock_process.returncode = 0
    mock_process.wait.return_value = 0
    return mock_process


@pytest.mark.unit
class TestRunClaudeWithOutputCaptureSignalHandling:
    """run_claude_with_output_capture integrates ManagedSubprocess for signal handling."""

    @patch("i2code.implement.claude_runner.subprocess.Popen")
    def test_popen_called_with_start_new_session(self, mock_popen_cls):
        mock_process = _make_mock_popen()
        mock_popen_cls.return_value = mock_process

        run_claude_with_output_capture(["claude", "-p", "task"], cwd="/tmp")

        mock_popen_cls.assert_called_once()
        call_kwargs = mock_popen_cls.call_args[1]
        assert call_kwargs.get("start_new_session") is True
        assert call_kwargs.get("stdin") == subprocess.DEVNULL

    @patch("i2code.implement.claude_runner.ManagedSubprocess")
    @patch("i2code.implement.claude_runner.subprocess.Popen")
    def test_managed_subprocess_used_with_correct_args(self, mock_popen_cls, mock_managed_cls):
        mock_process = _make_mock_popen()
        mock_popen_cls.return_value = mock_process

        mock_managed = MagicMock()
        mock_managed.interrupted = False
        mock_managed.__enter__ = MagicMock(return_value=mock_managed)
        mock_managed.__exit__ = MagicMock(return_value=False)
        mock_managed_cls.return_value = mock_managed

        run_claude_with_output_capture(["claude", "-p", "task"], cwd="/tmp")

        mock_managed_cls.assert_called_once()
        call_kwargs = mock_managed_cls.call_args[1]
        assert call_kwargs["process"] is mock_process
        assert call_kwargs["label"] == "claude"
        assert len(call_kwargs["threads"]) == 2

    @patch("i2code.implement.claude_runner.ManagedSubprocess")
    @patch("i2code.implement.claude_runner.subprocess.Popen")
    def test_returns_returncode_130_when_interrupted(self, mock_popen_cls, mock_managed_cls):
        mock_process = _make_mock_popen()
        mock_popen_cls.return_value = mock_process

        mock_managed = MagicMock()
        mock_managed.interrupted = True
        mock_managed.__enter__ = MagicMock(return_value=mock_managed)
        mock_managed.__exit__ = MagicMock(return_value=True)
        mock_managed_cls.return_value = mock_managed

        result = run_claude_with_output_capture(["claude", "-p", "task"], cwd="/tmp")

        assert result.returncode == 130
        assert result.output.stdout == ""
        assert result.output.stderr == ""


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


@pytest.mark.unit
class TestClaudeCodeCommand:
    """ClaudeCodeCommand dataclass field defaults and validation."""

    def test_claude_code_command_field_defaults(self):
        cmd = ClaudeCodeCommand(cwd="/x", prompt="hello")
        assert cmd.cwd == "/x"
        assert cmd.prompt == "hello"
        assert cmd.interactive is None
        assert cmd.allowed_tools is None
        assert cmd.session_id is None
        assert cmd.add_dirs == []
        assert cmd.extra_args == []
        assert cmd.mock_command is None

    def test_claude_code_command_requires_prompt_or_mock(self):
        with pytest.raises(ValueError):
            ClaudeCodeCommand(cwd="/x")

    def test_claude_code_command_mock_only_ok(self):
        cmd = ClaudeCodeCommand(cwd="/x", mock_command=["/usr/bin/mock", "label"])
        assert cmd.prompt is None
        assert cmd.mock_command == ["/usr/bin/mock", "label"]

    def test_claude_code_command_both_prompt_and_mock_ok(self):
        cmd = ClaudeCodeCommand(
            cwd="/x",
            prompt="hello",
            mock_command=["/usr/bin/mock", "label"],
        )
        assert cmd.prompt == "hello"
        assert cmd.mock_command == ["/usr/bin/mock", "label"]

    def test_session_id_frozen(self):
        sid = SessionId(session_id="abc123", is_new=True)
        assert sid.session_id == "abc123"
        assert sid.is_new is True
        with pytest.raises(Exception):
            sid.session_id = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestParseStreamJsonOutput:
    """_parse_stream_json_output extracts result_text from stream-json output."""

    def test_result_text_from_terminal_result_message(self):
        stdout = (
            '{"type":"assistant","message":{}}\n'
            '{"type":"result","result":"first"}\n'
            '{"type":"assistant","message":{}}\n'
            '{"type":"result","result":"last"}\n'
        )

        _diagnostics, result_text = _parse_stream_json_output(stdout)

        assert result_text == "last"

    def test_result_text_from_single_result_message(self):
        stdout = '{"type":"result","result":"only"}\n'

        _diagnostics, result_text = _parse_stream_json_output(stdout)

        assert result_text == "only"

    def test_result_text_falls_back_to_raw_stdout_when_no_result_message(self):
        stdout = "plain text without stream-json\nanother line\n"

        _diagnostics, result_text = _parse_stream_json_output(stdout)

        assert result_text == stdout


@pytest.mark.unit
class TestRunClaudeWithOutputCaptureResultText:
    """run_claude_with_output_capture populates ClaudeResult.result_text."""

    def test_result_text_populated_from_stream_json(self, mocker):
        result = _run_with_mocked_pipes(
            mocker, [b'{"type":"result","result":"hello"}\n'], [],
        )

        assert result.result_text == "hello"

    def test_result_text_falls_back_to_raw_stdout(self, mocker):
        result = _run_with_mocked_pipes(mocker, [b"raw output\n"], [])

        assert result.result_text == "raw output\n"


def _patch_interactive_run(mocker):
    mock_completed = MagicMock()
    mock_completed.returncode = 0
    return mocker.patch(
        'i2code.implement.claude_runner.subprocess.run',
        return_value=mock_completed,
    )


def _patch_batch_popen(mocker, stdout_chunks=(b"",)):
    mock_stdout = MagicMock()
    mock_stderr = MagicMock()
    mock_stdout.read1.side_effect = list(stdout_chunks)
    mock_stderr.read1.side_effect = [b""]

    mock_process = MagicMock()
    mock_process.stdout = mock_stdout
    mock_process.stderr = mock_stderr
    mock_process.returncode = 0
    return mocker.patch(
        'i2code.implement.claude_runner.subprocess.Popen',
        return_value=mock_process,
    )


def _assert_argv_and_cwd(mock_call, expected_argv, expected_cwd):
    mock_call.assert_called_once()
    args, kwargs = mock_call.call_args
    assert args[0] == expected_argv
    assert kwargs.get("cwd") == expected_cwd


@pytest.mark.unit
class TestClaudeRunnerExecute:
    """ClaudeRunner.execute(ClaudeCodeCommand) builds argv per spec §3.3."""

    def test_execute_interactive_no_session(self, mocker):
        mock_run = _patch_interactive_run(mocker)

        runner = ClaudeRunner(interactive=True)
        command = ClaudeCodeCommand(prompt="p", cwd="/c", interactive=True)

        result = runner.execute(command)

        _assert_argv_and_cwd(mock_run, ["claude", "p"], "/c")
        argv = mock_run.call_args[0][0]
        assert "--verbose" not in argv
        assert "--output-format=stream-json" not in argv
        assert "-p" not in argv
        assert result.result_text == ""

    def test_execute_interactive_with_resume(self, mocker):
        mock_run = _patch_interactive_run(mocker)

        runner = ClaudeRunner(interactive=True)
        command = ClaudeCodeCommand(
            prompt="p",
            cwd="/c",
            interactive=True,
            session_id=SessionId("abc123", is_new=False),
        )

        runner.execute(command)

        _assert_argv_and_cwd(mock_run, ["claude", "--resume", "abc123", "p"], "/c")

    def test_execute_with_new_session_id(self, mocker):
        mock_run = _patch_interactive_run(mocker)

        runner = ClaudeRunner(interactive=True)
        command = ClaudeCodeCommand(
            prompt="p",
            cwd="/c",
            interactive=True,
            session_id=SessionId("newid", is_new=True),
        )

        runner.execute(command)

        _assert_argv_and_cwd(mock_run, ["claude", "--session-id", "newid", "p"], "/c")

    @pytest.mark.parametrize(
        "add_dirs,expected_dir_args",
        [
            (["/d1"], ["--add-dir", "/d1"]),
            (["/d1", "/d2"], ["--add-dir", "/d1", "--add-dir", "/d2"]),
        ],
        ids=["one_dir", "two_dirs"],
    )
    def test_execute_with_add_dirs(self, mocker, add_dirs, expected_dir_args):
        mock_popen = _patch_batch_popen(mocker)

        runner = ClaudeRunner(interactive=True, debug=False)
        command = ClaudeCodeCommand(
            prompt="p",
            cwd="/c",
            interactive=False,
            allowed_tools="Read",
            add_dirs=add_dirs,
        )

        runner.execute(command)

        _assert_argv_and_cwd(
            mock_popen,
            [
                "claude",
                "--verbose",
                "--output-format=stream-json",
                "--allowedTools",
                "Read",
                *expected_dir_args,
                "-p",
                "p",
            ],
            "/c",
        )

    @pytest.mark.parametrize(
        "runner_interactive,expected_argv",
        [
            (False, ["claude", "--verbose", "--output-format=stream-json", "-p", "p"]),
            (True, ["claude", "p"]),
        ],
        ids=["runner_batch", "runner_interactive"],
    )
    def test_execute_mode_inherited_from_runner(
        self, mocker, runner_interactive, expected_argv,
    ):
        mock_run = _patch_interactive_run(mocker)
        mock_popen = _patch_batch_popen(mocker)

        runner = ClaudeRunner(interactive=runner_interactive)
        command = ClaudeCodeCommand(prompt="p", cwd="/c", interactive=None)

        runner.execute(command)

        dispatched = mock_run if runner_interactive else mock_popen
        not_dispatched = mock_popen if runner_interactive else mock_run
        _assert_argv_and_cwd(dispatched, expected_argv, "/c")
        not_dispatched.assert_not_called()

    @pytest.mark.parametrize(
        "runner_interactive",
        [False, True],
        ids=["runner_batch", "runner_interactive"],
    )
    def test_execute_mock_command_short_circuit(self, mocker, runner_interactive):
        mock_run = _patch_interactive_run(mocker)
        mock_popen = _patch_batch_popen(mocker)

        runner = ClaudeRunner(interactive=runner_interactive)
        command = ClaudeCodeCommand(
            cwd="/c",
            prompt="ignored prompt",
            interactive=not runner_interactive,
            allowed_tools="Read",
            session_id=SessionId("ignored-session", is_new=True),
            add_dirs=["/ignored"],
            extra_args=["--ignored-flag"],
            mock_command=["/path/mock-claude", "triage-42"],
        )

        runner.execute(command)

        dispatched = mock_run if runner_interactive else mock_popen
        not_dispatched = mock_popen if runner_interactive else mock_run
        _assert_argv_and_cwd(
            dispatched, ["/path/mock-claude", "triage-42"], "/c",
        )
        not_dispatched.assert_not_called()

    def test_execute_batch_with_allowed_tools_emits_expected_argv(self, mocker):
        mock_popen = _patch_batch_popen(
            mocker,
            stdout_chunks=[b'{"type":"result","result":"hello world"}\n', b""],
        )

        runner = ClaudeRunner(interactive=True, debug=False)
        command = ClaudeCodeCommand(
            prompt="do task",
            cwd="/repo",
            interactive=False,
            allowed_tools="Read(/repo/**)",
        )

        result = runner.execute(command)

        _assert_argv_and_cwd(
            mock_popen,
            [
                "claude",
                "--verbose",
                "--output-format=stream-json",
                "--allowedTools",
                "Read(/repo/**)",
                "-p",
                "do task",
            ],
            "/repo",
        )
        assert result.result_text == "hello world"


@pytest.mark.integration_claude
class TestClaudeRunnerExecuteRealClaude:
    """ClaudeRunner.execute() against the real claude CLI returns parsed result_text."""

    def test_execute_batch_returns_result_text_from_real_claude(self, tmp_path):
        command = ClaudeCodeCommand(
            prompt="Reply with exactly the word: pong",
            cwd=str(tmp_path),
            interactive=False,
            allowed_tools="Read(/dev/null)",
        )

        result = ClaudeRunner().execute(command)

        assert result.returncode == 0
        assert result.result_text
        assert not result.result_text.startswith("{")


@pytest.mark.unit
class TestClaudeRunnerRun:
    """ClaudeRunner.run() dispatches to run_interactive or run_batch."""

    def test_interactive_true_delegates_to_run_interactive(self, mocker):
        runner = ClaudeRunner(interactive=True)
        mock_result = ClaudeResult(returncode=0)
        mocker.patch.object(runner, 'run_interactive', return_value=mock_result)
        mocker.patch.object(runner, 'run_batch', return_value=mock_result)

        result = runner.run(["claude", "task"], cwd="/repo")

        runner.run_interactive.assert_called_once_with(["claude", "task"], cwd="/repo")
        runner.run_batch.assert_not_called()
        assert result is mock_result

    def test_interactive_false_delegates_to_run_batch(self, mocker):
        runner = ClaudeRunner(interactive=False)
        mock_result = ClaudeResult(returncode=0)
        mocker.patch.object(runner, 'run_interactive', return_value=mock_result)
        mocker.patch.object(runner, 'run_batch', return_value=mock_result)

        result = runner.run(["claude", "-p", "task"], cwd="/repo")

        runner.run_batch.assert_called_once_with(["claude", "-p", "task"], cwd="/repo")
        runner.run_interactive.assert_not_called()
        assert result is mock_result
