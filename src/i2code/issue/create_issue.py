"""Issue creation logic: parse JSON, render markdown, write file."""

import json
from datetime import datetime, timezone
from pathlib import Path


VALID_CATEGORIES = ("rule-violation", "improvement", "confusion")
REQUIRED_FIELDS = ("description", "category", "analysis", "context", "suggestion")

TEMPLATE = """\
---
id: {id}
created: {created}
status: active
category: {category}
claude_session_id: {session_id}
---

# {description}

{analysis}

{context}

## Suggested improvement

{suggestion}

## Resolution

[Empty - filled when resolved]
"""


def _parse_and_validate(json_str):
    """Parse JSON string and validate required fields and category.

    Returns:
        Parsed dict with validated issue data.

    Raises:
        ValueError: On invalid JSON, missing fields, or invalid category.
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    for field in REQUIRED_FIELDS:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")

    if data["category"] not in VALID_CATEGORIES:
        raise ValueError(
            f"Invalid category '{data['category']}'. "
            f"Must be one of: {', '.join(VALID_CATEGORIES)}"
        )
    return data


def create_issue(json_str, session_id, target_dir):
    """Parse JSON input and write an issue markdown file.

    Args:
        json_str: JSON string with issue fields.
        session_id: Claude session ID (or "unknown").
        target_dir: Path to .hitl/issues/active/ directory.

    Returns:
        Absolute path to the created file.

    Raises:
        ValueError: On invalid input.
        FileNotFoundError: If target_dir does not exist.
    """
    data = _parse_and_validate(json_str)

    target = Path(target_dir)
    if not target.is_dir():
        raise FileNotFoundError(
            ".hitl/issues/active/ not found. Run 'i2code tracking setup' first."
        )

    now = datetime.now(timezone.utc)
    timestamp_id = now.strftime("%Y-%m-%d-%H-%M-%S")
    iso_created = now.isoformat()

    content = TEMPLATE.format(
        id=timestamp_id,
        created=iso_created,
        category=data["category"],
        session_id=session_id,
        description=data["description"],
        analysis=data["analysis"],
        context=data["context"],
        suggestion=data["suggestion"],
    )

    file_path = target / f"{timestamp_id}.md"
    file_path.write_text(content)
    return str(file_path.resolve())
