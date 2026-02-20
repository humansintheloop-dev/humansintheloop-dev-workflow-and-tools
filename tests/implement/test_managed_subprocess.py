import os
import signal
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from i2code.implement.managed_subprocess import ManagedSubprocess


@pytest.fixture
def original_signal_handlers():
    """Capture SIGTSTP and SIGCONT handlers before test runs."""
    return signal.getsignal(signal.SIGTSTP), signal.getsignal(signal.SIGCONT)


def assert_handlers_restored(original_signal_handlers):
    sigtstp, sigcont = original_signal_handlers
    assert signal.getsignal(signal.SIGTSTP) == sigtstp
    assert signal.getsignal(signal.SIGCONT) == sigcont


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

    def test_normal_exit_restores_signal_handlers(self, original_signal_handlers):
        process = MagicMock()
        process.returncode = 0

        with ManagedSubprocess(process, label="test"):
            pass

        assert_handlers_restored(original_signal_handlers)


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

    def test_keyboard_interrupt_restores_signal_handlers(self, original_signal_handlers):
        process = MagicMock()
        process.returncode = None

        managed = ManagedSubprocess(process, label="test")
        managed.__enter__()
        managed.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)

        assert_handlers_restored(original_signal_handlers)

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


@pytest.mark.unit
class TestSignalForwarding:
    """ManagedSubprocess forwards SIGTSTP and SIGCONT to child process group."""

    def test_signal_forwarding_installs_custom_sigtstp_handler(self):
        process = MagicMock()

        original_sigtstp = signal.getsignal(signal.SIGTSTP)

        with ManagedSubprocess(process, label="test"):
            current_sigtstp = signal.getsignal(signal.SIGTSTP)
            assert current_sigtstp != original_sigtstp
            assert callable(current_sigtstp)

    @patch("i2code.implement.managed_subprocess.os.kill")
    @patch("i2code.implement.managed_subprocess.os.killpg")
    def test_signal_forwarding_sigtstp_forwards_to_child_group(self, mock_killpg, mock_kill):
        process = MagicMock()
        process.pid = 12345

        with ManagedSubprocess(process, label="test"):
            handler = signal.getsignal(signal.SIGTSTP)
            handler(signal.SIGTSTP, None)

        mock_killpg.assert_called_once_with(12345, signal.SIGTSTP)
        mock_kill.assert_called_once_with(os.getpid(), signal.SIGTSTP)

    @patch("i2code.implement.managed_subprocess.os.killpg")
    def test_signal_forwarding_sigcont_forwards_to_child_and_reinstalls_sigtstp(self, mock_killpg):
        process = MagicMock()
        process.pid = 12345

        with ManagedSubprocess(process, label="test"):
            # Get a reference to the custom SIGTSTP handler
            custom_sigtstp = signal.getsignal(signal.SIGTSTP)

            # Get and invoke the SIGCONT handler
            sigcont_handler = signal.getsignal(signal.SIGCONT)
            assert callable(sigcont_handler)
            sigcont_handler(signal.SIGCONT, None)

            # Verify SIGCONT was forwarded to child group
            mock_killpg.assert_called_once_with(12345, signal.SIGCONT)

            # Verify custom SIGTSTP handler was re-installed
            assert signal.getsignal(signal.SIGTSTP) == custom_sigtstp

    def test_signal_forwarding_restores_handlers_on_normal_exit(self, original_signal_handlers):
        process = MagicMock()
        sigtstp, sigcont = original_signal_handlers

        with ManagedSubprocess(process, label="test"):
            assert signal.getsignal(signal.SIGTSTP) != sigtstp
            assert signal.getsignal(signal.SIGCONT) != sigcont

        assert_handlers_restored(original_signal_handlers)

    def test_signal_forwarding_restores_handlers_on_keyboard_interrupt(self, original_signal_handlers):
        process = MagicMock()
        sigtstp, sigcont = original_signal_handlers

        managed = ManagedSubprocess(process, label="test")
        managed.__enter__()

        assert signal.getsignal(signal.SIGTSTP) != sigtstp
        assert signal.getsignal(signal.SIGCONT) != sigcont

        managed.__exit__(KeyboardInterrupt, KeyboardInterrupt(), None)

        assert_handlers_restored(original_signal_handlers)
