import os
import sys

import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, project_root)


def pytest_addoption(parser):
    parser.addoption(
        "--persist-dir",
        action="store",
        default=None,
        help="Directory to persist test case outputs for debugging.",
    )


@pytest.fixture
def persist_dir(request):
    """
    Pytest fixture to retrieve the value of the --persist-dir option.
    """
    return request.config.getoption("--persist-dir")
