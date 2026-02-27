"""Click handlers for thread commands."""

import json
import sys

import click

from i2code.plan.plan_file_io import with_error_handling, with_plan_file_update
from i2code.plan_domain.thread import Thread


def _thread_spec_options(fn):
    """Apply the shared Click options for specifying a new thread."""
    for option in reversed([
        click.option("--title", required=True, help="Thread title"),
        click.option("--introduction", required=True, help="Thread introduction text"),
        click.option("--tasks", required=True, help="JSON array of task objects"),
    ]):
        fn = option(fn)
    return fn


def _resolve_tasks_json(command_name, tasks, tasks_file):
    """Return tasks JSON string from either --tasks or --tasks-file."""
    if tasks and tasks_file:
        click.echo(f"{command_name}: --tasks and --tasks-file are mutually exclusive", err=True)
        sys.exit(1)
    if not tasks and not tasks_file:
        click.echo(f"{command_name}: either --tasks or --tasks-file is required", err=True)
        sys.exit(1)
    if tasks_file:
        with open(tasks_file) as f:
            return f.read()
    return tasks


def _parse_thread(command_name, title, introduction, tasks):
    """Parse tasks JSON and build a Thread, exit on invalid JSON."""
    try:
        tasks_list = json.loads(tasks)
    except json.JSONDecodeError as e:
        click.echo(f"{command_name}: --tasks is not valid JSON: {e}", err=True)
        sys.exit(1)
    return Thread.create(title=title, introduction=introduction, tasks=tasks_list)


@click.command("insert-thread-before")
@click.argument("plan_file")
@click.option("--before", required=True, type=int, help="Insert before this thread number")
@_thread_spec_options
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_thread_before_cmd(plan_file, before, rationale, **kwargs):
    """Insert a thread before a specified thread."""
    new_thread = _parse_thread("insert-thread-before", **kwargs)
    with with_error_handling():
        with with_plan_file_update(plan_file, "insert-thread-before", rationale) as domain_plan:
            domain_plan.insert_thread_before(before, new_thread)
    click.echo(f"Inserted thread '{kwargs['title']}'")


@click.command("insert-thread-after")
@click.argument("plan_file")
@click.option("--after", required=True, type=int, help="Insert after this thread number")
@_thread_spec_options
@click.option("--rationale", required=True, help="Rationale for change history")
def insert_thread_after_cmd(plan_file, after, rationale, **kwargs):
    """Insert a thread after a specified thread."""
    new_thread = _parse_thread("insert-thread-after", **kwargs)
    with with_error_handling():
        with with_plan_file_update(plan_file, "insert-thread-after", rationale) as domain_plan:
            domain_plan.insert_thread_after(after, new_thread)
    click.echo(f"Inserted thread '{kwargs['title']}'")


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


# @codescene(disable:"Excess Number of Function Arguments")
@click.command("replace-thread")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number to replace")
@click.option("--title", required=True, help="New thread title")
@click.option("--introduction", required=True, help="New thread introduction text")
@click.option("--tasks", default=None, help="JSON array of task objects")
@click.option("--tasks-file", default=None, type=click.Path(exists=True), help="Path to JSON file containing task objects")
@click.option("--rationale", required=True, help="Rationale for change history")
def replace_thread_cmd(plan_file, thread, title, introduction, tasks, tasks_file, rationale):
    """Replace a thread's entire content in place."""
    tasks_json = _resolve_tasks_json("replace-thread", tasks, tasks_file)
    new_thread = _parse_thread("replace-thread", title=title, introduction=introduction, tasks=tasks_json)
    with with_error_handling():
        with with_plan_file_update(plan_file, "replace-thread", rationale) as domain_plan:
            domain_plan.replace_thread(thread, new_thread)
    click.echo(f"Replaced thread {thread}")


@click.command("reorder-threads")
@click.argument("plan_file")
@click.option("--order", required=True, help="Comma-separated thread numbers in new order")
@click.option("--rationale", required=True, help="Rationale for change history")
def reorder_threads_cmd(plan_file, order, rationale):
    """Reorder threads according to a specified ordering."""
    try:
        thread_order = [int(n.strip()) for n in order.split(',')]
    except ValueError:
        click.echo("reorder-threads: --order must be comma-separated integers", err=True)
        sys.exit(1)

    with with_error_handling():
        with with_plan_file_update(plan_file, "reorder-threads", rationale) as domain_plan:
            domain_plan.reorder_threads(thread_order)
    click.echo(f"Reordered threads to [{order}]")


def register(group):
    """Register thread commands with the given Click group."""
    group.add_command(insert_thread_before_cmd)
    group.add_command(insert_thread_after_cmd)
    group.add_command(delete_thread_cmd)
    group.add_command(replace_thread_cmd)
    group.add_command(reorder_threads_cmd)
