"""Unit tests for Task.to_spec(), which returns a task.schema.json object."""

from i2code.plan_domain.task import Task


class TestTaskToSpec:

    def test_returns_schema_fields(self):
        task = Task(_lines=[
            '- [x] **Task 1.1: First task**',
            '  - TaskType: INFRA',
            '  - Entrypoint: `echo hello`',
            '  - Observable: Something happens',
            '  - Evidence: `echo done`',
            '  - Steps:',
            '    - [x] Do it',
            '    - [ ] Check it',
        ])

        assert task.to_spec() == {
            'title': 'First task',
            'task_type': 'INFRA',
            'entrypoint': 'echo hello',
            'observable': 'Something happens',
            'evidence': 'echo done',
            'steps': ['Do it', 'Check it'],
        }
