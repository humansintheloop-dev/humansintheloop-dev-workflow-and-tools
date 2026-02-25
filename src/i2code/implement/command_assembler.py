"""Assemble implement subcommands with their dependencies."""

from git import Repo

from i2code.implement.claude_runner import ClaudeRunner
from i2code.implement.command_builder import CommandBuilder
from i2code.implement.git_repository import GitRepository
from i2code.implement.github_actions_build_fixer import GithubActionsBuildFixerFactory
from i2code.implement.github_client import GitHubClient
from i2code.implement.idea_project import IdeaProject
from i2code.implement.implement_command import ImplementCommand
from i2code.implement.mode_factory import ModeFactory
from i2code.implement.project_setup import ProjectScaffolder
from i2code.implement.scaffold_command import ScaffoldCommand


def assemble_implement(opts):
    """Wire up dependencies and return an ImplementCommand."""
    project = IdeaProject(opts.idea_directory)
    repo = Repo(project.directory, search_parent_directories=True)
    gh_client = GitHubClient()
    git_repo = GitRepository(repo, gh_client=gh_client)
    claude_runner = ClaudeRunner(interactive=not opts.non_interactive)
    build_fixer_factory = GithubActionsBuildFixerFactory(
        opts=opts,
        claude_runner=claude_runner,
    )
    mode_factory = ModeFactory(
        opts=opts,
        claude_runner=claude_runner,
        build_fixer_factory=build_fixer_factory,
    )
    return ImplementCommand(opts, project, git_repo, mode_factory)


def assemble_scaffold(opts):
    """Wire up dependencies and return a ScaffoldCommand."""
    project = IdeaProject(opts.idea_directory)
    project.validate()
    project.validate_files()

    repo = Repo(project.directory, search_parent_directories=True)

    initializer = ProjectScaffolder(
        claude_runner=ClaudeRunner(interactive=not opts.non_interactive),
        command_builder=CommandBuilder(),
    )
    return ScaffoldCommand(opts, initializer, cwd=repo.working_tree_dir)


def assemble_command(ctx, default_factory, opts):
    """Resolve the factory from context or use the default, then build the command."""
    factory = (ctx.obj or {}).get("command_factory", default_factory)
    return factory(opts)
