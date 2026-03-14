"""Click command for displaying and transitioning idea lifecycle state."""

import subprocess
import sys
from pathlib import Path

import click

from i2code.idea.metadata import read_metadata, write_metadata
from i2code.idea_cmd.transition_rules import validate_transition
from i2code.idea.resolver import LIFECYCLE_STATES, list_ideas, resolve_idea
from i2code.plan_domain.parser import parse as parse_plan


def _complete_name_or_path(ctx, _param, incomplete):
    """Offer both idea names and filesystem paths for shell completion."""
    completions = []
    try:
        git_root = Path.cwd()
        for idea in list_ideas(git_root):
            if idea.name.startswith(incomplete):
                completions.append(idea.name)
    except Exception:
        pass
    return completions


def _resolve_state(name_or_path):
    """Resolve lifecycle state from a name or directory path."""
    path = Path(name_or_path)
    name = path.name if path.is_dir() else name_or_path
    return resolve_idea(name, Path.cwd()).state


def _git_commit(message, git_root):
    """Create a git commit. Raises RuntimeError on failure."""
    result = subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def execute_transition(name, old_path, new_state, git_root):
    """Update an idea's state in its metadata file and stage it.

    Returns a commit message string, or None if already in the target state.
    Raises RuntimeError on git failure.
    """
    old_state = resolve_idea(name, git_root).state
    if old_state == new_state:
        return None
    metadata_path = Path(old_path) / f"{name}-metadata.yaml"
    metadata = read_metadata(metadata_path)
    metadata["state"] = new_state
    write_metadata(metadata_path, metadata)
    result = subprocess.run(
        ["git", "add", str(metadata_path)],
        cwd=str(git_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return f"Move idea {name} from {old_state} to {new_state}"


def _handle_transition(name_or_path, new_state, *, force, no_commit):
    """Validate and execute a state transition."""
    git_root = Path.cwd()
    idea = resolve_idea(name_or_path, git_root)
    idea_dir = git_root / idea.directory
    if not force:
        violation = validate_transition(idea.state, new_state, idea_dir)
        if violation:
            click.echo(f"{violation}. Use --force to override.", err=True)
            sys.exit(1)
    message = execute_transition(idea.name, idea_dir, new_state, git_root)
    if message is None:
        click.echo(f"Idea {idea.name} is already in state {new_state}")
        return
    if not no_commit:
        _git_commit(message, git_root)
    click.echo(message)


def _has_fully_completed_plan(idea_dir, name):
    """Check if an idea has a plan file with all tasks completed."""
    plan_path = idea_dir / f"{name}-plan.md"
    if not plan_path.is_file():
        return False
    plan = parse_plan(plan_path.read_text())
    return plan.task_progress().total > 0 and plan.get_next_task() is None


def _find_active_incomplete_ideas(git_root):
    """Return active ideas in draft or wip state."""
    return [
        idea for idea in list_ideas(git_root)
        if idea.state in ("draft", "wip")
        and (git_root / "docs" / "ideas" / "active" / idea.name).is_dir()
    ]


def _preview_finished_ideas(wip_ideas, git_root):
    """Show wip ideas that would be transitioned, without making changes."""
    previewed = []
    for idea in wip_ideas:
        idea_dir = git_root / idea.directory
        if not _has_fully_completed_plan(idea_dir, idea.name):
            continue
        click.echo(f"Would move idea {idea.name} from wip to completed")
        previewed.append(idea.name)
    return previewed


def _transition_finished_ideas(wip_ideas, git_root):
    """Transition wip ideas with completed plans, returning transitioned names."""
    transitioned = []
    for idea in wip_ideas:
        idea_dir = git_root / idea.directory
        if not _has_fully_completed_plan(idea_dir, idea.name):
            continue
        message = execute_transition(idea.name, idea_dir, "completed", git_root)
        if message:
            click.echo(message)
            transitioned.append(idea.name)
    return transitioned


def _complete_finished_plans(git_root, no_commit, dry_run):
    """Transition all wip ideas with fully-completed plans to completed."""
    wip_ideas = _find_active_incomplete_ideas(git_root)
    process = _preview_finished_ideas if dry_run else _transition_finished_ideas
    transitioned = process(wip_ideas, git_root)
    if not transitioned:
        click.echo("No ideas with completed plans found")
        return
    if dry_run or no_commit:
        return
    names = ", ".join(transitioned)
    _git_commit(f"Mark ideas with completed plans as completed: {names}", git_root)


def _validate_args(name_or_path, completed_plans, dry_run):
    """Validate flag combinations for the state command."""
    if completed_plans:
        if name_or_path:
            raise click.UsageError("Provide an idea name or use --completed-plans, not both.")
        return
    if dry_run:
        raise click.UsageError("--dry-run can only be used with --completed-plans.")
    if name_or_path is None:
        raise click.UsageError("Provide an idea name or use --completed-plans.")


@click.command("state")
@click.argument("name_or_path", required=False, default=None, shell_complete=_complete_name_or_path)
@click.argument(
    "new_state",
    required=False,
    default=None,
    type=click.Choice(LIFECYCLE_STATES, case_sensitive=False),
)
@click.option("--completed-plans", is_flag=True, default=False, help="Transition all wip ideas with completed plans.")
@click.option("--dry-run", is_flag=True, default=False, help="Show what would change without making changes.")
@click.option("--force", is_flag=True, default=False, help="Bypass transition rules.")
@click.option("--no-commit", is_flag=True, default=False, help="Stage changes but do not commit.")
def idea_state(name_or_path, new_state, **kwargs):
    """Display or transition the lifecycle state of an idea."""
    completed_plans = kwargs["completed_plans"]
    dry_run = kwargs["dry_run"]
    no_commit = kwargs["no_commit"]
    try:
        _validate_args(name_or_path, completed_plans, dry_run)
        if completed_plans:
            _complete_finished_plans(Path.cwd(), no_commit, dry_run)
        elif new_state is None:
            click.echo(_resolve_state(name_or_path))
        else:
            _handle_transition(name_or_path, new_state, force=kwargs["force"], no_commit=no_commit)
    except (ValueError, RuntimeError) as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
