"""NumberedTask — a Task with its position in the plan."""

from dataclasses import dataclass

from i2code.plan_domain.task import Task


@dataclass
class TaskNumber:
    thread: int
    task: int


@dataclass
class NumberedTask:
    number: TaskNumber
    task: Task

    def print(self) -> str:
        n = self.number
        t = self.task
        lines = [
            f"Thread {n.thread}, Task {n.thread}.{n.task}: {t.title}",
            f"  TaskType: {t.task_type}",
            f"  Entrypoint: {t.entrypoint}",
            f"  Observable: {t.observable}",
            f"  Evidence: {t.evidence}",
            "  Steps:",
        ]
        for i, step in enumerate(t.steps, 1):
            status = 'x' if step['completed'] else ' '
            lines.append(f"    {i}. [{status}] {step['description']}")
        return '\n'.join(lines)
