"""Tests for test-scripts/test-plugin-evals.sh — runs the skill-based plugin eval suite."""

import os
import subprocess
from dataclasses import dataclass
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


def _fake_claude_body(claude_args_file, trace_file):
    aggregate_result = (
        '{"cases":[{"name":"revise-spec","arms":{"with":['
        f'{{"tracePath":"{trace_file}"}},{{"tracePath":"{trace_file}"}}'
        ']}}]}'
    )
    return "\n".join([
        f'echo "$@" > "{claude_args_file}"',
        'while [ $# -gt 0 ]; do [ "$1" = --output-dir ] && output_dir="$2"; shift; done',
        'mkdir -p "$output_dir"',
        f"echo '{aggregate_result}' > \"$output_dir/aggregate-result.json\"",
    ])


@dataclass
class ScriptRun:
    claude_args: list[str]
    output_dir: Path


def _run_script_with_fake_claude(tmp_path, *args):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    claude_args_file = tmp_path / "claude-args"
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text('{"type":"assistant"}\n')
    _write_fake_command(bin_dir, "claude", _fake_claude_body(claude_args_file, trace_file))
    for name in ["uv", "i2code"]:
        _write_fake_command(bin_dir, name)
    result = subprocess.run(
        [str(SCRIPT), *args],
        env={**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    claude_args = claude_args_file.read_text().split()
    return ScriptRun(claude_args, Path(_option_value(claude_args, "--output-dir")))


def _option_value(claude_args, option):
    return claude_args[claude_args.index(option) + 1]


@pytest.mark.unit
def test_runs_four_eval_sessions_at_once(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    assert _option_value(run.claude_args, "--concurrency") == "4"


@pytest.mark.unit
def test_runs_every_case_when_no_case_is_named(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    assert "--case" not in run.claude_args


@pytest.mark.unit
def test_runs_only_the_named_case(tmp_path):
    run = _run_script_with_fake_claude(tmp_path, "--case", "revise-spec")

    assert _option_value(run.claude_args, "--case") == "revise-spec"


@pytest.mark.unit
def test_keeps_eval_workspaces(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    assert "--keep-temp" in run.claude_args


@pytest.mark.unit
def test_copies_each_run_trace_next_to_the_results(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    traces = sorted(path.name for path in (run.output_dir / "traces").iterdir())
    assert traces == ["revise-spec-1.jsonl", "revise-spec-2.jsonl"]
    assert (run.output_dir / "traces" / "revise-spec-1.jsonl").read_text() == '{"type":"assistant"}\n'
