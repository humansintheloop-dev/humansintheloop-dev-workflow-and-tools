"""Unit tests for Thread.create() factory method."""

from i2code.plan_domain.thread import Thread


class TestThreadCreate:

    def test_creates_thread_with_correct_header_and_tasks(self):
        thread = Thread.create(
            title='Setup Infrastructure',
            introduction='Set up the base infrastructure.',
            tasks=[
                {
                    'title': 'Create database',
                    'task_type': 'INFRA',
                    'entrypoint': 'echo create',
                    'observable': 'Database exists',
                    'evidence': 'echo verify',
                    'steps': ['Run migration', 'Seed data'],
                },
            ],
        )

        assert len(thread.tasks) == 1
        assert thread.tasks[0].title == 'Create database'
        assert thread.tasks[0].task_type == 'INFRA'
        assert thread.tasks[0].steps == [
            {'description': 'Run migration', 'completed': False},
            {'description': 'Seed data', 'completed': False},
        ]

    def test_to_lines_produces_correctly_numbered_output(self):
        thread = Thread.create(
            title='Setup Infrastructure',
            introduction='Set up the base infrastructure.',
            tasks=[
                {
                    'title': 'Create database',
                    'task_type': 'INFRA',
                    'entrypoint': 'echo create',
                    'observable': 'Database exists',
                    'evidence': 'echo verify',
                    'steps': ['Run migration'],
                },
            ],
        )

        lines = thread.to_lines(thread_number=2)

        assert lines[0] == '## Steel Thread 2: Setup Infrastructure'
        assert lines[1] == 'Set up the base infrastructure.'
        assert lines[2] == ''
        assert '- [ ] **Task 2.1: Create database**' in lines
