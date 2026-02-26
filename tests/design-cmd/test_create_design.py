"""Tests for create_design: validates files, archives existing design, renders template, invokes Claude."""

import os
import sys

import pytest

from conftest import TempIdeaProject
from i2code.implement.claude_runner import ClaudeResult
from i2code.design_cmd.create_design import create_design

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "implement"))
from fake_claude_runner import FakeClaudeRunner


def _create_idea_file(project, content="My idea"):
    path = os.path.join(project.directory, f"{project.name}-idea.md")
    with open(path, "w") as f:
        f.write(content)


def _create_spec_file(project, content="My spec"):
    path = os.path.join(project.directory, f"{project.name}-spec.md")
    with open(path, "w") as f:
        f.write(content)


def _create_design_file(project, content="Old design"):
    path = os.path.join(project.directory, f"{project.name}-design.md")
    with open(path, "w") as f:
        f.write(content)


def _setup_project(project):
    """Create idea and spec files for a valid project."""
    _create_idea_file(project)
    _create_spec_file(project)


def _fake_plugin_skills():
    return "idea-to-code:tdd, idea-to-code:commit-guidelines"


def _run_create_design(project, runner=None, plugin_skills_fn=None):
    """Run create_design with a ready project and return (runner, result, method, cmd, cwd)."""
    _setup_project(project)
    if runner is None:
        runner = FakeClaudeRunner()
    if plugin_skills_fn is None:
        plugin_skills_fn = _fake_plugin_skills
    result = create_design(project, runner, plugin_skills_fn=plugin_skills_fn)
    method, cmd, cwd = runner.calls[0]
    return runner, result, method, cmd, cwd


@pytest.mark.unit
class TestCreateDesignValidation:

    def test_exits_when_idea_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            _create_spec_file(project)
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                create_design(project, runner, plugin_skills_fn=_fake_plugin_skills)
            assert len(runner.calls) == 0

    def test_exits_when_spec_file_missing(self):
        with TempIdeaProject("my-feature") as project:
            _create_idea_file(project)
            runner = FakeClaudeRunner()
            with pytest.raises(SystemExit):
                create_design(project, runner, plugin_skills_fn=_fake_plugin_skills)
            assert len(runner.calls) == 0


@pytest.mark.unit
class TestCreateDesignArchive:

    def test_archives_existing_design_file(self):
        with TempIdeaProject("my-feature") as project:
            _setup_project(project)
            _create_design_file(project, "Old design content")

            runner = FakeClaudeRunner()
            create_design(project, runner, plugin_skills_fn=_fake_plugin_skills)

            # Design file should no longer exist at original path
            assert not os.path.isfile(project.design_file)

            # Should exist in archive/ subdirectory
            archive_dir = os.path.join(project.directory, "archive")
            assert os.path.isdir(archive_dir)
            archived_files = os.listdir(archive_dir)
            assert len(archived_files) == 1
            assert archived_files[0].startswith("my-feature-design-")
            assert archived_files[0].endswith(".md")

            # Archived file should have original content
            archived_path = os.path.join(archive_dir, archived_files[0])
            with open(archived_path) as f:
                assert f.read() == "Old design content"

    def test_no_archive_when_no_existing_design(self):
        with TempIdeaProject("my-feature") as project:
            _setup_project(project)

            runner = FakeClaudeRunner()
            create_design(project, runner, plugin_skills_fn=_fake_plugin_skills)

            archive_dir = os.path.join(project.directory, "archive")
            assert not os.path.isdir(archive_dir)


@pytest.mark.unit
class TestCreateDesignTemplateRendering:

    def test_renders_template_with_all_variables(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_design(project)
            prompt = cmd[-1]
            assert project.idea_file in prompt
            assert project.discussion_file in prompt
            assert project.spec_file in prompt

    def test_renders_template_with_design_skills(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_design(project)
            prompt = cmd[-1]
            assert "idea-to-code:tdd" in prompt
            assert "idea-to-code:commit-guidelines" in prompt


@pytest.mark.unit
class TestCreateDesignSessionManagement:

    def test_resumes_session_when_session_file_exists(self):
        with TempIdeaProject("my-feature") as project:
            _setup_project(project)
            with open(project.session_id_file, "w") as f:
                f.write("existing-session-id")

            runner = FakeClaudeRunner()
            create_design(project, runner, plugin_skills_fn=_fake_plugin_skills)

            _, cmd, _ = runner.calls[0]
            assert "--resume" in cmd
            assert "existing-session-id" in cmd

    def test_no_resume_when_no_session_file(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_design(project)
            assert "--resume" not in cmd


@pytest.mark.unit
class TestCreateDesignClaudeInvocation:

    def test_invokes_claude_interactively(self):
        with TempIdeaProject("my-feature") as project:
            _, _, method, _, _ = _run_create_design(project)
            assert method == "run_interactive"

    def test_claude_command_starts_with_claude(self):
        with TempIdeaProject("my-feature") as project:
            _, _, _, cmd, _ = _run_create_design(project)
            assert cmd[0] == "claude"

    def test_returns_claude_result(self):
        with TempIdeaProject("my-feature") as project:
            runner = FakeClaudeRunner()
            runner.set_result(ClaudeResult(returncode=0))
            _, result, _, _, _ = _run_create_design(project, runner)
            assert result.returncode == 0
