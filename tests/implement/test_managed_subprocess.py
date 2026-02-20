import signal
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
