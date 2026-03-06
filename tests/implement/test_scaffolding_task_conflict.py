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

from i2code.implement.claude_permissions import ensure_claude_permissions
from i2code.implement.command_builder import CommandBuilder, TaskCommandOpts
from i2code.implement.claude_runner import ClaudeRunner, print_task_failure_diagnostics
from i2code.implement.idea_project import IdeaProject
from i2code.implement.project_scaffolding import ScaffoldingCreator

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "hello-world")


@pytest.mark.manual
@pytest.mark.xfail(
    strict=True,
    reason="Bug: scaffolding creates ci.yaml but task creates ci.yml",
)
def test_scaffolding_task_conflict_creates_duplicate_ci_files(tmp_path):
    """Reproduce bug: scaffolding and task execution create conflicting CI files."""
    print(f"\ntmp_path: {tmp_path}")
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

    config_dir = os.path.join(os.path.dirname(__file__), "..", "..", "config-files")
    shutil.copy2(os.path.join(config_dir, "CLAUDE.md"), tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(exist_ok=True)
    shutil.copy2(os.path.join(config_dir, "settings.local.json"), claude_dir)
    ensure_claude_permissions(str(tmp_path))

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

    # Task 1.3: Execute first plan task and assert the conflict
    idea_project = IdeaProject(str(idea_dir))
    task = idea_project.get_next_task()
    assert task is not None, "Expected at least one uncompleted task in the plan"

    task_cmd = command_builder.build_task_command(
        str(idea_dir), task.print(), TaskCommandOpts(
            interactive=False,
            extra_cli_args=["--allowed-tools", "Bash(rm:*)"],
        ),
    )
    head_before = repo.head.commit.hexsha
    task_result = claude_runner.run(task_cmd, cwd=str(tmp_path))
    head_after = repo.head.commit.hexsha
    print_task_failure_diagnostics(task_result, head_before, head_after)

    # Bug: ci.yml should NOT exist if scaffolding and task coordinate on naming.
    # The task creates ci.yml alongside scaffolding's ci.yaml.
    assert not ci_yml.exists(), (
        f"Bug reproduced: both ci.yaml and ci.yml exist in {workflows_dir}"
    )
