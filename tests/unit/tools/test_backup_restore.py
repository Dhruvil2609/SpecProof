from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.pilot.backup_restore import create_backup, restore_backup, verify_backup


class FakePaginator:
    def __init__(self, keys: list[str]) -> None:
        self._keys = keys

    def paginate(self, *, Bucket: str) -> list[dict[str, list[dict[str, str]]]]:  # noqa: N803
        del Bucket
        return [{"Contents": [{"Key": key} for key in self._keys]}]


class FakeObjectStorage:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.uploads: dict[str, bytes] = {}

    def get_paginator(self, operation_name: str) -> FakePaginator:
        assert operation_name == "list_objects_v2"
        return FakePaginator(list(self.objects))

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        assert bucket == "evidence"
        Path(filename).write_bytes(self.objects[key])

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        assert bucket == "evidence"
        self.uploads[key] = Path(filename).read_bytes()


def _database_dump_runner(arguments: list[str] | tuple[str, ...]) -> None:
    output_path = Path(arguments[arguments.index("--file") + 1])
    output_path.write_bytes(b"postgres-custom-dump")


@pytest.mark.unit
def test_create_backup_metadata_and_objects_writes_verified_utc_manifest(tmp_path: Path) -> None:
    storage = FakeObjectStorage({"tenant/a/evidence.json": b"evidence", "capture.bin": b"capture"})

    manifest_path = create_backup(
        tmp_path,
        "postgresql://database",
        "evidence",
        storage,
        command_runner=_database_dump_runner,
        now_utc=datetime(2026, 8, 15, tzinfo=UTC),
    )

    manifest = verify_backup(manifest_path)
    assert manifest.created_at_utc == "2026-08-15T00:00:00Z"
    assert len(manifest.objects) == 2


@pytest.mark.unit
def test_verify_backup_corrupted_object_rejects_restore(tmp_path: Path) -> None:
    storage = FakeObjectStorage({"evidence.json": b"evidence"})
    manifest_path = create_backup(
        tmp_path,
        "postgresql://database",
        "evidence",
        storage,
        command_runner=_database_dump_runner,
    )
    object_path = next((manifest_path.parent / "objects").iterdir())
    object_path.write_bytes(b"tampered")

    with pytest.raises(ValueError, match="(size|checksum) mismatch"):
        verify_backup(manifest_path)


@pytest.mark.unit
def test_restore_backup_verified_archive_restores_database_and_keys(tmp_path: Path) -> None:
    original = {"tenant/a/evidence.json": b"evidence", "capture.bin": b"capture"}
    source = FakeObjectStorage(original)
    manifest_path = create_backup(
        tmp_path,
        "postgresql://source",
        "evidence",
        source,
        command_runner=_database_dump_runner,
    )
    restored = FakeObjectStorage({})
    commands: list[tuple[str, ...]] = []

    restore_backup(
        manifest_path,
        "postgresql://empty-target",
        restored,
        command_runner=lambda arguments: commands.append(tuple(arguments)),
    )

    assert commands[0][0] == "pg_restore"
    assert restored.uploads == original
