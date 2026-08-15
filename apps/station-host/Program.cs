using System.Net.WebSockets;
using System.Text.Json;
using Grpc.Core;
using Grpc.Net.Client;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using SpecProof.Camera.Abstractions;
using SpecProof.Station.Contracts.V1;

var builder = WebApplication.CreateBuilder(args);
var captureServiceAddress =
    builder.Configuration["CaptureService:Address"] ?? "http://127.0.0.1:50051";

builder.Services.AddSingleton(_ => GrpcChannel.ForAddress(captureServiceAddress));
builder.Services.AddSingleton(serviceProvider =>
    new CaptureStation.CaptureStationClient(serviceProvider.GetRequiredService<GrpcChannel>()));
builder.Services.AddSingleton<ICameraProvider, GrpcCameraProvider>();
builder.Services.AddHostedService<StationSupervisor>();
builder.Services.AddCors(options =>
    options.AddDefaultPolicy(policy =>
        policy.WithOrigins(
                builder.Configuration["OperatorUi:Origin"] ?? "http://127.0.0.1:5173")
            .AllowAnyHeader()
            .AllowAnyMethod()));
builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource.AddService("specproof-station-host"))
    .WithTracing(tracing =>
    {
        if (!string.IsNullOrWhiteSpace(builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"]))
        {
            tracing.AddOtlpExporter();
        }
    });

var app = builder.Build();
app.UseCors();
app.UseWebSockets();

app.MapGet(
    "/api/v1/health",
    async (ICameraProvider cameraProvider, CancellationToken cancellationToken) =>
        Results.Ok(await cameraProvider.GetHealthAsync(cancellationToken)));
app.MapGet(
    "/api/v1/cameras",
    async (ICameraProvider cameraProvider, CancellationToken cancellationToken) =>
        Results.Ok(await cameraProvider.ListCamerasAsync(cancellationToken)));
app.MapPost(
    "/api/v1/captures",
    async (
        StationCaptureRequest request,
        ICameraProvider cameraProvider,
        CancellationToken cancellationToken) =>
    {
        try
        {
            var captured = await cameraProvider.CaptureAsync(
                new CameraCaptureRequest(
                    request.StationId.ToString(),
                    request.CameraSerial,
                    request.FrameCount,
                    request.Profile,
                    new InspectionCaptureContext(
                        request.TenantId,
                        request.InspectionId ?? Guid.NewGuid(),
                        request.StationCode,
                        request.OrderCode,
                        request.StyleCode,
                        request.SizeCode,
                        request.BatchId,
                        request.TechPackId,
                        request.TechPackVersion)),
                cancellationToken);
            return Results.Ok(
                new StationCaptureResponse(
                    captured.CaptureId,
                    captured.PackageSha256,
                    captured.CalibrationId,
                    captured.CapturedAtUtc,
                    captured.InspectionId,
                    captured.ProcessingStatus));
        }
        catch (CameraNotFoundException exception)
        {
            return Results.Problem(exception.Message, statusCode: StatusCodes.Status404NotFound);
        }
        catch (CalibrationRequiredException exception)
        {
            return Results.Problem(exception.Message, statusCode: StatusCodes.Status409Conflict);
        }
        catch (CameraUnavailableException exception)
        {
            return Results.Problem(exception.Message, statusCode: StatusCodes.Status503ServiceUnavailable);
        }
    });
app.Map(
    "/api/v1/preview",
    async context =>
    {
        if (!context.WebSockets.IsWebSocketRequest)
        {
            context.Response.StatusCode = StatusCodes.Status400BadRequest;
            return;
        }

        using var socket = await context.WebSockets.AcceptWebSocketAsync();
        var sequence = 0L;
        while (socket.State == WebSocketState.Open && !context.RequestAborted.IsCancellationRequested)
        {
            var frame = StationPreviewFrame.Create(sequence++, DateTimeOffset.UtcNow);
            var payload = JsonSerializer.SerializeToUtf8Bytes(frame, StationBrowserJsonContext.Default.StationPreviewFrame);
            await socket.SendAsync(
                payload,
                WebSocketMessageType.Text,
                endOfMessage: true,
                context.RequestAborted);
            await Task.Delay(TimeSpan.FromMilliseconds(250), context.RequestAborted);
        }
    });

await app.RunAsync();

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
            var grpcRequest = new SpecProof.Station.Contracts.V1.CaptureRequest
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
                };
            if (request.InspectionContext is not null)
            {
                grpcRequest.InspectionContext = new SpecProof.Station.Contracts.V1.InspectionContext
                {
                    TenantId = request.InspectionContext.TenantId.ToString(),
                    InspectionId = request.InspectionContext.InspectionId.ToString(),
                    StationCode = request.InspectionContext.StationCode,
                    OrderCode = request.InspectionContext.OrderCode,
                    StyleCode = request.InspectionContext.StyleCode,
                    SizeCode = request.InspectionContext.SizeCode,
                    BatchId = request.InspectionContext.BatchId?.ToString() ?? string.Empty,
                    TechPackId = request.InspectionContext.TechPackId.ToString(),
                    TechPackVersion = checked((uint)request.InspectionContext.TechPackVersion),
                };
            }
            var response = await client.CaptureAsync(
                grpcRequest,
                cancellationToken: cancellationToken);
            return new CameraCaptureResult(
                Guid.Parse(response.CaptureId),
                response.PackagePath,
                response.PackageSha256,
                response.CapturedAtUtc.ToDateTimeOffset(),
                response.CalibrationId,
                Guid.TryParse(response.InspectionId, out var inspectionId) ? inspectionId : null,
                response.ProcessingStatus.ToString());
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

public sealed record StationCaptureRequest(
    Guid TenantId,
    Guid StationId,
    string CameraSerial,
    string StationCode,
    string OrderCode,
    string StyleCode,
    string SizeCode,
    Guid? BatchId,
    Guid TechPackId,
    int TechPackVersion,
    Guid? InspectionId = null,
    int FrameCount = 5,
    CameraStreamProfile? Profile = null);

public sealed record StationCaptureResponse(
    Guid CaptureId,
    string ChecksumSha256,
    string CalibrationId,
    DateTimeOffset CapturedAtUtc,
    Guid? InspectionId,
    string ProcessingStatus);

public sealed record StationPreviewFrame(
    long Sequence,
    DateTimeOffset CapturedAtUtc,
    string ColorJpegBase64,
    string DepthPngBase64,
    int ColorWidth,
    int ColorHeight,
    int DepthWidth,
    int DepthHeight)
{
    private const string OnePixelJpeg =
        "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAf/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9oADAMBAAIAAwAAABD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAEDAQE/EH//xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oACAECAQE/EH//xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oACAEBAAE/EH//2Q==";
    private const string OnePixelPng =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=";

    public static StationPreviewFrame Create(long sequence, DateTimeOffset capturedAtUtc) =>
        new(sequence, capturedAtUtc, OnePixelJpeg, OnePixelPng, 1, 1, 1, 1);
}

[System.Text.Json.Serialization.JsonSerializable(typeof(StationPreviewFrame))]
internal sealed partial class StationBrowserJsonContext : System.Text.Json.Serialization.JsonSerializerContext;

public partial class Program;
