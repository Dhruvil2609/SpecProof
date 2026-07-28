using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using SpecProof.Camera.Abstractions;
using SpecProof.Station.Contracts.V1;

var builder = Host.CreateApplicationBuilder(args);
var captureServiceAddress =
    builder.Configuration["CaptureService:Address"] ?? "http://127.0.0.1:50051";

builder.Services.AddSingleton(_ => GrpcChannel.ForAddress(captureServiceAddress));
builder.Services.AddSingleton(serviceProvider =>
    new CaptureStation.CaptureStationClient(serviceProvider.GetRequiredService<GrpcChannel>()));
builder.Services.AddSingleton<ICameraProvider, GrpcCameraProvider>();
builder.Services.AddHostedService<StationSupervisor>();
builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource.AddService("specproof-station-host"))
    .WithTracing(tracing =>
    {
        if (!string.IsNullOrWhiteSpace(builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"]))
        {
            tracing.AddOtlpExporter();
        }
    });

await builder.Build().RunAsync();

public sealed class GrpcCameraProvider(CaptureStation.CaptureStationClient client) : ICameraProvider
{
    public async ValueTask<IReadOnlyList<CameraDeviceInfo>> ListCamerasAsync(
        CancellationToken cancellationToken)
    {
        try
        {
            var response = await client.ListDevicesAsync(
                new Google.Protobuf.WellKnownTypes.Empty(),
                cancellationToken: cancellationToken);
            return response.Devices.Select(MapDevice).ToArray();
        }
        catch (RpcException exception)
        {
            throw MapException(exception);
        }
    }

    public async ValueTask<CameraHealth> GetHealthAsync(CancellationToken cancellationToken)
    {
        try
        {
            var response = await client.GetHealthAsync(
                new Google.Protobuf.WellKnownTypes.Empty(),
                cancellationToken: cancellationToken);
            return new CameraHealth(
                response.Status,
                response.CameraStatus,
                response.StorageStatus,
                response.ClockStatus,
                checked((long)response.OfflineQueueDepth),
                response.CheckedAtUtc.ToDateTimeOffset(),
                response.Detail);
        }
        catch (RpcException exception)
        {
            throw MapException(exception);
        }
    }

    public async ValueTask<CameraCaptureResult> CaptureAsync(
        CameraCaptureRequest request,
        CancellationToken cancellationToken)
    {
        var profile = request.Profile ?? new CameraStreamProfile();
        try
        {
            var response = await client.CaptureAsync(
                new SpecProof.Station.Contracts.V1.CaptureRequest
                {
                    StationId = request.StationId,
                    CameraSerial = request.CameraSerial,
                    FrameCount = checked((uint)request.FrameCount),
                    Profile = new StreamProfile
                    {
                        ColorWidth = checked((uint)profile.ColorWidth),
                        ColorHeight = checked((uint)profile.ColorHeight),
                        DepthWidth = checked((uint)profile.DepthWidth),
                        DepthHeight = checked((uint)profile.DepthHeight),
                        FramesPerSecond = checked((uint)profile.FramesPerSecond),
                    },
                },
                cancellationToken: cancellationToken);
            return new CameraCaptureResult(
                Guid.Parse(response.CaptureId),
                response.PackagePath,
                response.PackageSha256,
                response.CapturedAtUtc.ToDateTimeOffset(),
                response.CalibrationId);
        }
        catch (RpcException exception)
        {
            throw MapException(exception);
        }
    }

    private static CameraDeviceInfo MapDevice(CameraDevice device)
    {
        CameraStreamProfile? profile = device.ActiveProfile is null
            ? null
            : new CameraStreamProfile(
                checked((int)device.ActiveProfile.ColorWidth),
                checked((int)device.ActiveProfile.ColorHeight),
                checked((int)device.ActiveProfile.DepthWidth),
                checked((int)device.ActiveProfile.DepthHeight),
                checked((int)device.ActiveProfile.FramesPerSecond));
        return new CameraDeviceInfo(
            "grpc",
            device.SerialNumber,
            device.Name,
            device.FirmwareVersion,
            device.UsbType,
            profile);
    }

    private static CameraProviderException MapException(RpcException exception) =>
        exception.StatusCode switch
        {
            Grpc.Core.StatusCode.NotFound => new CameraNotFoundException(
                exception.Status.Detail,
                exception),
            Grpc.Core.StatusCode.FailedPrecondition => new CalibrationRequiredException(
                exception.Status.Detail,
                exception),
            _ => new CameraUnavailableException(exception.Status.Detail, exception),
        };
}

public sealed class StationSupervisor(
    ICameraProvider cameraProvider,
    ILogger<StationSupervisor> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(TimeSpan.FromSeconds(30));
        do
        {
            try
            {
                var health = await cameraProvider.GetHealthAsync(stoppingToken);
                logger.LogInformation(
                    "Station health {Status}; camera {CameraStatus}; queue {QueueDepth}",
                    health.Status,
                    health.CameraStatus,
                    health.OfflineQueueDepth);
            }
            catch (CameraProviderException exception)
            {
                logger.LogWarning(exception, "Capture service health check failed");
            }
        }
        while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
