"""Tests for update_project: validates directories, extracts SHA from CLAUDE.md,
generates git diff, handles first sync (no previous SHA), template variables correct,
Claude invoked interactively."""

import json
import os
import subprocess
import tempfile
from typing import NamedTuple
from unittest.mock import patch

import pytest

from i2code.setup_cmd.update_project import update_project


class _FirstSyncCase(NamedTuple):
    kind: str
    template_name: str
    sha: str
    override: object = None
    expected_token: str = ""


def _create_project_dir(tmpdir, *, claude_md_content=None):
    """Create a project directory, optionally with CLAUDE.md."""
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    if claude_md_content is not None:
        with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
            f.write(claude_md_content)
    return project_dir


def _create_config_dir(tmpdir):
    """Create a config directory."""
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    return config_dir


def _per_file_subprocess_run(repo_root, *, per_file_shas=None, per_file_diffs=None):
    """Mock subprocess.run with per-file SHA/diff control keyed by relpath.

    per_file_shas maps `relpath -> SHA string` for `git log -1 --format=%H -- <relpath>`.
    per_file_diffs maps `relpath -> diff string` for `git diff <prev>..<curr> -- <relpath>`.
    Matching is done by the final argv element (the relpath after `--`).
    """
    per_file_shas = per_file_shas or {}
    per_file_diffs = per_file_diffs or {}

    def mock_run(cmd, capture_output=False, text=False, check=False, cwd=None):
        cmd_str = " ".join(cmd)
        result = subprocess.CompletedProcess(cmd, 0)
        result.stderr = ""
        if "rev-parse --show-toplevel" in cmd_str:
            result.stdout = repo_root + "\n"
        elif "log -1 --format=%H" in cmd_str:
            relpath = cmd[-1]
            result.stdout = per_file_shas.get(relpath, "") + "\n"
        elif "diff" in cmd_str:
            relpath = cmd[-1]
            result.stdout = per_file_diffs.get(relpath, "") + "\n"
        else:
            result.stdout = ""
        return result
    return mock_run


@pytest.mark.unit
class TestValidation:

    def test_raises_when_project_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = _create_config_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_project("/nonexistent/project", config_dir, fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0

    def test_raises_when_config_dir_does_not_exist(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _create_project_dir(tmpdir)
            with pytest.raises(SystemExit):
                update_project(project_dir, "/nonexistent/config", fake_runner, fake_renderer)
        assert len(fake_runner.calls) == 0


_DEFAULT_CURRENT_SHAS = {"claude_md": "CCC333", "settings": "DDD444"}


def _read_settings_allow(project_dir):
    with open(os.path.join(project_dir, ".claude", "settings.local.json")) as f:
        return json.load(f)["permissions"]["allow"]


def _assert_claude_md_marker_advanced(project_dir, sha):
    with open(os.path.join(project_dir, "CLAUDE.md")) as f:
        content = f.read().rstrip("\n")
    assert content.endswith(f"<!-- claude-config-files-sha: {sha} -->")


def _assert_settings_marker_advanced(project_dir, sha):
    sha_entries = [e for e in _read_settings_allow(project_dir)
                   if "i2code-config-files-sha" in e]
    assert sha_entries == [f"Bash(i2code-config-files-sha {sha})"]


def _setup_per_file_project(tmpdir, markers):
    """Create project_dir + config_dir with templates, returning paths and relpaths.

    `markers` is a dict; if it contains `"claude_md"` the project's CLAUDE.md is
    created with that SHA marker, otherwise the file is omitted. Same convention
    for `"settings"` and `.claude/settings.local.json`. The config_dir is always
    populated with both template files. Relpaths are relative to tmpdir (the repo
    root).

    Returns (project_dir, config_dir, claude_md_relpath, settings_relpath).
    """
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    if "claude_md" in markers:
        with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
            f.write(f"# Project\n<!-- claude-config-files-sha: {markers['claude_md']} -->\n")
    if "settings" in markers:
        os.makedirs(os.path.join(project_dir, ".claude"))
        with open(os.path.join(project_dir, ".claude", "settings.local.json"), "w") as f:
            json.dump(
                {"permissions": {"allow": [
                    "Bash(echo:*)",
                    f"Bash(i2code-config-files-sha {markers['settings']})",
                ]}},
                f,
            )

    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    with open(os.path.join(config_dir, "CLAUDE.md"), "w") as f:
        f.write("# Template CLAUDE.md content\n")
    with open(os.path.join(config_dir, "settings.local.json"), "w") as f:
        json.dump({"permissions": {"allow": ["Bash(echo:*)"]}}, f)

    claude_md_relpath = os.path.relpath(os.path.join(config_dir, "CLAUDE.md"), tmpdir)
    settings_relpath = os.path.relpath(
        os.path.join(config_dir, "settings.local.json"), tmpdir,
    )
    return project_dir, config_dir, claude_md_relpath, settings_relpath


def _run_update_with_per_file_mock(tmpdir, fakes, *, markers=None, diffs_by_kind=None):
    """Set up project + mock subprocess + invoke update_project. Returns project_dir.

    `markers` is a dict mapping file-kind ("claude_md", "settings") to its previous
    SHA marker; absent keys mean that project file is not created. `diffs_by_kind`
    maps file-kind to its per-file diff text; absent kinds default to an empty diff.
    """
    fake_runner, fake_renderer = fakes
    markers = markers or {}
    diffs_by_kind = diffs_by_kind or {}
    project_dir, config_dir, claude_md_relpath, settings_relpath = (
        _setup_per_file_project(tmpdir, markers)
    )
    relpath_by_kind = {"claude_md": claude_md_relpath, "settings": settings_relpath}
    per_file_diffs = {relpath_by_kind[k]: d for k, d in diffs_by_kind.items()}
    per_file_shas = {
        relpath_by_kind[k]: sha for k, sha in _DEFAULT_CURRENT_SHAS.items()
    }
    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = _per_file_subprocess_run(
            tmpdir, per_file_shas=per_file_shas, per_file_diffs=per_file_diffs,
        )
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return project_dir


@pytest.mark.unit
class TestMissingFileCopy:

    def _run_missing_claude_md(self, tmpdir, fake_runner, fake_renderer):
        return _run_update_with_per_file_mock(
            tmpdir, (fake_runner, fake_renderer),
            markers={"settings": "BBB222"},
        )

    def _run_missing_settings(self, tmpdir, fake_runner, fake_renderer):
        return _run_update_with_per_file_mock(
            tmpdir, (fake_runner, fake_renderer),
            markers={"claude_md": "CCC333"},
        )

    def test_copies_missing_claude_md_from_template(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_claude_md(tmpdir, fake_runner, fake_renderer)
            with open(os.path.join(project_dir, "CLAUDE.md")) as f:
                assert f.read().startswith("# Template CLAUDE.md content\n")

    def test_writes_claude_md_sha_marker_after_copy(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_claude_md(tmpdir, fake_runner, fake_renderer)
            _assert_claude_md_marker_advanced(project_dir, "CCC333")

    def test_no_claude_invocation_when_claude_md_missing(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._run_missing_claude_md(tmpdir, fake_runner, fake_renderer)
            assert len(fake_runner.calls) == 0

    def test_copies_missing_settings_from_template(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_settings(tmpdir, fake_runner, fake_renderer)
            assert "Bash(echo:*)" in _read_settings_allow(project_dir)

    def test_writes_settings_sha_marker_after_copy(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_settings(tmpdir, fake_runner, fake_renderer)
            _assert_settings_marker_advanced(project_dir, "DDD444")

    def test_creates_claude_directory_if_absent(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = self._run_missing_settings(tmpdir, fake_runner, fake_renderer)
            assert os.path.isdir(os.path.join(project_dir, ".claude"))

    def test_scenario_s6_both_files_missing_no_claude_invocations(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_update_with_per_file_mock(
                tmpdir, (fake_runner, fake_renderer),
            )
            _assert_claude_md_marker_advanced(project_dir, "CCC333")
            _assert_settings_marker_advanced(project_dir, "DDD444")
            assert len(fake_runner.calls) == 0


def _run_capturing_git_calls(tmpdir, fakes, markers):
    """Run update_project with per-file mock subprocess and capture all git calls.

    Returns (captured_cmds, claude_md_relpath, settings_relpath).
    """
    fake_runner, fake_renderer = fakes
    project_dir, config_dir, claude_md_relpath, settings_relpath = (
        _setup_per_file_project(tmpdir, markers)
    )
    per_file_diffs = {claude_md_relpath: "", settings_relpath: ""}
    per_file_shas = {
        claude_md_relpath: _DEFAULT_CURRENT_SHAS["claude_md"],
        settings_relpath: _DEFAULT_CURRENT_SHAS["settings"],
    }
    base_mock = _per_file_subprocess_run(
        tmpdir, per_file_shas=per_file_shas, per_file_diffs=per_file_diffs,
    )
    captured = []

    def tracking(cmd, capture_output=False, text=False, check=False, cwd=None):
        captured.append(cmd)
        return base_mock(
            cmd, capture_output=capture_output, text=text, check=check, cwd=cwd,
        )

    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = tracking
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return captured, claude_md_relpath, settings_relpath


@pytest.mark.unit
class TestPerFileShaReading:

    @pytest.mark.parametrize(
        "case",
        [
            pytest.param((1, "AAA111..CCC333"), id="claude_md"),
            pytest.param((2, "BBB222..DDD444"), id="settings"),
        ],
    )
    def test_reads_previous_sha_from_marker(self, fake_runner, fake_renderer, case):
        relpath_idx, expected_range = case
        with tempfile.TemporaryDirectory() as tmpdir:
            captured_and_relpaths = _run_capturing_git_calls(
                tmpdir, (fake_runner, fake_renderer),
                markers={"claude_md": "AAA111", "settings": "BBB222"},
            )
            captured = captured_and_relpaths[0]
            relpath = captured_and_relpaths[relpath_idx]
            diff_calls = [
                c for c in captured
                if "diff" in " ".join(c) and c[-1] == relpath
            ]
            assert len(diff_calls) == 1
            assert expected_range in " ".join(diff_calls[0])

    def test_per_file_diff_calls_use_per_file_previous_shas(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            captured, claude_md_relpath, settings_relpath = _run_capturing_git_calls(
                tmpdir, (fake_runner, fake_renderer),
                markers={"claude_md": "AAA111", "settings": "BBB222"},
            )
            diff_calls = [c for c in captured if "diff" in " ".join(c)]
            assert len(diff_calls) == 2
            claude_md_diff = next(
                c for c in diff_calls if c[-1] == claude_md_relpath
            )
            settings_diff = next(
                c for c in diff_calls if c[-1] == settings_relpath
            )
            assert "AAA111..CCC333" in " ".join(claude_md_diff)
            assert "BBB222..DDD444" in " ".join(settings_diff)


@pytest.mark.unit
class TestEmptyDiffSkip:

    def test_skips_claude_for_both_files_and_advances_both_markers(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_update_with_per_file_mock(
                tmpdir, (fake_runner, fake_renderer),
                markers={"claude_md": "AAA111", "settings": "BBB222"},
            )
            assert len(fake_runner.calls) == 0
            _assert_claude_md_marker_advanced(project_dir, "CCC333")
            _assert_settings_marker_advanced(project_dir, "DDD444")

    def test_scenario_s4_missing_claude_md_settings_synced(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_update_with_per_file_mock(
                tmpdir, (fake_runner, fake_renderer),
                markers={"settings": "BBB222"},
            )
            assert len(fake_runner.calls) == 0
            _assert_claude_md_marker_advanced(project_dir, "CCC333")
            assert "Bash(i2code-config-files-sha DDD444)" in _read_settings_allow(project_dir)


_DEFAULT_CLAUDE_MD_TEMPLATE = "# Template CLAUDE.md content\n"
_DEFAULT_SETTINGS_TEMPLATE = {"permissions": {"allow": ["Bash(echo:*)"]}}


def _setup_first_sync_project(tmpdir, *, missing_kind, claude_md_template, settings_template):
    """Create project where exactly one file is missing its SHA marker.

    `missing_kind` is "claude_md" or "settings". The non-missing file is created
    with its SHA marker so it routes through the synced (empty-diff) branch.
    """
    project_dir = os.path.join(tmpdir, "my-project")
    os.makedirs(project_dir)
    claude_md_content = "# Project\n"
    if missing_kind != "claude_md":
        claude_md_content += "<!-- claude-config-files-sha: AAA111 -->\n"
    with open(os.path.join(project_dir, "CLAUDE.md"), "w") as f:
        f.write(claude_md_content)
    os.makedirs(os.path.join(project_dir, ".claude"))
    settings_allow = ["Bash(echo:*)"]
    if missing_kind != "settings":
        settings_allow.append("Bash(i2code-config-files-sha BBB222)")
    with open(os.path.join(project_dir, ".claude", "settings.local.json"), "w") as f:
        json.dump({"permissions": {"allow": settings_allow}}, f)
    config_dir = os.path.join(tmpdir, "config-files")
    os.makedirs(config_dir)
    with open(os.path.join(config_dir, "CLAUDE.md"), "w") as f:
        f.write(claude_md_template)
    with open(os.path.join(config_dir, "settings.local.json"), "w") as f:
        json.dump(settings_template, f)
    claude_md_relpath = os.path.relpath(os.path.join(config_dir, "CLAUDE.md"), tmpdir)
    settings_relpath = os.path.relpath(os.path.join(config_dir, "settings.local.json"), tmpdir)
    return project_dir, config_dir, claude_md_relpath, settings_relpath


def _run_first_sync(tmpdir, fakes, *, missing_kind, template_override=None):
    """Set up a first-sync scenario for `missing_kind` and call update_project.

    `template_override`, if set, replaces the source template content for the
    missing file (str for CLAUDE.md, dict for settings).
    """
    fake_runner, fake_renderer = fakes
    claude_md_template = _DEFAULT_CLAUDE_MD_TEMPLATE
    settings_template = _DEFAULT_SETTINGS_TEMPLATE
    if template_override is not None:
        if missing_kind == "claude_md":
            claude_md_template = template_override
        else:
            settings_template = template_override
    project_dir, config_dir, claude_md_relpath, settings_relpath = (
        _setup_first_sync_project(
            tmpdir, missing_kind=missing_kind,
            claude_md_template=claude_md_template,
            settings_template=settings_template,
        )
    )
    synced_relpath = settings_relpath if missing_kind == "claude_md" else claude_md_relpath
    per_file_shas = {
        claude_md_relpath: _DEFAULT_CURRENT_SHAS["claude_md"],
        settings_relpath: _DEFAULT_CURRENT_SHAS["settings"],
    }
    with patch("i2code.setup_cmd.update_project.subprocess") as mock_sub:
        mock_sub.run = _per_file_subprocess_run(
            tmpdir, per_file_shas=per_file_shas, per_file_diffs={synced_relpath: ""},
        )
        update_project(project_dir, config_dir, fake_runner, fake_renderer)
    return project_dir


def _find_render_call(fake_renderer, template_name):
    matches = [c for c in fake_renderer.calls if c[0] == template_name]
    assert len(matches) == 1
    return matches[0]


_FIRST_SYNC_CASES = [
    pytest.param(
        _FirstSyncCase(
            kind="claude_md", template_name="update-project-claude-md.md", sha="CCC333",
            override="Hello template body", expected_token="Hello template body",
        ),
        id="claude_md",
    ),
    pytest.param(
        _FirstSyncCase(
            kind="settings", template_name="update-project-settings.md", sha="DDD444",
            override={"permissions": {"allow": ["Bash(unique-marker:*)"]}},
            expected_token="Bash(unique-marker:*)",
        ),
        id="settings",
    ),
]


def _assert_marker_advanced(kind, project_dir, sha):
    if kind == "claude_md":
        _assert_claude_md_marker_advanced(project_dir, sha)
    else:
        _assert_settings_marker_advanced(project_dir, sha)


@pytest.mark.unit
class TestFirstSync:

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_renders_first_sync_prompt(self, fake_runner, fake_renderer, case):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_first_sync(tmpdir, (fake_runner, fake_renderer), missing_kind=case.kind)
            _, variables = _find_render_call(fake_renderer, case.template_name)
            assert variables["IS_FIRST_SYNC"] == "true"
            assert variables["PREVIOUS_SHA"] == ""

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_first_sync_prompt_contains_full_template_content(
        self, fake_runner, fake_renderer, case,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_first_sync(
                tmpdir, (fake_runner, fake_renderer),
                missing_kind=case.kind, template_override=case.override,
            )
            _, variables = _find_render_call(fake_renderer, case.template_name)
            assert case.expected_token in variables["CONFIG_DIFF"]
            assert "first sync" in variables["CONFIG_DIFF"].lower()

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_first_sync_invokes_claude(self, fake_runner, fake_renderer, case):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_first_sync(
                tmpdir, (fake_runner, fake_renderer), missing_kind=case.kind,
            )
            method, cmd, cwd = fake_runner.calls[0]
            assert method == "run_interactive"
            assert cmd[0] == "claude"
            assert cwd == project_dir

    @pytest.mark.parametrize("case", _FIRST_SYNC_CASES)
    def test_python_writes_sha_after_claude_success(
        self, fake_runner, fake_renderer, case,
    ):
        from i2code.implement.claude_runner import ClaudeResult
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner.set_result(ClaudeResult(returncode=0))
            project_dir = _run_first_sync(
                tmpdir, (fake_runner, fake_renderer), missing_kind=case.kind,
            )
            _assert_marker_advanced(case.kind, project_dir, case.sha)


_S1_MARKERS = {"claude_md": "AAA111", "settings": "BBB222"}
_S1_DIFFS = {"claude_md": "diff-for-claude-md", "settings": "diff-for-settings"}


def _run_routine_update(tmpdir, fakes, *, diffs_by_kind=None):
    """Run scenario S-1: both markers present, custom per-file diffs."""
    return _run_update_with_per_file_mock(
        tmpdir, fakes,
        markers=_S1_MARKERS,
        diffs_by_kind=diffs_by_kind if diffs_by_kind is not None else _S1_DIFFS,
    )


@pytest.mark.unit
class TestRoutineUpdate:

    def test_two_renders_in_claude_md_then_settings_order(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            assert [call[0] for call in fake_renderer.calls] == [
                "update-project-claude-md.md",
                "update-project-settings.md",
            ]

    def test_each_render_has_per_file_diff_and_shas(
        self, fake_runner, fake_renderer,
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            claude_vars = fake_renderer.calls[0][1]
            assert claude_vars["IS_FIRST_SYNC"] == "false"
            assert claude_vars["PREVIOUS_SHA"] == "AAA111"
            assert claude_vars["CURRENT_SHA"] == "CCC333"
            assert claude_vars["CONFIG_DIFF"] == "diff-for-claude-md"
            settings_vars = fake_renderer.calls[1][1]
            assert settings_vars["IS_FIRST_SYNC"] == "false"
            assert settings_vars["PREVIOUS_SHA"] == "BBB222"
            assert settings_vars["CURRENT_SHA"] == "DDD444"
            assert settings_vars["CONFIG_DIFF"] == "diff-for-settings"

    def test_two_claude_invocations_in_order(self, fake_runner, fake_renderer):
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            assert len(fake_runner.calls) == 2
            for method, _, cwd in fake_runner.calls:
                assert method == "run_interactive"
                assert cwd == project_dir
            assert "template=update-project-claude-md.md" in fake_runner.calls[0][1][1]
            assert "template=update-project-settings.md" in fake_runner.calls[1][1][1]

    def test_scenario_s1_both_markers_advanced(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner.set_results([
                ClaudeResult(returncode=0), ClaudeResult(returncode=0),
            ])
            project_dir = _run_routine_update(tmpdir, (fake_runner, fake_renderer))
            _assert_claude_md_marker_advanced(project_dir, "CCC333")
            _assert_settings_marker_advanced(project_dir, "DDD444")

    def test_scenario_s2_only_claude_md_changed(self, fake_runner, fake_renderer):
        from i2code.implement.claude_runner import ClaudeResult
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_runner.set_result(ClaudeResult(returncode=0))
            project_dir = _run_update_with_per_file_mock(
                tmpdir, (fake_runner, fake_renderer),
                markers=_S1_MARKERS,
                diffs_by_kind={"claude_md": "diff-for-claude-md"},
            )
            assert len(fake_runner.calls) == 1
            assert "template=update-project-claude-md.md" in fake_runner.calls[0][1][1]
            _assert_claude_md_marker_advanced(project_dir, "CCC333")
            _assert_settings_marker_advanced(project_dir, "DDD444")
