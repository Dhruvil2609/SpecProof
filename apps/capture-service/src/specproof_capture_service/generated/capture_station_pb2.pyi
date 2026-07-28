import datetime

from google.protobuf import empty_pb2 as _empty_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CalibrationMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CALIBRATION_MODE_UNSPECIFIED: _ClassVar[CalibrationMode]
    CALIBRATION_MODE_DAILY: _ClassVar[CalibrationMode]
    CALIBRATION_MODE_FULL: _ClassVar[CalibrationMode]
CALIBRATION_MODE_UNSPECIFIED: CalibrationMode
CALIBRATION_MODE_DAILY: CalibrationMode
CALIBRATION_MODE_FULL: CalibrationMode

class StreamProfile(_message.Message):
    __slots__ = ("color_width", "color_height", "depth_width", "depth_height", "frames_per_second")
    COLOR_WIDTH_FIELD_NUMBER: _ClassVar[int]
    COLOR_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    DEPTH_WIDTH_FIELD_NUMBER: _ClassVar[int]
    DEPTH_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    FRAMES_PER_SECOND_FIELD_NUMBER: _ClassVar[int]
    color_width: int
    color_height: int
    depth_width: int
    depth_height: int
    frames_per_second: int
    def __init__(self, color_width: _Optional[int] = ..., color_height: _Optional[int] = ..., depth_width: _Optional[int] = ..., depth_height: _Optional[int] = ..., frames_per_second: _Optional[int] = ...) -> None: ...

class CameraDevice(_message.Message):
    __slots__ = ("serial_number", "name", "firmware_version", "usb_type", "active_profile")
    SERIAL_NUMBER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    FIRMWARE_VERSION_FIELD_NUMBER: _ClassVar[int]
    USB_TYPE_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_PROFILE_FIELD_NUMBER: _ClassVar[int]
    serial_number: str
    name: str
    firmware_version: str
    usb_type: str
    active_profile: StreamProfile
    def __init__(self, serial_number: _Optional[str] = ..., name: _Optional[str] = ..., firmware_version: _Optional[str] = ..., usb_type: _Optional[str] = ..., active_profile: _Optional[_Union[StreamProfile, _Mapping]] = ...) -> None: ...

class ListDevicesResponse(_message.Message):
    __slots__ = ("devices",)
    DEVICES_FIELD_NUMBER: _ClassVar[int]
    devices: _containers.RepeatedCompositeFieldContainer[CameraDevice]
    def __init__(self, devices: _Optional[_Iterable[_Union[CameraDevice, _Mapping]]] = ...) -> None: ...

class StationHealth(_message.Message):
    __slots__ = ("status", "checked_at_utc", "camera_status", "storage_status", "clock_status", "offline_queue_depth", "detail")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    CHECKED_AT_UTC_FIELD_NUMBER: _ClassVar[int]
    CAMERA_STATUS_FIELD_NUMBER: _ClassVar[int]
    STORAGE_STATUS_FIELD_NUMBER: _ClassVar[int]
    CLOCK_STATUS_FIELD_NUMBER: _ClassVar[int]
    OFFLINE_QUEUE_DEPTH_FIELD_NUMBER: _ClassVar[int]
    DETAIL_FIELD_NUMBER: _ClassVar[int]
    status: str
    checked_at_utc: _timestamp_pb2.Timestamp
    camera_status: str
    storage_status: str
    clock_status: str
    offline_queue_depth: int
    detail: str
    def __init__(self, status: _Optional[str] = ..., checked_at_utc: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., camera_status: _Optional[str] = ..., storage_status: _Optional[str] = ..., clock_status: _Optional[str] = ..., offline_queue_depth: _Optional[int] = ..., detail: _Optional[str] = ...) -> None: ...

class PreviewRequest(_message.Message):
    __slots__ = ("camera_serial", "profile")
    CAMERA_SERIAL_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    camera_serial: str
    profile: StreamProfile
    def __init__(self, camera_serial: _Optional[str] = ..., profile: _Optional[_Union[StreamProfile, _Mapping]] = ...) -> None: ...

class PreviewFrame(_message.Message):
    __slots__ = ("frame_id", "captured_at_utc", "color_jpeg", "depth_preview_png", "color_width", "color_height")
    FRAME_ID_FIELD_NUMBER: _ClassVar[int]
    CAPTURED_AT_UTC_FIELD_NUMBER: _ClassVar[int]
    COLOR_JPEG_FIELD_NUMBER: _ClassVar[int]
    DEPTH_PREVIEW_PNG_FIELD_NUMBER: _ClassVar[int]
    COLOR_WIDTH_FIELD_NUMBER: _ClassVar[int]
    COLOR_HEIGHT_FIELD_NUMBER: _ClassVar[int]
    frame_id: str
    captured_at_utc: _timestamp_pb2.Timestamp
    color_jpeg: bytes
    depth_preview_png: bytes
    color_width: int
    color_height: int
    def __init__(self, frame_id: _Optional[str] = ..., captured_at_utc: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., color_jpeg: _Optional[bytes] = ..., depth_preview_png: _Optional[bytes] = ..., color_width: _Optional[int] = ..., color_height: _Optional[int] = ...) -> None: ...

class CaptureRequest(_message.Message):
    __slots__ = ("camera_serial", "station_id", "frame_count", "profile")
    CAMERA_SERIAL_FIELD_NUMBER: _ClassVar[int]
    STATION_ID_FIELD_NUMBER: _ClassVar[int]
    FRAME_COUNT_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    camera_serial: str
    station_id: str
    frame_count: int
    profile: StreamProfile
    def __init__(self, camera_serial: _Optional[str] = ..., station_id: _Optional[str] = ..., frame_count: _Optional[int] = ..., profile: _Optional[_Union[StreamProfile, _Mapping]] = ...) -> None: ...

class CaptureResponse(_message.Message):
    __slots__ = ("capture_id", "package_path", "package_sha256", "captured_at_utc", "calibration_id")
    CAPTURE_ID_FIELD_NUMBER: _ClassVar[int]
    PACKAGE_PATH_FIELD_NUMBER: _ClassVar[int]
    PACKAGE_SHA256_FIELD_NUMBER: _ClassVar[int]
    CAPTURED_AT_UTC_FIELD_NUMBER: _ClassVar[int]
    CALIBRATION_ID_FIELD_NUMBER: _ClassVar[int]
    capture_id: str
    package_path: str
    package_sha256: str
    captured_at_utc: _timestamp_pb2.Timestamp
    calibration_id: str
    def __init__(self, capture_id: _Optional[str] = ..., package_path: _Optional[str] = ..., package_sha256: _Optional[str] = ..., captured_at_utc: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., calibration_id: _Optional[str] = ...) -> None: ...

class RecordingRequest(_message.Message):
    __slots__ = ("camera_serial", "output_path", "profile")
    CAMERA_SERIAL_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_PATH_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    camera_serial: str
    output_path: str
    profile: StreamProfile
    def __init__(self, camera_serial: _Optional[str] = ..., output_path: _Optional[str] = ..., profile: _Optional[_Union[StreamProfile, _Mapping]] = ...) -> None: ...

class RecordingResponse(_message.Message):
    __slots__ = ("active", "output_path")
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_PATH_FIELD_NUMBER: _ClassVar[int]
    active: bool
    output_path: str
    def __init__(self, active: _Optional[bool] = ..., output_path: _Optional[str] = ...) -> None: ...

class CalibrationRequest(_message.Message):
    __slots__ = ("camera_serial", "station_id", "operator_id", "artefact_id", "mode")
    CAMERA_SERIAL_FIELD_NUMBER: _ClassVar[int]
    STATION_ID_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_ID_FIELD_NUMBER: _ClassVar[int]
    ARTEFACT_ID_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    camera_serial: str
    station_id: str
    operator_id: str
    artefact_id: str
    mode: CalibrationMode
    def __init__(self, camera_serial: _Optional[str] = ..., station_id: _Optional[str] = ..., operator_id: _Optional[str] = ..., artefact_id: _Optional[str] = ..., mode: _Optional[_Union[CalibrationMode, str]] = ...) -> None: ...

class ActiveCalibrationRequest(_message.Message):
    __slots__ = ("camera_serial", "station_id")
    CAMERA_SERIAL_FIELD_NUMBER: _ClassVar[int]
    STATION_ID_FIELD_NUMBER: _ClassVar[int]
    camera_serial: str
    station_id: str
    def __init__(self, camera_serial: _Optional[str] = ..., station_id: _Optional[str] = ...) -> None: ...

class CalibrationMetrics(_message.Message):
    __slots__ = ("scale_error_percent", "plane_rms_mm", "tilt_degrees", "lighting_variation_percent", "alignment_valid")
    SCALE_ERROR_PERCENT_FIELD_NUMBER: _ClassVar[int]
    PLANE_RMS_MM_FIELD_NUMBER: _ClassVar[int]
    TILT_DEGREES_FIELD_NUMBER: _ClassVar[int]
    LIGHTING_VARIATION_PERCENT_FIELD_NUMBER: _ClassVar[int]
    ALIGNMENT_VALID_FIELD_NUMBER: _ClassVar[int]
    scale_error_percent: float
    plane_rms_mm: float
    tilt_degrees: float
    lighting_variation_percent: float
    alignment_valid: bool
    def __init__(self, scale_error_percent: _Optional[float] = ..., plane_rms_mm: _Optional[float] = ..., tilt_degrees: _Optional[float] = ..., lighting_variation_percent: _Optional[float] = ..., alignment_valid: _Optional[bool] = ...) -> None: ...

class CalibrationRecord(_message.Message):
    __slots__ = ("calibration_id", "version", "station_id", "camera_serial", "operator_id", "artefact_id", "mode", "metrics", "calibrated_at_utc", "expires_at_utc", "checksum_sha256", "valid")
    CALIBRATION_ID_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    STATION_ID_FIELD_NUMBER: _ClassVar[int]
    CAMERA_SERIAL_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_ID_FIELD_NUMBER: _ClassVar[int]
    ARTEFACT_ID_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    CALIBRATED_AT_UTC_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_UTC_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_SHA256_FIELD_NUMBER: _ClassVar[int]
    VALID_FIELD_NUMBER: _ClassVar[int]
    calibration_id: str
    version: int
    station_id: str
    camera_serial: str
    operator_id: str
    artefact_id: str
    mode: CalibrationMode
    metrics: CalibrationMetrics
    calibrated_at_utc: _timestamp_pb2.Timestamp
    expires_at_utc: _timestamp_pb2.Timestamp
    checksum_sha256: str
    valid: bool
    def __init__(self, calibration_id: _Optional[str] = ..., version: _Optional[int] = ..., station_id: _Optional[str] = ..., camera_serial: _Optional[str] = ..., operator_id: _Optional[str] = ..., artefact_id: _Optional[str] = ..., mode: _Optional[_Union[CalibrationMode, str]] = ..., metrics: _Optional[_Union[CalibrationMetrics, _Mapping]] = ..., calibrated_at_utc: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., expires_at_utc: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., checksum_sha256: _Optional[str] = ..., valid: _Optional[bool] = ...) -> None: ...
