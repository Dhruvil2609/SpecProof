namespace SpecProof.Camera.Abstractions;

public sealed record CameraStreamProfile(
    int ColorWidth = 1280,
    int ColorHeight = 720,
    int DepthWidth = 848,
    int DepthHeight = 480,
    int FramesPerSecond = 30);

public sealed record CameraDeviceInfo(
    string ProviderName,
    string SerialNumber,
    string Name,
    string FirmwareVersion,
    string UsbType,
    CameraStreamProfile? ActiveProfile);

public sealed record CameraCaptureRequest(
    string StationId,
    string CameraSerial,
    int FrameCount = 5,
    CameraStreamProfile? Profile = null);

public sealed record CameraCaptureResult(
    Guid CaptureId,
    string PackagePath,
    string PackageSha256,
    DateTimeOffset CapturedAtUtc,
    string CalibrationId);

public sealed record CameraHealth(
    string Status,
    string CameraStatus,
    string StorageStatus,
    string ClockStatus,
    long OfflineQueueDepth,
    DateTimeOffset CheckedAtUtc,
    string Detail);

public interface ICameraProvider
{
    ValueTask<IReadOnlyList<CameraDeviceInfo>> ListCamerasAsync(
        CancellationToken cancellationToken);

    ValueTask<CameraHealth> GetHealthAsync(CancellationToken cancellationToken);

    ValueTask<CameraCaptureResult> CaptureAsync(
        CameraCaptureRequest request,
        CancellationToken cancellationToken);
}

public class CameraProviderException(string message, Exception? innerException = null)
    : Exception(message, innerException);

public sealed class CameraNotFoundException(string message, Exception? innerException = null)
    : CameraProviderException(message, innerException);

public sealed class CalibrationRequiredException(string message, Exception? innerException = null)
    : CameraProviderException(message, innerException);

public sealed class CameraUnavailableException(string message, Exception? innerException = null)
    : CameraProviderException(message, innerException);
