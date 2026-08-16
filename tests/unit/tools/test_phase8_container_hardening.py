from __future__ import annotations

from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[3]


@pytest.mark.unit
def test_application_images_are_non_root_health_checked_and_labelled() -> None:
    dockerfiles = (
        "apps/platform-api/Dockerfile",
        "apps/measurement-service/Dockerfile",
        "apps/operator-ui/Dockerfile",
        "apps/admin-ui/Dockerfile",
    )
    for relative_path in dockerfiles:
        dockerfile = (WORKSPACE / relative_path).read_text(encoding="utf-8")
        assert "\nUSER " in dockerfile
        assert "\nHEALTHCHECK " in dockerfile
        assert "org.opencontainers.image.title" in dockerfile
        assert "org.opencontainers.image.vendor" in dockerfile


@pytest.mark.unit
def test_application_compose_drops_privileges_and_uses_read_only_filesystems() -> None:
    compose = (WORKSPACE / "docker-compose.yml").read_text(encoding="utf-8")

    assert compose.count("    read_only: true") >= 4
    assert compose.count("    cap_drop: [ALL]") >= 4
    assert compose.count("    security_opt: [no-new-privileges:true]") >= 4
    nginx = (WORKSPACE / "infra/docker/web/nginx-main.conf").read_text(encoding="utf-8")
    assert "pid /tmp/nginx.pid;" in nginx
    assert "client_body_temp_path /tmp/client_temp;" in nginx
