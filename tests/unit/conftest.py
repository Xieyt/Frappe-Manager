"""
Shared pytest fixtures for all unit tests.

This module provides fixtures that are automatically available to all unit tests.
"""

import os

import pytest

from frappe_manager.logger import reset_context
from frappe_manager.output_manager import set_global_output_handler
from frappe_manager.output_manager.rich_output import RichOutputHandler


@pytest.fixture(autouse=True, scope="session")
def _plain_output():
    """Assertions read what fm SAID, not how a terminal would paint it.

    A GitHub runner makes rich emit colour, which lands escape sequences INSIDE a refusal, so a
    test searching for the plain phrase fails there and passes locally for reasons unconnected to
    the code. NO_COLOR is the cross-tool convention rich honours, and it leaves markup parsing
    (which other tests pin) untouched.
    """
    os.environ["NO_COLOR"] = "1"
    yield
    os.environ.pop("NO_COLOR", None)


@pytest.fixture(autouse=True)
def clean_ambient_log_context():
    """Ambient logging context is process-global state; never bleed across tests."""
    reset_context()
    yield
    reset_context()


@pytest.fixture(autouse=True)
def init_global_output_handler():
    """
    Initialize global output handler for all tests.

    This fixture runs automatically before every test to ensure the global
    output handler is initialized, which is required by app_callback() and
    other functions that use get_global_output_handler().

    After each test, the handler is reset to None to ensure test isolation.
    """
    # Initialize with a basic RichOutputHandler (no logging)
    handler = RichOutputHandler()
    set_global_output_handler(handler)

    yield

    # Reset after test to ensure isolation
    set_global_output_handler(None)
