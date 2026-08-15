"""gRPC capture station server."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

import cv2
import grpc
import numpy as np
import structlog
from google.protobuf import empty_pb2, timestamp_pb2
from specproof_measurement_service.inspection import (
    InspectionContext,
    InspectionPipeline,
    InspectionPipelineRequest,
    InspectionPipelineResult,
)

from specproof_capture_service.calibration import (
    CalibrationEvaluator,
    CalibrationStore,
    create_calibration_record,
    fixed_calibration_evaluator,
)
from specproof_capture_service.coordinator import CaptureCoordinator
from specproof_capture_service.errors import (
    CalibrationExpiredError,
    CameraNotFoundError,
    CameraUnavailableError,
)
from specproof_capture_service.generated import capture_station_pb2, capture_station_pb2_grpc
from specproof_capture_service.inspection_queue import OfflineInspectionQueue
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
from specproof_capture_service.observability import configure_observability
from specproof_capture_service.offline_queue import OfflineCaptureQueue
from specproof_capture_service.provider import CameraProvider
from specproof_capture_service.realsense_provider import RealSenseCameraProvider
from specproof_capture_service.replay_provider import CaptureReplayProvider
from specproof_capture_service.storage import S3CaptureObjectStore
from specproof_capture_service.synchronization import (
    CaptureSynchronizer,
    HttpPlatformStationClient,
    InspectionResultSynchronizer,
)
from specproof_capture_service.tech_pack_repository import (
    LocalTechPackRepository,
    TechPackProvider,
)

logger = structlog.get_logger(__name__)


class InspectionProcessor(Protocol):
    """Inspection pipeline boundary used by the capture gRPC service."""

    def run(self, request: InspectionPipelineRequest) -> InspectionPipelineResult:
        """Process one captured package into sealed platform evidence."""
        ...


class CaptureStationService(capture_station_pb2_grpc.CaptureStationServicer):
    """Capture station gRPC implementation."""

    def __init__(
        self,
        *,
        provider: CameraProvider,
        coordinator: CaptureCoordinator,
        calibration_store: CalibrationStore,
        calibration_evaluator: CalibrationEvaluator | None,
        thresholds: CalibrationThresholds | None = None,
        inspection_processor: InspectionProcessor | None = None,
        inspection_queue: OfflineInspectionQueue | None = None,
        tech_pack_provider: TechPackProvider | None = None,
    ) -> None:
        self._provider = provider
        self._coordinator = coordinator
        self._calibration_store = calibration_store
        self._calibration_evaluator = calibration_evaluator
        self._thresholds = thresholds or CalibrationThresholds()
        self._inspection_processor = inspection_processor
        self._inspection_queue = inspection_queue
        self._tech_pack_provider = tech_pack_provider

    async def ListDevices(
        self,
        request: empty_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.ListDevicesResponse:
        del request, context
        devices = await self._provider.list_devices()
        return capture_station_pb2.ListDevicesResponse(
            devices=[self._device_message(device) for device in devices]
        )

    async def GetHealth(
        self,
        request: empty_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.StationHealth:
        del request, context
        health = await self._coordinator.health()
        return capture_station_pb2.StationHealth(
            status=health.status,
            checked_at_utc=self._timestamp(health.checked_at_utc),
            camera_status=health.camera_status,
            storage_status=health.storage_status,
            clock_status=health.clock_status,
            offline_queue_depth=health.offline_queue_depth,
            detail=health.detail,
        )

    async def StreamPreview(
        self,
        request: capture_station_pb2.PreviewRequest,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[capture_station_pb2.PreviewFrame]:
        profile = self._profile_model(request.profile)
        try:
            async for frame in self._provider.stream_preview(request.camera_serial, profile):
                if context.cancelled():
                    return
                yield self._preview_message(frame)
        except CameraNotFoundError as error:
            await context.abort(grpc.StatusCode.NOT_FOUND, str(error))
        except CameraUnavailableError as error:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(error))

    async def Capture(
        self,
        request: capture_station_pb2.CaptureRequest,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.CaptureResponse:
        try:
            manifest, path, digest = await self._coordinator.capture(
                station_id=request.station_id,
                camera_serial=request.camera_serial,
                profile=self._profile_model(request.profile),
                frame_count=request.frame_count or 5,
            )
            inspection_id = ""
            processing_status = capture_station_pb2.CAPTURE_PROCESSING_STATUS_CAPTURED
            if request.HasField("inspection_context"):
                if (
                    self._inspection_processor is None
                    or self._inspection_queue is None
                    or self._tech_pack_provider is None
                ):
                    await context.abort(
                        grpc.StatusCode.FAILED_PRECONDITION,
                        "Integrated inspection processing is not configured",
                    )
                selected = request.inspection_context
                inspection_id = selected.inspection_id or str(uuid4())
                tech_pack_id = UUID(selected.tech_pack_id)
                tech_pack = self._tech_pack_provider.get(
                    tech_pack_id,
                    selected.tech_pack_version,
                )
                pipeline_request = InspectionPipelineRequest(
                    context=InspectionContext(
                        tenant_id=UUID(selected.tenant_id),
                        station_id=UUID(request.station_id),
                        inspection_id=UUID(inspection_id),
                        capture_id=UUID(manifest.capture_id),
                        calibration_id=UUID(manifest.calibration_id),
                        station_code=selected.station_code,
                        order_code=selected.order_code,
                        style_code=selected.style_code,
                        size_code=selected.size_code,
                        batch_id=UUID(selected.batch_id) if selected.batch_id else None,
                        tech_pack_id=tech_pack_id,
                        tech_pack_version=selected.tech_pack_version,
                    ),
                    package_path=path,
                    tech_pack=tech_pack,
                )
                pipeline_result = await asyncio.to_thread(
                    self._inspection_processor.run,
                    pipeline_request,
                )
                self._inspection_queue.enqueue(
                    capture_id=manifest.capture_id,
                    inspection_id=inspection_id,
                    payload=pipeline_result.platform_submission.to_canonical_payload(),
                )
                processing_status = capture_station_pb2.CAPTURE_PROCESSING_STATUS_QUEUED
            return capture_station_pb2.CaptureResponse(
                capture_id=manifest.capture_id,
                package_path=str(path),
                package_sha256=digest,
                captured_at_utc=self._timestamp(manifest.captured_at_utc),
                calibration_id=manifest.calibration_id,
                inspection_id=inspection_id,
                processing_status=processing_status,
            )
        except (KeyError, ValueError) as error:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(error))
        except CameraNotFoundError as error:
            await context.abort(grpc.StatusCode.NOT_FOUND, str(error))
        except CalibrationExpiredError as error:
            await context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(error))
        except (CameraUnavailableError, OSError) as error:
            await context.abort(grpc.StatusCode.UNAVAILABLE, str(error))
        raise RuntimeError("gRPC context abort did not terminate the call")

    async def StartRecording(
        self,
        request: capture_station_pb2.RecordingRequest,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.RecordingResponse:
        del context
        path = Path(request.output_path)
        await self._provider.start_recording(
            request.camera_serial,
            self._profile_model(request.profile),
            path,
        )
        return capture_station_pb2.RecordingResponse(active=True, output_path=str(path))

    async def StopRecording(
        self,
        request: empty_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.RecordingResponse:
        del request, context
        path = await self._provider.stop_recording()
        return capture_station_pb2.RecordingResponse(active=False, output_path=str(path))

    async def RunCalibration(
        self,
        request: capture_station_pb2.CalibrationRequest,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.CalibrationRecord:
        if self._calibration_evaluator is None:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "Physical calibration evaluator is unavailable on this station",
            )
        mode = (
            CalibrationMode.FULL
            if request.mode == capture_station_pb2.CALIBRATION_MODE_FULL
            else CalibrationMode.DAILY
        )
        metrics = self._calibration_evaluator(request.camera_serial, mode)
        record = create_calibration_record(
            version=self._calibration_store.next_version(
                request.station_id,
                request.camera_serial,
            ),
            station_id=request.station_id,
            camera_serial=request.camera_serial,
            operator_id=request.operator_id,
            artefact_id=request.artefact_id,
            mode=mode,
            metrics=metrics,
            thresholds=self._thresholds,
        )
        self._calibration_store.save(record)
        return self._calibration_message(record)

    async def GetActiveCalibration(
        self,
        request: capture_station_pb2.ActiveCalibrationRequest,
        context: grpc.aio.ServicerContext,
    ) -> capture_station_pb2.CalibrationRecord:
        record = self._calibration_store.get_active(
            request.station_id,
            request.camera_serial,
        )
        if record is None:
            await context.abort(
                grpc.StatusCode.FAILED_PRECONDITION,
                "No active calibration is available",
            )
        return self._calibration_message(record)

    @staticmethod
    def _profile_model(value: capture_station_pb2.StreamProfile) -> StreamProfile:
        if value.color_width == 0:
            return StreamProfile()
        return StreamProfile(
            color_width=value.color_width,
            color_height=value.color_height,
            depth_width=value.depth_width,
            depth_height=value.depth_height,
            frames_per_second=value.frames_per_second,
        )

    @staticmethod
    def _profile_message(value: StreamProfile) -> capture_station_pb2.StreamProfile:
        return capture_station_pb2.StreamProfile(
            color_width=value.color_width,
            color_height=value.color_height,
            depth_width=value.depth_width,
            depth_height=value.depth_height,
            frames_per_second=value.frames_per_second,
        )

    def _device_message(self, device: CameraDevice) -> capture_station_pb2.CameraDevice:
        message = capture_station_pb2.CameraDevice(
            serial_number=device.serial_number,
            name=device.name,
            firmware_version=device.firmware_version,
            usb_type=device.usb_type,
        )
        if device.active_profile is not None:
            message.active_profile.CopyFrom(self._profile_message(device.active_profile))
        return message

    @staticmethod
    def _preview_message(frame: CameraFrame) -> capture_station_pb2.PreviewFrame:
        color_ok, color = cv2.imencode(".jpg", frame.color_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        normalized = cv2.normalize(frame.depth_units, None, 0, 255, cv2.NORM_MINMAX)
        depth_preview = cv2.applyColorMap(normalized.astype(np.uint8), cv2.COLORMAP_TURBO)
        depth_ok, depth = cv2.imencode(".png", depth_preview)
        if not color_ok or not depth_ok:
            raise CameraUnavailableError("Preview encoding failed")
        return capture_station_pb2.PreviewFrame(
            frame_id=frame.frame_id,
            captured_at_utc=CaptureStationService._timestamp(frame.captured_at_utc),
            color_jpeg=color.tobytes(),
            depth_preview_png=depth.tobytes(),
            color_width=frame.color_bgr.shape[1],
            color_height=frame.color_bgr.shape[0],
        )

    @staticmethod
    def _calibration_message(
        record: CalibrationRecord,
    ) -> capture_station_pb2.CalibrationRecord:
        mode = (
            capture_station_pb2.CALIBRATION_MODE_FULL
            if record.mode == CalibrationMode.FULL
            else capture_station_pb2.CALIBRATION_MODE_DAILY
        )
        return capture_station_pb2.CalibrationRecord(
            calibration_id=record.calibration_id,
            version=record.version,
            station_id=record.station_id,
            camera_serial=record.camera_serial,
            operator_id=record.operator_id,
            artefact_id=record.artefact_id,
            mode=mode,
            metrics=capture_station_pb2.CalibrationMetrics(
                scale_error_percent=record.metrics.scale_error_percent,
                plane_rms_mm=record.metrics.plane_rms_mm,
                tilt_degrees=record.metrics.tilt_degrees,
                lighting_variation_percent=record.metrics.lighting_variation_percent,
                alignment_valid=record.metrics.alignment_valid,
            ),
            calibrated_at_utc=CaptureStationService._timestamp(record.calibrated_at_utc),
            expires_at_utc=CaptureStationService._timestamp(record.expires_at_utc),
            checksum_sha256=record.checksum_sha256,
            valid=record.valid,
        )

    @staticmethod
    def _timestamp(value: datetime) -> timestamp_pb2.Timestamp:
        timestamp = timestamp_pb2.Timestamp()
        timestamp.FromDatetime(value)
        return timestamp


async def serve() -> None:
    """Start the configured capture service."""

    configure_observability()
    data_root = Path(os.getenv("SPEC_PROOF_STATION_DATA", "station-data"))
    provider_name = os.getenv("SPEC_PROOF_CAMERA_PROVIDER", "mock").lower()
    calibration_evaluator: CalibrationEvaluator | None
    if provider_name == "realsense":
        provider: CameraProvider = RealSenseCameraProvider()
        calibration_evaluator = None
    elif provider_name == "replay":
        replay_path = os.getenv("SPEC_PROOF_REPLAY_PATH")
        if replay_path is None:
            raise ValueError("SPEC_PROOF_REPLAY_PATH is required for replay mode")
        provider = CaptureReplayProvider(Path(replay_path))
        calibration_evaluator = fixed_calibration_evaluator(_passing_metrics())
    else:
        provider = MockCameraProvider()
        calibration_evaluator = fixed_calibration_evaluator(_passing_metrics())

    calibration_store = CalibrationStore(data_root / "calibrations")
    queue = OfflineCaptureQueue(data_root / "queue" / "captures.sqlite3")
    inspection_queue = OfflineInspectionQueue(data_root / "queue" / "inspection-results.sqlite3")
    coordinator = CaptureCoordinator(
        provider=provider,
        calibration_store=calibration_store,
        queue=queue,
        capture_root=data_root / "captures",
    )
    service = CaptureStationService(
        provider=provider,
        coordinator=coordinator,
        calibration_store=calibration_store,
        calibration_evaluator=calibration_evaluator,
        inspection_processor=InspectionPipeline(),
        inspection_queue=inspection_queue,
        tech_pack_provider=LocalTechPackRepository(
            Path(os.getenv("SPEC_PROOF_TECH_PACK_ROOT", "config/station/tech-packs"))
        ),
    )
    synchronization_task = _start_synchronization(
        capture_queue=queue,
        inspection_queue=inspection_queue,
    )
    server = grpc.aio.server()
    capture_station_pb2_grpc.add_CaptureStationServicer_to_server(service, server)
    address = os.getenv("SPEC_PROOF_CAPTURE_ADDRESS", "127.0.0.1:50051")
    server.add_insecure_port(address)
    await server.start()
    logger.info("capture_service_started", address=address, provider=provider_name)
    try:
        await server.wait_for_termination()
    finally:
        if synchronization_task is not None:
            synchronization_task.cancel()
            await asyncio.gather(synchronization_task, return_exceptions=True)
        await provider.close()
        queue.close()
        inspection_queue.close()


def _start_synchronization(
    *,
    capture_queue: OfflineCaptureQueue,
    inspection_queue: OfflineInspectionQueue,
) -> asyncio.Task[None] | None:
    platform_url = os.getenv("SPEC_PROOF_PLATFORM_URL")
    bearer_token = os.getenv("SPEC_PROOF_STATION_TOKEN")
    tenant_id = os.getenv("SPEC_PROOF_TENANT_ID")
    station_id = os.getenv("SPEC_PROOF_STATION_ID")
    bucket_name = os.getenv("SPEC_PROOF_CAPTURE_BUCKET")
    if (
        platform_url is None
        or bearer_token is None
        or tenant_id is None
        or station_id is None
        or bucket_name is None
    ):
        logger.warning("station_synchronization_disabled", reason="configuration_incomplete")
        return None
    client = HttpPlatformStationClient(
        base_url=platform_url,
        tenant_id=tenant_id,
        station_id=station_id,
        bearer_token=bearer_token,
    )
    capture_sync = CaptureSynchronizer(
        queue=capture_queue,
        platform_client=client,
        object_store=S3CaptureObjectStore(
            bucket_name=bucket_name,
            endpoint_url=os.getenv("SPEC_PROOF_S3_ENDPOINT"),
        ),
    )
    result_sync = InspectionResultSynchronizer(
        capture_queue=capture_queue,
        result_queue=inspection_queue,
        platform_client=client,
    )
    return asyncio.create_task(_synchronization_loop(capture_sync, result_sync))


async def _synchronization_loop(
    capture_sync: CaptureSynchronizer,
    result_sync: InspectionResultSynchronizer,
) -> None:
    while True:
        capture_progress = await asyncio.to_thread(capture_sync.synchronize_once)
        result_progress = await asyncio.to_thread(result_sync.synchronize_once)
        if not capture_progress and not result_progress:
            await asyncio.sleep(1)


def _passing_metrics() -> CalibrationMetrics:
    return CalibrationMetrics(
        scale_error_percent=0.0,
        plane_rms_mm=0.0,
        tilt_degrees=0.0,
        lighting_variation_percent=0.0,
        alignment_valid=True,
    )


def main() -> None:
    """CLI entry point."""

    asyncio.run(serve())


if __name__ == "__main__":
    main()
