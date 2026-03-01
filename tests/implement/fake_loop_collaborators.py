"""Fake loop collaborators for WorktreeMode tests.

Shared test doubles for review processors, build fixers, and commit recovery
used across multiple test files.
"""


class SequentialReviewProcessor:
    """Fake review processor that returns values from a pre-configured sequence."""

    def __init__(self, results, call_log=None):
        self._results = list(results)
        self._index = 0
        self.call_count = 0
        self._call_log = call_log

    def process_feedback(self):
        self.call_count += 1
        if self._call_log is not None:
            self._call_log.append("process_feedback")
        if self._index < len(self._results):
            result = self._results[self._index]
            self._index += 1
            return result
        return False


class SequentialBuildFixer:
    """Fake build fixer that returns values from a pre-configured sequence."""

    def __init__(self, results, call_log=None):
        self._results = list(results)
        self._index = 0
        self.call_count = 0
        self._call_log = call_log

    def check_and_fix_ci(self):
        self.call_count += 1
        if self._call_log is not None:
            self._call_log.append("check_and_fix_ci")
        if self._index < len(self._results):
            result = self._results[self._index]
            self._index += 1
            return result
        return False


class NoOpBuildFixer:
    def check_and_fix_ci(self):
        return False


class NoOpCommitRecovery:
    def commit_if_needed(self):
        pass
