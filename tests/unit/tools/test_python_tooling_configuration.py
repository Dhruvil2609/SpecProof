from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_pyright_uses_locked_workspace_virtual_environment() -> None:
    """Strict type checks must resolve the dependencies installed by uv sync."""
    configuration = tomllib.loads((WORKSPACE / "pyproject.toml").read_text(encoding="utf-8"))
    pyright = configuration["tool"]["pyright"]

    assert pyright["venvPath"] == "."
    assert pyright["venv"] == ".venv"
