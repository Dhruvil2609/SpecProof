"""gRPC bindings for the generated capture station messages."""

from __future__ import annotations

import grpc
from google.protobuf import empty_pb2

from specproof_capture_service.generated import capture_station_pb2


class CaptureStationStub:
    """Client stub for the capture station service."""

    def __init__(self, channel: grpc.Channel) -> None:
        self.ListDevices = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/ListDevices",
            request_serializer=empty_pb2.Empty.SerializeToString,
            response_deserializer=capture_station_pb2.ListDevicesResponse.FromString,
        )
        self.GetHealth = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/GetHealth",
            request_serializer=empty_pb2.Empty.SerializeToString,
            response_deserializer=capture_station_pb2.StationHealth.FromString,
        )
        self.StreamPreview = channel.unary_stream(
            "/specproof.station.v1.CaptureStation/StreamPreview",
            request_serializer=capture_station_pb2.PreviewRequest.SerializeToString,
            response_deserializer=capture_station_pb2.PreviewFrame.FromString,
        )
        self.Capture = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/Capture",
            request_serializer=capture_station_pb2.CaptureRequest.SerializeToString,
            response_deserializer=capture_station_pb2.CaptureResponse.FromString,
        )
        self.StartRecording = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/StartRecording",
            request_serializer=capture_station_pb2.RecordingRequest.SerializeToString,
            response_deserializer=capture_station_pb2.RecordingResponse.FromString,
        )
        self.StopRecording = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/StopRecording",
            request_serializer=empty_pb2.Empty.SerializeToString,
            response_deserializer=capture_station_pb2.RecordingResponse.FromString,
        )
        self.RunCalibration = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/RunCalibration",
            request_serializer=capture_station_pb2.CalibrationRequest.SerializeToString,
            response_deserializer=capture_station_pb2.CalibrationRecord.FromString,
        )
        self.GetActiveCalibration = channel.unary_unary(
            "/specproof.station.v1.CaptureStation/GetActiveCalibration",
            request_serializer=capture_station_pb2.ActiveCalibrationRequest.SerializeToString,
            response_deserializer=capture_station_pb2.CalibrationRecord.FromString,
        )


class CaptureStationServicer:
    """Base service implementation."""

    async def ListDevices(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def GetHealth(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def StreamPreview(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def Capture(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def StartRecording(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def StopRecording(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def RunCalibration(self, request: object, context: grpc.aio.ServicerContext) -> object:
        raise NotImplementedError

    async def GetActiveCalibration(
        self,
        request: object,
        context: grpc.aio.ServicerContext,
    ) -> object:
        raise NotImplementedError


def add_CaptureStationServicer_to_server(
    servicer: CaptureStationServicer,
    server: grpc.aio.Server,
) -> None:
    """Register the capture station service with a server."""

    handlers = {
        "ListDevices": grpc.unary_unary_rpc_method_handler(
            servicer.ListDevices,
            request_deserializer=empty_pb2.Empty.FromString,
            response_serializer=capture_station_pb2.ListDevicesResponse.SerializeToString,
        ),
        "GetHealth": grpc.unary_unary_rpc_method_handler(
            servicer.GetHealth,
            request_deserializer=empty_pb2.Empty.FromString,
            response_serializer=capture_station_pb2.StationHealth.SerializeToString,
        ),
        "StreamPreview": grpc.unary_stream_rpc_method_handler(
            servicer.StreamPreview,
            request_deserializer=capture_station_pb2.PreviewRequest.FromString,
            response_serializer=capture_station_pb2.PreviewFrame.SerializeToString,
        ),
        "Capture": grpc.unary_unary_rpc_method_handler(
            servicer.Capture,
            request_deserializer=capture_station_pb2.CaptureRequest.FromString,
            response_serializer=capture_station_pb2.CaptureResponse.SerializeToString,
        ),
        "StartRecording": grpc.unary_unary_rpc_method_handler(
            servicer.StartRecording,
            request_deserializer=capture_station_pb2.RecordingRequest.FromString,
            response_serializer=capture_station_pb2.RecordingResponse.SerializeToString,
        ),
        "StopRecording": grpc.unary_unary_rpc_method_handler(
            servicer.StopRecording,
            request_deserializer=empty_pb2.Empty.FromString,
            response_serializer=capture_station_pb2.RecordingResponse.SerializeToString,
        ),
        "RunCalibration": grpc.unary_unary_rpc_method_handler(
            servicer.RunCalibration,
            request_deserializer=capture_station_pb2.CalibrationRequest.FromString,
            response_serializer=capture_station_pb2.CalibrationRecord.SerializeToString,
        ),
        "GetActiveCalibration": grpc.unary_unary_rpc_method_handler(
            servicer.GetActiveCalibration,
            request_deserializer=capture_station_pb2.ActiveCalibrationRequest.FromString,
            response_serializer=capture_station_pb2.CalibrationRecord.SerializeToString,
        ),
    }
    server.add_generic_rpc_handlers(
        (
            grpc.method_handlers_generic_handler(
                "specproof.station.v1.CaptureStation",
                handlers,
            ),
        )
    )
