"""Click handlers for thread commands."""

import json
import sys

import click

from i2code.plan.plan_file_io import atomic_write, with_error_handling, with_plan_file_update
from i2code.plan.threads import replace_thread, reorder_threads
from i2code.plan_domain.thread import Thread


@click.command("insert-thread-before")
@click.argument("plan_file")
@click.option("--before", required=True, type=int, help="Insert before this thread number")
@click.option("--title", required=True, help="Thread title")
@click.option("--introduction", required=True, help="Thread introduction text")
@click.option("--tasks", required=True, help="JSON array of task objects")
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_thread_before_cmd(plan_file, before, title, introduction, tasks, rationale):
    """Insert a thread before a specified thread."""
    try:
        tasks_list = json.loads(tasks)
    except json.JSONDecodeError as e:
        click.echo(f"insert-thread-before: --tasks is not valid JSON: {e}", err=True)
        sys.exit(1)

    new_thread = Thread.create(title=title, introduction=introduction, tasks=tasks_list)
    with with_error_handling():
        with with_plan_file_update(plan_file, "insert-thread-before", rationale) as domain_plan:
            domain_plan.insert_thread_before(before, new_thread)
    click.echo(f"Inserted thread '{title}'")


@click.command("insert-thread-after")
@click.argument("plan_file")
@click.option("--after", required=True, type=int, help="Insert after this thread number")
@click.option("--title", required=True, help="Thread title")
@click.option("--introduction", required=True, help="Thread introduction text")
@click.option("--tasks", required=True, help="JSON array of task objects")
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_thread_after_cmd(plan_file, after, title, introduction, tasks, rationale):
    """Insert a thread after a specified thread."""
    try:
        tasks_list = json.loads(tasks)
    except json.JSONDecodeError as e:
        click.echo(f"insert-thread-after: --tasks is not valid JSON: {e}", err=True)
        sys.exit(1)

    new_thread = Thread.create(title=title, introduction=introduction, tasks=tasks_list)
    with with_error_handling():
        with with_plan_file_update(plan_file, "insert-thread-after", rationale) as domain_plan:
            domain_plan.insert_thread_after(after, new_thread)
    click.echo(f"Inserted thread '{title}'")


@click.command("delete-thread")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number to delete")
@click.option("--rationale", required=True, help="Rationale for change history")
def delete_thread_cmd(plan_file, thread, rationale):
    """Remove a thread entirely."""
    with with_error_handling():
        with with_plan_file_update(plan_file, "delete-thread", rationale) as domain_plan:
            domain_plan.delete_thread(thread)
    click.echo(f"Deleted thread {thread}")


@click.command("replace-thread")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number to replace")
@click.option("--title", required=True, help="New thread title")
@click.option("--introduction", required=True, help="New thread introduction text")
@click.option("--tasks", required=True, help="JSON array of task objects")
@click.option("--rationale", required=True, help="Rationale for change history")
def replace_thread_cmd(plan_file, thread, title, introduction, tasks, rationale):
    """Replace a thread's entire content in place."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        tasks_list = json.loads(tasks)
    except json.JSONDecodeError as e:
        click.echo(f"replace-thread: --tasks is not valid JSON: {e}", err=True)
        sys.exit(1)

    try:
        result = replace_thread(plan, thread, title, introduction, tasks_list, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Replaced thread {thread}")


@click.command("reorder-threads")
@click.argument("plan_file")
@click.option("--order", required=True, help="Comma-separated thread numbers in new order")
@click.option("--rationale", required=True, help="Rationale for change history")
def reorder_threads_cmd(plan_file, order, rationale):
    """Reorder threads according to a specified ordering."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        thread_order = [int(n.strip()) for n in order.split(',')]
    except ValueError:
        click.echo("reorder-threads: --order must be comma-separated integers", err=True)
        sys.exit(1)

    try:
        result = reorder_threads(plan, thread_order, rationale)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    atomic_write(plan_file, result)
    click.echo(f"Reordered threads to [{order}]")


def register(group):
    """Register thread commands with the given Click group."""
    group.add_command(insert_thread_before_cmd)
    group.add_command(insert_thread_after_cmd)
    group.add_command(delete_thread_cmd)
    group.add_command(replace_thread_cmd)
    group.add_command(reorder_threads_cmd)
