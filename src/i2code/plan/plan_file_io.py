"""Plan file I/O: atomic writes and context managers for reading/updating plans."""

import os
import sys
import tempfile
from contextlib import contextmanager

import click

from i2code.plan._helpers import append_change_history
from i2code.plan_domain.parser import parse


def atomic_write(file_path: str, content: str) -> None:
    """Write content to file atomically using temp file + rename."""
    dir_name = os.path.dirname(os.path.abspath(file_path))
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        os.rename(tmp_path, file_path)
    except Exception:
        os.unlink(tmp_path)
        raise


@contextmanager
def with_error_handling():
    try:
        yield
    except ValueError as e:
        click.echo(str(e), err=True)
        sys.exit(1)


@contextmanager
def with_plan_file(plan_file):
    with open(plan_file, "r", encoding="utf-8") as f:
        yield parse(f.read())


@contextmanager
def with_plan_file_update(plan_file, operation=None, rationale=None):
    with open(plan_file, "r", encoding="utf-8") as f:
        original_text = f.read()
    domain_plan = parse(original_text)
    yield domain_plan
    result = domain_plan.to_text()
    if operation is not None and rationale is not None:
        result = append_change_history(result, operation, rationale)
    if result != original_text:
        atomic_write(plan_file, result)
