"""Generate shell completion scripts for the i2code CLI."""

import click
from click.shell_completion import get_completion_class


@click.command("completion")
@click.argument(
    "shell", type=click.Choice(["bash", "zsh", "fish"]), required=False
)
@click.pass_context
def completion(ctx, shell):
    """Generate shell completion scripts."""
    if shell is None:
        click.echo("Generate shell completion scripts.")
        click.echo()
        click.echo("Supported shells: bash, zsh, fish")
        click.echo()
        click.echo("To install, add to your shell config:")
        click.echo('  eval "$(i2code completion zsh)"')
        return
    cli = ctx.find_root().command
    prog_name = ctx.find_root().info_name
    complete_var = f"_{prog_name.upper()}_COMPLETE"
    comp_cls = get_completion_class(shell)
    if comp_cls is None:
        raise click.UsageError(f"Unsupported shell: {shell}")
    comp = comp_cls(cli=cli, ctx_args={}, prog_name=prog_name, complete_var=complete_var)
    click.echo(comp.source())
