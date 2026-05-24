"""Shared pytest configuration and fixtures."""

import os
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: tests requiring GROQ_API_KEY (skipped when key is absent)",
    )


def pytest_collection_modifyitems(config, items):
    if os.getenv("GROQ_API_KEY"):
        return
    skip_integration = pytest.mark.skip(
        reason="GROQ_API_KEY non définie — tests d'intégration ignorés"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)
