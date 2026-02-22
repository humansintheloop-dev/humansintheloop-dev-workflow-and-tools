"""Directory-based test cases for setup_tracking."""

from pathlib import Path

import pytest

from i2code.tracking.manage import setup_tracking

from conftest import create_tree, assert_tree

CASES_DIR = Path(__file__).parent / "cases"

ALL_CASES = [d.name for d in sorted(CASES_DIR.iterdir()) if d.is_dir()]


@pytest.mark.unit
@pytest.mark.parametrize("case", ALL_CASES)
def test_case(case, tmp_path):
    case_dir = CASES_DIR / case
    create_tree(tmp_path, case_dir / "before")
    link_target = tmp_path / "link-target"
    target_link = str(link_target) if link_target.exists() else None
    setup_tracking(str(tmp_path / "project"), target_link=target_link)
    assert_tree(tmp_path, case_dir / "before", case_dir / "after")
