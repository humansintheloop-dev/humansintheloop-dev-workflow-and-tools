"""Click commands for the idea-to-plan workflow."""

import click

from i2code.script_command import script_command


@click.group("idea-to-plan")
def idea_to_plan():
    """Develop an idea into an implementation plan."""


script_command(
    idea_to_plan,
    "brainstorm",
    "brainstorm-idea.sh",
    "Brainstorm an idea.",
)

script_command(
    idea_to_plan,
    "spec",
    "make-spec.sh",
    "Create a specification from an idea.",
)

script_command(
    idea_to_plan,
    "revise-spec",
    "revise-spec.sh",
    "Revise an existing specification.",
)

script_command(
    idea_to_plan,
    "revise-plan",
    "revise-plan.sh",
    "Revise an existing implementation plan.",
)

script_command(
    idea_to_plan,
    "make-plan",
    "make-plan.sh",
    "Create an implementation plan from a specification.",
)

script_command(
    idea_to_plan,
    "design-doc",
    "create-design-doc.sh",
    "Create a design document from a specification.",
)

script_command(
    idea_to_plan,
    "run",
    "idea-to-code.sh",
    "Run the idea-to-code orchestrator.",
)
