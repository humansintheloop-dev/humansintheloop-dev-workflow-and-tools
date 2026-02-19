"""Click commands for the idea-to-plan workflow."""

import sys

import click

from i2code.script_runner import run_script


@click.group("idea-to-plan")
def idea_to_plan():
    """Develop an idea into an implementation plan."""


@idea_to_plan.command("brainstorm")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def brainstorm_cmd(args):
    """Brainstorm an idea."""
    result = run_script("brainstorm-idea.sh", args)
    sys.exit(result.returncode)


@idea_to_plan.command("spec")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def spec_cmd(args):
    """Create a specification from an idea."""
    result = run_script("make-spec.sh", args)
    sys.exit(result.returncode)


@idea_to_plan.command("revise-spec")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def revise_spec_cmd(args):
    """Revise an existing specification."""
    result = run_script("revise-spec.sh", args)
    sys.exit(result.returncode)


@idea_to_plan.command("revise-plan")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def revise_plan_cmd(args):
    """Revise an existing implementation plan."""
    result = run_script("revise-plan.sh", args)
    sys.exit(result.returncode)


@idea_to_plan.command("make-plan")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def make_plan_cmd(args):
    """Create an implementation plan from a specification."""
    result = run_script("make-plan.sh", args)
    sys.exit(result.returncode)


@idea_to_plan.command("design-doc")
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def design_doc_cmd(args):
    """Create a design document from a specification."""
    result = run_script("create-design-doc.sh", args)
    sys.exit(result.returncode)
