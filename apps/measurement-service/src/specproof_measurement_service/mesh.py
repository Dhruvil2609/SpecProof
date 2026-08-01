"""Lightweight indexed mesh generation for perception visualisation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from specproof_measurement_service.parameterization import (
    SurfaceMapPoint,
    SurfaceParameterization,
    mapping_by_pixel,
)


@dataclass(frozen=True)
class MeshVertex:
    """Mesh vertex with preserved image, metric 3D, and UV coordinates."""

    pixel_x: int
    pixel_y: int
    x_metres: float
    y_metres: float
    z_metres: float
    u_mm: float
    v_mm: float


@dataclass(frozen=True)
class IndexedMesh:
    """Simple indexed triangle mesh for lightweight visualisation exports."""

    schema_version: int
    coordinate_system: str
    vertices: tuple[MeshVertex, ...]
    triangle_indices: tuple[tuple[int, int, int], ...]

    @property
    def vertex_count(self) -> int:
        """Return the number of mesh vertices."""

        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        """Return the number of mesh triangles."""

        return len(self.triangle_indices)

    def to_canonical_json(self) -> str:
        """Return canonical JSON for the indexed mesh contract."""

        payload = asdict(self)
        payload["vertex_count"] = self.vertex_count
        payload["triangle_count"] = self.triangle_count
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )


def build_indexed_mesh(parameterization: SurfaceParameterization) -> IndexedMesh:
    """Build an indexed triangle mesh from a preserved surface parameterisation."""

    vertices = tuple(_vertex_from_mapping(point) for point in parameterization.points)
    vertex_index_by_pixel = {
        (vertex.pixel_x, vertex.pixel_y): index for index, vertex in enumerate(vertices)
    }
    point_by_pixel = mapping_by_pixel(parameterization)
    triangles: list[tuple[int, int, int]] = []
    for pixel_x, pixel_y in sorted(point_by_pixel):
        top_left = (pixel_x, pixel_y)
        top_right = (pixel_x + 1, pixel_y)
        bottom_left = (pixel_x, pixel_y + 1)
        bottom_right = (pixel_x + 1, pixel_y + 1)
        if (
            top_right in vertex_index_by_pixel
            and bottom_left in vertex_index_by_pixel
            and bottom_right in vertex_index_by_pixel
        ):
            triangles.append(
                (
                    vertex_index_by_pixel[top_left],
                    vertex_index_by_pixel[bottom_left],
                    vertex_index_by_pixel[top_right],
                )
            )
            triangles.append(
                (
                    vertex_index_by_pixel[top_right],
                    vertex_index_by_pixel[bottom_left],
                    vertex_index_by_pixel[bottom_right],
                )
            )
    return IndexedMesh(
        schema_version=1,
        coordinate_system=parameterization.coordinate_system,
        vertices=vertices,
        triangle_indices=tuple(triangles),
    )


def write_indexed_mesh(mesh: IndexedMesh, output_path: Path) -> None:
    """Write canonical indexed mesh JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mesh.to_canonical_json() + "\n", encoding="utf-8", newline="\n")


def _vertex_from_mapping(point: SurfaceMapPoint) -> MeshVertex:
    return MeshVertex(
        pixel_x=point.pixel_x,
        pixel_y=point.pixel_y,
        x_metres=point.x_metres,
        y_metres=point.y_metres,
        z_metres=point.z_metres,
        u_mm=point.u_mm,
        v_mm=point.v_mm,
    )
