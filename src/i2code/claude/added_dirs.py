"""Directories `i2code --add-dir` gives Claude access to."""

import os
from pathlib import Path
from typing import Iterable, List

ADDED_DIRS_ENV = "I2CODE_ADD_DIRS"


def use_added_dirs(directories: Iterable[str]) -> None:
    absolute_dirs = [str(Path(directory).resolve()) for directory in directories]
    os.environ[ADDED_DIRS_ENV] = os.pathsep.join(absolute_dirs)


def added_dirs() -> List[str]:
    value = os.environ.get(ADDED_DIRS_ENV)
    return value.split(os.pathsep) if value else []
