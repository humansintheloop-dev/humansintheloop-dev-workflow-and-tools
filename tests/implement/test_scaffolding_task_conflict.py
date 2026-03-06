"""Test that reproduces the scaffolding-task CI file conflict bug.

Scaffolding creates .github/workflows/ci.yaml, but the first plan task
creates .github/workflows/ci.yml — a different extension. This test
reproduces that conflict using real Claude in non-interactive mode.

Usage:
    uv run pytest tests/implement/test_scaffolding_task_conflict.py -m manual -v
"""

import json
import os
import shutil

import pytest
from git import Repo

from i2code.implement.command_builder import CommandBuilder
from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.project_scaffolding import ScaffoldingCreator

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

    # Task 1.2: Run scaffolding phase and assert ci.yaml is created
    # Unset CLAUDECODE to allow launching a nested Claude session from tests
    os.environ.pop("CLAUDECODE", None)

    # Grant the nested Claude session permissions to write files and run git
    claude_settings_dir = tmp_path / ".claude"
    claude_settings_dir.mkdir()
    settings = {
        "permissions": {
            "allow": [
                "Bash(chmod:*)",
                "Bash(git add:*)",
                "Bash(git commit:*)",
                "Bash(git status:*)",
                "Bash(gradle wrapper:*)",
                "Bash(gradle --version)",
                "Bash(mkdir:*)",
                "Bash(mkdir -p:*)",
            ],
            "deny": [],
        }
    }
    (claude_settings_dir / "settings.local.json").write_text(json.dumps(settings))

    command_builder = CommandBuilder()
    claude_runner = ClaudeRunner(interactive=False)
    scaffolding_creator = ScaffoldingCreator(command_builder, claude_runner)

    scaffolding_creator.run_scaffolding(
        str(idea_dir), cwd=str(tmp_path), interactive=False,
    )

    workflows_dir = tmp_path / ".github" / "workflows"
    ci_yaml = workflows_dir / "ci.yaml"
    ci_yml = workflows_dir / "ci.yml"
    assert ci_yaml.exists() or ci_yml.exists(), (
        f"Expected ci.yaml or ci.yml in {workflows_dir}"
    )
