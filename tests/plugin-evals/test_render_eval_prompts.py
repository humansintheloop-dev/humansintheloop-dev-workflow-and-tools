"""Tests for test-scripts/render_eval_prompts.py — renders the eval case prompts."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "test-scripts" / "render_eval_prompts.py"

CASES = ["create-spec", "revise-spec", "create-plan", "revise-plan"]

TEMPLATE_MARKERS = {
    "create-spec": "idea-to-code:write-spec",
    "create-plan": "## Task model",
}

APPENDED_REQUESTS = {
    "revise-spec": "add a non-functional requirement that a full eval run costs at most USD 25.",
    "revise-plan": "adds a README section describing how to run the evals.",
}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("out")
    fixture_tmp = tmp_path_factory.mktemp("fixture-tmp")
    env = {**os.environ, "TMPDIR": str(fixture_tmp)}
    subprocess.run(
        [sys.executable, str(SCRIPT), str(out_dir)],
        check=True, env=env, cwd=PROJECT_ROOT,
    )
    prompts = {case: _read_prompt(out_dir, case) for case in CASES}
    return prompts, fixture_tmp


def _read_prompt(out_dir, case):
    prompt_file = out_dir / case / "prompt.md"
    return prompt_file.read_text() if prompt_file.exists() else None


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
def test_prompt_file_exists(rendered, case):
    prompts, _ = rendered
    assert prompts[case] is not None


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
def test_prompt_uses_workspace_relative_idea_directory(rendered, case):
    prompts, _ = rendered
    assert "docs/ideas/active/eval-idea" in prompts[case]


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
def test_prompt_does_not_contain_fixture_copy_path(rendered, case):
    prompts, fixture_tmp = rendered
    assert str(fixture_tmp) not in prompts[case]
    assert os.path.realpath(fixture_tmp) not in prompts[case]


@pytest.mark.unit
@pytest.mark.parametrize("case", sorted(TEMPLATE_MARKERS))
def test_prompt_contains_template_marker(rendered, case):
    prompts, _ = rendered
    assert TEMPLATE_MARKERS[case] in prompts[case]


@pytest.mark.unit
@pytest.mark.parametrize("case", sorted(APPENDED_REQUESTS))
def test_prompt_ends_with_appended_request(rendered, case):
    prompts, _ = rendered
    assert prompts[case].rstrip().endswith(APPENDED_REQUESTS[case])


@pytest.mark.unit
@pytest.mark.parametrize("case", CASES)
def test_prompt_starts_with_case_frontmatter(rendered, case):
    prompts, _ = rendered
    frontmatter = prompts[case].split("---\n")[1]
    assert prompts[case].startswith("---\n")
    assert "max_turns:" in frontmatter
    assert "allowed_tools:" in frontmatter
