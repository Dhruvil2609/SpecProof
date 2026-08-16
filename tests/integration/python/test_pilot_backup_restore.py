from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Protocol, TypedDict, cast

import boto3
import psycopg
import pytest

from tools.pilot.backup_restore import ObjectStorageClient, create_backup, restore_backup

pytestmark = pytest.mark.integration


def _integration_configuration() -> dict[str, str]:
    if os.getenv("SPEC_PROOF_RUN_BACKUP_RESTORE_INTEGRATION") != "1":
        pytest.skip("Set SPEC_PROOF_RUN_BACKUP_RESTORE_INTEGRATION=1 to run restore acceptance")
    required = [
        "SPEC_PROOF_SOURCE_DATABASE_URL",
        "SPEC_PROOF_RESTORE_DATABASE_URL",
        "SPEC_PROOF_SOURCE_OBJECT_STORAGE_ENDPOINT",
        "SPEC_PROOF_RESTORE_OBJECT_STORAGE_ENDPOINT",
        "SPEC_PROOF_OBJECT_STORAGE_ACCESS_KEY",
        "SPEC_PROOF_OBJECT_STORAGE_SECRET_KEY",
        "SPEC_PROOF_EVIDENCE_BUCKET",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.fail(f"Missing backup/restore integration settings: {', '.join(missing)}")
    configuration = {name: os.environ[name] for name in required}
    if "restore" not in configuration["SPEC_PROOF_RESTORE_DATABASE_URL"].lower():
        pytest.fail("Restore database URL must identify a dedicated database containing 'restore'")
    return configuration


class ObjectBody(Protocol):
    def read(self) -> bytes:
        """Read the complete object body."""


class GetObjectResponse(TypedDict):
    Body: ObjectBody


class RestoreStorageClient(ObjectStorageClient, Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> GetObjectResponse:  # noqa: N803
        """Read one object."""


def _storage(endpoint: str, configuration: dict[str, str]) -> RestoreStorageClient:
    return cast(
        RestoreStorageClient,
        boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=configuration["SPEC_PROOF_OBJECT_STORAGE_ACCESS_KEY"],
        aws_secret_access_key=configuration["SPEC_PROOF_OBJECT_STORAGE_SECRET_KEY"],
        ),
    )


def _integrity_rows(
    database_url: str,
) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    with psycopg.connect(database_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT id::text, evidence_record_hash FROM inspection_records ORDER BY id"
        )
        inspections = cursor.fetchall()
        cursor.execute(
            "SELECT inspection_id::text, record_hash_sha256, "
            "COALESCE(signature_value_base64, '') FROM evidence_records ORDER BY inspection_id"
        )
        evidence = cursor.fetchall()
    return inspections, evidence


def _object_hashes(storage: RestoreStorageClient, bucket: str) -> dict[str, str]:
    hashes: dict[str, str] = {}
    paginator = storage.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key = str(item["Key"])
            payload = storage.get_object(Bucket=bucket, Key=key)["Body"].read()
            hashes[key] = hashlib.sha256(payload).hexdigest()
    return hashes


def test_backup_restore_empty_environment_preserves_inspection_and_evidence(
    tmp_path: Path,
) -> None:
    configuration = _integration_configuration()
    source_database = configuration["SPEC_PROOF_SOURCE_DATABASE_URL"]
    restore_database = configuration["SPEC_PROOF_RESTORE_DATABASE_URL"]
    bucket = configuration["SPEC_PROOF_EVIDENCE_BUCKET"]
    source_storage = _storage(
        configuration["SPEC_PROOF_SOURCE_OBJECT_STORAGE_ENDPOINT"], configuration
    )
    restore_storage = _storage(
        configuration["SPEC_PROOF_RESTORE_OBJECT_STORAGE_ENDPOINT"], configuration
    )
    with psycopg.connect(restore_database) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )
        assert cursor.fetchone() == (0,)
    assert _object_hashes(restore_storage, bucket) == {}
    source_rows = _integrity_rows(source_database)
    assert source_rows[0], "Source database must contain inspections for restore acceptance"

    manifest_path = create_backup(tmp_path, source_database, bucket, source_storage)
    restore_backup(manifest_path, restore_database, restore_storage)

    assert _integrity_rows(restore_database) == source_rows
    assert _object_hashes(restore_storage, bucket) == _object_hashes(source_storage, bucket)
