"""FakeClaudeRunner: test double for ClaudeRunner.

Separated into its own module so tests can import it unambiguously
regardless of pytest's conftest resolution order.
"""

from i2code.implement.claude_runner import ClaudeResult


class FakeClaudeRunner:
    """Test double for ClaudeRunner that returns canned ClaudeResult values.

    Usage:
        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=0))
        result = fake.run(["claude", "do task"], cwd="/repo")
        assert result.returncode == 0
        assert fake.calls == [("run", ["claude", "do task"], "/repo")]
    """

    def __init__(self, interactive: bool = True):
        self._interactive = interactive
        self._results = []
        self._default_result = ClaudeResult(returncode=0)
        self._side_effects = []
        self.calls = []

    def set_result(self, result):
        """Set a single result to return for the next call."""
        self._results = [result]

    def set_results(self, results):
        """Set a sequence of results to return for successive calls."""
        self._results = list(results)

    def set_side_effect(self, fn):
        """Set a single side-effect callback for the next call."""
        self._side_effects = [fn]

    def set_side_effects(self, fns):
        """Set side-effect callbacks for successive calls."""
        self._side_effects = list(fns)

    def _next_result(self):
        if self._side_effects:
            self._side_effects.pop(0)()
        if self._results:
            return self._results.pop(0)
        return self._default_result

    def run(self, cmd, cwd):
        self.calls.append(("run", cmd, cwd))
        return self._next_result()

    def run_interactive(self, cmd, cwd):
        self.calls.append(("run_interactive", cmd, cwd))
        return self._next_result()

    def run_batch(self, cmd, cwd):
        self.calls.append(("run_batch", cmd, cwd))
        return self._next_result()
