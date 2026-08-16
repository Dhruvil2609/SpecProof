"""Create, sign, verify, stage, activate, and roll back release packages."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

SIGNATURE_ALGORITHM = "RSA-PSS-SHA256"


def create_manifest(
    *,
    version: str,
    artifacts: Sequence[tuple[str, Path]],
    minimum_schema_version: int,
    maximum_schema_version: int,
    rollout_percentage: int,
    generated_at: datetime | None = None,
) -> dict[str, object]:
    """Create a canonical release manifest from local package artifacts."""

    if not version or any(character in version for character in "/\\"):
        raise ValueError("release version must be filename-safe")
    if minimum_schema_version < 1 or maximum_schema_version < minimum_schema_version:
        raise ValueError("release schema compatibility range is invalid")
    if rollout_percentage not in range(0, 101):
        raise ValueError("rollout percentage must be from 0 through 100")
    entries: list[dict[str, object]] = []
    for runtime_identifier, path in artifacts:
        if not runtime_identifier or not path.is_file():
            raise FileNotFoundError(path)
        entries.append(
            {
                "fileName": path.name,
                "runtimeIdentifier": runtime_identifier,
                "sizeBytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    if not entries:
        raise ValueError("release manifest requires at least one artifact")
    timestamp = (generated_at or datetime.now(UTC)).astimezone(UTC)
    return {
        "schemaVersion": 1,
        "releaseVersion": version,
        "generatedAtUtc": timestamp.isoformat().replace("+00:00", "Z"),
        "minimumDataSchemaVersion": minimum_schema_version,
        "maximumDataSchemaVersion": maximum_schema_version,
        "rolloutPercentage": rollout_percentage,
        "artifacts": sorted(entries, key=lambda entry: str(entry["runtimeIdentifier"])),
    }


def sign_manifest(
    manifest: dict[str, object],
    private_key_pem: bytes,
    key_id: str,
) -> dict[str, str]:
    """Sign canonical manifest bytes with an RSA-PSS private key."""

    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("release signing key must be RSA")
    payload = canonical_json(manifest)
    signature = private_key.sign(
        payload,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {
        "algorithm": SIGNATURE_ALGORITHM,
        "keyId": key_id,
        "manifestSha256": hashlib.sha256(payload).hexdigest(),
        "signatureBase64": base64.b64encode(signature).decode("ascii"),
    }


def verify_manifest_signature(
    manifest: dict[str, object],
    signature: dict[str, str],
    public_key_pem: bytes,
) -> None:
    """Reject an altered manifest, signature, algorithm, or key type."""

    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        raise ValueError("release signature algorithm is not allowed")
    payload = canonical_json(manifest)
    if signature.get("manifestSha256") != hashlib.sha256(payload).hexdigest():
        raise ValueError("release manifest checksum does not match the signature envelope")
    public_key = serialization.load_pem_public_key(public_key_pem)
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise TypeError("release verification key must be RSA")
    try:
        public_key.verify(
            base64.b64decode(signature["signatureBase64"], validate=True),
            payload,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
    except (InvalidSignature, ValueError, KeyError) as exception:
        raise ValueError("release manifest signature is invalid") from exception


def select_verified_artifact(
    *,
    manifest: dict[str, object],
    signature: dict[str, str],
    public_key_pem: bytes,
    package_directory: Path,
    runtime_identifier: str,
    station_id: uuid.UUID,
    data_schema_version: int,
) -> Path:
    """Verify trust, compatibility, rollout eligibility, and package checksum."""

    verify_manifest_signature(manifest, signature, public_key_pem)
    minimum = _integer(manifest, "minimumDataSchemaVersion")
    maximum = _integer(manifest, "maximumDataSchemaVersion")
    if data_schema_version not in range(minimum, maximum + 1):
        raise ValueError("station data schema is incompatible with this release")
    rollout = _integer(manifest, "rolloutPercentage")
    if not is_station_eligible(station_id, rollout):
        raise ValueError("station is outside the current staged rollout")
    for artifact in _artifacts(manifest):
        if artifact.get("runtimeIdentifier") != runtime_identifier:
            continue
        path = package_directory / str(artifact["fileName"])
        if not path.is_file() or path.stat().st_size != artifact.get("sizeBytes"):
            raise ValueError("release package size does not match the manifest")
        if _sha256(path) != artifact.get("sha256"):
            raise ValueError("release package checksum does not match the manifest")
        return path
    raise ValueError(f"release has no artifact for {runtime_identifier}")


def is_station_eligible(station_id: uuid.UUID, rollout_percentage: int) -> bool:
    """Select stable station cohorts without server-side state."""

    if rollout_percentage not in range(0, 101):
        raise ValueError("rollout percentage must be from 0 through 100")
    bucket = int.from_bytes(hashlib.sha256(station_id.bytes).digest()[:8], "big") % 10_000
    return bucket < rollout_percentage * 100


def activate_package(package: Path, install_root: Path, version: str) -> Path:
    """Stage an offline package and atomically activate its release descriptor."""

    if not package.is_file():
        raise FileNotFoundError(package)
    version_root = install_root / "versions" / version
    version_root.mkdir(parents=True, exist_ok=True)
    staged_package = version_root / package.name
    shutil.copy2(package, staged_package)
    descriptor = {
        "releaseVersion": version,
        "packagePath": staged_package.relative_to(install_root).as_posix(),
        "sha256": _sha256(staged_package),
    }
    current = install_root / "current.json"
    previous = install_root / "previous.json"
    if current.is_file():
        os.replace(current, previous)
    _atomic_json(current, descriptor)
    return staged_package


def rollback_package(install_root: Path) -> dict[str, object]:
    """Atomically exchange current and previous release descriptors."""

    current = install_root / "current.json"
    previous = install_root / "previous.json"
    if not current.is_file() or not previous.is_file():
        raise FileNotFoundError("current and previous release descriptors are required")
    temporary = install_root / "rollback.json.tmp"
    os.replace(current, temporary)
    os.replace(previous, current)
    os.replace(temporary, previous)
    return cast(dict[str, object], json.loads(current.read_text(encoding="utf-8")))


def canonical_json(value: dict[str, object]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _artifacts(manifest: dict[str, object]) -> list[dict[str, object]]:
    raw = manifest.get("artifacts")
    if not isinstance(raw, list):
        raise ValueError("release manifest artifacts must be a list")
    artifacts: list[dict[str, object]] = []
    for item in cast(list[object], raw):
        if not isinstance(item, dict):
            raise ValueError("release artifact entries must be objects")
        artifacts.append(cast(dict[str, object], item))
    return artifacts


def _integer(manifest: dict[str, object], name: str) -> int:
    value = manifest.get(name)
    if not isinstance(value, int):
        raise ValueError(f"release manifest {name} must be an integer")
    return value


def _atomic_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="specproof-signed-update")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("signature", type=Path)
    parser.add_argument("public_key", type=Path)
    parsed = parser.parse_args(arguments)
    manifest = cast(dict[str, object], json.loads(parsed.manifest.read_text(encoding="utf-8")))
    signature = cast(dict[str, str], json.loads(parsed.signature.read_text(encoding="utf-8")))
    verify_manifest_signature(manifest, signature, parsed.public_key.read_bytes())
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
