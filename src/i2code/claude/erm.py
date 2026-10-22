"""Eventuate repo manager (ERM) workspace: the parent directory holding a .erm directory."""

import os
from pathlib import Path
from typing import Optional

import click

ERM_ROOT_ENV = "I2CODE_ERM_ROOT"


def find_erm_root(start: Path) -> Path:
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / ".erm").is_dir():
            return directory
    raise click.ClickException(f"No .erm directory found above {start}")


def use_erm_root(start: Path) -> None:
    os.environ[ERM_ROOT_ENV] = str(find_erm_root(start))


def erm_root() -> Optional[str]:
    return os.environ.get(ERM_ROOT_ENV)
