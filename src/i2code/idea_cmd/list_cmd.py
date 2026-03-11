"""Click command for listing ideas."""

from pathlib import Path

import click

from i2code.idea.resolver import LIFECYCLE_STATES, list_ideas


def _format_idea_table(ideas):
    """Format ideas as aligned columnar output."""
    if not ideas:
        return ""
    name_width = max(len(idea.name) for idea in ideas)
    state_width = max(len(idea.state) for idea in ideas)
    lines = []
    for idea in ideas:
        lines.append(
            f"{idea.name:<{name_width}}  {idea.state:<{state_width}}  {idea.directory}"
        )
    return "\n".join(lines)


class _MutuallyExclusiveOption(click.Option):
    """Click option that is mutually exclusive with another option."""

    def __init__(self, *args, mutually_exclusive=None, **kwargs):
        self._mutually_exclusive = mutually_exclusive or []
        super().__init__(*args, **kwargs)

    def _is_set(self, opts):
        return self.name is not None and opts.get(self.name)

    def _find_conflict(self, opts):
        return next((o for o in self._mutually_exclusive if opts.get(o)), None)

    def handle_parse_result(self, ctx, opts, args):
        conflict = self._find_conflict(opts) if self._is_set(opts) else None
        if conflict:
            raise click.UsageError(
                f"--{self.name} and --{conflict} are mutually exclusive."
            )
        return super().handle_parse_result(ctx, opts, args)


@click.command("list")
@click.option(
    "--state",
    type=click.Choice(LIFECYCLE_STATES, case_sensitive=False),
    default=None,
    help="Filter ideas by lifecycle state.",
)
@click.option(
    "--archived",
    is_flag=True,
    default=False,
    cls=_MutuallyExclusiveOption,
    mutually_exclusive=["all"],
    help="Show only archived ideas.",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    default=False,
    cls=_MutuallyExclusiveOption,
    mutually_exclusive=["archived"],
    help="Show both active and archived ideas.",
)
def idea_list(state, archived, show_all):
    """List all ideas with their lifecycle state."""
    git_root = Path.cwd()
    if archived:
        all_ideas = list_ideas(git_root, include_archived=True)
        ideas = [i for i in all_ideas if i.directory.startswith("docs/ideas/archived/")]
    elif show_all:
        ideas = list_ideas(git_root, include_archived=True)
    else:
        ideas = list_ideas(git_root)
    if state:
        ideas = [idea for idea in ideas if idea.state == state]
    output = _format_idea_table(ideas)
    if output:
        click.echo(output)
