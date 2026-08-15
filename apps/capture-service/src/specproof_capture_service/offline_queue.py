"""Durable SQLite-backed offline capture queue."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from uuid import uuid4


class QueueState(StrEnum):
    """Offline upload states."""

    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class QueueItem:
    """Queued capture upload."""

    id: str
    capture_id: str
    package_path: Path
    package_sha256: str
    idempotency_key: str
    state: QueueState
    attempts: int
    next_attempt_at_utc: datetime
    last_error: str | None


class OfflineCaptureQueue:
    """Transactional queue that survives process restarts."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._create_schema()
        self.recover_interrupted()

    def enqueue(self, capture_id: str, package_path: Path, package_sha256: str) -> QueueItem:
        """Add a capture once using its capture ID as an idempotency key."""

        now = self._iso(datetime.now(UTC))
        item_id = str(uuid4())
        self._connection.execute(
            """
            INSERT OR IGNORE INTO capture_queue (
                id, capture_id, package_path, package_sha256, idempotency_key,
                state, attempts, next_attempt_at_utc, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, NULL)
            """,
            (
                item_id,
                capture_id,
                str(package_path),
                package_sha256,
                capture_id,
                QueueState.PENDING.value,
                now,
            ),
        )
        self._connection.commit()
        item = self.get_by_capture_id(capture_id)
        if item is None:
            raise RuntimeError("Queue insert did not return an item")
        return item

    def claim_next(self, now: datetime | None = None) -> QueueItem | None:
        """Atomically claim the next eligible item."""

        instant = now or datetime.now(UTC)
        with self._connection:
            row = self._connection.execute(
                """
                SELECT * FROM capture_queue
                WHERE state IN (?, ?) AND next_attempt_at_utc <= ?
                ORDER BY next_attempt_at_utc, id
                LIMIT 1
                """,
                (QueueState.PENDING.value, QueueState.FAILED.value, self._iso(instant)),
            ).fetchone()
            if row is None:
                return None
            updated = self._connection.execute(
                """
                UPDATE capture_queue
                SET state = ?, attempts = attempts + 1
                WHERE id = ? AND state IN (?, ?)
                """,
                (
                    QueueState.UPLOADING.value,
                    row["id"],
                    QueueState.PENDING.value,
                    QueueState.FAILED.value,
                ),
            )
            if updated.rowcount != 1:
                return None
        return self.get(row["id"])

    def complete(self, item_id: str) -> None:
        """Mark an upload as completed."""

        self._transition(item_id, QueueState.UPLOADING, QueueState.COMPLETED, None, None)

    def fail(self, item_id: str, error: str, now: datetime | None = None) -> None:
        """Return an upload to retry with bounded exponential backoff."""

        item = self.get(item_id)
        if item is None:
            raise KeyError(item_id)
        delay_seconds = min(300, 2 ** min(item.attempts, 8))
        next_attempt = (now or datetime.now(UTC)) + timedelta(seconds=delay_seconds)
        self._transition(
            item_id,
            QueueState.UPLOADING,
            QueueState.FAILED,
            error[:1000],
            next_attempt,
        )

    def recover_interrupted(self) -> None:
        """Return interrupted uploads to the pending state."""

        with self._connection:
            self._connection.execute(
                """
                UPDATE capture_queue
                SET state = ?, last_error = ?
                WHERE state = ?
                """,
                (
                    QueueState.FAILED.value,
                    "Upload interrupted by process restart",
                    QueueState.UPLOADING.value,
                ),
            )

    def depth(self) -> int:
        """Return the number of incomplete queue items."""

        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM capture_queue WHERE state != ?",
            (QueueState.COMPLETED.value,),
        ).fetchone()
        return int(row["count"])

    def get(self, item_id: str) -> QueueItem | None:
        """Return a queue item by ID."""

        row = self._connection.execute(
            "SELECT * FROM capture_queue WHERE id = ?",
            (item_id,),
        ).fetchone()
        return self._map(row) if row is not None else None

    def get_by_capture_id(self, capture_id: str) -> QueueItem | None:
        """Return a queue item by capture ID."""

        row = self._connection.execute(
            "SELECT * FROM capture_queue WHERE capture_id = ?",
            (capture_id,),
        ).fetchone()
        return self._map(row) if row is not None else None

    def close(self) -> None:
        """Close the queue database."""

        self._connection.close()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS capture_queue (
                    id TEXT PRIMARY KEY,
                    capture_id TEXT NOT NULL UNIQUE,
                    package_path TEXT NOT NULL,
                    package_sha256 TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    next_attempt_at_utc TEXT NOT NULL,
                    last_error TEXT NULL
                )
                """
            )

    def _transition(
        self,
        item_id: str,
        expected: QueueState,
        target: QueueState,
        error: str | None,
        next_attempt: datetime | None,
    ) -> None:
        with self._connection:
            updated = self._connection.execute(
                """
                UPDATE capture_queue
                SET state = ?, last_error = ?,
                    next_attempt_at_utc = COALESCE(?, next_attempt_at_utc)
                WHERE id = ? AND state = ?
                """,
                (
                    target.value,
                    error,
                    self._iso(next_attempt) if next_attempt is not None else None,
                    item_id,
                    expected.value,
                ),
            )
            if updated.rowcount != 1:
                raise RuntimeError(f"Invalid queue transition for {item_id}")

    @staticmethod
    def _map(row: sqlite3.Row) -> QueueItem:
        return QueueItem(
            id=str(row["id"]),
            capture_id=str(row["capture_id"]),
            package_path=Path(str(row["package_path"])),
            package_sha256=str(row["package_sha256"]),
            idempotency_key=str(row["idempotency_key"]),
            state=QueueState(str(row["state"])),
            attempts=int(row["attempts"]),
            next_attempt_at_utc=datetime.fromisoformat(str(row["next_attempt_at_utc"])),
            last_error=str(row["last_error"]) if row["last_error"] is not None else None,
        )

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()
