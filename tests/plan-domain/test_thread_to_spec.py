"""Unit tests for Thread.to_spec(), which returns a thread.schema.json object."""

from i2code.plan_domain.task import Task
from i2code.plan_domain.thread import Thread


class TestThreadToSpec:

    def test_returns_title_introduction_and_task_specs(self):
        task = Task(_lines=[
            '- [ ] **Task 1.1: First task**',
            '  - TaskType: INFRA',
            '  - Entrypoint: `echo hello`',
            '  - Observable: Something happens',
            '  - Evidence: `echo done`',
            '  - Steps:',
            '    - [ ] Do it',
        ])
        thread = Thread(
            _header_lines=['## Steel Thread 1: Setup', 'First paragraph.', '', 'Second paragraph.', ''],
            tasks=[task],
        )

        assert thread.to_spec() == {
            'title': 'Setup',
            'introduction': 'First paragraph.\n\nSecond paragraph.',
            'tasks': [task.to_spec()],
        }
