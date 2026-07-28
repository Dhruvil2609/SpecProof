"""Capture service exceptions."""


class CaptureServiceError(Exception):
    """Base capture service exception."""


class CameraNotFoundError(CaptureServiceError):
    """Raised when the requested camera is unavailable."""


class CameraUnavailableError(CaptureServiceError):
    """Raised when a camera operation cannot continue."""


class CalibrationExpiredError(CaptureServiceError):
    """Raised when capture is attempted without a valid calibration."""


class CapturePackageError(CaptureServiceError):
    """Raised when a capture package is invalid."""
