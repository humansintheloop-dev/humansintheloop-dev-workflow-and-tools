"""Click handlers for task and step commands."""

import json
import sys

import click

from i2code.plan._helpers import atomic_write
from i2code.plan.tasks import (
    mark_task_complete, mark_task_incomplete,
    mark_step_complete, mark_step_incomplete,
    insert_task_before, insert_task_after,
    delete_task, replace_task, reorder_tasks,
    move_task_before, move_task_after,
)


@click.command("mark-task-complete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--rationale", default=None, help="Rationale for change history")
def mark_task_complete_cmd(plan_file, thread, task, rationale):
    """Mark a task and all its steps as complete."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = mark_task_complete(plan, thread, task, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Marked task {thread}.{task} as complete")


@click.command("mark-task-incomplete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--rationale", default=None, help="Rationale for change history")
def mark_task_incomplete_cmd(plan_file, thread, task, rationale):
    """Mark a completed task and all its steps as incomplete."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = mark_task_incomplete(plan, thread, task, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Marked task {thread}.{task} as incomplete")


@click.command("mark-step-complete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--step", required=True, type=int, help="Step number")
@click.option("--rationale", required=True, help="Rationale for change history")
def mark_step_complete_cmd(plan_file, thread, task, step, rationale):
    """Mark a single step as complete."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = mark_step_complete(plan, thread, task, step, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Marked step {step} of task {thread}.{task} as complete")


@click.command("mark-step-incomplete")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number")
@click.option("--step", required=True, type=int, help="Step number")
@click.option("--rationale", required=True, help="Rationale for change history")
def mark_step_incomplete_cmd(plan_file, thread, task, step, rationale):
    """Mark a single completed step as incomplete."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = mark_step_incomplete(plan, thread, task, step, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Marked step {step} of task {thread}.{task} as incomplete")


@click.command("insert-task-before")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--before", required=True, type=int, help="Insert before this task number")
@click.option("--title", required=True, help="Task title")
@click.option("--task-type", required=True, help="Task type (INFRA or OUTCOME)")
@click.option("--entrypoint", required=True, help="Entrypoint command")
@click.option("--observable", required=True, help="Observable outcome")
@click.option("--evidence", required=True, help="Evidence command")
@click.option("--steps", required=True, help="JSON array of step descriptions")
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_task_before_cmd(plan_file, thread, before, title, task_type,
                           entrypoint, observable, evidence, steps, rationale):
    """Insert a task before a specified task within a thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        steps_list = json.loads(steps)
    except json.JSONDecodeError as e:
        click.echo(f"insert-task-before: --steps is not valid JSON: {e}", err=True)
        sys.exit(1)

    try:
        result = insert_task_before(plan, thread, before, title, task_type,
                                    entrypoint, observable, evidence, steps_list, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Inserted task '{title}' in thread {thread}")


@click.command("insert-task-after")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--after", required=True, type=int, help="Insert after this task number")
@click.option("--title", required=True, help="Task title")
@click.option("--task-type", required=True, help="Task type (INFRA or OUTCOME)")
@click.option("--entrypoint", required=True, help="Entrypoint command")
@click.option("--observable", required=True, help="Observable outcome")
@click.option("--evidence", required=True, help="Evidence command")
@click.option("--steps", required=True, help="JSON array of step descriptions")
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_task_after_cmd(plan_file, thread, after, title, task_type,
                          entrypoint, observable, evidence, steps, rationale):
    """Insert a task after a specified task within a thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        steps_list = json.loads(steps)
    except json.JSONDecodeError as e:
        click.echo(f"insert-task-after: --steps is not valid JSON: {e}", err=True)
        sys.exit(1)

    try:
        result = insert_task_after(plan, thread, after, title, task_type,
                                   entrypoint, observable, evidence, steps_list, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Inserted task '{title}' in thread {thread}")


@click.command("delete-task")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to delete")
@click.option("--rationale", required=True, help="Rationale for change history")
def delete_task_cmd(plan_file, thread, task, rationale):
    """Remove a task from a thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = delete_task(plan, thread, task, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Deleted task {thread}.{task}")


@click.command("replace-task")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to replace")
@click.option("--title", required=True, help="New task title")
@click.option("--task-type", required=True, help="Task type (INFRA or OUTCOME)")
@click.option("--entrypoint", required=True, help="Entrypoint command")
@click.option("--observable", required=True, help="Observable outcome")
@click.option("--evidence", required=True, help="Evidence command")
@click.option("--steps", required=True, help="JSON array of step descriptions")
@click.option("--rationale", required=True, help="Rationale for change history")
def replace_task_cmd(plan_file, thread, task, title, task_type,
                     entrypoint, observable, evidence, steps, rationale):
    """Replace a task's content in place within a thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        steps_list = json.loads(steps)
    except json.JSONDecodeError as e:
        click.echo(f"replace-task: --steps is not valid JSON: {e}", err=True)
        sys.exit(1)

    try:
        result = replace_task(plan, thread, task, title, task_type,
                              entrypoint, observable, evidence, steps_list, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Replaced task {thread}.{task}")


@click.command("reorder-tasks")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--order", required=True, help="Comma-separated task numbers in new order")
@click.option("--rationale", required=True, help="Rationale for change history")
def reorder_tasks_cmd(plan_file, thread, order, rationale):
    """Reorder tasks within a thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        task_order = [int(n.strip()) for n in order.split(',')]
    except ValueError:
        click.echo("reorder-tasks: --order must be comma-separated integers", err=True)
        sys.exit(1)

    try:
        result = reorder_tasks(plan, thread, task_order, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Reordered tasks in thread {thread} to [{order}]")


@click.command("move-task-before")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to move")
@click.option("--before", required=True, type=int, help="Move before this task number")
@click.option("--rationale", required=True, help="Rationale for change history")
def move_task_before_cmd(plan_file, thread, task, before, rationale):
    """Move a task to before another task within the same thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = move_task_before(plan, thread, task, before, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Moved task {thread}.{task} before task {thread}.{before}")


@click.command("move-task-after")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
@click.option("--task", required=True, type=int, help="Task number to move")
@click.option("--after", required=True, type=int, help="Move after this task number")
@click.option("--rationale", required=True, help="Rationale for change history")
def move_task_after_cmd(plan_file, thread, task, after, rationale):
    """Move a task to after another task within the same thread."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        result = move_task_after(plan, thread, task, after, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
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
