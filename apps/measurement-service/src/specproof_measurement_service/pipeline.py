"""End-to-end perception pipeline for `.spcapture` packages."""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import cv2
import numpy as np
from pydantic import BaseModel, Field
from specproof_capture_service.capture_package import CapturePackageReader, sha256_file
from specproof_capture_service.models import CameraIntrinsics

from specproof_measurement_service.landmarks import Landmark, LandmarkSet, detect_tshirt_landmarks
from specproof_measurement_service.mesh import IndexedMesh, build_indexed_mesh
from specproof_measurement_service.parameterization import (
    SurfaceParameterization,
    parameterize_surface,
)
from specproof_measurement_service.point_cloud import (
    detect_support_plane,
    estimate_normals,
    organized_point_cloud,
)
from specproof_measurement_service.preprocessing import (
    BackgroundModel,
    build_background_model,
    preprocess_rgbd,
)
from specproof_measurement_service.segmentation import SegmentationResult, segment_garment
from specproof_measurement_service.surface import SurfaceConfidence, score_surface_confidence


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(UTC)


class PerceptionBoundingBox(BaseModel):
    """JSON contract for an image-space bounding box."""

    left: int
    top: int
    width: int
    height: int


class PerceptionLandmark(BaseModel):
    """JSON contract for one detected landmark."""

    name: str
    x: float
    y: float
    confidence: float
    status: str


class PerceptionSurfaceQuality(BaseModel):
    """JSON contract for surface quality scores."""

    overall: float
    valid_depth_ratio: float
    surface_coverage: float
    plane_fit_score: float
    normal_consistency: float
    reason: str


class PerceptionSurfaceMapPoint(BaseModel):
    """JSON contract for one preserved surface coordinate mapping."""

    pixel_x: int
    pixel_y: int
    x_metres: float
    y_metres: float
    z_metres: float
    u_mm: float
    v_mm: float


class PerceptionSurfaceMapping(BaseModel):
    """JSON contract for the flattened garment surface map."""

    coordinate_system: str
    mapped_pixel_count: int
    u_min_mm: float
    u_max_mm: float
    v_min_mm: float
    v_max_mm: float
    area_distortion_percent: float
    points: tuple[PerceptionSurfaceMapPoint, ...]


class PerceptionMesh(BaseModel):
    """JSON contract for lightweight indexed visualisation mesh metadata."""

    schema_version: int
    coordinate_system: str
    vertex_count: int
    triangle_count: int
    triangle_indices: tuple[tuple[int, int, int], ...]


class PerceptionResult(BaseModel):
    """Versioned JSON perception result contract."""

    schema_version: int = 1
    pipeline_version: str = "phase-3-deterministic-v1"
    capture_id: str
    station_id: str
    camera_serial: str
    package_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    produced_at_utc: datetime = Field(default_factory=utc_now)
    category: str
    orientation: str
    segmentation_confidence: float
    segmentation_area_pixels: int
    segmentation_iou: float | None = None
    bounding_box: PerceptionBoundingBox | None
    surface_quality: PerceptionSurfaceQuality
    surface_mapping: PerceptionSurfaceMapping
    mesh: PerceptionMesh
    landmarks: tuple[PerceptionLandmark, ...]
    landmark_confidence: float
    review_required: bool
    metadata: dict[str, str] = Field(default_factory=dict)

    def to_canonical_json(self) -> str:
        """Return canonical UTF-8 JSON text."""

        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def to_regression_json(self) -> str:
        """Return canonical JSON excluding non-deterministic runtime fields."""

        return json.dumps(
            self.model_dump(mode="json", exclude={"produced_at_utc"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

    def regression_sha256(self) -> str:
        """Return a stable SHA-256 fingerprint for regression comparisons."""

        return sha256(self.to_regression_json().encode("utf-8")).hexdigest()


class PerceptionPipeline:
    """Load `.spcapture` packages and produce versioned perception results."""

    def run(
        self,
        package_path: Path,
        *,
        background: BackgroundModel | None = None,
    ) -> PerceptionResult:
        """Run the deterministic Phase 3 perception pipeline."""

        manifest = CapturePackageReader().read_manifest(package_path)
        color_bgr, depth_units, intrinsics = _load_fused_payload(package_path)
        active_background = background or estimate_background_from_border(color_bgr, depth_units)
        preprocessed = preprocess_rgbd(color_bgr, depth_units, active_background)
        capture_zone_mask = np.ones(depth_units.shape, dtype=np.bool_)
        support_mask = capture_zone_mask & ~preprocessed.foreground_mask & (depth_units > 0)
        if int(np.count_nonzero(support_mask)) < 3:
            support_mask = capture_zone_mask & (depth_units > 0)
        points = organized_point_cloud(
            depth_units,
            depth_scale_metres=manifest.depth_scale_metres,
            intrinsics=intrinsics,
        )
        support_plane = detect_support_plane(points, support_mask)
        depth_garment_mask = preprocessed.foreground_mask & (depth_units > 0)
        segmentation = segment_garment(
            foreground_mask=preprocessed.foreground_mask,
            depth_garment_mask=depth_garment_mask,
        )
        surface_quality = score_surface_confidence(
            points=points,
            garment_mask=segmentation.mask,
            capture_zone_mask=capture_zone_mask,
            support_plane=support_plane,
            normals=estimate_normals(points),
        )
        surface_mapping = parameterize_surface(
            points=points,
            garment_mask=segmentation.mask,
            support_plane=support_plane,
        )
        mesh = build_indexed_mesh(surface_mapping)
        landmarks = detect_tshirt_landmarks(segmentation.mask)
        return _build_result(
            package_path=package_path,
            capture_id=manifest.capture_id,
            station_id=manifest.station_id,
            camera_serial=manifest.camera_serial,
            segmentation=segmentation,
            surface_quality=surface_quality,
            surface_mapping=surface_mapping,
            mesh=mesh,
            landmarks=landmarks,
        )


def estimate_background_from_border(
    color_bgr: np.ndarray,
    depth_units: np.ndarray,
) -> BackgroundModel:
    """Estimate a static background from package image border pixels."""

    if color_bgr.dtype != np.uint8 or color_bgr.ndim != 3 or color_bgr.shape[2] != 3:
        raise ValueError("color_bgr must be an HxWx3 uint8 image")
    if depth_units.dtype != np.uint16 or depth_units.ndim != 2:
        raise ValueError("depth_units must be an HxW uint16 image")
    if color_bgr.shape[:2] != depth_units.shape:
        raise ValueError("Color and depth shapes must match")
    border_mask = np.zeros(depth_units.shape, dtype=np.bool_)
    border_mask[0, :] = True
    border_mask[-1, :] = True
    border_mask[:, 0] = True
    border_mask[:, -1] = True
    color_median = np.median(color_bgr[border_mask], axis=0).astype(np.uint8)
    valid_depth = depth_units[border_mask & (depth_units > 0)]
    depth_value = np.uint16(np.median(valid_depth) if valid_depth.size else 0)
    background_color = np.empty_like(color_bgr)
    background_color[:, :] = color_median
    background_depth = np.full(depth_units.shape, depth_value, dtype=np.uint16)
    return build_background_model(background_color, background_depth)


def write_perception_result(result: PerceptionResult, output_path: Path) -> None:
    """Write canonical perception result JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.to_canonical_json() + "\n", encoding="utf-8", newline="\n")


def _build_result(
    *,
    package_path: Path,
    capture_id: str,
    station_id: str,
    camera_serial: str,
    segmentation: SegmentationResult,
    surface_quality: SurfaceConfidence,
    surface_mapping: SurfaceParameterization,
    mesh: IndexedMesh,
    landmarks: LandmarkSet,
) -> PerceptionResult:
    return PerceptionResult(
        capture_id=capture_id,
        station_id=station_id,
        camera_serial=camera_serial,
        package_sha256=sha256_file(package_path),
        category=segmentation.category.value,
        orientation=segmentation.orientation.value,
        segmentation_confidence=segmentation.confidence,
        segmentation_area_pixels=segmentation.area_pixels,
        bounding_box=(
            None
            if segmentation.bounding_box is None
            else PerceptionBoundingBox(
                left=segmentation.bounding_box.left,
                top=segmentation.bounding_box.top,
                width=segmentation.bounding_box.width,
                height=segmentation.bounding_box.height,
            )
        ),
        surface_quality=PerceptionSurfaceQuality(
            overall=surface_quality.overall,
            valid_depth_ratio=surface_quality.valid_depth_ratio,
            surface_coverage=surface_quality.surface_coverage,
            plane_fit_score=surface_quality.plane_fit_score,
            normal_consistency=surface_quality.normal_consistency,
            reason=surface_quality.reason,
        ),
        surface_mapping=PerceptionSurfaceMapping(
            coordinate_system=surface_mapping.coordinate_system,
            mapped_pixel_count=surface_mapping.mapped_pixel_count,
            u_min_mm=surface_mapping.u_min_mm,
            u_max_mm=surface_mapping.u_max_mm,
            v_min_mm=surface_mapping.v_min_mm,
            v_max_mm=surface_mapping.v_max_mm,
            area_distortion_percent=surface_mapping.area_distortion_percent,
            points=tuple(
                PerceptionSurfaceMapPoint(
                    pixel_x=point.pixel_x,
                    pixel_y=point.pixel_y,
                    x_metres=point.x_metres,
                    y_metres=point.y_metres,
                    z_metres=point.z_metres,
                    u_mm=point.u_mm,
                    v_mm=point.v_mm,
                )
                for point in surface_mapping.points
            ),
        ),
        mesh=PerceptionMesh(
            schema_version=mesh.schema_version,
            coordinate_system=mesh.coordinate_system,
            vertex_count=mesh.vertex_count,
            triangle_count=mesh.triangle_count,
            triangle_indices=mesh.triangle_indices,
        ),
        landmarks=tuple(_landmark_to_contract(landmark) for landmark in landmarks.landmarks),
        landmark_confidence=landmarks.confidence,
        review_required=landmarks.review_required or surface_quality.overall < 0.75,
        metadata={"source": "spcapture", "algorithm": "deterministic"},
    )


def _landmark_to_contract(landmark: Landmark) -> PerceptionLandmark:
    return PerceptionLandmark(
        name=landmark.name.value,
        x=landmark.x,
        y=landmark.y,
        confidence=landmark.confidence,
        status=landmark.status.value,
    )


def _load_fused_payload(package_path: Path) -> tuple[np.ndarray, np.ndarray, CameraIntrinsics]:
    with zipfile.ZipFile(package_path, mode="r") as archive:
        color = _decode_png(archive.read("frames/fused-color.png"), cv2.IMREAD_COLOR)
        depth = _decode_png(archive.read("frames/fused-depth.png"), cv2.IMREAD_UNCHANGED)
        intrinsics = CameraIntrinsics.model_validate_json(
            archive.read("calibration/depth-intrinsics.json")
        )
    if depth.dtype != np.uint16:
        depth = depth.astype(np.uint16)
    if intrinsics.width != depth.shape[1] or intrinsics.height != depth.shape[0]:
        intrinsics = intrinsics.model_copy(
            update={
                "width": int(depth.shape[1]),
                "height": int(depth.shape[0]),
                "fx": max(float(depth.shape[1]), 1.0),
                "fy": max(float(depth.shape[0]), 1.0),
                "ppx": depth.shape[1] / 2,
                "ppy": depth.shape[0] / 2,
            }
        )
    return color, depth, intrinsics


def _decode_png(payload: bytes, mode: int) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), mode)
    if image is None:
        raise ValueError("Capture package PNG payload could not be decoded")
    return image
