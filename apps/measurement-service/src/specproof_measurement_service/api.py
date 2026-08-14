"""HTTP facade for structured tech-pack import and compiler validation."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from specproof_measurement_service.compiler import CompiledMeasurementRule, compile_tech_pack
from specproof_measurement_service.ontology import tshirt_ontology
from specproof_measurement_service.techpack import (
    TechPackVersion,
    default_mapping_resolver,
    parse_csv_tech_pack,
    parse_json_tech_pack,
    parse_xlsx_tech_pack,
)

MAX_TECH_PACK_BYTES = 10 * 1024 * 1024
SUPPORTED_SUFFIXES = {".csv", ".json", ".xlsx"}


class TechPackValidationRequest(BaseModel):
    """Approved tech pack and size selected for compiler readiness."""

    tech_pack: TechPackVersion
    size_code: str = Field(min_length=1, max_length=50)


class TechPackValidationResponse(BaseModel):
    """Deterministic compiler validation result."""

    ready: bool
    rules: tuple[CompiledMeasurementRule, ...]


app = FastAPI(
    title="SpecProof Measurement Service",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return process health for platform readiness checks."""

    return {"status": "ok"}


@app.post("/v1/tech-packs/import", response_model=TechPackVersion)
async def import_tech_pack(
    file: Annotated[UploadFile, File(description="Structured CSV, XLSX, or JSON tech pack")],
    tech_pack_id: Annotated[str, Form()] = "tech-pack",
    version: Annotated[int, Form(ge=1)] = 1,
    brand: Annotated[str, Form()] = "Unknown",
    style_code: Annotated[str, Form()] = "UNKNOWN",
    garment_category: Annotated[str, Form()] = "t_shirt",
) -> TechPackVersion:
    """Import a bounded structured tech pack using canonical Phase 4 mapping."""

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only CSV, XLSX, and JSON tech packs are supported",
        )
    payload = await file.read(MAX_TECH_PACK_BYTES + 1)
    if len(payload) > MAX_TECH_PACK_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Tech-pack file exceeds the 10 MiB limit",
        )
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File is empty",
        )

    metadata: dict[str, object] = {
        "tech_pack_id": tech_pack_id,
        "version": version,
        "brand": brand,
        "style_code": style_code,
        "garment_category": garment_category,
    }
    resolver = default_mapping_resolver(tshirt_ontology())
    try:
        with TemporaryDirectory(prefix="specproof-tech-pack-") as directory:
            path = Path(directory) / f"upload{suffix}"
            path.write_bytes(payload)
            if suffix == ".csv":
                return parse_csv_tech_pack(path, resolver, **metadata)
            if suffix == ".xlsx":
                return parse_xlsx_tech_pack(path, resolver, **metadata)
            return parse_json_tech_pack(path, resolver)
    except (KeyError, TypeError, ValueError) as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Malformed tech pack: {exception}",
        ) from exception


@app.post("/v1/tech-packs/validate", response_model=TechPackValidationResponse)
def validate_tech_pack(request: TechPackValidationRequest) -> TechPackValidationResponse:
    """Validate approved mappings by compiling executable rules for one size."""

    try:
        rules = compile_tech_pack(request.tech_pack, tshirt_ontology(), size_code=request.size_code)
    except (KeyError, ValueError) as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exception),
        ) from exception
    if not rules:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"No grading rules exist for size {request.size_code}",
        )
    return TechPackValidationResponse(ready=True, rules=rules)


def main() -> None:
    """Run the measurement HTTP facade."""

    uvicorn.run("specproof_measurement_service.api:app", host="127.0.0.1", port=8010)
