from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tools.release_management.signed_updates import (
    activate_package,
    create_manifest,
    is_station_eligible,
    rollback_package,
    select_verified_artifact,
    sign_manifest,
    verify_manifest_signature,
)


def _keys() -> tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def _release(tmp_path: Path, rollout: int = 100) -> tuple[dict[str, object], Path]:
    package = tmp_path / "station.zip"
    package.write_bytes(b"signed-offline-package")
    manifest = create_manifest(
        version="1.2.3",
        artifacts=[("win-x64", package)],
        minimum_schema_version=4,
        maximum_schema_version=6,
        rollout_percentage=rollout,
        generated_at=datetime(2026, 8, 16, tzinfo=UTC),
    )
    return manifest, package


@pytest.mark.unit
def test_signed_manifest_verifies_and_rejects_tampering(tmp_path: Path) -> None:
    manifest, _ = _release(tmp_path)
    private_pem, public_pem = _keys()
    signature = sign_manifest(manifest, private_pem, "release-test")

    verify_manifest_signature(manifest, signature, public_pem)
    manifest["releaseVersion"] = "altered"

    with pytest.raises(ValueError, match="checksum"):
        verify_manifest_signature(manifest, signature, public_pem)


@pytest.mark.unit
def test_release_selection_enforces_signature_schema_rollout_and_checksum(tmp_path: Path) -> None:
    manifest, package = _release(tmp_path)
    private_pem, public_pem = _keys()
    signature = sign_manifest(manifest, private_pem, "release-test")
    station_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    selected = select_verified_artifact(
        manifest=manifest,
        signature=signature,
        public_key_pem=public_pem,
        package_directory=tmp_path,
        runtime_identifier="win-x64",
        station_id=station_id,
        data_schema_version=5,
    )

    assert selected == package
    with pytest.raises(ValueError, match="schema"):
        select_verified_artifact(
            manifest=manifest,
            signature=signature,
            public_key_pem=public_pem,
            package_directory=tmp_path,
            runtime_identifier="win-x64",
            station_id=station_id,
            data_schema_version=7,
        )
    package.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="size|checksum"):
        select_verified_artifact(
            manifest=manifest,
            signature=signature,
            public_key_pem=public_pem,
            package_directory=tmp_path,
            runtime_identifier="win-x64",
            station_id=station_id,
            data_schema_version=5,
        )


@pytest.mark.unit
def test_station_rollout_is_deterministic_and_bounded() -> None:
    station_id = uuid.UUID("22222222-2222-2222-2222-222222222222")

    assert not is_station_eligible(station_id, 0)
    assert is_station_eligible(station_id, 100)
    assert is_station_eligible(station_id, 50) == is_station_eligible(station_id, 50)


@pytest.mark.unit
def test_offline_activation_and_rollback_exchange_descriptors(tmp_path: Path) -> None:
    install_root = tmp_path / "installed"
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    activate_package(first, install_root, "1.0.0")
    activate_package(second, install_root, "2.0.0")
    rolled_back = rollback_package(install_root)

    assert rolled_back["releaseVersion"] == "1.0.0"
    assert (install_root / "previous.json").read_text(encoding="utf-8").find("2.0.0") > 0
