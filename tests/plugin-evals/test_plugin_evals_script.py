"""Tests for test-scripts/test-plugin-evals.sh — runs the skill-based plugin eval suite."""

import os
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "test-scripts" / "test-plugin-evals.sh"


@pytest.mark.unit
def test_exits_1_naming_the_commands_missing_from_path():
    result = subprocess.run(
        [str(SCRIPT)],
        env={**os.environ, "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "required command 'claude' is not on PATH" in result.stderr
    assert "required command 'i2code' is not on PATH" in result.stderr
