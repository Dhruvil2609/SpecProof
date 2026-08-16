from __future__ import annotations

from pathlib import Path

import pytest

from tools.security.scan_secrets import scan_paths, tracked_paths

WORKSPACE = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_secret_scanner_private_key_detects_forbidden_material(tmp_path: Path) -> None:
    secret = tmp_path / "secret.txt"
    private_key = "-----BEGIN PRIVATE " + "KEY-----\nmaterial\n"
    secret.write_text(private_key, encoding="utf-8")

    findings = scan_paths([Path("secret.txt")], tmp_path)

    assert [(finding.kind, finding.line) for finding in findings] == [("private_key", 1)]


@pytest.mark.unit
def test_secret_scanner_provider_token_detects_credential(tmp_path: Path) -> None:
    token = tmp_path / "config.txt"
    token.write_text(f"token={'ghp_' + ('a' * 36)}\n", encoding="utf-8")

    findings = scan_paths([Path("config.txt")], tmp_path)

    assert {finding.kind for finding in findings} == {"github_token"}


@pytest.mark.unit
def test_secret_scanner_deployment_placeholder_allows_template(tmp_path: Path) -> None:
    template = tmp_path / ".env.example"
    template.write_text("SIGNING_SECRET=replace-at-deployment\n", encoding="utf-8")

    assert scan_paths([Path(".env.example")], tmp_path) == ()


@pytest.mark.unit
def test_secret_scanner_tracked_workspace_has_no_credential_material() -> None:
    findings = scan_paths(tracked_paths(WORKSPACE), WORKSPACE)

    assert findings == (), "\n".join(
        f"{finding.path}:{finding.line} {finding.kind}" for finding in findings
    )
