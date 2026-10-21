"""CLI integration tests for get-task command."""

import json

from click.testing import CliRunner

from i2code.plan.plan_cli import get_task_cmd

from test_get_thread_cli import PLAN_WITH_TWO_THREADS


def _invoke(plan_file, *args):
    runner = CliRunner(catch_exceptions=False)
    return runner.invoke(get_task_cmd, [str(plan_file), *args])


class TestGetTaskCli:

    def test_json_outputs_task_object(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        result = _invoke(plan_file, "--thread", "1", "--task", "2", "--json")

        assert result.exit_code == 0
        assert json.loads(result.output) == {
            "title": "Pending task",
            "task_type": "OUTCOME",
            "entrypoint": "echo run",
            "observable": "Feature works",
            "evidence": "pytest tests/",
            "steps": ["Write the test", "Implement the code", "Verify it works"],
        }

    def test_outputs_task_text_with_completion_state(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        result = _invoke(plan_file, "--thread", "1", "--task", "2")

        assert result.exit_code == 0
        assert "- [ ] Task 1.2: Pending task" in result.output
        assert "Entrypoint: echo run" in result.output
        assert "2. [x] Implement the code" in result.output

    def test_error_on_nonexistent_task(self, tmp_path):
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(PLAN_WITH_TWO_THREADS)

        result = _invoke(plan_file, "--thread", "1", "--task", "9", "--json")

        assert result.exit_code == 1
        assert "task 9 does not exist" in result.output
