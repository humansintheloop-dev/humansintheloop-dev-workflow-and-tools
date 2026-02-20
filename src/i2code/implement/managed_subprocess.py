import os
import signal
import subprocess
import sys
import threading
from typing import List, Optional


class ManagedSubprocess:
    """Context manager for subprocess lifecycle with Ctrl+C and Ctrl+Z handling.

    The child process must be started with start_new_session=True so that
    signals can be explicitly forwarded to its process group.
    """

    def __init__(
        self,
        process: subprocess.Popen,
        label: str,
        threads: Optional[List[threading.Thread]] = None,
        terminate_timeout: float = 5.0,
    ):
        self.process = process
        self.label = label
        self.threads = threads or []
        self.terminate_timeout = terminate_timeout
        self.interrupted = False
        self._original_sigtstp = None
        self._original_sigcont = None

    def _handle_sigtstp(self, signum, frame):
        os.killpg(self.process.pid, signal.SIGTSTP)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTSTP)

    def _handle_sigcont(self, signum, frame):
        os.killpg(self.process.pid, signal.SIGCONT)
        signal.signal(signal.SIGTSTP, self._handle_sigtstp)

    def __enter__(self) -> "ManagedSubprocess":
        self._original_sigtstp = signal.getsignal(signal.SIGTSTP)
        self._original_sigcont = signal.getsignal(signal.SIGCONT)
        signal.signal(signal.SIGTSTP, self._handle_sigtstp)
        signal.signal(signal.SIGCONT, self._handle_sigcont)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        try:
            if exc_type is KeyboardInterrupt:
                return self._handle_interrupt()
            return False
        finally:
            signal.signal(signal.SIGTSTP, self._original_sigtstp)
            signal.signal(signal.SIGCONT, self._original_sigcont)

    def _handle_interrupt(self) -> bool:
        print(
            f"\nInterrupted. Terminating {self.label} process...",
            file=sys.stderr,
        )
        self.process.terminate()
        try:
            self.process.wait(timeout=self.terminate_timeout)
        except subprocess.TimeoutExpired:
            print(
                f"Force-killing {self.label} process...",
                file=sys.stderr,
            )
            self.process.kill()
            self.process.wait()
        for thread in self.threads:
            thread.join(timeout=self.terminate_timeout)
        print("Done.", file=sys.stderr)
        self.interrupted = True
        return True
