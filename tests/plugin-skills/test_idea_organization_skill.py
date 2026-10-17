"""Checks that the idea-organization skill's file table matches IdeaProject's file properties."""

import re
from pathlib import Path

import pytest

from i2code.implement.idea_project import IdeaProject

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_FILE = PROJECT_ROOT / "claude-code-plugins" / "idea-to-code" / "skills" / "idea-organization" / "SKILL.md"


def idea_files_table_rows(skill_text: str) -> list[str]:
    section = skill_text.split("## Idea files", 1)[1]
    rows = []
    for line in section.splitlines()[1:]:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            rows.append(line)
    return rows[2:]


def skill_table_suffixes() -> set[str]:
    rows = idea_files_table_rows(SKILL_FILE.read_text())
    file_cells = [row.split("|")[1] for row in rows]
    return {re.search(r"<name>-([^`\s]+)", cell).group(1) for cell in file_cells}


def idea_project_suffixes() -> set[str]:
    project = IdeaProject("/tmp/x/x")
    file_properties = [name for name in dir(IdeaProject) if name.endswith("_file")]
    suffixes = {Path(getattr(project, name)).name.removeprefix("x-") for name in file_properties}
    return {"idea.md" if suffix.startswith("idea.") else suffix for suffix in suffixes}


@pytest.mark.unit
def test_idea_files_table_lists_every_idea_project_file_property():
    table = skill_table_suffixes()
    properties = idea_project_suffixes()

    assert table == properties, (
        f"missing from skill table: {sorted(properties - table)}; "
        f"not an IdeaProject property: {sorted(table - properties)}"
    )
