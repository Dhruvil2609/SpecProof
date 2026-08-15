from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import grpc
import pytest
from google.protobuf import empty_pb2
from specproof_capture_service.calibration import (
    CalibrationStore,
    fixed_calibration_evaluator,
)
from specproof_capture_service.coordinator import CaptureCoordinator
from specproof_capture_service.generated import capture_station_pb2
from specproof_capture_service.grpc_server import CaptureStationService
from specproof_capture_service.inspection_queue import OfflineInspectionQueue
from specproof_capture_service.mock_provider import MockCameraProvider
from specproof_capture_service.models import CalibrationMetrics
from specproof_capture_service.offline_queue import OfflineCaptureQueue
from specproof_capture_service.tech_pack_repository import LocalTechPackRepository
from specproof_measurement_service import InspectionPipeline


class FakeContext:
    def __init__(self, *, cancelled: bool = False) -> None:
        self.status_code: grpc.StatusCode | None = None
        self.detail: str | None = None
        self._cancelled = cancelled

    def cancelled(self) -> bool:
        return self._cancelled

    async def abort(self, status_code: grpc.StatusCode, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        raise RuntimeError(detail)


@pytest.fixture
def grpc_service(
    tmp_path: Path,
) -> tuple[CaptureStationService, OfflineCaptureQueue]:
    provider = MockCameraProvider()
    store = CalibrationStore(tmp_path / "calibrations")
    queue = OfflineCaptureQueue(tmp_path / "queue.sqlite3")
    coordinator = CaptureCoordinator(
        provider=provider,
        calibration_store=store,
        queue=queue,
        capture_root=tmp_path / "captures",
    )
    service = CaptureStationService(
        provider=provider,
        coordinator=coordinator,
        calibration_store=store,
        calibration_evaluator=fixed_calibration_evaluator(
            CalibrationMetrics(
                scale_error_percent=0.01,
                plane_rms_mm=0.5,
                tilt_degrees=0.1,
                lighting_variation_percent=2.0,
                alignment_valid=True,
            )
        ),
    )
    return service, queue


@pytest.mark.unit
async def test_grpc_list_devices_returns_mock_camera(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service

    response = await service.ListDevices(empty_pb2.Empty(), FakeContext())

    queue.close()
    assert response.devices[0].serial_number == "MOCK-001"


@pytest.mark.unit
async def test_grpc_health_returns_valid_queue_depth(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service

    response = await service.GetHealth(empty_pb2.Empty(), FakeContext())

    queue.close()
    assert response.status == "healthy" and response.offline_queue_depth == 0


@pytest.mark.unit
async def test_grpc_calibration_then_capture_returns_package(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    calibration = await service.RunCalibration(
        capture_station_pb2.CalibrationRequest(
            camera_serial="MOCK-001",
            station_id="station-001",
            operator_id="operator-001",
            artefact_id="artefact-001",
            mode=capture_station_pb2.CALIBRATION_MODE_FULL,
        ),
        FakeContext(),
    )

    response = await service.Capture(
        capture_station_pb2.CaptureRequest(
            camera_serial="MOCK-001",
            station_id="station-001",
            frame_count=3,
            profile=capture_station_pb2.StreamProfile(
                color_width=8,
                color_height=6,
                depth_width=8,
                depth_height=6,
                frames_per_second=30,
            ),
        ),
        FakeContext(),
    )

    queue.close()
    assert calibration.valid is True and Path(response.package_path).exists()


@pytest.mark.unit
async def test_grpc_integrated_capture_persists_result_before_acknowledgement(
    tmp_path: Path,
) -> None:
    provider = MockCameraProvider()
    calibration_store = CalibrationStore(tmp_path / "calibrations")
    capture_queue = OfflineCaptureQueue(tmp_path / "captures.sqlite3")
    result_queue = OfflineInspectionQueue(tmp_path / "inspection-results.sqlite3")
    coordinator = CaptureCoordinator(
        provider=provider,
        calibration_store=calibration_store,
        queue=capture_queue,
        capture_root=tmp_path / "captures",
    )
    service = CaptureStationService(
        provider=provider,
        coordinator=coordinator,
        calibration_store=calibration_store,
        calibration_evaluator=fixed_calibration_evaluator(
            CalibrationMetrics(
                scale_error_percent=0.01,
                plane_rms_mm=0.5,
                tilt_degrees=0.1,
                lighting_variation_percent=2.0,
                alignment_valid=True,
            )
        ),
        inspection_processor=InspectionPipeline(),
        inspection_queue=result_queue,
        tech_pack_provider=LocalTechPackRepository(Path("config/station/tech-packs")),
    )
    station_id = uuid4()
    inspection_id = uuid4()
    await service.RunCalibration(
        capture_station_pb2.CalibrationRequest(
            camera_serial="MOCK-001",
            station_id=str(station_id),
            operator_id=str(uuid4()),
            artefact_id="artefact-001",
            mode=capture_station_pb2.CALIBRATION_MODE_FULL,
        ),
        FakeContext(),
    )

    response = await service.Capture(
        capture_station_pb2.CaptureRequest(
            camera_serial="MOCK-001",
            station_id=str(station_id),
            frame_count=3,
            profile=capture_station_pb2.StreamProfile(
                color_width=40,
                color_height=32,
                depth_width=40,
                depth_height=32,
                frames_per_second=30,
            ),
            inspection_context=capture_station_pb2.InspectionContext(
                tenant_id=str(uuid4()),
                inspection_id=str(inspection_id),
                station_code="STATION-INTEGRATED-001",
                order_code="PO-24081",
                style_code="SP-TEE-01",
                size_code="M",
                batch_id=str(uuid4()),
                tech_pack_id="55555555-5555-5555-5555-555555555555",
                tech_pack_version=1,
            ),
        ),
        FakeContext(),
    )

    persisted = result_queue.get_by_inspection_id(str(inspection_id))
    capture_queue.close()
    result_queue.close()
    assert response.inspection_id == str(inspection_id)
    assert response.processing_status == capture_station_pb2.CAPTURE_PROCESSING_STATUS_QUEUED
    assert persisted is not None and persisted.verify_hash()


@pytest.mark.unit
async def test_grpc_get_active_calibration_returns_latest_record(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    await service.RunCalibration(
        capture_station_pb2.CalibrationRequest(
            camera_serial="MOCK-001",
            station_id="station-001",
            operator_id="operator-001",
            artefact_id="artefact-001",
            mode=capture_station_pb2.CALIBRATION_MODE_DAILY,
        ),
        FakeContext(),
    )

    active = await service.GetActiveCalibration(
        capture_station_pb2.ActiveCalibrationRequest(
            camera_serial="MOCK-001",
            station_id="station-001",
        ),
        FakeContext(),
    )

    queue.close()
    assert active.version == 1


@pytest.mark.unit
async def test_grpc_preview_returns_encoded_rgb_and_depth(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    stream = service.StreamPreview(
        capture_station_pb2.PreviewRequest(
            camera_serial="MOCK-001",
            profile=capture_station_pb2.StreamProfile(
                color_width=8,
                color_height=6,
                depth_width=8,
                depth_height=6,
                frames_per_second=30,
            ),
        ),
        FakeContext(),
    )

    frame = await anext(stream)
    await stream.aclose()

    queue.close()
    assert frame.color_jpeg and frame.depth_preview_png


@pytest.mark.unit
async def test_grpc_recording_start_and_stop_returns_same_path(
    tmp_path: Path,
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    recording_path = tmp_path / "recordings" / "capture.bag"

    started = await service.StartRecording(
        capture_station_pb2.RecordingRequest(
            camera_serial="MOCK-001",
            output_path=str(recording_path),
            profile=capture_station_pb2.StreamProfile(
                color_width=8,
                color_height=6,
                depth_width=8,
                depth_height=6,
                frames_per_second=30,
            ),
        ),
        FakeContext(),
    )
    stopped = await service.StopRecording(empty_pb2.Empty(), FakeContext())

    queue.close()
    assert started.active is True and stopped.output_path == str(recording_path)


@pytest.mark.unit
async def test_grpc_capture_without_calibration_maps_failed_precondition(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    context = FakeContext()

    with pytest.raises(RuntimeError, match="calibration"):
        await service.Capture(
            capture_station_pb2.CaptureRequest(
                camera_serial="MOCK-001",
                station_id="station-001",
            ),
            context,
        )

    queue.close()
    assert context.status_code == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.unit
async def test_grpc_get_active_calibration_without_record_aborts(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    context = FakeContext()

    with pytest.raises(RuntimeError, match="No active calibration"):
        await service.GetActiveCalibration(
            capture_station_pb2.ActiveCalibrationRequest(
                camera_serial="MOCK-001",
                station_id="station-001",
            ),
            context,
        )

    queue.close()
    assert context.status_code == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.unit
async def test_grpc_run_calibration_without_evaluator_aborts(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    service._calibration_evaluator = None
    context = FakeContext()

    with pytest.raises(RuntimeError, match="evaluator"):
        await service.RunCalibration(
            capture_station_pb2.CalibrationRequest(
                camera_serial="MOCK-001",
                station_id="station-001",
            ),
            context,
        )

    queue.close()
    assert context.status_code == grpc.StatusCode.FAILED_PRECONDITION


@pytest.mark.unit
async def test_grpc_cancelled_preview_stops_without_frame(
    grpc_service: tuple[CaptureStationService, OfflineCaptureQueue],
) -> None:
    service, queue = grpc_service
    stream = service.StreamPreview(
        capture_station_pb2.PreviewRequest(camera_serial="MOCK-001"),
        FakeContext(cancelled=True),
    )

    with pytest.raises(StopAsyncIteration):
        await anext(stream)

    queue.close()
