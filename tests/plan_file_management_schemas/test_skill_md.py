"""Tests for the `## Schemas` section in the `plan-file-management` SKILL.md.

The schemas added in Steel Threads 2 and 3 are only useful if a Claude session
reading SKILL.md top-to-bottom discovers them before any command that consumes
JSON. The discoverability requirement is the `## Schemas` section inserted
before `## fix-numbering`; these tests pin its location, its links to the two
schema files, and its clarifying note that `--tasks` / `--tasks-file` accept
the *array* of Task objects (not a full Thread object).
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_MD_PATH = (
    REPO_ROOT
    / "claude-code-plugins"
    / "idea-to-code"
    / "skills"
    / "plan-file-management"
    / "SKILL.md"
)


@pytest.mark.unit
def test_schemas_section_present_before_fix_numbering() -> None:
    assert SKILL_MD_PATH.is_file(), f"SKILL.md not found: {SKILL_MD_PATH}"

    lines = SKILL_MD_PATH.read_text().splitlines()

    schemas_indices = [i for i, line in enumerate(lines) if line == "## Schemas"]
    fix_numbering_indices = [
        i for i, line in enumerate(lines) if line == "## fix-numbering"
    ]

    assert schemas_indices, "`## Schemas` heading not found in SKILL.md"
    assert fix_numbering_indices, "`## fix-numbering` heading not found in SKILL.md"

    assert schemas_indices[0] < fix_numbering_indices[0], (
        f"`## Schemas` (line {schemas_indices[0]}) must appear before "
        f"`## fix-numbering` (line {fix_numbering_indices[0]})"
    )


@pytest.mark.unit
def test_schemas_section_links_both_files() -> None:
    content = SKILL_MD_PATH.read_text()

    assert "[references/task.schema.json](references/task.schema.json)" in content, (
        "SKILL.md must contain a markdown link "
        "`[references/task.schema.json](references/task.schema.json)`"
    )
    assert (
        "[references/thread.schema.json](references/thread.schema.json)" in content
    ), (
        "SKILL.md must contain a markdown link "
        "`[references/thread.schema.json](references/thread.schema.json)`"
    )


@pytest.mark.unit
def test_schemas_section_clarifies_tasks_file_is_array() -> None:
    content = SKILL_MD_PATH.read_text()

    assert "tasks[]" in content, (
        "SKILL.md must reference the `tasks[]` array shape to clarify that "
        "`--tasks` / `--tasks-file` accept the array, not a full Thread object"
    )
    assert "array" in content, (
        "SKILL.md must include the word `array` to clarify the JSON shape "
        "accepted by `--tasks` / `--tasks-file`"
    )

    tasks_idx = content.index("tasks[]")
    array_idx = content.index("array")
    assert abs(tasks_idx - array_idx) < 400, (
        "`tasks[]` and `array` must appear in close proximity (same sentence "
        "or paragraph) so the clarification is unambiguous"
    )
