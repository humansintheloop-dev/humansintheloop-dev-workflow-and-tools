"""Tests for the Thread JSON Schema artifact.

`jsonschema` is not a project dependency (see `pyproject.toml`), so meta-schema
validation is performed via `uvx check-jsonschema --check-metaschema` per the
plan's "no new dependencies" constraint.

Instance validation also uses `uvx check-jsonschema --schemafile <thread.schema.json>`;
because both schemas share the `references/` directory, the relative
`$ref: "task.schema.json"` inside `thread.schema.json` resolves to the sibling
file automatically.
"""

import copy
import json
import subprocess
from pathlib import Path
from typing import cast

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


KNOWN_GOOD_THREAD: dict[str, object] = {
    "title": "Spring Boot Application with Health Check",
    "introduction": "Stand up the service and confirm it responds to actuator health probes.",
    "tasks": [
        {
            "title": "Add health endpoint",
            "task_type": "OUTCOME",
            "entrypoint": "./gradlew bootRun",
            "observable": "GET /actuator/health returns 200",
            "evidence": "curl -fsS http://localhost:8080/actuator/health",
            "steps": ["Add HealthController", "Wire route", "Add integration test"],
        }
    ],
}


def _validate_thread_instance(
    instance: dict[str, object], tmp_path: Path
) -> subprocess.CompletedProcess[str]:
    instance_path = tmp_path / "thread_instance.json"
    instance_path.write_text(json.dumps(instance))
    return subprocess.run(
        [
            "uvx",
            "check-jsonschema",
            "--schemafile",
            THREAD_SCHEMA_PATH.name,
            str(instance_path),
        ],
        cwd=THREAD_SCHEMA_PATH.parent,
        capture_output=True,
        text=True,
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


@pytest.mark.unit
def test_known_good_thread_validates(tmp_path: Path) -> None:
    result = _validate_thread_instance(KNOWN_GOOD_THREAD, tmp_path)
    assert result.returncode == 0, (
        f"Known-good Thread was rejected by schema:\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.unit
def test_missing_required_field_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = copy.deepcopy(KNOWN_GOOD_THREAD)
    del instance["introduction"]
    result = _validate_thread_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Thread missing required field `introduction` should have been rejected, "
        f"but validation succeeded:\nstdout:\n{result.stdout}"
    )


@pytest.mark.unit
def test_thread_additional_property_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = copy.deepcopy(KNOWN_GOOD_THREAD)
    instance["summary"] = "extra"
    result = _validate_thread_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Thread with extra property `summary` should have been rejected by "
        f"`additionalProperties: false`, but validation succeeded:\n"
        f"stdout:\n{result.stdout}"
    )


@pytest.mark.unit
def test_empty_tasks_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = copy.deepcopy(KNOWN_GOOD_THREAD)
    instance["tasks"] = []
    result = _validate_thread_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Thread with empty `tasks` array should have been rejected by "
        f"`minItems: 1`, but validation succeeded:\nstdout:\n{result.stdout}"
    )


@pytest.mark.unit
def test_invalid_embedded_task_rejected(tmp_path: Path) -> None:
    instance: dict[str, object] = copy.deepcopy(KNOWN_GOOD_THREAD)
    tasks = cast(list[dict[str, object]], instance["tasks"])
    embedded_task = tasks[0]
    del embedded_task["evidence"]
    result = _validate_thread_instance(instance, tmp_path)
    assert result.returncode != 0, (
        "Thread whose embedded task is missing required field `evidence` "
        "should have been rejected via the `$ref` to task.schema.json, "
        f"but validation succeeded:\nstdout:\n{result.stdout}"
    )
