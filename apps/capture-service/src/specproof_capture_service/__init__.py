"""Capture service package."""

from specproof_capture_service.calibration import (
    CalibrationStore,
    calibration_is_acceptable,
    create_calibration_record,
)
from specproof_capture_service.calibration_evaluator import (
    CalibrationScene,
    evaluate_synthetic_calibration,
)
from specproof_capture_service.capture_package import CapturePackageReader, CapturePackageWriter
from specproof_capture_service.coordinator import CaptureCoordinator
from specproof_capture_service.framing import CaptureZone, FramingResult, validate_capture_zone_framing
from specproof_capture_service.fusion import fuse_depth_median, select_midpoint_color
from specproof_capture_service.metadata import CaptureMetadata
from specproof_capture_service.mock_provider import MockCameraProvider
from specproof_capture_service.models import (
    CalibrationMetrics,
    CalibrationMode,
    CalibrationRecord,
    CalibrationThresholds,
    CameraDevice,
    CameraFrame,
    StreamProfile,
)
from specproof_capture_service.offline_queue import OfflineCaptureQueue, QueueItem, QueueState
from specproof_capture_service.replay_provider import CaptureReplayProvider
from specproof_capture_service.replay_validation import (
    ReplayValidationResult,
    validate_replay_corpus,
    validate_replay_package,
)

__all__ = [
    "CalibrationMetrics",
    "CalibrationMode",
    "CalibrationRecord",
    "CalibrationScene",
    "CalibrationStore",
    "CalibrationThresholds",
    "CameraDevice",
    "CameraFrame",
    "CaptureCoordinator",
    "CaptureMetadata",
    "CapturePackageReader",
    "CapturePackageWriter",
    "CaptureReplayProvider",
    "CaptureZone",
    "FramingResult",
    "MockCameraProvider",
    "OfflineCaptureQueue",
    "QueueItem",
    "QueueState",
    "ReplayValidationResult",
    "StreamProfile",
    "calibration_is_acceptable",
    "create_calibration_record",
    "evaluate_synthetic_calibration",
    "fuse_depth_median",
    "select_midpoint_color",
    "validate_capture_zone_framing",
    "validate_replay_corpus",
    "validate_replay_package",
]
