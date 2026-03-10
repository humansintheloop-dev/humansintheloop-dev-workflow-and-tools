"""CLI integration tests for i2code idea state."""

import os
import subprocess

import pytest
import yaml
from click.testing import CliRunner

from i2code.cli import main


def _create_idea(base, state, name):
    """Create an idea directory under docs/ideas/{state}/{name}/ with a placeholder file."""
    idea_dir = os.path.join(base, "docs", "ideas", state, name)
    os.makedirs(idea_dir, exist_ok=True)
    placeholder = os.path.join(idea_dir, "idea.md")
    with open(placeholder, "w") as f:
        f.write(f"# {name}\n")
    return idea_dir


def _create_active_idea(base, name, state="draft"):
    """Create an idea in docs/ideas/active/<name>/ with a metadata file."""
    idea_dir = os.path.join(base, "docs", "ideas", "active", name)
    os.makedirs(idea_dir, exist_ok=True)
    metadata_path = os.path.join(idea_dir, f"{name}-metadata.yaml")
    with open(metadata_path, "w") as f:
        yaml.safe_dump({"state": state}, f)
    placeholder = os.path.join(idea_dir, f"{name}-idea.md")
    with open(placeholder, "w") as f:
        f.write(f"# {name}\n")
    return idea_dir


def _create_plan_file(base, state, name):
    """Create a plan file inside an idea directory."""
    plan_path = os.path.join(base, "docs", "ideas", state, name, f"{name}-plan.md")
    with open(plan_path, "w") as f:
        f.write(f"# {name} plan\n")
    return plan_path


def _create_active_plan_file(base, name):
    """Create a plan file inside an active idea directory."""
    plan_path = os.path.join(base, "docs", "ideas", "active", name, f"{name}-plan.md")
    with open(plan_path, "w") as f:
        f.write(f"# {name} plan\n")
    return plan_path


def _invoke_idea_state(runner, name_or_path):
    """Invoke `i2code idea state <name-or-path>` and return the result."""
    return runner.invoke(main, ["idea", "state", name_or_path])


def _invoke_transition(runner, name, new_state, force=False):
    """Invoke `i2code idea state <name> <new-state>` and return the result."""
    args = ["idea", "state", name, new_state]
    if force:
        args.append("--force")
    return runner.invoke(main, args)


def _init_git_repo(path):
    """Initialize a git repo and make an initial commit."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, check=True, capture_output=True,
    )


def _git_add_and_commit(path, message):
    """Stage all files and create a commit."""
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=path, check=True, capture_output=True,
    )


def _last_commit_message(path):
    """Return the most recent commit message."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=path, check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def cli(tmp_path, monkeypatch):
    """CliRunner rooted at tmp_path."""
    monkeypatch.chdir(tmp_path)
    return CliRunner()


@pytest.fixture
def git_repo(tmp_path):
    """A tmp_path that is an initialized git repository."""
    _init_git_repo(tmp_path)
    return tmp_path


def _committed_idea(git_repo, state, name, with_plan=False):
    """Create an idea in a git repo and commit it. Returns the repo path."""
    _create_idea(git_repo, state, name)
    if with_plan:
        _create_plan_file(git_repo, state, name)
    _git_add_and_commit(git_repo, "Initial commit")
    return git_repo


def _committed_active_idea(git_repo, name, state="draft", with_plan=False):
    """Create an active idea in a git repo and commit it. Returns the repo path."""
    _create_active_idea(git_repo, name, state)
    if with_plan:
        _create_active_plan_file(git_repo, name)
    _git_add_and_commit(git_repo, "Initial commit")
    return git_repo


@pytest.mark.unit
class TestIdeaStateQuery:

    def test_returns_state_from_metadata_file(self, tmp_path, cli):
        _create_active_idea(tmp_path, "my-feature", state="draft")

        result = _invoke_idea_state(cli, "my-feature")

        assert result.exit_code == 0
        assert result.output.strip() == "draft"

    def test_returns_wip_state_from_metadata(self, tmp_path, cli):
        _create_active_idea(tmp_path, "active-project", state="wip")

        result = _invoke_idea_state(cli, "active-project")

        assert result.exit_code == 0
        assert result.output.strip() == "wip"

    def test_returns_completed_state_from_metadata(self, tmp_path, cli):
        _create_active_idea(tmp_path, "done-idea", state="completed")

        result = _invoke_idea_state(cli, "done-idea")

        assert result.exit_code == 0
        assert result.output.strip() == "completed"

    def test_returns_state_when_queried_by_path(self, tmp_path, cli):
        _create_active_idea(tmp_path, "path-idea", state="ready")

        result = _invoke_idea_state(cli, "docs/ideas/active/path-idea")

        assert result.exit_code == 0
        assert result.output.strip() == "ready"


@pytest.mark.unit
class TestIdeaStateByName:

    def test_returns_state_for_known_idea(self, tmp_path, cli):
        _create_idea(tmp_path, "draft", "my-feature")

        result = _invoke_idea_state(cli, "my-feature")

        assert result.exit_code == 0
        assert result.output.strip() == "draft"

    def test_returns_wip_state(self, tmp_path, cli):
        _create_idea(tmp_path, "wip", "active-project")

        result = _invoke_idea_state(cli, "active-project")

        assert result.exit_code == 0
        assert result.output.strip() == "wip"


@pytest.mark.unit
class TestIdeaStateByPath:

    def test_returns_state_for_directory_path(self, tmp_path, cli):
        _create_idea(tmp_path, "ready", "path-idea")
        idea_path = os.path.join(
            str(tmp_path), "docs", "ideas", "ready", "path-idea"
        )

        result = _invoke_idea_state(cli, idea_path)

        assert result.exit_code == 0
        assert result.output.strip() == "ready"

    def test_returns_state_for_relative_directory_path(self, tmp_path, cli):
        _create_idea(tmp_path, "completed", "done-idea")

        result = _invoke_idea_state(cli, "docs/ideas/completed/done-idea")

        assert result.exit_code == 0
        assert result.output.strip() == "completed"


@pytest.mark.unit
class TestIdeaStateErrors:

    def test_unknown_name_returns_error(self, tmp_path, cli):
        _create_idea(tmp_path, "draft", "other-idea")

        result = _invoke_idea_state(cli, "nonexistent")

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


@pytest.mark.unit
class TestIdeaStateTransition:

    def test_moves_idea_directory_and_creates_commit(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")

        result = _invoke_transition(cli, "my-feature", "completed")

        assert result.exit_code == 0
        new_dir = git_repo / "docs" / "ideas" / "completed" / "my-feature"
        old_dir = git_repo / "docs" / "ideas" / "wip" / "my-feature"
        assert new_dir.is_dir()
        assert not old_dir.exists()
        assert _last_commit_message(git_repo) == "Move idea my-feature from wip to completed"


@pytest.mark.unit
class TestIdeaStateTransitionNoop:

    def test_noop_when_already_in_target_state(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")

        result = _invoke_transition(cli, "my-feature", "wip")

        assert result.exit_code == 0
        assert "already" in result.output.lower()
        assert _last_commit_message(git_repo) == "Initial commit"


@pytest.mark.unit
class TestTransitionRuleBackwardBlocked:

    def test_backward_move_is_blocked(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")

        result = _invoke_transition(cli, "my-feature", "draft")

        assert result.exit_code == 1
        assert "backward" in result.output.lower()
        assert "--force" in result.output


@pytest.mark.unit
class TestTransitionRulePlanRequired:

    def test_draft_to_ready_blocked_without_plan(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature")

        result = _invoke_transition(cli, "my-feature", "ready")

        assert result.exit_code == 1
        assert "plan" in result.output.lower()
        assert "--force" in result.output

    def test_ready_to_wip_blocked_without_plan(self, git_repo, cli):
        _committed_idea(git_repo, "ready", "my-feature")

        result = _invoke_transition(cli, "my-feature", "wip")

        assert result.exit_code == 1
        assert "plan" in result.output.lower()
        assert "--force" in result.output

    def test_draft_to_ready_allowed_with_plan(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature", with_plan=True)

        result = _invoke_transition(cli, "my-feature", "ready")

        assert result.exit_code == 0
        assert "ready" in result.output.lower()

    def test_ready_to_wip_allowed_with_plan(self, git_repo, cli):
        _committed_idea(git_repo, "ready", "my-feature", with_plan=True)

        result = _invoke_transition(cli, "my-feature", "wip")

        assert result.exit_code == 0
        assert "wip" in result.output.lower()


@pytest.mark.unit
class TestTransitionRuleAlwaysAllowed:

    def test_any_to_abandoned_is_allowed(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature")

        result = _invoke_transition(cli, "my-feature", "abandoned")

        assert result.exit_code == 0
        assert "abandoned" in result.output.lower()

    def test_wip_to_abandoned_is_allowed(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")

        result = _invoke_transition(cli, "my-feature", "abandoned")

        assert result.exit_code == 0
        assert "abandoned" in result.output.lower()

    def test_wip_to_completed_is_allowed(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")

        result = _invoke_transition(cli, "my-feature", "completed")

        assert result.exit_code == 0
        assert "completed" in result.output.lower()


@pytest.mark.unit
class TestTransitionRuleSkipBlocked:

    def test_skipping_states_is_blocked(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature")

        result = _invoke_transition(cli, "my-feature", "wip")

        assert result.exit_code == 1
        assert "skipping" in result.output.lower()
        assert "--force" in result.output


@pytest.mark.unit
class TestTransitionForceOverride:

    def test_force_allows_backward_move(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")

        result = _invoke_transition(cli, "my-feature", "draft", force=True)

        assert result.exit_code == 0
        assert (git_repo / "docs" / "ideas" / "draft" / "my-feature").is_dir()

    def test_force_allows_state_skip(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature")

        result = _invoke_transition(cli, "my-feature", "wip", force=True)

        assert result.exit_code == 0
        assert (git_repo / "docs" / "ideas" / "wip" / "my-feature").is_dir()

    def test_force_allows_transition_without_plan(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature")

        result = _invoke_transition(cli, "my-feature", "ready", force=True)

        assert result.exit_code == 0
        assert (git_repo / "docs" / "ideas" / "ready" / "my-feature").is_dir()


@pytest.mark.unit
class TestIdeaStatePathWithInvalidState:

    def test_path_with_misspelled_state_reports_invalid_state(self, tmp_path, cli):
        _create_idea(tmp_path, "draft", "simple-banking")

        result = _invoke_idea_state(cli, "docs/ideas/drafts/simple-banking")

        assert result.exit_code == 1
        assert "drafts" in result.output
        assert "draft" in result.output
        assert "valid" in result.output.lower() or "Valid" in result.output


@pytest.mark.unit
class TestIdeaStateTransitionByPath:

    def test_transitions_idea_when_given_path(self, git_repo, cli):
        _committed_idea(git_repo, "wip", "my-feature")
        idea_path = os.path.join(str(git_repo), "docs", "ideas", "wip", "my-feature")

        result = _invoke_transition(cli, idea_path, "completed")

        assert result.exit_code == 0
        assert (git_repo / "docs" / "ideas" / "completed" / "my-feature").is_dir()
        assert not (git_repo / "docs" / "ideas" / "wip" / "my-feature").exists()

    def test_transitions_idea_when_given_relative_path(self, git_repo, cli):
        _committed_idea(git_repo, "draft", "my-feature", with_plan=True)

        result = _invoke_transition(cli, "docs/ideas/draft/my-feature", "ready")

        assert result.exit_code == 0
        assert (git_repo / "docs" / "ideas" / "ready" / "my-feature").is_dir()


@pytest.mark.unit
class TestIdeaStateTransitionUntracked:

    def test_moves_untracked_idea_directory(self, git_repo, cli):
        # Make an initial commit so the repo isn't empty
        readme = git_repo / "README.md"
        readme.write_text("# test\n")
        _git_add_and_commit(git_repo, "Initial commit")
        # Create idea files but do NOT stage or commit them
        _create_idea(git_repo, "draft", "new-feature")
        _create_plan_file(git_repo, "draft", "new-feature")

        result = _invoke_transition(cli, "docs/ideas/draft/new-feature", "ready")

        assert result.exit_code == 0
        assert (git_repo / "docs" / "ideas" / "ready" / "new-feature").is_dir()
        assert not (git_repo / "docs" / "ideas" / "draft" / "new-feature").exists()


@pytest.mark.unit
class TestIdeaStateTransitionGitError:

    def test_reports_git_error_when_target_exists(self, git_repo, cli):
        _create_idea(git_repo, "wip", "my-feature")
        _create_idea(git_repo, "completed", "my-feature")
        _git_add_and_commit(git_repo, "Initial commit")

        result = _invoke_transition(cli, "my-feature", "completed")

        assert result.exit_code == 1
        assert "my-feature" in result.output
