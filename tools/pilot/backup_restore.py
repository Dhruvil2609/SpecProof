"""Verified PostgreSQL metadata and S3-compatible evidence backup/restore tooling."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

MANIFEST_SCHEMA_VERSION = 1


class ObjectStorageClient(Protocol):
    """Operations required from an S3-compatible object-storage client."""

    def get_paginator(self, operation_name: str) -> ObjectPaginator:
        """Return a paginator for an S3 operation."""
        ...

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        """Download one object."""

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        """Upload one object."""


CommandRunner = Callable[[Sequence[str]], None]


class ObjectPaginator(Protocol):
    """Paginator shape returned for object listing."""

    def paginate(self, *, Bucket: str) -> Iterable[dict[str, list[dict[str, str]]]]:  # noqa: N803
        """Yield object listing pages for one bucket."""
        ...


@dataclass(frozen=True)
class BackupArtifact:
    """One checksummed file in a pilot backup."""

    relative_path: str
    sha256: str
    size_bytes: int
    bucket: str | None = None
    object_key: str | None = None


@dataclass(frozen=True)
class BackupManifest:
    """Versioned integrity manifest for database metadata and evidence objects."""

    schema_version: int
    created_at_utc: str
    database: BackupArtifact
    objects: tuple[BackupArtifact, ...]


def create_backup(
    output_directory: Path,
    database_url: str,
    bucket: str,
    object_storage: ObjectStorageClient,
    *,
    command_runner: CommandRunner | None = None,
    now_utc: datetime | None = None,
) -> Path:
    """Create a PostgreSQL/custom-format and object-storage backup with SHA-256 manifest."""

    runner = command_runner or _run_command
    created_at = now_utc or datetime.now(UTC)
    if created_at.utcoffset() != UTC.utcoffset(created_at):
        raise ValueError("Backup timestamp must be UTC")
    backup_root = output_directory / created_at.strftime("specproof-backup-%Y%m%dT%H%M%SZ")
    objects_root = backup_root / "objects"
    objects_root.mkdir(parents=True, exist_ok=False)
    database_path = backup_root / "postgresql.dump"
    runner(["pg_dump", "--format=custom", "--file", str(database_path), database_url])
    database_artifact = _artifact(backup_root, database_path)

    object_artifacts: list[BackupArtifact] = []
    for object_key in sorted(_list_object_keys(object_storage, bucket)):
        filename = f"{hashlib.sha256(object_key.encode('utf-8')).hexdigest()}.object"
        object_path = objects_root / filename
        object_storage.download_file(bucket, object_key, str(object_path))
        artifact = _artifact(backup_root, object_path)
        object_artifacts.append(
            BackupArtifact(
                relative_path=artifact.relative_path,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
                bucket=bucket,
                object_key=object_key,
            )
        )

    manifest = BackupManifest(
        schema_version=MANIFEST_SCHEMA_VERSION,
        created_at_utc=created_at.isoformat().replace("+00:00", "Z"),
        database=database_artifact,
        objects=tuple(object_artifacts),
    )
    manifest_path = backup_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    verify_backup(manifest_path)
    return manifest_path


def verify_backup(manifest_path: Path) -> BackupManifest:
    """Validate manifest schema, relative paths, file sizes, and SHA-256 checksums."""

    manifest = _load_manifest(manifest_path)
    backup_root = manifest_path.parent.resolve()
    for artifact in (manifest.database, *manifest.objects):
        artifact_path = (backup_root / artifact.relative_path).resolve()
        if backup_root not in artifact_path.parents:
            raise ValueError(f"Backup artifact escapes backup root: {artifact.relative_path}")
        if not artifact_path.is_file():
            raise ValueError(f"Backup artifact is missing: {artifact.relative_path}")
        if artifact_path.stat().st_size != artifact.size_bytes:
            raise ValueError(f"Backup artifact size mismatch: {artifact.relative_path}")
        if _sha256(artifact_path) != artifact.sha256:
            raise ValueError(f"Backup artifact checksum mismatch: {artifact.relative_path}")
    return manifest


def restore_backup(
    manifest_path: Path,
    database_url: str,
    object_storage: ObjectStorageClient,
    *,
    command_runner: CommandRunner | None = None,
) -> BackupManifest:
    """Restore a verified backup into an empty PostgreSQL database and evidence bucket."""

    runner = command_runner or _run_command
    manifest = verify_backup(manifest_path)
    backup_root = manifest_path.parent
    runner(
        [
            "pg_restore",
            "--exit-on-error",
            "--no-owner",
            "--no-privileges",
            "--dbname",
            database_url,
            str(backup_root / manifest.database.relative_path),
        ]
    )
    for artifact in manifest.objects:
        if artifact.bucket is None or artifact.object_key is None:
            raise ValueError("Object artifact is missing bucket or object key")
        object_storage.upload_file(
            str(backup_root / artifact.relative_path),
            artifact.bucket,
            artifact.object_key,
        )
    return manifest


def _load_manifest(manifest_path: Path) -> BackupManifest:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("Unsupported backup manifest schema version")
    database = BackupArtifact(**payload["database"])
    objects = tuple(BackupArtifact(**item) for item in payload["objects"])
    created_at = datetime.fromisoformat(payload["created_at_utc"].replace("Z", "+00:00"))
    if created_at.utcoffset() != UTC.utcoffset(created_at):
        raise ValueError("Backup manifest timestamp must be UTC")
    return BackupManifest(
        schema_version=payload["schema_version"],
        created_at_utc=payload["created_at_utc"],
        database=database,
        objects=objects,
    )


def _list_object_keys(client: ObjectStorageClient, bucket: str) -> Iterable[str]:
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            yield str(item["Key"])


def _artifact(backup_root: Path, path: Path) -> BackupArtifact:
    return BackupArtifact(
        relative_path=path.relative_to(backup_root).as_posix(),
        sha256=_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_command(arguments: Sequence[str]) -> None:
    subprocess.run(arguments, check=True)


def _object_storage_client(endpoint_url: str) -> ObjectStorageClient:
    import boto3

    return cast(
        ObjectStorageClient,
        boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=os.environ["SPEC_PROOF_OBJECT_STORAGE_ACCESS_KEY"],
            aws_secret_access_key=os.environ["SPEC_PROOF_OBJECT_STORAGE_SECRET_KEY"],
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url-env",
        default="SPEC_PROOF_DATABASE_URL",
        help="Environment variable containing the PostgreSQL connection URL",
    )
    parser.add_argument("--endpoint-url", default="http://127.0.0.1:9000")
    parser.add_argument("--bucket", default="specproof-evidence")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("output_directory", type=Path)
    verify = subparsers.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    restore = subparsers.add_parser("restore")
    restore.add_argument("manifest", type=Path)
    return parser


def main() -> None:
    """Run backup, verification, or empty-environment restore."""

    arguments = _parser().parse_args()
    if arguments.command == "verify":
        verify_backup(arguments.manifest)
        return
    database_url = os.environ[arguments.database_url_env]
    storage = _object_storage_client(arguments.endpoint_url)
    if arguments.command == "backup":
        create_backup(arguments.output_directory, database_url, arguments.bucket, storage)
        return
    restore_backup(arguments.manifest, database_url, storage)


if __name__ == "__main__":
    main()
