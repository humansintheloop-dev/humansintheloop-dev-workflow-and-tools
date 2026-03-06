"""Test that reproduces the scaffolding-task CI file conflict bug.

Scaffolding creates .github/workflows/ci.yaml, but the first plan task
creates .github/workflows/ci.yml — a different extension. This test
reproduces that conflict using real Claude in non-interactive mode.

Usage:
    uv run pytest tests/implement/test_scaffolding_task_conflict.py -m manual -v
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from git import Repo

from i2code.implement.claude_permissions import ensure_claude_permissions
from i2code.implement.command_builder import CommandBuilder, TaskCommandOpts
from i2code.implement.claude_runner import ClaudeRunner, print_task_failure_diagnostics
from i2code.implement.idea_project import IdeaProject
from i2code.implement.project_scaffolding import ScaffoldingCreator

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "hello-world")
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config-files")


@dataclass
class TestProject:
    tmp_path: Path
    repo: Repo
    idea_dir: Path
    command_builder: CommandBuilder
    claude_runner: ClaudeRunner

    @property
    def workflows_dir(self) -> Path:
        return self.tmp_path / ".github" / "workflows"

    @property
    def ci_yaml(self) -> Path:
        return self.workflows_dir / "ci.yaml"

    @property
    def ci_yml(self) -> Path:
        return self.workflows_dir / "ci.yml"


@pytest.mark.manual
def test_scaffolding_task_conflict_creates_duplicate_ci_files(tmp_path):
    """Reproduce bug: scaffolding and task execution create conflicting CI files."""
    print(f"\ntmp_path: {tmp_path}")

    project = _create_test_project(tmp_path)
    _run_scaffolding(project)

    scaffolding_used_yaml = project.ci_yaml.exists()
    scaffolding_used_yml = project.ci_yml.exists()
    assert scaffolding_used_yaml or scaffolding_used_yml, (
        f"Expected ci.yaml or ci.yml in {project.workflows_dir}"
    )

    _run_first_task(project)

    if scaffolding_used_yaml:
        assert not project.ci_yml.exists(), (
            f"Task created ci.yml but scaffolding created ci.yaml in {project.workflows_dir}"
        )
    else:
        assert not project.ci_yaml.exists(), (
            f"Task created ci.yaml but scaffolding created ci.yml in {project.workflows_dir}"
        )


def _create_test_project(tmp_path: Path) -> TestProject:
    repo = Repo.init(tmp_path)
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    repo.config_writer().set_value("user", "name", "Test").release()

    idea_dir = tmp_path / "docs" / "features" / "hello-world"
    idea_dir.mkdir(parents=True)
    for filename in os.listdir(FIXTURES_DIR):
        shutil.copy2(os.path.join(FIXTURES_DIR, filename), idea_dir / filename)

    repo.index.add([str(p.relative_to(tmp_path)) for p in idea_dir.iterdir()])
    repo.index.commit("Add hello-world idea files")

    os.environ.pop("CLAUDECODE", None)
    shutil.copy2(os.path.join(CONFIG_DIR, "CLAUDE.md"), tmp_path)
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir(exist_ok=True)
    shutil.copy2(os.path.join(CONFIG_DIR, "settings.local.json"), claude_dir)
    ensure_claude_permissions(str(tmp_path))

    return TestProject(
        tmp_path=tmp_path,
        repo=repo,
        idea_dir=idea_dir,
        command_builder=CommandBuilder(),
        claude_runner=ClaudeRunner(interactive=False),
    )


def _run_scaffolding(project: TestProject):
    scaffolding_creator = ScaffoldingCreator(project.command_builder, project.claude_runner)
    scaffolding_creator.run_scaffolding(
        str(project.idea_dir), cwd=str(project.tmp_path), interactive=False,
    )


def _run_first_task(project: TestProject):
    idea_project = IdeaProject(str(project.idea_dir))
    task = idea_project.get_next_task()
    assert task is not None, "Expected at least one uncompleted task in the plan"

    task_cmd = project.command_builder.build_task_command(
        str(project.idea_dir), task.print(), TaskCommandOpts(
            interactive=False,
            extra_cli_args=["--allowed-tools", "Bash(rm:*)"],
        ),
    )
    head_before = project.repo.head.commit.hexsha
    task_result = project.claude_runner.run(task_cmd, cwd=str(project.tmp_path))
    head_after = project.repo.head.commit.hexsha
    print_task_failure_diagnostics(task_result, head_before, head_after)
    _print_recent_commits(project.repo)


def _print_recent_commits(repo: Repo):
    for commit in list(repo.iter_commits(max_count=2)):
        print(f"\n{commit.hexsha[:7]} {commit.message.strip()}")
        parent = commit.parents[0] if commit.parents else None
        diffs = parent.diff(commit) if parent else commit.diff(None)
        for diff in diffs:
            print(f"  {_diff_status(diff)}\t{diff.b_path or diff.a_path}")


def _diff_status(diff) -> str:
    if diff.new_file:
        return "A"
    if diff.deleted_file:
        return "D"
    if diff.renamed_file:
        return "R"
    return "M"
