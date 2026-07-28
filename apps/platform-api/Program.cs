using System.Globalization;
using System.Text.Json;
using Microsoft.AspNetCore.Localization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using SpecProof.Contracts;
using SpecProof.Platform.Data;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddLocalization(options => options.ResourcesPath = "Resources");
builder.Services.Configure<RequestLocalizationOptions>(options =>
{
    var supportedCultures = new[] { new CultureInfo("en") };
    options.DefaultRequestCulture = new RequestCulture("en");
    options.SupportedCultures = supportedCultures;
    options.SupportedUICultures = supportedCultures;
});
builder.Services.AddProblemDetails();
builder.Services.AddOpenApi();
builder.Services.AddDbContext<SpecProofDbContext>(options =>
    options.UseNpgsql(builder.Configuration.GetConnectionString("SpecProof")));
builder.Services.AddOpenTelemetry()
    .ConfigureResource(resource => resource.AddService("specproof-platform-api"))
    .WithTracing(tracing =>
    {
        tracing
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation();
        if (!string.IsNullOrWhiteSpace(builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"]))
        {
            tracing.AddOtlpExporter();
        }
    })
    .WithMetrics(metrics =>
    {
        metrics
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddRuntimeInstrumentation();
        if (!string.IsNullOrWhiteSpace(builder.Configuration["OTEL_EXPORTER_OTLP_ENDPOINT"]))
        {
            metrics.AddOtlpExporter();
        }
    });

var app = builder.Build();

app.UseRequestLocalization();
app.UseExceptionHandler();

app.MapOpenApi("/api/v1/openapi.json");

app.MapGet("/healthz", () => Results.Ok(new { status = "ok", checkedAtUtc = DateTimeOffset.UtcNow }))
    .WithName("HealthCheck");

app.MapGet("/api/v1/inspections/{id:guid}", (Guid id) =>
    {
        var result = new InspectionResultDto(
            id,
            "station-demo",
            "camera-demo",
            DateTimeOffset.UtcNow,
            [],
            InspectionStatus.Pending,
            "not-yet-signed");
        return Results.Ok(result);
    })
    .WithName("GetInspection");

app.MapPost(
        "/api/v1/stations/register",
        async (
            RegisterStationRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var station = await database.Stations.SingleOrDefaultAsync(
                candidate =>
                    candidate.TenantId == request.TenantId
                    && candidate.StationCode == request.StationCode,
                cancellationToken);
            if (station is null)
            {
                station = new Station
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    FactoryId = request.FactoryId,
                    StationCode = request.StationCode,
                };
                database.Stations.Add(station);
                await database.SaveChangesAsync(cancellationToken);
            }
            return Results.Ok(
                new RegisterStationResponse(station.Id, station.StationCode, DateTimeOffset.UtcNow));
        })
    .WithName("RegisterStation");

app.MapPut(
        "/api/v1/stations/{stationId:guid}/health",
        async (
            Guid stationId,
            StationHealthRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var station = await database.Stations.SingleOrDefaultAsync(
                candidate => candidate.Id == stationId && candidate.TenantId == request.TenantId,
                cancellationToken);
            if (station is null)
            {
                return Results.NotFound();
            }
            database.AuditEvents.Add(
                new AuditEvent
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    EventType = "station.health_reported",
                    EntityType = "station",
                    EntityId = stationId,
                    PayloadJson = JsonSerializer.Serialize(request),
                    OccurredAtUtc = request.CheckedAtUtc,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.NoContent();
        })
    .WithName("ReportStationHealth");

app.MapPost(
        "/api/v1/captures/initiate",
        async (
            InitiateCaptureUploadRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var stationExists = await database.Stations.AnyAsync(
                station => station.Id == request.StationId && station.TenantId == request.TenantId,
                cancellationToken);
            if (!stationExists)
            {
                return Results.NotFound();
            }
            var existing = await database.CaptureAssets.SingleOrDefaultAsync(
                asset =>
                    asset.TenantId == request.TenantId
                    && asset.CaptureId == request.CaptureId,
                cancellationToken);
            if (existing is not null)
            {
                return Results.Ok(
                    new InitiateCaptureUploadResponse(existing.Id, existing.ObjectKey));
            }
            var asset = new CaptureAsset
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                StationId = request.StationId,
                CaptureId = request.CaptureId,
                ObjectKey =
                    $"{request.TenantId:N}/{request.StationId:N}/{request.CaptureId:N}.spcapture",
                ContentType = "application/vnd.specproof.capture+zip",
                SizeBytes = request.SizeBytes,
                ChecksumSha256 = request.ChecksumSha256,
                RetentionCategory = "standard",
                Encrypted = false,
            };
            database.CaptureAssets.Add(asset);
            await database.SaveChangesAsync(cancellationToken);
            return Results.Created(
                $"/api/v1/captures/{asset.Id}",
                new InitiateCaptureUploadResponse(asset.Id, asset.ObjectKey));
        })
    .WithName("InitiateCaptureUpload");

app.MapPost(
        "/api/v1/captures/{assetId:guid}/complete",
        async (
            Guid assetId,
            CompleteCaptureUploadRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var asset = await database.CaptureAssets.SingleOrDefaultAsync(
                candidate =>
                    candidate.Id == assetId
                    && candidate.TenantId == request.TenantId,
                cancellationToken);
            if (asset is null)
            {
                return Results.NotFound();
            }
            if (!string.Equals(
                    asset.ChecksumSha256,
                    request.ChecksumSha256,
                    StringComparison.OrdinalIgnoreCase))
            {
                return Results.BadRequest(
                    new ProblemDetails
                    {
                        Title = "Capture checksum mismatch",
                        Status = StatusCodes.Status400BadRequest,
                    });
            }
            asset.UploadCompletedAtUtc ??= DateTimeOffset.UtcNow;
            asset.UpdatedAtUtc = DateTimeOffset.UtcNow;
            await database.SaveChangesAsync(cancellationToken);
            return Results.NoContent();
        })
    .WithName("CompleteCaptureUpload");

app.Run();

public sealed record RegisterStationRequest(Guid TenantId, Guid FactoryId, string StationCode);

public sealed record RegisterStationResponse(
    Guid StationId,
    string StationCode,
    DateTimeOffset RegisteredAtUtc);

public sealed record StationHealthRequest(
    Guid TenantId,
    string Status,
    string CameraStatus,
    string StorageStatus,
    string ClockStatus,
    long OfflineQueueDepth,
    DateTimeOffset CheckedAtUtc);

public sealed record InitiateCaptureUploadRequest(
    Guid TenantId,
    Guid StationId,
    Guid CaptureId,
    long SizeBytes,
    string ChecksumSha256);

public sealed record InitiateCaptureUploadResponse(Guid AssetId, string ObjectKey);

public sealed record CompleteCaptureUploadRequest(Guid TenantId, string ChecksumSha256);

public partial class Program;
