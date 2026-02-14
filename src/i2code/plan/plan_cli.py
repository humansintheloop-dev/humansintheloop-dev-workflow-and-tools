"""Click handlers for plan-level commands."""

import click

from i2code.plan.plan_file_io import with_error_handling, with_plan_file, with_plan_file_update


@click.command("fix-numbering")
@click.argument("plan_file")
def fix_numbering_cmd(plan_file):
    """Renumber all threads and tasks sequentially."""
    with with_plan_file_update(plan_file):
        pass  # parse + to_text() round-trip handles renumbering
    click.echo(f"Fixed numbering in {plan_file}")


@click.command("get-next-task")
@click.argument("plan_file")
def get_next_task_cmd(plan_file):
    """Get the first uncompleted task."""
    with with_plan_file(plan_file) as domain_plan:
        task = domain_plan.get_next_task()
    if task is None:
        click.echo("All tasks are complete.")
    else:
        click.echo(task.print())


@click.command("list-threads")
@click.argument("plan_file")
def list_threads_cmd(plan_file):
    """List all threads with completion status."""
    with with_plan_file(plan_file) as domain_plan:
        for thread_num, thread in enumerate(domain_plan.threads, 1):
            completed = sum(1 for t in thread.tasks if t.is_completed)
            total = len(thread.tasks)
            click.echo(f"Thread {thread_num}: {thread.title} ({completed}/{total} tasks completed)")


@click.command("get-summary")
@click.argument("plan_file")
def get_summary_cmd(plan_file):
    """Get plan metadata and progress summary."""
    with with_plan_file(plan_file) as domain_plan:
        total_threads = len(domain_plan.threads)
        total_tasks = sum(len(t.tasks) for t in domain_plan.threads)
        completed_tasks = sum(
            1 for t in domain_plan.threads for task in t.tasks if task.is_completed
        )
        click.echo(f"Plan: {domain_plan.name}")
        click.echo(f"Idea Type: {domain_plan.idea_type}")
        click.echo(f"Overview: {domain_plan.overview}")
        click.echo(f"Threads: {total_threads}")
        click.echo(f"Tasks: {completed_tasks}/{total_tasks} completed")


@click.command("get-thread")
@click.argument("plan_file")
@click.option("--thread", required=True, type=int, help="Thread number")
def get_thread_cmd(plan_file, thread):
    """Get a thread's full content."""
    with with_error_handling():
        with with_plan_file(plan_file) as domain_plan:
            domain_thread = domain_plan.get_thread(thread)
            click.echo(f"Thread {thread}: {domain_thread.title}")
            click.echo()
            click.echo(domain_thread.introduction)
            click.echo()
            for task_num, task in enumerate(domain_thread.tasks, 1):
                status = 'x' if task.is_completed else ' '
                click.echo(f"- [{status}] Task {thread}.{task_num}: {task.title}")
                click.echo(f"  TaskType: {task.task_type}")
                click.echo(f"  Entrypoint: {task.entrypoint}")
                click.echo(f"  Observable: {task.observable}")
                click.echo(f"  Evidence: {task.evidence}")
                click.echo(f"  Steps:")
                for i, step in enumerate(task.steps, 1):
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
