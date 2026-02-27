"""Shared fixtures for improve tests."""

import os
import sys

import pytest

# Make FakeClaudeRunner importable from tests/implement/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))

from fake_claude_runner import FakeClaudeRunner  # noqa: E402


@pytest.fixture
def fake_runner():
    return FakeClaudeRunner()


@pytest.fixture
def fake_renderer():
    """Template renderer that records calls and returns rendered string."""
    calls = []

    def renderer(template_name, variables):
        calls[:]  # keep reference alive
        calls.append((template_name, variables))
        parts = [f"template={template_name}"]
        for key, value in sorted(variables.items()):
            parts.append(f"{key}={value}")
        return " | ".join(parts)

    renderer.calls = calls
    return renderer
