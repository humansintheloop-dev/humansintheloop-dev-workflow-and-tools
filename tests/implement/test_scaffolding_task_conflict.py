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
from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.claude_services import ClaudeServices
from i2code.implement.git_repository import GitRepository
from i2code.implement.idea_project import IdeaProject
from i2code.implement.project_scaffolding import ScaffoldingCreator

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "hello-world")
CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config-files")


@dataclass
class ProjectFixture:
    git_repo: GitRepository
    idea_dir: Path
    claude_services: ClaudeServices

    @property
    def tmp_path(self) -> Path:
        return Path(self.git_repo.working_tree_dir)

    @property
    def repo(self) -> Repo:
        return self.git_repo._repo

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
    _print_ci_file(project, "after scaffolding")

    _run_first_task(project)
    _print_ci_file(project, "after task")

    workflow_changes = _workflow_files_in_last_commit(project.repo)
    assert not workflow_changes, (
        f"Task should not modify .github/workflows/ but changed: {workflow_changes}"
    )


def _create_test_project(tmp_path: Path) -> ProjectFixture:
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

    return ProjectFixture(
        git_repo=GitRepository(repo, gh_client=None),
        idea_dir=idea_dir,
        claude_services=ClaudeServices(
            ClaudeRunner(interactive=False), CommandBuilder(),
        ),
    )


def _run_scaffolding(project: ProjectFixture):
    cs = project.claude_services
    scaffolding_creator = ScaffoldingCreator(cs.command_builder, cs.claude_runner)
    scaffolding_creator.run_scaffolding(
        str(project.idea_dir), cwd=str(project.tmp_path), interactive=False,
    )


def _run_first_task(project: ProjectFixture):
    idea_project = IdeaProject(str(project.idea_dir))
    task = idea_project.get_next_task()
    assert task is not None, "Expected at least one uncompleted task in the plan"

    project.claude_services.run_task(
        str(project.idea_dir), task.print(), TaskCommandOpts(
            interactive=False,
            extra_cli_args=["--allowed-tools", "Bash(rm:*)"],
        ),
        project.git_repo,
    )
    _print_recent_commits(project.repo)
    _print_last_commit_diff(project.repo)


def _workflow_files_in_last_commit(repo: Repo) -> list:
    return [line for line in repo.git.diff("HEAD~1", "--name-only").splitlines()
            if line.startswith(".github/workflows/")]


def _print_ci_file(project: ProjectFixture, label: str):
    ci_file = project.ci_yaml if project.ci_yaml.exists() else project.ci_yml
    if ci_file.exists():
        print(f"\n--- {ci_file.name} {label} ---")
        print(ci_file.read_text())
    else:
        print(f"\n--- no CI file found {label} ---")


def _print_recent_commits(repo: Repo):
    for commit in list(repo.iter_commits(max_count=2)):
        print(f"\n{commit.hexsha[:7]} {commit.message.strip()}")
        parent = commit.parents[0] if commit.parents else None
        diffs = parent.diff(commit) if parent else commit.diff(None)
        for diff in diffs:
            print(f"  {_diff_status(diff)}\t{diff.b_path or diff.a_path}")


def _print_last_commit_diff(repo: Repo):
    print("\ngit diff HEAD~1:")
    print(repo.git.diff("HEAD~1"))


def _diff_status(diff) -> str:
    if diff.new_file:
        return "A"
    if diff.deleted_file:
        return "D"
    if diff.renamed_file:
        return "R"
    return "M"
