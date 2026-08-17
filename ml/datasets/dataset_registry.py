"""Dataset versioning and management for SpecProof ML datasets.

Provides a file-based dataset registry that tracks dataset versions,
content integrity (SHA-256), train/val/test splits, and metadata.
Each version is an immutable record; promotion creates a new version.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class DatasetSplit(BaseModel):
    """One train/val/test split entry."""

    name: str = Field(description="'train', 'val', or 'test'")
    file_paths: list[str]
    count: int
    checksum_sha256: str = Field(description="SHA-256 of sorted, concatenated file checksums")


class DatasetVersion(BaseModel):
    """Immutable dataset version manifest."""

    dataset_id: str
    version: str = Field(description="Semantic version string, e.g. '1.0.0'")
    description: str
    category: str = Field(description="Garment category, e.g. 't_shirt'")
    total_annotations: int
    splits: list[DatasetSplit]
    manifest_sha256: str = Field(description="SHA-256 of the canonical manifest JSON")
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = "specproof-ml"
    metadata: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1

    def to_canonical_json(self) -> str:
        """Return canonical UTF-8 JSON with sorted keys."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


# ---------------------------------------------------------------------------
# Dataset registry
# ---------------------------------------------------------------------------


class DatasetRegistry:
    """File-based dataset version registry.

    Each version is stored as a JSON manifest in ``registry_dir``.
    The registry is append-only — existing versions are never modified.

    Parameters
    ----------
    registry_dir:
        Directory where version manifests are stored.
    """

    def __init__(self, registry_dir: Path) -> None:
        self._dir = Path(registry_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        *,
        dataset_id: str,
        version: str,
        description: str,
        category: str,
        splits: dict[str, list[Path]],
        created_by: str = "specproof-ml",
        metadata: dict[str, Any] | None = None,
    ) -> DatasetVersion:
        """Register a new dataset version.

        Parameters
        ----------
        dataset_id:
            Logical dataset identifier, e.g. ``'tshirt-segmentation'``.
        version:
            Semantic version string, e.g. ``'1.0.0'``.
        description:
            Human-readable description of this version.
        category:
            Garment category.
        splits:
            Mapping of split name (``'train'``, ``'val'``, ``'test'``) to
            lists of annotation file paths.
        created_by:
            Creator identifier.
        metadata:
            Optional arbitrary metadata.

        Returns
        -------
        DatasetVersion
            The registered version manifest.

        Raises
        ------
        FileExistsError
            If this ``(dataset_id, version)`` is already registered.
        """
        manifest_path = self._manifest_path(dataset_id, version)
        if manifest_path.exists():
            raise FileExistsError(
                f"Dataset version '{dataset_id}@{version}' is already registered at "
                f"{manifest_path}"
            )

        split_records: list[DatasetSplit] = []
        total = 0
        for split_name, paths in splits.items():
            sorted_paths = sorted(paths)
            file_checksums = [_sha256_file(p) for p in sorted_paths]
            combined = hashlib.sha256(
                ",".join(file_checksums).encode("utf-8")
            ).hexdigest()
            split_records.append(
                DatasetSplit(
                    name=split_name,
                    file_paths=[str(p) for p in sorted_paths],
                    count=len(sorted_paths),
                    checksum_sha256=combined,
                )
            )
            total += len(sorted_paths)

        # Build a temporary version to compute its manifest checksum
        temp_version = DatasetVersion(
            dataset_id=dataset_id,
            version=version,
            description=description,
            category=category,
            total_annotations=total,
            splits=split_records,
            manifest_sha256="",  # placeholder
            created_at_utc=datetime.now(UTC),
            created_by=created_by,
            metadata=metadata or {},
        )
        manifest_body = temp_version.to_canonical_json()
        manifest_checksum = hashlib.sha256(manifest_body.encode("utf-8")).hexdigest()

        final_version = temp_version.model_copy(
            update={"manifest_sha256": manifest_checksum}
        )
        manifest_path.write_text(
            final_version.to_canonical_json() + "\n", encoding="utf-8", newline="\n"
        )
        return final_version

    def get(self, dataset_id: str, version: str) -> DatasetVersion:
        """Load a registered dataset version by ID and version.

        Raises
        ------
        KeyError
            If the version is not found.
        """
        manifest_path = self._manifest_path(dataset_id, version)
        if not manifest_path.exists():
            raise KeyError(f"Dataset version '{dataset_id}@{version}' not found")
        return DatasetVersion.model_validate_json(manifest_path.read_text(encoding="utf-8"))

    def list_versions(self, dataset_id: str) -> list[str]:
        """Return all registered version strings for a dataset, sorted."""
        prefix = f"{dataset_id}@"
        versions = [
            p.stem[len(prefix):]
            for p in self._dir.glob(f"{dataset_id}@*.json")
        ]
        return sorted(versions)

    def verify_integrity(self, dataset_id: str, version: str) -> bool:
        """Verify that all annotation files in a version still match their checksums.

        Returns
        -------
        bool
            ``True`` if all files are intact, ``False`` if any checksum fails.
        """
        dv = self.get(dataset_id, version)
        for split in dv.splits:
            file_checksums = []
            for path_str in split.file_paths:
                p = Path(path_str)
                if not p.exists():
                    return False
                file_checksums.append(_sha256_file(p))
            combined = hashlib.sha256(
                ",".join(file_checksums).encode("utf-8")
            ).hexdigest()
            if combined != split.checksum_sha256:
                return False
        return True

    def _manifest_path(self, dataset_id: str, version: str) -> Path:
        safe_id = dataset_id.replace("/", "_")
        safe_ver = version.replace("/", "_")
        return self._dir / f"{safe_id}@{safe_ver}.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()
