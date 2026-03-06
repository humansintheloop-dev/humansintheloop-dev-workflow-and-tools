"""Test that reproduces the scaffolding-task CI file conflict bug.

Scaffolding creates .github/workflows/ci.yaml, but the first plan task
creates .github/workflows/ci.yml — a different extension. This test
reproduces that conflict using real Claude in non-interactive mode.

Usage:
    uv run pytest tests/implement/test_scaffolding_task_conflict.py -m manual -v
"""

import os
import shutil

import pytest
from git import Repo

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "hello-world")


@pytest.mark.manual
def test_scaffolding_task_conflict_creates_duplicate_ci_files(tmp_path):
    """Reproduce bug: scaffolding and task execution create conflicting CI files."""
    # Set up temp git repo with hello-world idea fixtures
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    repo.config_writer().set_value("user", "name", "Test").release()

    idea_dir = tmp_path / "docs" / "features" / "hello-world"
    idea_dir.mkdir(parents=True)
    for filename in os.listdir(FIXTURES_DIR):
        shutil.copy2(os.path.join(FIXTURES_DIR, filename), idea_dir / filename)

    repo.index.add([str(p.relative_to(tmp_path)) for p in idea_dir.iterdir()])
    repo.index.commit("Add hello-world idea files")

    assert (idea_dir / "hello-world-idea.txt").exists()
    assert (idea_dir / "hello-world-plan.md").exists()
