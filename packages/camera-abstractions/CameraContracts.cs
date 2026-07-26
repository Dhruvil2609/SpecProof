namespace SpecProof.Camera.Abstractions;

public sealed record CameraCapabilities(
    string ProviderName,
    string SerialNumber,
    int ColorWidth,
    int ColorHeight,
    int DepthWidth,
    int DepthHeight,
    int FramesPerSecond);

public sealed record CameraFrame(
    Guid FrameId,
    string CameraSerial,
    DateTimeOffset CapturedAtUtc,
    ReadOnlyMemory<byte> ColorImage,
    ReadOnlyMemory<byte> DepthImage,
    string IntrinsicsJson);

public interface ICameraProvider
{
    ValueTask<IReadOnlyList<CameraCapabilities>> ListCamerasAsync(CancellationToken cancellationToken);

    ValueTask<CameraFrame> CaptureAsync(string cameraSerial, CancellationToken cancellationToken);
}
