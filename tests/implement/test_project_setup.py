"""Tests for project scaffolding setup."""

import os
import tempfile

import pytest

from i2code.implement.claude_runner import CapturedOutput, ClaudeResult, DiagnosticInfo
from i2code.implement.implement_opts import ImplementOpts


def _opts(**kwargs):
    """Build ImplementOpts with defaults suitable for project setup tests."""
    kwargs.setdefault("idea_directory", "/tmp/fake-idea")
    return ImplementOpts(**kwargs)


@pytest.mark.unit
class TestBuildScaffoldingPrompt:
    """Test build_scaffolding_prompt() constructs correct Claude commands."""

    def test_interactive_mode_returns_claude_with_prompt(self):
        """Interactive mode should return ['claude', <prompt>]."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=True)

        assert cmd[0] == "claude"
        assert len(cmd) == 2
        # Second element is the prompt string
        assert isinstance(cmd[1], str)

    def test_non_interactive_mode_returns_claude_with_p_flag(self):
        """Non-interactive mode should return ['claude', '--verbose', '--output-format=stream-json', '-p', <prompt>]."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=False)

        assert cmd[0] == "claude"
        assert "--verbose" in cmd
        assert "--output-format=stream-json" in cmd
        assert "-p" in cmd
        # Prompt should be the last element (after -p)
        p_index = cmd.index("-p")
        assert p_index == len(cmd) - 2
        assert isinstance(cmd[p_index + 1], str)

    def test_prompt_references_idea_files(self):
        """Prompt should reference the idea directory files."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=True)
        prompt = cmd[1]

        assert "/tmp/docs/features/my-service" in prompt
        assert "*-idea.*" in prompt or "idea" in prompt.lower()
        assert "*-spec.md" in prompt or "spec" in prompt.lower()

    def test_prompt_describes_scaffolding_goals(self):
        """Prompt should describe desired scaffolding outcome without prescribing versions."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command("/tmp/docs/features/my-service", interactive=True)
        prompt = cmd[1]

        # Should mention key scaffolding concepts
        assert "ci.yaml" in prompt.lower() or "ci" in prompt.lower()
        assert "scaffold" in prompt.lower() or "placeholder" in prompt.lower()
        assert "commit" in prompt.lower()

    def test_mock_claude_returns_mock_script_command(self):
        """When mock_claude is provided, should return [mock_script, 'setup']."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command(
            "/tmp/docs/features/my-service",
            mock_claude="/path/to/mock-claude.sh"
        )

        assert cmd == ["/path/to/mock-claude.sh", "setup"]

    def test_mock_claude_none_returns_normal_command(self):
        """When mock_claude is None, should return normal Claude command."""
        from i2code.implement.command_builder import CommandBuilder

        cmd = CommandBuilder().build_scaffolding_command(
            "/tmp/docs/features/my-service",
            mock_claude=None
        )

        assert cmd[0] == "claude"


@pytest.mark.unit
class TestRunScaffoldingFailure:
    """Test ProjectScaffolder.run_scaffolding() exits on Claude failure."""

    def _make_scaffolding_creator(self, fake):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ScaffoldingCreator
        return ScaffoldingCreator(command_builder=CommandBuilder(), claude_runner=fake)

    def test_non_zero_exit_code_exits(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=1, diagnostics=DiagnosticInfo(error_message="Something broke")))
        creator = self._make_scaffolding_creator(fake)

        with pytest.raises(SystemExit) as exc_info:
            creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert exc_info.value.code == 1

    def test_no_success_tag_exits(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(returncode=0, output=CapturedOutput("no tag here")))
        creator = self._make_scaffolding_creator(fake)

        with pytest.raises(SystemExit) as exc_info:
            creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert exc_info.value.code == 1

    def test_failure_prints_permission_denials(self, capsys):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=0,
            output=CapturedOutput("<FAILURE>no perms</FAILURE>"),
            diagnostics=DiagnosticInfo(
                permission_denials=[{"tool_name": "Bash", "tool_input": {"command": "git commit"}}],
            ),
        ))
        creator = self._make_scaffolding_creator(fake)

        with pytest.raises(SystemExit):
            creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        captured = capsys.readouterr()
        assert "Permission denied" in captured.err

    def test_failure_prints_last_messages(self, capsys):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=1,
            diagnostics=DiagnosticInfo(last_messages=[
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "I cannot write files"}]}},
                {"type": "result", "result": "No permissions to complete task"},
            ]),
        ))
        creator = self._make_scaffolding_creator(fake)

        with pytest.raises(SystemExit):
            creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        captured = capsys.readouterr()
        assert "I cannot write files" in captured.err
        assert "No permissions to complete task" in captured.err

    def test_success_tag_does_not_exit(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=0, output=CapturedOutput("...<SUCCESS>Scaffold created</SUCCESS>...")
        ))
        creator = self._make_scaffolding_creator(fake)

        creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

    def test_interactive_mode_does_not_check_stdout(self):
        """Interactive mode has empty stdout — should not exit."""
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        creator = self._make_scaffolding_creator(fake)

        creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=True)


@pytest.mark.unit
class TestRunScaffolding:
    """Test ScaffoldingCreator.run_scaffolding() delegates to correct runner."""

    def _make_creator(self, fake_runner):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ScaffoldingCreator

        return ScaffoldingCreator(command_builder=CommandBuilder(), claude_runner=fake_runner)

    def test_interactive_calls_run(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        creator = self._make_creator(fake)

        creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=True)

        assert len(fake.calls) == 1
        method, cmd, cwd = fake.calls[0]
        assert method == "run"
        assert cmd[0] == "claude"
        assert cwd == "/tmp/repo"

    def test_non_interactive_calls_run(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        fake.set_result(ClaudeResult(
            returncode=0, output=CapturedOutput("<SUCCESS>Scaffold created</SUCCESS>")
        ))
        creator = self._make_creator(fake)

        creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", interactive=False)

        assert len(fake.calls) == 1
        method, cmd, cwd = fake.calls[0]
        assert method == "run"
        assert cmd[0] == "claude"
        assert "-p" in cmd
        assert cwd == "/tmp/repo"

    def test_forwards_mock_claude(self):
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        fake = FakeClaudeRunner()
        creator = self._make_creator(fake)

        creator.run_scaffolding("/tmp/idea", cwd="/tmp/repo", mock_claude="/mock.sh")

        assert len(fake.calls) == 1
        method, cmd, cwd = fake.calls[0]
        assert method == "run"
        assert cmd == ["/mock.sh", "setup"]


class FakeBuildFixer:
    """Records fix_ci_failure calls and returns a canned result."""

    def __init__(self, result=True):
        self.calls = []
        self.result = result

    def fix_ci_failure(self):
        self.calls.append("fix_ci_failure")
        return self.result


@pytest.mark.unit
class TestEnsureProjectSetupMethod:
    """Test ProjectScaffolder.ensure_scaffolding_setup() with fakes — no @patch."""

    def _make_fakes(self, tmp_path):
        from tests.implement.fake_claude_runner import FakeClaudeRunner
        from tests.implement.fake_git_repository import FakeGitRepository
        from tests.implement.fake_github_client import FakeGitHubClient

        fake_gh = FakeGitHubClient()
        fake_runner = FakeClaudeRunner()
        fake_git = FakeGitRepository(working_tree_dir=str(tmp_path), gh_client=fake_gh)
        return fake_runner, fake_git, fake_gh

    def _make_initializer(self, fake_runner=None, git_repo=None, build_fixer=None, push_fn=None):
        from i2code.implement.command_builder import CommandBuilder
        from i2code.implement.project_setup import ProjectScaffolder, ScaffoldingCreator, ScaffoldingSteps
        from tests.implement.fake_claude_runner import FakeClaudeRunner

        runner = fake_runner or FakeClaudeRunner()
        scaffolding_creator = ScaffoldingCreator(
            command_builder=CommandBuilder(),
            claude_runner=runner,
        )
        steps = ScaffoldingSteps(
            claude_runner=runner,
            build_fixer=build_fixer,
            push_fn=push_fn,
        )
        return ProjectScaffolder(
            scaffolding_creator=scaffolding_creator,
            git_repo=git_repo,
            steps=steps,
        )

    def _advance_head(self, fake_runner, fake_git, new_sha="bbb222"):
        def side_effect():
            fake_git.set_head_sha(new_sha)
        fake_runner.set_side_effect(side_effect)

    def _setup_with_push_tracking(self, tmp_path):
        fake_runner, fake_git, fake_gh = self._make_fakes(tmp_path)
        fake_git.set_head_sha("aaa111")
        pushed = []
        self._advance_head(fake_runner, fake_git)
        initializer = self._make_initializer(
            fake_runner=fake_runner, git_repo=fake_git,
            push_fn=lambda branch: pushed.append(branch) or True,
        )
        return initializer, fake_gh, pushed

    def _setup_ci_failure(self, tmp_path, ci_result, build_fixer):
        fake_runner, fake_git, fake_gh = self._make_fakes(tmp_path)
        fake_git.set_head_sha("aaa111")
        self._advance_head(fake_runner, fake_git)
        fake_gh.set_workflow_completion_result(
            "idea/test/integration", "bbb222", ci_result,
        )
        initializer = self._make_initializer(
            fake_runner=fake_runner, git_repo=fake_git,
            build_fixer=build_fixer, push_fn=lambda branch: True,
        )
        return initializer, fake_git

    def test_no_new_commits_returns_true_without_waiting_for_ci(self, tmp_path):
        """When scaffolding makes no commits, should return True without waiting for CI."""
        fake_runner, fake_git, fake_gh = self._make_fakes(tmp_path)
        fake_git.set_head_sha("abc123")

        initializer = self._make_initializer(
            fake_runner=fake_runner, git_repo=fake_git, push_fn=lambda branch: True,
        )

        result = initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )

        assert result is True
        assert not any(call[0] == "wait_for_workflow_completion" for call in fake_gh.calls)

    def test_commits_made_pushes_and_waits_for_ci(self, tmp_path):
        """When scaffolding makes commits, should push and wait for CI."""
        initializer, fake_gh, pushed = self._setup_with_push_tracking(tmp_path)
        fake_gh.set_workflow_completion_result("idea/test/integration", "bbb222", (True, None))

        result = initializer.ensure_scaffolding_setup(
            _opts(ci_timeout=300), idea_directory=str(tmp_path),
            branch="idea/test/integration",
        )

        assert result is True
        assert pushed == ["idea/test/integration"]
        assert ("wait_for_workflow_completion", "idea/test/integration", "bbb222") in fake_gh.calls

    def test_skip_ci_wait_pushes_but_does_not_wait(self, tmp_path):
        """When skip_ci_wait=True, should push but not wait for CI."""
        initializer, fake_gh, pushed = self._setup_with_push_tracking(tmp_path)

        result = initializer.ensure_scaffolding_setup(
            _opts(skip_ci_wait=True), idea_directory=str(tmp_path),
            branch="idea/test/integration",
        )

        assert result is True
        assert pushed == ["idea/test/integration"]
        assert not any(call[0] == "wait_for_workflow_completion" for call in fake_gh.calls)

    def test_ci_failure_sets_branch_and_calls_build_fixer(self, tmp_path):
        """When CI fails, should set git_repo.branch and call build_fixer.fix_ci_failure()."""
        fake_fixer = FakeBuildFixer(result=True)
        initializer, fake_git = self._setup_ci_failure(
            tmp_path, ci_result=(False, {"name": "CI", "id": 123}), build_fixer=fake_fixer,
        )

        result = initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )

        assert result is True
        assert fake_fixer.calls == ["fix_ci_failure"]
        assert fake_git.branch == "idea/test/integration"

    def test_ci_failure_fix_fails_returns_false(self, tmp_path):
        """When CI fails and fix_ci_failure returns False, should return False."""
        fake_fixer = FakeBuildFixer(result=False)
        initializer, _ = self._setup_ci_failure(
            tmp_path, ci_result=(False, {"name": "CI", "id": 123}), build_fixer=fake_fixer,
        )

        result = initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )

        assert result is False

    def test_checkouts_branch(self, tmp_path):
        """Should checkout the branch before scaffolding."""
        fake_runner, fake_git, _ = self._make_fakes(tmp_path)
        fake_git.set_head_sha("abc123")

        initializer = self._make_initializer(
            fake_runner=fake_runner, git_repo=fake_git, push_fn=lambda branch: True,
        )

        initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )

        assert ("checkout", "idea/test/integration") in fake_git.calls

    def test_ci_failure_no_failing_run_returns_false(self, tmp_path):
        """When CI reports failure but no failing run, should return False."""
        initializer, _ = self._setup_ci_failure(
            tmp_path, ci_result=(False, None), build_fixer=None,
        )

        result = initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )

        assert result is False

    def test_guard_file_skips_scaffolding_on_second_call(self, tmp_path):
        """When guard file exists, should return True without running scaffolding."""
        fake_runner, fake_git, _ = self._make_fakes(tmp_path)
        fake_git.set_head_sha("abc123")

        initializer = self._make_initializer(
            fake_runner=fake_runner, git_repo=fake_git, push_fn=lambda branch: True,
        )

        # First call — runs scaffolding and creates guard file
        initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )
        assert len(fake_runner.calls) == 1

        # Second call — guard file exists, skips scaffolding
        result = initializer.ensure_scaffolding_setup(
            _opts(), idea_directory=str(tmp_path), branch="idea/test/integration",
        )
        assert result is True
        assert len(fake_runner.calls) == 1


def _create_idea_dir_in_git_repo(tmpdir, idea_name="test-feature"):
    """Create a temp git repo with a valid idea directory containing all required files."""
    from git import Repo
    repo = Repo.init(tmpdir)
    repo.config_writer().set_value("user", "email", "test@test.com").release()
    repo.config_writer().set_value("user", "name", "Test").release()

    idea_dir = os.path.join(tmpdir, "docs", "features", idea_name)
    os.makedirs(idea_dir)
    for suffix in ["idea.md", "discussion.md", "spec.md", "plan.md"]:
        with open(os.path.join(idea_dir, f"{idea_name}-{suffix}"), "w") as f:
            f.write(f"# {suffix}\n")

    repo.index.add([os.path.relpath(p, tmpdir) for p in _all_files(idea_dir)])
    repo.index.commit("Add idea files")
    return idea_dir


def _all_files(directory):
    """Return all file paths in directory."""
    result = []
    for root, _dirs, files in os.walk(directory):
        for name in files:
            result.append(os.path.join(root, name))
    return result


class FakeScaffoldingCreator:
    """Records run_scaffolding calls for testing scaffold_cmd."""

    def __init__(self):
        self.calls = []

    def run_scaffolding(self, idea_directory, cwd, interactive=True, mock_claude=None):
        self.calls.append({
            "idea_directory": idea_directory,
            "cwd": cwd,
            "interactive": interactive,
            "mock_claude": mock_claude,
        })


def _fake_assemble_scaffold(fake_creator):
    """Return an assemble_scaffold override that injects a fake ScaffoldingCreator."""
    def assemble(opts):
        from git import Repo
        from i2code.implement.idea_project import IdeaProject
        from i2code.implement.scaffold_command import ScaffoldCommand
        project = IdeaProject(opts.idea_directory)
        project.validate()
        project.validate_files()
        repo = Repo(project.directory, search_parent_directories=True)
        return ScaffoldCommand(opts, fake_creator, cwd=repo.working_tree_dir)
    return assemble


@pytest.mark.unit
class TestScaffoldCmd:
    """Test scaffold CLI command — no @patch."""

    def _invoke_scaffold(self, extra_args=None):
        from click.testing import CliRunner
        from i2code.implement.cli import scaffold_cmd

        with tempfile.TemporaryDirectory() as tmpdir:
            idea_dir = _create_idea_dir_in_git_repo(tmpdir)
            fake_initializer = FakeScaffoldingCreator()

            args = [idea_dir] + (extra_args or [])
            runner = CliRunner(catch_exceptions=False)
            result = runner.invoke(
                scaffold_cmd, args,
                obj={"command_factory": _fake_assemble_scaffold(fake_initializer)},
            )
            return result, fake_initializer, idea_dir, tmpdir

    def test_scaffold_validates_and_invokes_run_scaffolding(self):
        result, fake_initializer, idea_dir, tmpdir = self._invoke_scaffold()

        assert result.exit_code == 0
        assert len(fake_initializer.calls) == 1
        call = fake_initializer.calls[0]
        assert call["idea_directory"] == idea_dir
        assert call["cwd"] == tmpdir
        assert call["interactive"] is True
        assert call["mock_claude"] is None

    def test_scaffold_non_interactive_forwards_flag(self):
        result, fake_initializer, _, _ = self._invoke_scaffold(["--non-interactive"])

        assert result.exit_code == 0
        assert fake_initializer.calls[0]["interactive"] is False

    def test_scaffold_forwards_mock_claude(self):
        result, fake_initializer, _, _ = self._invoke_scaffold(["--mock-claude", "/mock.sh"])

        assert result.exit_code == 0
        assert fake_initializer.calls[0]["mock_claude"] == "/mock.sh"


