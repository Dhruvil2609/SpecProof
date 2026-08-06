"""Shared pytest configuration and fixtures for SpecProof test suite.

Overrides the built-in ``tmp_path`` fixture to use a workspace-local
directory (``tests/_tmp``) instead of the Windows system temp folder,
which may be blocked by Application Control policy.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest


@pytest.fixture()
def tmp_path(request: pytest.FixtureRequest) -> Path:  # type: ignore[override]
    """Return a per-test temporary directory inside the workspace.

    Uses ``tests/_tmp/<test-node-safe-name>/`` to avoid Windows
    ``AppData\\Local\\Temp`` permission errors under Application Control.
    """
    base = Path(__file__).parent / "_tmp"
    # Use a short unique suffix to avoid collisions between parameterised tests
    safe_name = request.node.nodeid.replace("::", "_").replace("/", "_").replace("\\", "_")
    # Truncate to avoid path-length issues on Windows
    safe_name = safe_name[:80] + "_" + uuid.uuid4().hex[:8]
    test_dir = base / safe_name
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Clean up after each test
    shutil.rmtree(test_dir, ignore_errors=True)
