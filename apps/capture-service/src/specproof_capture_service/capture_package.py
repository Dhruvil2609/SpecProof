"""Platform-neutral capture package writer and reader."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from specproof_capture_service.errors import CapturePackageError
from specproof_capture_service.fusion import fuse_depth_median, select_midpoint_color
from specproof_capture_service.models import CameraFrame, CaptureManifest, StreamProfile


def sha256_bytes(payload: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _encode_png(image: np.ndarray) -> bytes:
    success, encoded = cv2.imencode(".png", image)
    if not success:
        raise CapturePackageError("OpenCV failed to encode PNG data")
    return encoded.tobytes()


class CapturePackageWriter:
    """Create complete ZIP64 `.spcapture` packages atomically."""

    def write(
        self,
        *,
        output_path: Path,
        station_id: str,
        calibration_id: str,
        profile: StreamProfile,
        frames: Sequence[CameraFrame],
        environment: Mapping[str, str] | None = None,
    ) -> tuple[CaptureManifest, str]:
        """Write a validated package and return its manifest and digest."""

        if not 3 <= len(frames) <= 15:
            raise ValueError("Capture frame count must be between 3 and 15")
        serials = {frame.camera_serial for frame in frames}
        if len(serials) != 1:
            raise ValueError("All frames must come from one camera")

        capture_id = str(uuid4())
        assets: dict[str, bytes] = {
            "frames/fused-color.png": _encode_png(select_midpoint_color(frames)),
            "frames/fused-depth.png": _encode_png(fuse_depth_median(frames)),
            "calibration/color-intrinsics.json": self._canonical_json(
                frames[0].color_intrinsics.model_dump(mode="json")
            ),
            "calibration/depth-intrinsics.json": self._canonical_json(
                frames[0].depth_intrinsics.model_dump(mode="json")
            ),
            "calibration/depth-to-color.json": self._canonical_json(
                frames[0].depth_to_color.model_dump(mode="json")
            ),
        }
        for index, frame in enumerate(frames):
            assets[f"frames/{index:03d}-color.png"] = _encode_png(frame.color_bgr)
            assets[f"frames/{index:03d}-depth.png"] = _encode_png(frame.depth_units)
            assets[f"frames/{index:03d}-metadata.json"] = self._canonical_json(
                {
                    "frame_id": frame.frame_id,
                    "captured_at_utc": frame.captured_at_utc.isoformat(),
                }
            )

        manifest = CaptureManifest(
            capture_id=capture_id,
            station_id=station_id,
            camera_serial=frames[0].camera_serial,
            captured_at_utc=frames[len(frames) // 2].captured_at_utc,
            frame_count=len(frames),
            profile=profile,
            depth_scale_metres=frames[0].depth_scale_metres,
            calibration_id=calibration_id,
            environment=dict(environment or {}),
            files=tuple(sorted(assets)),
        )
        assets["manifest.json"] = self._canonical_json(manifest.model_dump(mode="json"))
        checksum_lines = [
            f"{sha256_bytes(payload)}  {name}" for name, payload in sorted(assets.items())
        ]
        assets["checksums.sha256"] = ("\n".join(checksum_lines) + "\n").encode("utf-8")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=output_path.parent,
                prefix=f".{output_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
            with zipfile.ZipFile(
                temporary_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            ) as archive:
                for name, payload in sorted(assets.items()):
                    archive.writestr(name, payload)
            os.replace(temporary_path, output_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

        return manifest, sha256_file(output_path)

    @staticmethod
    def _canonical_json(value: object) -> bytes:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")


class CapturePackageReader:
    """Load and validate `.spcapture` packages."""

    def read_manifest(self, package_path: Path) -> CaptureManifest:
        """Validate package checksums and return its manifest."""

        try:
            with zipfile.ZipFile(package_path, mode="r") as archive:
                names = set(archive.namelist())
                required = {"manifest.json", "checksums.sha256"}
                if not required.issubset(names):
                    raise CapturePackageError("Capture package is missing required files")
                expected = self._parse_checksums(archive.read("checksums.sha256"))
                for name, digest in expected.items():
                    if name not in names:
                        raise CapturePackageError(f"Capture package is missing {name}")
                    if sha256_bytes(archive.read(name)) != digest:
                        raise CapturePackageError(f"Checksum mismatch for {name}")
                return CaptureManifest.model_validate_json(archive.read("manifest.json"))
        except (OSError, zipfile.BadZipFile) as error:
            raise CapturePackageError(str(error)) from error

    @staticmethod
    def _parse_checksums(payload: bytes) -> dict[str, str]:
        checksums: dict[str, str] = {}
        for line in payload.decode("utf-8").splitlines():
            digest, separator, name = line.partition("  ")
            if not separator or len(digest) != 64 or not name:
                raise CapturePackageError("Invalid checksums.sha256 format")
            checksums[name] = digest
        return checksums
