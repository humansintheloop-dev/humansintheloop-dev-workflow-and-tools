import pytest


def pytest_collection_modifyitems(items):
    for item in items:
        if "plan-domain" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
