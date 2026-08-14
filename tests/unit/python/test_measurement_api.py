from __future__ import annotations

import csv
import io

from fastapi.testclient import TestClient
from specproof_measurement_service.api import app


def _csv_payload() -> bytes:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=(
            "pom",
            "size",
            "target_mm",
            "lower_tolerance_mm",
            "upper_tolerance_mm",
        ),
    )
    writer.writeheader()
    writer.writerow(
        {
            "pom": "Across Chest",
            "size": "M",
            "target_mm": "500",
            "lower_tolerance_mm": "5",
            "upper_tolerance_mm": "5",
        }
    )
    return output.getvalue().encode("utf-8")


def test_tech_pack_import_and_validation_compile_approved_mapping() -> None:
    client = TestClient(app)
    imported = client.post(
        "/v1/tech-packs/import",
        files={"file": ("core-tee.csv", _csv_payload(), "text/csv")},
        data={
            "tech_pack_id": "tp-core-tee",
            "brand": "SpecProof Demo",
            "style_code": "CORE-TEE",
        },
    )

    assert imported.status_code == 200
    tech_pack = imported.json()
    assert tech_pack["approved"] is True
    assert tech_pack["imported_poms"][0]["canonical_pom_id"] == "chest_width"
    assert len(tech_pack["version_hash_sha256"]) == 64

    validated = client.post(
        "/v1/tech-packs/validate",
        json={"tech_pack": tech_pack, "size_code": "M"},
    )

    assert validated.status_code == 200
    assert validated.json()["ready"] is True
    assert validated.json()["rules"][0]["pom_id"] == "chest_width"


def test_tech_pack_import_rejects_unsupported_and_oversized_files() -> None:
    client = TestClient(app)

    unsupported = client.post(
        "/v1/tech-packs/import",
        files={"file": ("tech-pack.pdf", b"not-a-pdf", "application/pdf")},
    )
    oversized = client.post(
        "/v1/tech-packs/import",
        files={"file": ("tech-pack.csv", b"x" * (10 * 1024 * 1024 + 1), "text/csv")},
    )

    assert unsupported.status_code == 415
    assert oversized.status_code == 413


def test_tech_pack_validation_rejects_unapproved_mapping() -> None:
    client = TestClient(app)
    imported = client.post(
        "/v1/tech-packs/import",
        files={
            "file": (
                "unknown.csv",
                _csv_payload().replace(b"Across Chest", b"Unmapped Dimension"),
                "text/csv",
            )
        },
    )

    response = client.post(
        "/v1/tech-packs/validate",
        json={"tech_pack": imported.json(), "size_code": "M"},
    )

    assert response.status_code == 422
    assert "approved" in response.json()["detail"]
