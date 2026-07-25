---
name: specproof-python
description: Python development skill for SpecProof. ALWAYS ACTIVE for any Python, camera, capture, measurement, perception, geometry, ML, CV, inference, calibration, point cloud, segmentation, landmark, ONNX, PyTorch, OpenCV, Open3D, NumPy, or service task. Covers typing, Pydantic, pathlib, UTC timestamps, structured logging, and pytest.
---

# SpecProof Python Development Skill

## When to Use
Activate this skill when writing Python code for SpecProof — camera service, measurement service, geometry utilities, ML training, or any Python module.

## Environment
- Python 3.11 (pinned)
- Package manager: `uv`
- Virtual environment: `.venv`
- Dependencies: `pyproject.toml` + `uv.lock`

## Code Standards

### Type Safety
```python
from datetime import datetime, timezone
from pathlib import Path

def process_capture(
    capture_path: Path,
    timestamp: datetime,
    station_id: str,
) -> MeasurementResult:
    """Process a capture package and return measurements.
    
    Args:
        capture_path: Path to the capture package directory.
        timestamp: UTC timestamp of the capture.
        station_id: Unique station identifier.
    
    Returns:
        MeasurementResult with all POM values and decision.
    
    Raises:
        CalibrationExpiredError: If station calibration has expired.
    """
    ...
```

### Timestamps
```python
# CORRECT
from datetime import datetime, timezone
now = datetime.now(timezone.utc)

# WRONG — never do this
now = datetime.now()       # naive, local time
now = datetime.utcnow()   # naive UTC (deprecated)
```

### File Paths
```python
# CORRECT
from pathlib import Path
capture_dir = Path("captures") / station_id / capture_id

# WRONG
capture_dir = f"captures\\{station_id}\\{capture_id}"  # Windows-only
```

### Data Models
```python
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class CaptureMetadata(BaseModel):
    station_id: str
    camera_serial: str
    capture_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checksum_sha256: str
    
    model_config = {"json_schema_extra": {"examples": [...]}}
```

### Error Handling
```python
class SpecProofError(Exception):
    """Base exception for SpecProof."""

class CalibrationExpiredError(SpecProofError):
    """Raised when station calibration has expired."""

class CameraNotFoundError(SpecProofError):
    """Raised when no camera is detected."""
```

### Logging
```python
import structlog

logger = structlog.get_logger(__name__)

logger.info(
    "capture_completed",
    station_id=station_id,
    capture_id=capture_id,
    duration_ms=duration_ms,
)
```

## Key Libraries
- **Camera:** pyrealsense2
- **Images:** OpenCV (`cv2`)
- **3D:** Open3D, trimesh
- **Numerics:** NumPy, SciPy
- **ML:** PyTorch, ONNX Runtime
- **Validation:** Pydantic
- **Testing:** pytest
- **Linting:** Ruff
- **Types:** Pyright

## Package Structure
```text
packages/
  geometry/           # Shared geometry utilities
  camera-abstractions/ # ICameraProvider interface
apps/
  capture-service/    # Camera integration service
  measurement-service/ # Perception + measurement pipeline
ml/
  training/           # Model training scripts
  evaluation/         # Model evaluation
  exports/            # ONNX model exports
```

## Testing Pattern
```python
import pytest
import numpy as np
from specproof.geometry import compute_distance

class TestComputeDistance:
    def test_straight_line_known_points(self):
        p1 = np.array([0.0, 0.0, 0.0])
        p2 = np.array([3.0, 4.0, 0.0])
        result = compute_distance(p1, p2, path_type="straight")
        assert result == pytest.approx(5.0, abs=0.001)

    def test_zero_distance_same_point(self):
        p = np.array([1.0, 2.0, 3.0])
        result = compute_distance(p, p, path_type="straight")
        assert result == pytest.approx(0.0, abs=1e-10)
```
