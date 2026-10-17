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


def _write_fake_command(bin_dir, name, body="exit 0"):
    command = bin_dir / name
    command.write_text(f"#!/bin/sh\n{body}\n")
    command.chmod(0o755)


def _run_script_with_fake_claude(tmp_path, *args):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude_args_file = tmp_path / "claude-args"
    _write_fake_command(bin_dir, "claude", f'echo "$@" > "{claude_args_file}"')
    for name in ["uv", "i2code", "jq"]:
        _write_fake_command(bin_dir, name)
    result = subprocess.run(
        [str(SCRIPT), *args],
        env={**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return claude_args_file.read_text().split()


def _option_value(claude_args, option):
    return claude_args[claude_args.index(option) + 1]


@pytest.mark.unit
def test_runs_four_eval_sessions_at_once(tmp_path):
    claude_args = _run_script_with_fake_claude(tmp_path)

    assert _option_value(claude_args, "--concurrency") == "4"


@pytest.mark.unit
def test_runs_every_case_when_no_case_is_named(tmp_path):
    claude_args = _run_script_with_fake_claude(tmp_path)

    assert "--case" not in claude_args


@pytest.mark.unit
def test_runs_only_the_named_case(tmp_path):
    claude_args = _run_script_with_fake_claude(tmp_path, "--case", "revise-spec")

    assert _option_value(claude_args, "--case") == "revise-spec"
