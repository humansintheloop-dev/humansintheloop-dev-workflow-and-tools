"""Unit tests for Task read-only properties."""

from i2code.plan_domain.task import Task


class TestTaskIsCompleted:

    def test_incomplete_task(self):
        task = Task(_lines=['- [ ] **Task 1.1: Foo**'])
        assert task.is_completed is False

    def test_completed_task(self):
        task = Task(_lines=['- [x] **Task 1.1: Foo**'])
        assert task.is_completed is True


class TestTaskTitle:

    def test_extracts_title(self):
        task = Task(_lines=['- [ ] **Task 1.1: First task**'])
        assert task.title == 'First task'


FULL_TASK_LINES = [
    '- [ ] **Task 1.1: First task**',
    '  - TaskType: INFRA',
    '  - Entrypoint: `echo hello`',
    '  - Observable: Something happens',
    '  - Evidence: `echo done`',
    '  - Steps:',
    '    - [ ] Step one',
    '    - [x] Step two',
]


class TestTaskMetadata:

    def test_task_type(self):
        task = Task(_lines=FULL_TASK_LINES)
        assert task.task_type == 'INFRA'

    def test_entrypoint_strips_backticks(self):
        task = Task(_lines=FULL_TASK_LINES)
        assert task.entrypoint == 'echo hello'

    def test_observable(self):
        task = Task(_lines=FULL_TASK_LINES)
        assert task.observable == 'Something happens'

    def test_evidence_strips_backticks(self):
        task = Task(_lines=FULL_TASK_LINES)
        assert task.evidence == 'echo done'

    def test_missing_metadata_returns_empty_string(self):
        task = Task(_lines=['- [ ] **Task 1.1: Bare**'])
        assert task.task_type == ''
        assert task.entrypoint == ''
        assert task.observable == ''
        assert task.evidence == ''


class TestTaskSteps:

    def test_returns_steps_with_completion(self):
        task = Task(_lines=FULL_TASK_LINES)
        assert task.steps == [
            {'description': 'Step one', 'completed': False},
            {'description': 'Step two', 'completed': True},
        ]

    def test_no_steps_returns_empty_list(self):
        task = Task(_lines=['- [ ] **Task 1.1: Bare**'])
        assert task.steps == []
