"""Replay corpus validation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from specproof_capture_service.capture_package import CapturePackageReader, sha256_file
from specproof_capture_service.errors import CapturePackageError


@dataclass(frozen=True)
class ReplayValidationResult:
    """Validation result for one replay capture package."""

    package_path: Path
    valid: bool
    capture_id: str | None
    package_sha256: str | None
    reason: str


def validate_replay_package(package_path: Path) -> ReplayValidationResult:
    """Validate one `.spcapture` package without requiring camera hardware."""

    try:
        manifest = CapturePackageReader().read_manifest(package_path)
        return ReplayValidationResult(
            package_path=package_path,
            valid=True,
            capture_id=manifest.capture_id,
            package_sha256=sha256_file(package_path),
            reason="ok",
        )
    except (CapturePackageError, OSError, ValueError) as error:
        return ReplayValidationResult(
            package_path=package_path,
            valid=False,
            capture_id=None,
            package_sha256=None,
            reason=str(error),
        )


def validate_replay_corpus(root: Path) -> tuple[ReplayValidationResult, ...]:
    """Validate every `.spcapture` package under a corpus root."""

    packages = sorted(root.rglob("*.spcapture"))
    return tuple(validate_replay_package(path) for path in packages)
