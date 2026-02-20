import signal
import subprocess
from unittest.mock import MagicMock

import pytest

from i2code.implement.managed_subprocess import ManagedSubprocess


@pytest.mark.unit
class TestNormalExit:
    """ManagedSubprocess has no effect on normal process exit."""

    def test_normal_exit_does_not_terminate_or_kill(self):
        process = MagicMock()
        process.returncode = 0

        with ManagedSubprocess(process, label="test"):
            pass

        process.terminate.assert_not_called()
        process.kill.assert_not_called()

    def test_normal_exit_no_stderr_output(self, capsys):
        process = MagicMock()
        process.returncode = 0

        with ManagedSubprocess(process, label="test"):
            pass

        captured = capsys.readouterr()
        assert captured.err == ""

    def test_normal_exit_restores_signal_handlers(self):
        process = MagicMock()
        process.returncode = 0

        original_sigtstp = signal.getsignal(signal.SIGTSTP)
        original_sigcont = signal.getsignal(signal.SIGCONT)

        with ManagedSubprocess(process, label="test"):
            pass

        assert signal.getsignal(signal.SIGTSTP) == original_sigtstp
        assert signal.getsignal(signal.SIGCONT) == original_sigcont


@pytest.mark.unit
class TestKeyboardInterrupt:
    """ManagedSubprocess terminates child on KeyboardInterrupt with cleanup messages."""

    def test_keyboard_interrupt_terminates_process_and_prints_messages(self, capsys):
        process = MagicMock()
        process.returncode = None

        managed = ManagedSubprocess(process, label="claude")
        managed.__enter__()
        result = managed.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)

        process.terminate.assert_called_once()
        process.wait.assert_called()

        captured = capsys.readouterr()
        assert "\nInterrupted. Terminating claude process..." in captured.err
        assert "Done." in captured.err

        assert result is True  # exception suppressed
        assert managed.interrupted is True

    def test_keyboard_interrupt_restores_signal_handlers(self):
        process = MagicMock()
        process.returncode = None

        original_sigtstp = signal.getsignal(signal.SIGTSTP)
        original_sigcont = signal.getsignal(signal.SIGCONT)

        managed = ManagedSubprocess(process, label="test")
        managed.__enter__()
        managed.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)

        assert signal.getsignal(signal.SIGTSTP) == original_sigtstp
        assert signal.getsignal(signal.SIGCONT) == original_sigcont

    def test_keyboard_interrupt_joins_all_threads_with_timeout(self):
        process = MagicMock()
        process.returncode = None

        thread1 = MagicMock()
        thread2 = MagicMock()
        timeout = 3.0

        managed = ManagedSubprocess(
            process, label="test", threads=[thread1, thread2], terminate_timeout=timeout
        )
        managed.__enter__()
        managed.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)

        thread1.join.assert_called_once_with(timeout=timeout)
        thread2.join.assert_called_once_with(timeout=timeout)


@pytest.mark.unit
class TestSigkillEscalation:
    """ManagedSubprocess escalates to SIGKILL when SIGTERM times out."""

    def test_sigkill_escalation(self, capsys):
        process = MagicMock()
        process.returncode = None

        # First wait(timeout=...) after terminate() raises TimeoutExpired,
        # second wait() (after kill()) succeeds
        process.wait.side_effect = [
            subprocess.TimeoutExpired(cmd="test", timeout=5.0),
            None,
        ]

        managed = ManagedSubprocess(process, label="claude")
        managed.__enter__()
        managed.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)

        process.terminate.assert_called_once()
        process.kill.assert_called_once()

        captured = capsys.readouterr()
        err = captured.err
        assert "Force-killing claude process..." in err
        assert "Done." in err
        # Force-killing must appear before Done.
        assert err.index("Force-killing claude process...") < err.index("Done.")
