"""Fixtures shared by every test."""

import pytest

from i2code.claude.erm import ERM_ROOT_ENV


@pytest.fixture(autouse=True)
def without_erm_root(monkeypatch):
    """Clear the ERM root so neither the shell nor `i2code --erm` leaks into a test."""
    monkeypatch.setenv(ERM_ROOT_ENV, "placeholder")
    monkeypatch.delenv(ERM_ROOT_ENV)
