"""CLI integration tests for i2code plan create and i2code plan revise."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from i2code.cli import main


@pytest.mark.unit
class TestPlanCreateCommandRegistered:

    def test_plan_create_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "create", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_plan_create_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "create"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestPlanReviseCommandRegistered:

    def test_plan_revise_listed_in_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "revise", "--help"])
        assert result.exit_code == 0
        assert "directory" in result.output.lower()

    def test_plan_revise_requires_directory_argument(self):
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "revise"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestPlanCreateInvokesPythonFunction:

    @pytest.fixture
    def plan_create_mocks(self):
        with patch("i2code.plan.cli.create_plan") as mock_fn, \
             patch("i2code.plan.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            yield mock_fn, mock_runner

    def test_invokes_create_plan(self, tmp_path, plan_create_mocks):
        mock_fn, _ = plan_create_mocks
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "create", str(tmp_path)])
        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_constructs_idea_project_with_directory(self, tmp_path, plan_create_mocks):
        mock_fn, _ = plan_create_mocks
        runner = CliRunner()
        runner.invoke(main, ["plan", "create", str(tmp_path)])
        project = mock_fn.call_args[0][0]
        assert project.directory == str(tmp_path)

    def test_passes_claude_runner_instance(self, tmp_path, plan_create_mocks):
        mock_fn, mock_runner = plan_create_mocks
        runner = CliRunner()
        runner.invoke(main, ["plan", "create", str(tmp_path)])
        assert mock_fn.call_args[0][1] is mock_runner

    def test_passes_plan_services(self, tmp_path, plan_create_mocks):
        mock_fn, _ = plan_create_mocks
        runner = CliRunner()
        runner.invoke(main, ["plan", "create", str(tmp_path)])
        services = mock_fn.call_args[0][2]
        assert callable(services.template_renderer)
        assert callable(services.plugin_skills_fn)
        assert callable(services.validator_fn)


@pytest.mark.unit
class TestPlanReviseInvokesPythonFunction:

    @pytest.fixture
    def plan_revise_mocks(self):
        with patch("i2code.plan.cli.revise_plan") as mock_fn, \
             patch("i2code.plan.cli.ClaudeRunner") as mock_runner_cls:
            mock_runner = MagicMock()
            mock_runner_cls.return_value = mock_runner
            mock_fn.return_value = MagicMock(returncode=0)
            yield mock_fn, mock_runner

    def test_invokes_revise_plan(self, tmp_path, plan_revise_mocks):
        mock_fn, _ = plan_revise_mocks
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "revise", str(tmp_path)])
        assert result.exit_code == 0
        mock_fn.assert_called_once()

    def test_constructs_idea_project_with_directory(self, tmp_path, plan_revise_mocks):
        mock_fn, _ = plan_revise_mocks
        runner = CliRunner()
        runner.invoke(main, ["plan", "revise", str(tmp_path)])
        project = mock_fn.call_args[0][0]
        assert project.directory == str(tmp_path)

    def test_passes_claude_runner_instance(self, tmp_path, plan_revise_mocks):
        mock_fn, mock_runner = plan_revise_mocks
        runner = CliRunner()
        runner.invoke(main, ["plan", "revise", str(tmp_path)])
        assert mock_fn.call_args[0][1] is mock_runner
