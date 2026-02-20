import signal
import subprocess
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

    def __enter__(self) -> "ManagedSubprocess":
        self._original_sigtstp = signal.getsignal(signal.SIGTSTP)
        self._original_sigcont = signal.getsignal(signal.SIGCONT)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        signal.signal(signal.SIGTSTP, self._original_sigtstp)
        signal.signal(signal.SIGCONT, self._original_sigcont)
        return False
