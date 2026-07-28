import pytest
from specproof_geometry import Point3D, euclidean_distance_mm


@pytest.mark.unit
def test_euclidean_distance_mm_known_3_4_12_triangle_returns_13_mm() -> None:
    first = Point3D(0.0, 0.0, 0.0)
    second = Point3D(3.0, 4.0, 12.0)

    actual = euclidean_distance_mm(first, second)

    assert actual == pytest.approx(13.0, abs=0.001)


@pytest.mark.unit
def test_euclidean_distance_mm_same_point_returns_zero() -> None:
    point = Point3D(10.0, -4.0, 7.5)

    actual = euclidean_distance_mm(point, point)

    assert actual == pytest.approx(0.0, abs=0.001)
