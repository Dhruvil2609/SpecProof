"""Durable SQLite queue for sealed inspection-result delivery."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import cast
from uuid import uuid4


class InspectionQueueState(StrEnum):
    """Durable inspection-result delivery states."""

    PENDING = "pending"
    SUBMITTING = "submitting"
    RETRYABLE_FAILURE = "retryable_failure"
    DEAD_LETTER = "dead_letter"
    COMPLETED = "completed"


@dataclass(frozen=True)
class InspectionQueueItem:
    """One immutable sealed inspection payload awaiting delivery."""

    id: str
    capture_id: str
    inspection_id: str
    payload_json: str
    payload_hash_sha256: str
    idempotency_key: str
    state: InspectionQueueState
    attempts: int
    next_attempt_at_utc: datetime
    last_error: str | None

    def payload(self) -> dict[str, object]:
        """Deserialize the canonical platform submission payload."""

        value = json.loads(self.payload_json)
        if not isinstance(value, dict):
            raise ValueError("Inspection queue payload must be a JSON object")
        return cast(dict[str, object], value)

    def verify_hash(self) -> bool:
        """Verify the immutable payload digest before delivery."""

        return sha256(self.payload_json.encode("utf-8")).hexdigest() == self.payload_hash_sha256


class OfflineInspectionQueue:
    """Transactional inspection-result queue that survives process restarts."""

    def __init__(self, database_path: Path, *, maximum_attempts: int = 8) -> None:
        if maximum_attempts < 1:
            raise ValueError("maximum_attempts must be at least one")
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._maximum_attempts = maximum_attempts
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._create_schema()
        self.recover_interrupted()

    def enqueue(
        self,
        *,
        capture_id: str,
        inspection_id: str,
        payload: dict[str, object],
    ) -> InspectionQueueItem:
        """Persist a sealed result before operator capture acknowledgement."""

        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        payload_hash = sha256(canonical.encode("utf-8")).hexdigest()
        now = self._iso(datetime.now(UTC))
        try:
            self._connection.execute(
                """
                INSERT INTO inspection_result_queue (
                    id, capture_id, inspection_id, payload_json, payload_hash_sha256,
                    idempotency_key, state, attempts, next_attempt_at_utc, last_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, NULL)
                """,
                (
                    str(uuid4()),
                    capture_id,
                    inspection_id,
                    canonical,
                    payload_hash,
                    inspection_id,
                    InspectionQueueState.PENDING.value,
                    now,
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError:
            existing = self.get_by_inspection_id(inspection_id)
            if (
                existing is None
                or existing.capture_id != capture_id
                or existing.payload_hash_sha256 != payload_hash
            ):
                raise ValueError("Conflicting inspection result replay") from None
            return existing
        item = self.get_by_inspection_id(inspection_id)
        if item is None:
            raise RuntimeError("Inspection queue insert did not return an item")
        return item

    def pending_capture_ids(self, now: datetime | None = None) -> tuple[str, ...]:
        """Return capture IDs with inspection results eligible for submission."""

        rows = self._connection.execute(
            """
            SELECT DISTINCT capture_id FROM inspection_result_queue
            WHERE state IN (?, ?) AND next_attempt_at_utc <= ?
            ORDER BY capture_id
            """,
            (
                InspectionQueueState.PENDING.value,
                InspectionQueueState.RETRYABLE_FAILURE.value,
                self._iso(now or datetime.now(UTC)),
            ),
        ).fetchall()
        return tuple(str(row["capture_id"]) for row in rows)

    def claim_for_captures(
        self,
        capture_ids: tuple[str, ...],
        now: datetime | None = None,
    ) -> InspectionQueueItem | None:
        """Atomically claim one result whose capture upload is complete."""

        if not capture_ids:
            return None
        placeholders = ",".join("?" for _ in capture_ids)
        instant = self._iso(now or datetime.now(UTC))
        with self._connection:
            row = self._connection.execute(
                f"""
                SELECT * FROM inspection_result_queue
                WHERE capture_id IN ({placeholders})
                  AND state IN (?, ?)
                  AND next_attempt_at_utc <= ?
                ORDER BY next_attempt_at_utc, id
                LIMIT 1
                """,
                (
                    *capture_ids,
                    InspectionQueueState.PENDING.value,
                    InspectionQueueState.RETRYABLE_FAILURE.value,
                    instant,
                ),
            ).fetchone()
            if row is None:
                return None
            updated = self._connection.execute(
                """
                UPDATE inspection_result_queue
                SET state = ?, attempts = attempts + 1
                WHERE id = ? AND state IN (?, ?)
                """,
                (
                    InspectionQueueState.SUBMITTING.value,
                    row["id"],
                    InspectionQueueState.PENDING.value,
                    InspectionQueueState.RETRYABLE_FAILURE.value,
                ),
            )
            if updated.rowcount != 1:
                return None
        return self.get(str(row["id"]))

    def complete(self, item_id: str) -> None:
        """Mark an inspection result as delivered."""

        self._transition(
            item_id,
            InspectionQueueState.SUBMITTING,
            InspectionQueueState.COMPLETED,
            None,
            None,
        )

    def fail(self, item_id: str, error: str, now: datetime | None = None) -> None:
        """Retry with bounded exponential backoff or enter dead-letter state."""

        item = self._required(item_id)
        target = (
            InspectionQueueState.DEAD_LETTER
            if item.attempts >= self._maximum_attempts
            else InspectionQueueState.RETRYABLE_FAILURE
        )
        delay = min(300, 2 ** min(item.attempts, 8))
        self._transition(
            item_id,
            InspectionQueueState.SUBMITTING,
            target,
            error[:1000],
            (now or datetime.now(UTC)) + timedelta(seconds=delay),
        )

    def dead_letter(self, item_id: str, error: str) -> None:
        """Move an invalid immutable payload directly to dead-letter state."""

        self._transition(
            item_id,
            InspectionQueueState.SUBMITTING,
            InspectionQueueState.DEAD_LETTER,
            error[:1000],
            None,
        )

    def retry_dead_letter(self, item_id: str) -> None:
        """Requeue one operator-reviewed dead-letter item."""

        self._transition(
            item_id,
            InspectionQueueState.DEAD_LETTER,
            InspectionQueueState.RETRYABLE_FAILURE,
            None,
            datetime.now(UTC),
        )

    def recover_interrupted(self) -> None:
        """Recover a process terminated after the durable claim."""

        with self._connection:
            self._connection.execute(
                """
                UPDATE inspection_result_queue
                SET state = ?, last_error = ?, next_attempt_at_utc = ?
                WHERE state = ?
                """,
                (
                    InspectionQueueState.RETRYABLE_FAILURE.value,
                    "Submission interrupted by process restart",
                    self._iso(datetime.now(UTC)),
                    InspectionQueueState.SUBMITTING.value,
                ),
            )

    def depth(self) -> int:
        """Return the number of incomplete result deliveries."""

        row = self._connection.execute(
            "SELECT COUNT(*) AS count FROM inspection_result_queue WHERE state != ?",
            (InspectionQueueState.COMPLETED.value,),
        ).fetchone()
        return int(row["count"])

    def get(self, item_id: str) -> InspectionQueueItem | None:
        """Return one inspection queue item by internal ID."""

        row = self._connection.execute(
            "SELECT * FROM inspection_result_queue WHERE id = ?",
            (item_id,),
        ).fetchone()
        return self._map(row) if row is not None else None

    def get_by_inspection_id(self, inspection_id: str) -> InspectionQueueItem | None:
        """Return one inspection queue item by inspection ID."""

        row = self._connection.execute(
            "SELECT * FROM inspection_result_queue WHERE inspection_id = ?",
            (inspection_id,),
        ).fetchone()
        return self._map(row) if row is not None else None

    def close(self) -> None:
        """Close the queue database."""

        self._connection.close()

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inspection_result_queue (
                    id TEXT PRIMARY KEY,
                    capture_id TEXT NOT NULL,
                    inspection_id TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    payload_hash_sha256 TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    next_attempt_at_utc TEXT NOT NULL,
                    last_error TEXT NULL,
                    UNIQUE(capture_id, inspection_id)
                )
                """
            )

    def _required(self, item_id: str) -> InspectionQueueItem:
        item = self.get(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def _transition(
        self,
        item_id: str,
        expected: InspectionQueueState,
        target: InspectionQueueState,
        error: str | None,
        next_attempt: datetime | None,
    ) -> None:
        with self._connection:
            updated = self._connection.execute(
                """
                UPDATE inspection_result_queue
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
                raise RuntimeError(f"Invalid inspection queue transition for {item_id}")

    @staticmethod
    def _map(row: sqlite3.Row) -> InspectionQueueItem:
        return InspectionQueueItem(
            id=str(row["id"]),
            capture_id=str(row["capture_id"]),
            inspection_id=str(row["inspection_id"]),
            payload_json=str(row["payload_json"]),
            payload_hash_sha256=str(row["payload_hash_sha256"]),
            idempotency_key=str(row["idempotency_key"]),
            state=InspectionQueueState(str(row["state"])),
            attempts=int(row["attempts"]),
            next_attempt_at_utc=datetime.fromisoformat(str(row["next_attempt_at_utc"])),
            last_error=str(row["last_error"]) if row["last_error"] is not None else None,
        )

    @staticmethod
    def _iso(value: datetime) -> str:
        return value.astimezone(UTC).isoformat()
