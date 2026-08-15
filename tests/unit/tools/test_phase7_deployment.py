from __future__ import annotations

import json
import shutil
import subprocess
import tarfile
from pathlib import Path

import pytest

from tools.packaging.build_station_package import (
    assemble_station_package,
    verify_station_package,
)


@pytest.mark.unit
def test_station_package_contains_host_python_config_services_and_valid_hashes(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    publish_dir = tmp_path / "publish"
    publish_dir.mkdir()
    (publish_dir / "SpecProof.Station.Host").write_bytes(b"linux-host")
    python_wheel = tmp_path / "specproof-0.1.0-py3-none-any.whl"
    python_wheel.write_bytes(b"wheel")
    requirements = tmp_path / "requirements.lock"
    requirements.write_text("pydantic==2.11.0\n", encoding="utf-8")

    archive_path = assemble_station_package(
        repository_root=repository_root,
        station_publish_dir=publish_dir,
        python_wheel=python_wheel,
        requirements_lock=requirements,
        output_dir=tmp_path / "artifacts",
        version="0.1.0-test",
    )

    verify_station_package(archive_path)
    with tarfile.open(archive_path, "r:gz") as archive:
        install_member = next(
            member for member in archive.getmembers() if member.name.endswith("/install.sh")
        )
        manifest_member = next(
            member for member in archive.getmembers() if member.name.endswith("/manifest.json")
        )
        manifest_stream = archive.extractfile(manifest_member)
        assert manifest_stream is not None
        manifest = json.load(manifest_stream)
    assert manifest["runtimeIdentifier"] == "linux-x64"
    assert manifest["packageVersion"] == "0.1.0-test"
    assert install_member.mode & 0o111


@pytest.mark.unit
def test_station_package_verifier_rejects_tampered_manifest_file(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[3]
    publish_dir = tmp_path / "publish"
    publish_dir.mkdir()
    (publish_dir / "SpecProof.Station.Host").write_bytes(b"linux-host")
    python_wheel = tmp_path / "specproof-0.1.0-py3-none-any.whl"
    python_wheel.write_bytes(b"wheel")
    requirements = tmp_path / "requirements.lock"
    requirements.write_text("pydantic==2.11.0\n", encoding="utf-8")
    archive_path = assemble_station_package(
        repository_root=repository_root,
        station_publish_dir=publish_dir,
        python_wheel=python_wheel,
        requirements_lock=requirements,
        output_dir=tmp_path / "artifacts",
        version="0.1.0-test",
    )
    extraction_root = tmp_path / "extracted"
    with tarfile.open(archive_path, "r:gz") as archive:
        archive.extractall(extraction_root, filter="data")
    package_root = next(extraction_root.iterdir())
    (package_root / "config" / "station.env.example").write_text(
        "tampered=true\n",
        encoding="utf-8",
    )
    tampered_archive = tmp_path / "tampered.tar.gz"
    with tarfile.open(tampered_archive, "w:gz") as archive:
        archive.add(package_root, arcname=package_root.name)

    with pytest.raises(ValueError, match="hash mismatch"):
        verify_station_package(tampered_archive)


@pytest.mark.unit
def test_application_compose_profile_defines_migrations_and_health_checks() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    compose = (repository_root / "docker-compose.yml").read_text(encoding="utf-8")

    for service in ("platform-api", "measurement-service", "operator-ui", "admin-ui"):
        assert f"  {service}:" in compose
    assert 'profiles: ["application"]' in compose
    assert 'Database__ApplyMigrations: "true"' in compose
    assert compose.count("healthcheck:") >= 12
    for dockerfile in (
        "apps/platform-api/Dockerfile",
        "apps/measurement-service/Dockerfile",
        "apps/operator-ui/Dockerfile",
        "apps/admin-ui/Dockerfile",
    ):
        assert (repository_root / dockerfile).is_file()


@pytest.mark.integration
def test_application_compose_profile_is_syntactically_valid() -> None:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker CLI is unavailable")
    repository_root = Path(__file__).resolve().parents[3]

    result = subprocess.run(
        [docker, "compose", "--profile", "application", "config", "--quiet"],
        cwd=repository_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
