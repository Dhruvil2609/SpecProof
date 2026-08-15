"""Seeded PostgreSQL EXPLAIN ANALYZE profiling for Phase 7 query shapes."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Final
from uuid import uuid4

import psycopg

PROFILE_QUERIES: Final[dict[str, str]] = {
    "dashboard": """
        SELECT * FROM inspection_records
        WHERE tenant_id = %(tenant_id)s AND deleted_at_utc IS NULL
        ORDER BY captured_at_utc DESC LIMIT 100
    """,
    "inspection_history": """
        SELECT * FROM inspection_records
        WHERE tenant_id = %(tenant_id)s AND deleted_at_utc IS NULL
          AND (order_code ILIKE %(search)s OR style_code ILIKE %(search)s
               OR station_code ILIKE %(search)s)
        ORDER BY captured_at_utc DESC LIMIT 100
    """,
    "station_health": """
        SELECT * FROM station_health_reports
        WHERE tenant_id = %(tenant_id)s AND station_id = %(station_id)s
        ORDER BY checked_at_utc DESC LIMIT 1
    """,
    "queue_claim": """
        SELECT * FROM background_jobs
        WHERE tenant_id = %(tenant_id)s AND queue_name = 'reports'
          AND status = 'queued' AND available_at_utc <= now()
        ORDER BY available_at_utc LIMIT 1 FOR UPDATE SKIP LOCKED
    """,
    "batch_summary": """
        SELECT status, count(*) FROM inspection_records
        WHERE tenant_id = %(tenant_id)s AND batch_id = %(batch_id)s
          AND deleted_at_utc IS NULL GROUP BY status
    """,
    "dashboard_evidence": """
        SELECT * FROM evidence_records
        WHERE tenant_id = %(tenant_id)s
        ORDER BY created_at_utc DESC LIMIT 100
    """,
}


def profile_queries(connection_string: str) -> dict[str, object]:
    """Profile seeded query shapes inside a transaction that is always rolled back."""

    tenant_id = uuid4()
    station_id = uuid4()
    batch_id = uuid4()
    plans: dict[str, object] = {}
    with psycopg.connect(connection_string) as connection:
        try:
            with connection.cursor() as cursor:
                _seed(cursor, tenant_id, station_id, batch_id)
                parameters = {
                    "tenant_id": tenant_id,
                    "station_id": station_id,
                    "batch_id": batch_id,
                    "search": "%PO-PROFILE%",
                }
                for name, query in PROFILE_QUERIES.items():
                    cursor.execute(
                        f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}",
                        parameters,
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise RuntimeError(f"PostgreSQL returned no plan for {name}")
                    plans[name] = row[0]
        finally:
            connection.rollback()
    return plans


def _seed(
    cursor: psycopg.Cursor[object],
    tenant_id: object,
    station_id: object,
    batch_id: object,
) -> None:
    cursor.execute(
        """
        INSERT INTO tenants (id, name, created_at_utc, updated_at_utc)
        VALUES (%s, %s, now(), now())
        """,
        (tenant_id, "Phase 7 Profile Tenant"),
    )
    cursor.execute(
        """
        INSERT INTO inspection_records (
            id, tenant_id, capture_id, station_id, batch_id, station_code, order_code,
            style_code, size_code, inspection_result, status, evidence_record_hash,
            captured_at_utc, created_at_utc, updated_at_utc)
        SELECT gen_random_uuid(), %s, gen_random_uuid(), %s, %s, 'STATION-PROFILE',
            'PO-PROFILE-' || series, 'STYLE-PROFILE', 'M', '{}'::jsonb,
            CASE WHEN series %% 10 = 0 THEN 'Fail' ELSE 'Pass' END,
            encode(digest(series::text, 'sha256'), 'hex'),
            now() - (series || ' seconds')::interval, now(), now()
        FROM generate_series(1, 10000) AS series
        """,
        (tenant_id, station_id, batch_id),
    )
    cursor.execute(
        """
        INSERT INTO station_health_reports (
            id, tenant_id, station_id, status, camera_status, storage_status, clock_status,
            offline_queue_depth, checked_at_utc, created_at_utc, updated_at_utc)
        SELECT gen_random_uuid(), %s, %s, 'healthy', 'available', 'available', 'utc', 0,
            now() - (series || ' seconds')::interval, now(), now()
        FROM generate_series(1, 1000) AS series
        """,
        (tenant_id, station_id),
    )
    cursor.execute(
        """
        INSERT INTO background_jobs (
            id, tenant_id, queue_name, job_type, payload, status, attempts,
            available_at_utc, created_at_utc, updated_at_utc)
        SELECT gen_random_uuid(), %s, 'reports', 'inspection.report.refresh', '{}'::jsonb,
            'queued', 0, now() - (series || ' seconds')::interval, now(), now()
        FROM generate_series(1, 1000) AS series
        """,
        (tenant_id,),
    )
    cursor.execute(
        """
        INSERT INTO evidence_records (
            id, tenant_id, inspection_id, capture_id, capture_hash_sha256, evidence,
            record_hash_sha256, created_at_utc, updated_at_utc)
        SELECT gen_random_uuid(), %s, gen_random_uuid(), gen_random_uuid(),
            encode(digest(('capture-' || series)::text, 'sha256'), 'hex'), '{}'::jsonb,
            encode(digest(('evidence-' || series)::text, 'sha256'), 'hex'),
            now() - (series || ' seconds')::interval, now()
        FROM generate_series(1, 10000) AS series
        """,
        (tenant_id,),
    )


def psycopg_connection_string(connection_string: str) -> str:
    """Convert the repository's Npgsql-style test connection string when necessary."""

    if ";" not in connection_string:
        return connection_string
    aliases = {
        "host": "host",
        "port": "port",
        "database": "dbname",
        "username": "user",
        "password": "password",
    }
    values: list[str] = []
    for segment in connection_string.split(";"):
        if not segment:
            continue
        key, separator, value = segment.partition("=")
        mapped_key = aliases.get(key.strip().lower())
        if not separator or mapped_key is None:
            raise ValueError(f"Unsupported database connection segment: {segment}")
        escaped_value = value.replace("\\", "\\\\").replace("'", "\\'")
        values.append(f"{mapped_key}='{escaped_value}'")
    return " ".join(values)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run PostgreSQL profiling and write JSON plans."""

    parser = argparse.ArgumentParser(prog="profile-platform-queries")
    parser.add_argument("--output", type=Path, required=True)
    parsed = parser.parse_args(arguments)
    connection_string = os.getenv(
        "SPEC_PROOF_TEST_DATABASE",
        "Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123",
    )
    plans = profile_queries(psycopg_connection_string(connection_string))
    parsed.output.parent.mkdir(parents=True, exist_ok=True)
    parsed.output.write_text(
        json.dumps(plans, indent=2, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
