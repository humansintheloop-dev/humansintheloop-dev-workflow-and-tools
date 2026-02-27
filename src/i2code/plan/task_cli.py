"""Click handlers for task and step commands."""

import json
import sys

import click

from i2code.plan.plan_file_io import with_error_handling, with_plan_file_update
from i2code.plan_domain.task import Task, TaskMetadata


def _task_spec_options(fn):
    """Apply the shared Click options for specifying a new task."""
    for option in reversed([
        click.option("--title", required=True, help="Task title"),
        click.option("--task-type", required=True, help="Task type (INFRA or OUTCOME)"),
        click.option("--entrypoint", required=True, help="Entrypoint command"),
        click.option("--observable", required=True, help="Observable outcome"),
        click.option("--evidence", required=True, help="Evidence command"),
        click.option("--steps", required=True, help="JSON array of step descriptions"),
    ]):
        fn = option(fn)
    return fn


def _parse_task_spec(command_name, **kwargs):
    """Parse steps JSON and create a Task, exiting on invalid input."""
    try:
        steps = json.loads(kwargs['steps'])
    except json.JSONDecodeError as e:
        click.echo(f"{command_name}: --steps is not valid JSON: {e}", err=True)
        sys.exit(1)
    metadata = TaskMetadata(
        task_type=kwargs['task_type'],
        entrypoint=kwargs['entrypoint'],
        observable=kwargs['observable'],
        evidence=kwargs['evidence'],
    )
    return Task.create(kwargs['title'], metadata, steps)


@click.command("mark-task-complete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--rationale", default=None, help="Rationale for change history")
def mark_task_complete_cmd(plan_file, thread, task, rationale):
    """Mark a task and all its steps as complete."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "mark-task-complete", rationale) as domain_plan:
            domain_plan.mark_task_complete(thread, task)
    click.echo(f"Marked task {thread}.{task} as complete")


@click.command("mark-task-incomplete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--rationale", default=None, help="Rationale for change history")
def mark_task_incomplete_cmd(plan_file, thread, task, rationale):
    """Mark a completed task and all its steps as incomplete."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "mark-task-incomplete", rationale) as domain_plan:
            domain_plan.mark_task_incomplete(thread, task)
    click.echo(f"Marked task {thread}.{task} as incomplete")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("mark-step-complete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--step", required=True, type=int, help="Step number")
@click.option("--rationale", required=True, help="Rationale for change history")
def mark_step_complete_cmd(plan_file, thread, task, step, rationale):
    """Mark a single step as complete."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "mark-step-complete", rationale) as domain_plan:
            domain_plan.mark_step_complete(thread, task, step)
    click.echo(f"Marked step {step} of task {thread}.{task} as complete")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("mark-step-incomplete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--step", required=True, type=int, help="Step number")
@click.option("--rationale", required=True, help="Rationale for change history")
def mark_step_incomplete_cmd(plan_file, thread, task, step, rationale):
    """Mark a single completed step as incomplete."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "mark-step-incomplete", rationale) as domain_plan:
            domain_plan.mark_step_incomplete(thread, task, step)
    click.echo(f"Marked step {step} of task {thread}.{task} as incomplete")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("insert-task-before")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--before", required=True, type=int, help="Insert before this task number")
@_task_spec_options
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_task_before_cmd(plan_file, thread, before, rationale, **kwargs):
    """Insert a task before a specified task within a thread."""
    new_task = _parse_task_spec("insert-task-before", **kwargs)
    with with_error_handling():
        with with_plan_file_update(plan_file, "insert-task-before", rationale) as domain_plan:
            domain_plan.insert_task_before(thread, before, new_task)
    click.echo(f"Inserted task '{kwargs['title']}' in thread {thread}")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("insert-task-after")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--after", required=True, type=int, help="Insert after this task number")
@_task_spec_options
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_task_after_cmd(plan_file, thread, after, rationale, **kwargs):
    """Insert a task after a specified task within a thread."""
    new_task = _parse_task_spec("insert-task-after", **kwargs)
    with with_error_handling():
        with with_plan_file_update(plan_file, "insert-task-after", rationale) as domain_plan:
            domain_plan.insert_task_after(thread, after, new_task)
    click.echo(f"Inserted task '{kwargs['title']}' in thread {thread}")


@click.command("delete-task")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to delete")
@click.option("--rationale", required=True, help="Rationale for change history")
def delete_task_cmd(plan_file, thread, task, rationale):
    """Remove a task from a thread."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "delete-task", rationale) as domain_plan:
            domain_plan.delete_task(thread, task)
    click.echo(f"Deleted task {thread}.{task}")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("replace-task")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to replace")
@_task_spec_options
@click.option("--rationale", required=True, help="Rationale for change history")
def replace_task_cmd(plan_file, thread, task, rationale, **kwargs):
    """Replace a task's content in place within a thread."""
    new_task = _parse_task_spec("replace-task", **kwargs)
    with with_error_handling():
        with with_plan_file_update(plan_file, "replace-task", rationale) as domain_plan:
            domain_plan.replace_task(thread, task, new_task)
    click.echo(f"Replaced task {thread}.{task}")


@click.command("reorder-tasks")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--order", required=True, help="Comma-separated task numbers in new order")
@click.option("--rationale", required=True, help="Rationale for change history")
def reorder_tasks_cmd(plan_file, thread, order, rationale):
    """Reorder tasks within a thread."""
    try:
        task_order = [int(n.strip()) for n in order.split(',')]
    except ValueError:
        click.echo("reorder-tasks: --order must be comma-separated integers", err=True)
        sys.exit(1)

    with with_error_handling():
        with with_plan_file_update(plan_file, "reorder-tasks", rationale) as domain_plan:
            domain_plan.reorder_tasks(thread, task_order)
    click.echo(f"Reordered tasks in thread {thread} to [{order}]")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("move-task-before")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to move")
@click.option("--before", required=True, type=int, help="Move before this task number")
@click.option("--rationale", required=True, help="Rationale for change history")
def move_task_before_cmd(plan_file, thread, task, before, rationale):
    """Move a task to before another task within the same thread."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "move-task-before", rationale) as domain_plan:
            domain_plan.move_task_before(thread, task, before)
    click.echo(f"Moved task {thread}.{task} before task {thread}.{before}")


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("move-task-after")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to move")
@click.option("--after", required=True, type=int, help="Move after this task number")
@click.option("--rationale", required=True, help="Rationale for change history")
def move_task_after_cmd(plan_file, thread, task, after, rationale):
    """Move a task to after another task within the same thread."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "move-task-after", rationale) as domain_plan:
            domain_plan.move_task_after(thread, task, after)
    click.echo(f"Moved task {thread}.{task} after task {thread}.{after}")


def register(group):
    """Register task and step commands with the given Click group."""
    group.add_command(mark_task_complete_cmd)
    group.add_command(mark_task_incomplete_cmd)
    group.add_command(mark_step_complete_cmd)
    group.add_command(mark_step_incomplete_cmd)
    group.add_command(insert_task_before_cmd)
    group.add_command(insert_task_after_cmd)
    group.add_command(delete_task_cmd)
    group.add_command(replace_task_cmd)
    group.add_command(reorder_tasks_cmd)
    group.add_command(move_task_before_cmd)
    group.add_command(move_task_after_cmd)
