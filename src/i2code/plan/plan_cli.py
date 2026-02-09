"""Click handlers for plan-level commands."""

import sys

import click

from i2code.plan._helpers import atomic_write
from i2code.plan.plans import fix_numbering, get_next_task, get_summary, get_thread, list_threads


@click.command("fix-numbering")
@click.argument("plan_file")
def fix_numbering_cmd(plan_file):
    """Renumber all threads and tasks sequentially."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    result = fix_numbering(plan)
    atomic_write(plan_file, result)
    click.echo(f"Fixed numbering in {plan_file}")


@click.command("get-next-task")
@click.argument("plan_file")
def get_next_task_cmd(plan_file):
    """Get the first uncompleted task."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    task = get_next_task(plan)
    if task is None:
        click.echo("All tasks are complete.")
    else:
        click.echo(f"Thread {task['thread_number']}, Task {task['thread_number']}.{task['task_number']}: {task['title']}")
        click.echo(f"  TaskType: {task['task_type']}")
        click.echo(f"  Entrypoint: {task['entrypoint']}")
        click.echo(f"  Observable: {task['observable']}")
        click.echo(f"  Evidence: {task['evidence']}")
        click.echo(f"  Steps:")
        for i, step in enumerate(task['steps'], 1):
            status = 'x' if step['completed'] else ' '
            click.echo(f"    {i}. [{status}] {step['description']}")


@click.command("list-threads")
@click.argument("plan_file")
def list_threads_cmd(plan_file):
    """List all threads with completion status."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    threads = list_threads(plan)
    for t in threads:
        click.echo(f"Thread {t['number']}: {t['title']} ({t['completed_tasks']}/{t['total_tasks']} tasks completed)")


@click.command("get-summary")
@click.argument("plan_file")
def get_summary_cmd(plan_file):
    """Get plan metadata and progress summary."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    summary = get_summary(plan)
    click.echo(f"Plan: {summary['plan_name']}")
    click.echo(f"Idea Type: {summary['idea_type']}")
    click.echo(f"Overview: {summary['overview']}")
    click.echo(f"Threads: {summary['total_threads']}")
    click.echo(f"Tasks: {summary['completed_tasks']}/{summary['total_tasks']} completed")


@click.command("get-thread")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
def get_thread_cmd(plan_file, thread):
    """Get a thread's full content."""
    with open(plan_file, "r", encoding="utf-8") as f:
        plan = f.read()

    try:
        thread_data = get_thread(plan, thread)
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)

    click.echo(f"Thread {thread_data['number']}: {thread_data['title']}")
    click.echo()
    click.echo(thread_data['introduction'])
    click.echo()
    for task in thread_data['tasks']:
        status = 'x' if task['completed'] else ' '
        click.echo(f"- [{status}] Task {task['thread_number']}.{task['task_number']}: {task['title']}")
        click.echo(f"  TaskType: {task['task_type']}")
        click.echo(f"  Entrypoint: {task['entrypoint']}")
        click.echo(f"  Observable: {task['observable']}")
        click.echo(f"  Evidence: {task['evidence']}")
        click.echo(f"  Steps:")
        for i, step in enumerate(task['steps'], 1):
            step_status = 'x' if step['completed'] else ' '
            click.echo(f"    {i}. [{step_status}] {step['description']}")
        click.echo()


def register(group):
    """Register plan-level commands with the given Click group."""
    group.add_command(fix_numbering_cmd)
    group.add_command(get_next_task_cmd)
    group.add_command(list_threads_cmd)
    group.add_command(get_summary_cmd)
    group.add_command(get_thread_cmd)
