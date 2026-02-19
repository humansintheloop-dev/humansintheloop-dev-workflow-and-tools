import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "setup-cmd" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
