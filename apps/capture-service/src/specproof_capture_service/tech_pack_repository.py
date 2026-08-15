"""Versioned local tech-pack lookup for offline station inspection."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID

from specproof_measurement_service.techpack import TechPackVersion


class TechPackProvider(Protocol):
    """Resolve the immutable tech-pack version selected by the operator."""

    def get(self, tech_pack_id: UUID, version: int) -> TechPackVersion:
        """Return one exact approved tech-pack version."""
        ...


class LocalTechPackRepository:
    """Read approved station tech packs from versioned JSON files."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def get(self, tech_pack_id: UUID, version: int) -> TechPackVersion:
        """Load `<uuid>-v<version>.json` and verify immutable identifiers."""

        path = self._root / f"{tech_pack_id}-v{version}.json"
        if not path.is_file():
            raise KeyError(f"Tech pack version is not available offline: {tech_pack_id} v{version}")
        tech_pack = TechPackVersion.model_validate_json(path.read_text(encoding="utf-8"))
        if tech_pack.tech_pack_id != str(tech_pack_id) or tech_pack.version != version:
            raise ValueError("Tech-pack file identifiers do not match its versioned filename")
        if not tech_pack.approved:
            raise ValueError("Tech-pack version is not approved")
        return tech_pack
