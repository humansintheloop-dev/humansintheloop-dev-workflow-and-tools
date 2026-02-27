"""Unit tests for Task.create() factory method."""

from i2code.plan_domain.task import Task, TaskMetadata


class TestTaskCreate:

    def test_creates_task_with_correct_properties(self):
        task = Task.create(
            'Set up database',
            TaskMetadata('INFRA', 'uv run pytest tests/', 'Database schema created', 'uv run pytest tests/ -v'),
            ['Create migration', 'Run migration'],
        )

        assert task.title == 'Set up database'
        assert task.task_type == 'INFRA'
        assert task.entrypoint == 'uv run pytest tests/'
        assert task.observable == 'Database schema created'
        assert task.evidence == 'uv run pytest tests/ -v'
        assert task.is_completed is False
        assert task.steps == [
            {'description': 'Create migration', 'completed': False},
            {'description': 'Run migration', 'completed': False},
        ]

    def test_to_lines_produces_correctly_numbered_output(self):
        task = Task.create(
            'Add endpoint',
            TaskMetadata('OUTCOME', 'curl localhost:8080/api', 'Returns 200 OK', 'uv run pytest tests/api/'),
            ['Write test', 'Implement handler'],
        )

        lines = task.to_lines(thread_num=3, task_num=2)

        assert lines == [
            '- [ ] **Task 3.2: Add endpoint**',
            '  - TaskType: OUTCOME',
            '  - Entrypoint: `curl localhost:8080/api`',
            '  - Observable: Returns 200 OK',
            '  - Evidence: `uv run pytest tests/api/`',
            '  - Steps:',
            '    - [ ] Write test',
            '    - [ ] Implement handler',
        ]
