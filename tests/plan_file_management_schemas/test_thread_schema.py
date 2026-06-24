"""Tests for the Thread JSON Schema artifact.

`jsonschema` is not a project dependency (see `pyproject.toml`), so meta-schema
validation is performed via `uvx check-jsonschema --check-metaschema` per the
plan's "no new dependencies" constraint.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
THREAD_SCHEMA_PATH = (
    REPO_ROOT
    / "claude-code-plugins"
    / "idea-to-code"
    / "skills"
    / "plan-file-management"
    / "references"
    / "thread.schema.json"
)


@pytest.mark.unit
def test_schema_file_is_valid() -> None:
    assert THREAD_SCHEMA_PATH.is_file(), f"Schema file not found: {THREAD_SCHEMA_PATH}"

    with THREAD_SCHEMA_PATH.open() as f:
        data = json.load(f)

    assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert data["$id"] == "thread.schema.json"

    result = subprocess.run(
        ["uvx", "check-jsonschema", "--check-metaschema", str(THREAD_SCHEMA_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"check-jsonschema --check-metaschema failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
