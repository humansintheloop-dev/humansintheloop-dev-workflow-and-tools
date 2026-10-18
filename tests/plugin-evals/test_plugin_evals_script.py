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


def _fake_claude_body(claude_args_file, claude_path_file, trace_file):
    aggregate_result = (
        '{"cases":[{"name":"revise-spec","arms":{"with":['
        f'{{"tracePath":"{trace_file}"}},{{"tracePath":"{trace_file}"}}'
        ']}}]}'
    )
    return "\n".join([
        f'echo "$@" > "{claude_args_file}"',
        f'echo "$PATH" > "{claude_path_file}"',
        'while [ $# -gt 0 ]; do [ "$1" = --output-dir ] && output_dir="$2"; shift; done',
        'mkdir -p "$output_dir"',
        f"echo '{aggregate_result}' > \"$output_dir/aggregate-result.json\"",
    ])


def _fake_uv_body(uv_args_file, python_executable):
    return "\n".join([
        f'echo "$@" >> "{uv_args_file}"',
        f'[ "$1 $2" = "python find" ] && echo "{python_executable}"',
        "exit 0",
    ])


def _fake_python_install(tmp_path):
    """Mirror uv's layout: `uv python find` answers through a minor-version symlink."""
    uv_python_dir = tmp_path / "uv-python"
    python_bin = uv_python_dir / "cpython-3.12.12-macos-aarch64-none" / "bin"
    python_bin.mkdir(parents=True)
    _write_fake_command(python_bin, "python3")
    minor_version_link = uv_python_dir / "cpython-3.12-macos-aarch64-none"
    minor_version_link.symlink_to("cpython-3.12.12-macos-aarch64-none")
    return minor_version_link / "bin" / "python3"


@dataclass
class ScriptRun:
    claude_args: list[str]
    claude_path: list[str]
    uv_args: list[str]
    output_dir: Path
    home: Path

    @property
    def eval_i2code_dir(self):
        return self.home / ".cache" / "i2code-plugin-evals"


def _run_script_with_fake_claude(tmp_path, *args):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    claude_args_file = tmp_path / "claude-args"
    claude_path_file = tmp_path / "claude-path"
    uv_args_file = tmp_path / "uv-args"
    trace_file = tmp_path / "trace.jsonl"
    trace_file.write_text('{"type":"assistant"}\n')
    _write_fake_command(bin_dir, "claude", _fake_claude_body(claude_args_file, claude_path_file, trace_file))
    _write_fake_command(bin_dir, "uv", _fake_uv_body(uv_args_file, _fake_python_install(tmp_path)))
    _write_fake_command(bin_dir, "i2code")
    git_dir = tmp_path / "git-bin"
    git_dir.mkdir()
    _write_fake_command(git_dir, "git")
    result = subprocess.run(
        [str(SCRIPT), *args],
        env={**os.environ, "PATH": f"{bin_dir}:/usr/bin:/bin:{git_dir}", "HOME": str(home)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    claude_args = claude_args_file.read_text().split()
    return ScriptRun(
        claude_args=claude_args,
        claude_path=claude_path_file.read_text().strip().split(":"),
        uv_args=uv_args_file.read_text().splitlines(),
        output_dir=Path(_option_value(claude_args, "--output-dir")),
        home=home,
    )


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


@pytest.mark.unit
def test_runs_claude_with_the_eval_i2code_install_first_on_path(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    assert run.claude_path[0] == str(run.eval_i2code_dir)


@pytest.mark.unit
def test_installs_i2code_from_the_working_tree_into_the_eval_venv(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    venv_python = run.eval_i2code_dir / "venv" / "bin" / "python"
    assert f"pip install --python {venv_python} {PROJECT_ROOT}" in run.uv_args


@pytest.mark.unit
def test_eval_i2code_runs_the_venv_i2code_with_a_git_other_than_apples_shim(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    wrapper = (run.eval_i2code_dir / "i2code").read_text()
    assert f"GIT_PYTHON_GIT_EXECUTABLE={tmp_path / 'git-bin' / 'git'}" in wrapper
    assert f'exec "{run.eval_i2code_dir}/venv/bin/i2code" "$@"' in wrapper


@pytest.mark.unit
def test_copies_the_python_install_rather_than_the_symlink_uv_reports(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    python_dir = run.eval_i2code_dir / "python"
    assert not python_dir.is_symlink()
    assert (python_dir / "bin" / "python3").is_file()


@pytest.mark.unit
def test_copies_a_uv_managed_python_rather_than_an_active_venv(tmp_path):
    run = _run_script_with_fake_claude(tmp_path)

    assert "python find --managed-python --system 3.12" in run.uv_args
