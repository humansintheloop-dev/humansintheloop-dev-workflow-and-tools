"""Tests for the Task JSON Schema artifact.

`jsonschema` is not a project dependency (see `pyproject.toml`), so meta-schema
validation is performed via `uvx check-jsonschema --check-metaschema` per the
plan's "no new dependencies" constraint.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_SCHEMA_PATH = (
    REPO_ROOT
    / "claude-code-plugins"
    / "idea-to-code"
    / "skills"
    / "plan-file-management"
    / "references"
    / "task.schema.json"
)


KNOWN_GOOD_TASK: dict[str, object] = {
    "title": "Add health endpoint",
    "task_type": "OUTCOME",
    "entrypoint": "./gradlew bootRun",
    "observable": 'GET /actuator/health returns 200 with {"status":"UP"}',
    "evidence": "curl -fsS http://localhost:8080/actuator/health",
    "steps": ["Add HealthController", "Wire route", "Add integration test"],
}


def _validate_task_instance(
    instance: dict[str, object], tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    instance_path = tmp_path / "task_instance.json"
    instance_path.write_text(json.dumps(instance))
    return subprocess.run(
        [
            "uvx",
            "check-jsonschema",
            "--schemafile",
            str(TASK_SCHEMA_PATH),
            str(instance_path),
        ],
        capture_output=True,
        text=True,
    )


@pytest.mark.unit
def test_schema_file_is_valid() -> None:
    assert TASK_SCHEMA_PATH.is_file(), f"Schema file not found: {TASK_SCHEMA_PATH}"

    with TASK_SCHEMA_PATH.open() as f:
        data = json.load(f)

    assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert data["$id"] == "task.schema.json"

    result = subprocess.run(
        ["uvx", "check-jsonschema", "--check-metaschema", str(TASK_SCHEMA_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"check-jsonschema --check-metaschema failed:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.unit
def test_known_good_task_validates(tmp_path: Path) -> None:
    result = _validate_task_instance(KNOWN_GOOD_TASK, tmp_path)
    assert result.returncode == 0, (
        f"Known-good Task was rejected by schema:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.unit
def test_missing_required_field_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = dict(KNOWN_GOOD_TASK)
    del instance["evidence"]
    result = _validate_task_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Task missing required field `evidence` should have been rejected, "
        f"but validation succeeded:\nstdout:\n{result.stdout}"
    )


@pytest.mark.unit
def test_additional_property_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = dict(KNOWN_GOOD_TASK)
    instance["description"] = "extra"
    result = _validate_task_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Task with extra property `description` should have been rejected by "
        f"`additionalProperties: false`, but validation succeeded:\n"
        f"stdout:\n{result.stdout}"
    )


@pytest.mark.unit
def test_empty_steps_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = dict(KNOWN_GOOD_TASK)
    instance["steps"] = []
    result = _validate_task_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Task with empty `steps` array should have been rejected by "
        f"`minItems: 1`, but validation succeeded:\nstdout:\n{result.stdout}"
    )


@pytest.mark.unit
def test_refactor_task_type_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = dict(KNOWN_GOOD_TASK)
    instance["task_type"] = "REFACTOR"
    result = _validate_task_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Task with `task_type: REFACTOR` should have been rejected by the "
        f"`enum: [INFRA, OUTCOME]` constraint, but validation succeeded:\n"
        f"stdout:\n{result.stdout}"
    )
