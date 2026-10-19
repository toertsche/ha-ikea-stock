"""Test-Setup für pytest-homeassistant-custom-component."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Custom-Integration im Testlauf zulassen."""
    yield
