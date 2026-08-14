using System.Globalization;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using System.Threading.RateLimiting;
using FluentValidation;
using Microsoft.AspNetCore.Localization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using SpecProof.Contracts;
using SpecProof.Platform.Api;
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
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy(
        "api",
        context => RateLimitPartition.GetFixedWindowLimiter(
            context.Connection.RemoteIpAddress?.ToString() ?? "local",
            _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 120,
                QueueLimit = 0,
                Window = TimeSpan.FromMinutes(1),
            }));
});
builder.Services.AddScoped<TenantScopeAccessor>();
builder.Services.AddScoped<ITenantScope>(provider => provider.GetRequiredService<TenantScopeAccessor>());
builder.Services.AddSingleton<SpecProofJwtValidator>();
builder.Services.AddSingleton<IDeviceCertificateAuthenticator, DeviceCertificateAuthenticator>();
builder.Services.AddSingleton<DeviceCertificateRotationService>();
builder.Services.AddSingleton<EvidenceSignatureService>();
builder.Services.AddSingleton<SyncProtocolService>();
builder.Services.AddSingleton<ReportingExportService>();
builder.Services.AddSingleton<IEvidenceAssetReader, FileSystemEvidenceAssetReader>();
builder.Services.AddHttpClient<ITechPackImportGateway, TechPackImportGateway>(client =>
    client.BaseAddress = new Uri(
        builder.Configuration["MeasurementService:BaseUrl"] ?? "http://127.0.0.1:8010/"));
builder.Services.AddScoped<IValidator<RegisterStationRequest>, RegisterStationRequestValidator>();
builder.Services.AddScoped<IValidator<RotateDeviceCertificateRequest>, RotateDeviceCertificateRequestValidator>();
builder.Services.AddScoped<IValidator<SyncEnvelopeRequest>, SyncEnvelopeRequestValidator>();
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
app.UseRateLimiter();
app.UseMiddleware<JwtAuthenticationMiddleware>();
app.UseMiddleware<DeviceCertificateAuthenticationMiddleware>();
app.UseMiddleware<TenantResolutionMiddleware>();

app.MapOpenApi("/api/v1/openapi.json");

app.MapGet("/healthz", () => Results.Ok(new { status = "ok", checkedAtUtc = DateTimeOffset.UtcNow }))
    .WithName("HealthCheck");

var api = app.MapGroup("/api/v1")
    .RequireRateLimiting("api");

api.MapGet("/auth/dev-token", (Guid tenantId, string subject, string role, SpecProofJwtValidator jwtValidator, IWebHostEnvironment environment) =>
    {
        if (!environment.IsDevelopment() && !environment.IsEnvironment("Test"))
        {
            return Results.NotFound();
        }

        var token = jwtValidator.CreateToken(tenantId, subject, role, DateTimeOffset.UtcNow.AddHours(1));
        return Results.Ok(new { token, expiresAtUtc = DateTimeOffset.UtcNow.AddHours(1) });
    })
    .WithName("CreateDevelopmentToken");

api.MapGet(
        "/inspections/{id:guid}",
        async (
            Guid id,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var record = await database.InspectionRecords.SingleOrDefaultAsync(
                candidate => candidate.Id == id && candidate.DeletedAtUtc == null,
                cancellationToken);
            if (record is null)
            {
                return Results.NotFound();
            }

            var result = JsonSerializer.Deserialize(
                record.InspectionResultJson,
                SpecProofJsonContext.Default.InspectionResultDto);
            return result is null ? Results.Problem(statusCode: StatusCodes.Status500InternalServerError) : Results.Ok(result);
        })
    .WithName("GetInspection")
    .RequireSpecProofPermission(PlatformPermissions.ReadInspections);

api.MapPost(
        "/inspections",
        async (
            CreateInspectionRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var json = JsonSerializer.Serialize(request.Result, SpecProofJsonContext.Default.InspectionResultDto);
            var record = new InspectionRecord
            {
                Id = request.InspectionId,
                TenantId = request.TenantId,
                CaptureId = request.CaptureId,
                StationId = request.StationId,
                BatchId = request.BatchId,
                StationCode = request.StationCode,
                OrderCode = request.OrderCode,
                StyleCode = request.StyleCode,
                SizeCode = request.SizeCode,
                InspectionResultJson = json,
                Status = request.Result.Status.ToString(),
                EvidenceRecordHash = request.Result.EvidenceRecordHash,
                CapturedAtUtc = request.Result.CapturedAtUtc,
            };
            database.InspectionRecords.Add(record);
            database.BackgroundJobs.Add(
                new BackgroundJobRecord
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    QueueName = "reports",
                    JobType = "inspection.report.refresh",
                    PayloadJson = JsonSerializer.Serialize(new { request.InspectionId }, SpecProofJsonOptions.Canonical),
                    Status = "queued",
                    AvailableAtUtc = DateTimeOffset.UtcNow,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.Created($"/api/v1/inspections/{record.Id}", request.Result);
        })
    .WithName("CreateInspection")
    .RequireTenantMatch<CreateInspectionRequest>()
    .RequireDeviceStationMatch<CreateInspectionRequest>()
    .RequireSpecProofPermission(PlatformPermissions.SyncWrite);

api.MapGet(
        "/reports/batches/{batchId:guid}",
        async (Guid batchId, SpecProofDbContext database, CancellationToken cancellationToken) =>
        {
            var records = await database.InspectionRecords
                .Where(record => record.BatchId == batchId && record.DeletedAtUtc == null)
                .ToArrayAsync(cancellationToken);
            var summary = new BatchSummaryDto(
                batchId,
                records.Length,
                records.Count(record => record.Status == InspectionStatus.Pass.ToString()),
                records.Count(record => record.Status == InspectionStatus.Fail.ToString()),
                records.Count(record => record.Status == InspectionStatus.Review.ToString()),
                records.Count(record => record.Status == InspectionStatus.Invalid.ToString()));
            return Results.Ok(summary);
        })
    .WithName("GetBatchSummary")
    .RequireSpecProofPermission(PlatformPermissions.ReadInspections);

api.MapGet(
        "/reports/inspections.csv",
        async (
            SpecProofDbContext database,
            ReportingExportService exportService,
            CancellationToken cancellationToken) =>
        {
            var records = await database.InspectionRecords
                .Where(record => record.DeletedAtUtc == null)
                .OrderBy(record => record.CapturedAtUtc)
                .ToArrayAsync(cancellationToken);
            var inspections = records
                .Select(record => JsonSerializer.Deserialize(
                    record.InspectionResultJson,
                    SpecProofJsonContext.Default.InspectionResultDto))
                .Where(result => result is not null)
                .Cast<InspectionResultDto>();
            return Results.Text(
                exportService.ToInspectionCsv(inspections),
                "text/csv",
                Encoding.UTF8);
        })
    .WithName("ExportInspectionsCsv")
    .RequireSpecProofPermission(PlatformPermissions.ExportReports);

api.MapDelete(
        "/retention/inspections/{id:guid}",
        async (Guid id, SpecProofDbContext database, CancellationToken cancellationToken) =>
        {
            var record = await database.InspectionRecords.SingleOrDefaultAsync(
                candidate => candidate.Id == id,
                cancellationToken);
            if (record is null)
            {
                return Results.NotFound();
            }

            record.DeletedAtUtc = DateTimeOffset.UtcNow;
            record.UpdatedAtUtc = DateTimeOffset.UtcNow;
            await database.SaveChangesAsync(cancellationToken);
            return Results.NoContent();
        })
    .WithName("DeleteInspectionForRetention")
    .RequireSpecProofPermission(PlatformPermissions.ExportReports);

api.MapPost(
        "/stations/register",
        async (
            RegisterStationRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var certificateThumbprint = DeviceCertificateThumbprint.Normalize(
                request.CertificateThumbprintSha256);
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
            }

            var existingIdentities = await database.DeviceIdentities
                .IgnoreQueryFilters()
                .Where(identity => identity.CertificateThumbprintSha256 == certificateThumbprint)
                .Take(2)
                .ToArrayAsync(cancellationToken);
            if (existingIdentities.Length > 1
                || (existingIdentities.Length == 1
                    && (existingIdentities[0].TenantId != request.TenantId
                        || existingIdentities[0].StationId != station.Id)))
            {
                return Results.Conflict();
            }

            if (existingIdentities.Length == 0)
            {
                database.DeviceIdentities.Add(
                    new DeviceIdentity
                    {
                        Id = Guid.NewGuid(),
                        TenantId = request.TenantId,
                        StationId = station.Id,
                        CertificateThumbprintSha256 = certificateThumbprint,
                        PublicKeyPem = request.PublicKeyPem,
                        NotBeforeUtc = DateTimeOffset.UtcNow,
                        ExpiresAtUtc = DateTimeOffset.UtcNow.AddDays(90),
                        Active = true,
                    });
            }

            await database.SaveChangesAsync(cancellationToken);
            return Results.Ok(
                new StationRegistrationDto(
                    station.Id,
                    station.TenantId,
                    station.FactoryId,
                    station.StationCode,
                    certificateThumbprint,
                    DateTimeOffset.UtcNow));
        })
    .WithName("RegisterStation")
    .AddEndpointFilter<ValidationFilter<RegisterStationRequest>>()
    .RequireTenantMatch<RegisterStationRequest>()
    .RequireSpecProofPermission(PlatformPermissions.ManageStations);

api.MapPost(
        "/stations/{stationId:guid}/certificate/rotate",
        async (
            Guid stationId,
            RotateDeviceCertificateRequest request,
            SpecProofDbContext database,
            TenantScopeAccessor tenantScope,
            DeviceCertificateRotationService rotationService,
            CancellationToken cancellationToken) =>
        {
            if (tenantScope.TenantId is not Guid tenantId)
            {
                return Results.Forbid();
            }

            var stationExists = await database.Stations.AnyAsync(
                station => station.Id == stationId,
                cancellationToken);
            if (!stationExists)
            {
                return Results.NotFound();
            }

            var certificateThumbprint = DeviceCertificateThumbprint.Normalize(
                request.CertificateThumbprintSha256);
            var duplicateExists = await database.DeviceIdentities
                .IgnoreQueryFilters()
                .AnyAsync(
                    identity => identity.CertificateThumbprintSha256 == certificateThumbprint,
                    cancellationToken);
            if (duplicateExists)
            {
                return Results.Conflict();
            }

            var activeIdentities = await database.DeviceIdentities
                .Where(identity => identity.StationId == stationId && identity.Active)
                .ToArrayAsync(cancellationToken);
            var rotation = rotationService.Rotate(
                tenantId,
                stationId,
                request,
                activeIdentities,
                DateTimeOffset.UtcNow);
            database.DeviceIdentities.Add(rotation.Replacement);
            database.AuditEvents.Add(rotation.AuditEvent);
            await database.SaveChangesAsync(cancellationToken);
            return Results.Ok(
                new DeviceCertificateRotationResponse(
                    rotation.Replacement.Id,
                    stationId,
                    rotation.Replacement.CertificateThumbprintSha256,
                    rotation.Replacement.NotBeforeUtc,
                    rotation.Replacement.ExpiresAtUtc));
        })
    .WithName("RotateStationCertificate")
    .AddEndpointFilter<ValidationFilter<RotateDeviceCertificateRequest>>()
    .RequireSpecProofPermission(PlatformPermissions.ManageStations);

api.MapPut(
        "/stations/{stationId:guid}/health",
        async (
            Guid stationId,
            StationHealthRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var stationExists = await database.Stations.AnyAsync(
                station => station.Id == stationId && station.TenantId == request.TenantId,
                cancellationToken);
            if (!stationExists)
            {
                return Results.NotFound();
            }

            database.StationHealthReports.Add(
                new StationHealthReport
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    StationId = stationId,
                    Status = request.Status,
                    CameraStatus = request.CameraStatus,
                    StorageStatus = request.StorageStatus,
                    ClockStatus = request.ClockStatus,
                    OfflineQueueDepth = request.OfflineQueueDepth,
                    CheckedAtUtc = request.CheckedAtUtc,
                });
            database.AuditEvents.Add(
                new AuditEvent
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    EventType = "station.health_reported",
                    EntityType = "station",
                    EntityId = stationId,
                    PayloadJson = JsonSerializer.Serialize(request, SpecProofJsonOptions.Canonical),
                    OccurredAtUtc = request.CheckedAtUtc,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.NoContent();
        })
    .WithName("ReportStationHealth")
    .RequireTenantMatch<StationHealthRequest>()
    .RequireDeviceStationRouteMatch()
    .RequireSpecProofPermission(PlatformPermissions.ReportStationHealth);

api.MapPost(
        "/stations/{stationId:guid}/diagnostics",
        async (
            Guid stationId,
            StationDiagnosticsRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            database.StationDiagnosticReports.Add(
                new StationDiagnosticReport
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    StationId = stationId,
                    DiagnosticsJson = request.DiagnosticsJson,
                    RequestedAtUtc = DateTimeOffset.UtcNow,
                    CompletedAtUtc = DateTimeOffset.UtcNow,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.Accepted();
        })
    .WithName("SubmitStationDiagnostics")
    .RequireTenantMatch<StationDiagnosticsRequest>()
    .RequireDeviceStationMatch<StationDiagnosticsRequest>()
    .RequireDeviceStationRouteMatch()
    .RequireSpecProofPermission(PlatformPermissions.ManageStations);

api.MapPost(
        "/stations/{stationId:guid}/configuration",
        async (
            Guid stationId,
            StationConfigurationPushRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            database.StationConfigurationVersions.Add(
                new StationConfigurationVersion
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    StationId = stationId,
                    Version = request.Version,
                    ConfigurationJson = request.ConfigurationJson,
                    PushedAtUtc = DateTimeOffset.UtcNow,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.Accepted();
        })
    .WithName("PushStationConfiguration")
    .RequireTenantMatch<StationConfigurationPushRequest>()
    .RequireDeviceStationMatch<StationConfigurationPushRequest>()
    .RequireDeviceStationRouteMatch()
    .RequireSpecProofPermission(PlatformPermissions.ManageStations);

api.MapPut(
        "/stations/{stationId:guid}/versions/{componentName}",
        async (
            Guid stationId,
            string componentName,
            StationVersionRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            database.StationSoftwareVersions.Add(
                new StationSoftwareVersion
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    StationId = stationId,
                    ComponentName = componentName,
                    Version = request.Version,
                    ReportedAtUtc = DateTimeOffset.UtcNow,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.NoContent();
        })
    .WithName("ReportStationVersion")
    .RequireTenantMatch<StationVersionRequest>()
    .RequireDeviceStationMatch<StationVersionRequest>()
    .RequireDeviceStationRouteMatch()
    .RequireSpecProofPermission(PlatformPermissions.ReportStationHealth);

api.MapPost(
        "/captures/initiate",
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
                return Results.Ok(new InitiateCaptureUploadResponse(existing.Id, existing.ObjectKey));
            }

            var asset = new CaptureAsset
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                StationId = request.StationId,
                CaptureId = request.CaptureId,
                ObjectKey = TenantObjectStorageNamespace.BuildObjectKey(
                    request.TenantId,
                    request.StationId,
                    request.CaptureId,
                    ".spcapture"),
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
    .WithName("InitiateCaptureUpload")
    .RequireTenantMatch<InitiateCaptureUploadRequest>()
    .RequireDeviceStationMatch<InitiateCaptureUploadRequest>()
    .RequireSpecProofPermission(PlatformPermissions.SyncWrite);

api.MapPost(
        "/captures/{assetId:guid}/complete",
        async (
            Guid assetId,
            CompleteCaptureUploadRequest request,
            SpecProofDbContext database,
            ClaimsPrincipal principal,
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

            if (!DeviceStationAccess.Matches(principal, asset.StationId))
            {
                return Results.Forbid();
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
    .WithName("CompleteCaptureUpload")
    .RequireTenantMatch<CompleteCaptureUploadRequest>()
    .RequireSpecProofPermission(PlatformPermissions.SyncWrite);

api.MapPost(
        "/sync/envelopes",
        async (
            Guid tenantId,
            SyncEnvelopeRequest request,
            SyncProtocolService syncProtocol,
            SpecProofDbContext database,
            TenantScopeAccessor tenantScope,
            CancellationToken cancellationToken) =>
        {
            if (!tenantScope.Matches(tenantId))
            {
                return Results.Forbid();
            }

            var envelope = await syncProtocol.AcceptAsync(database, tenantId, request, cancellationToken);
            return Results.Ok(
                new SyncEnvelopeDto(
                    envelope.Id,
                    envelope.TenantId,
                    envelope.StationId,
                    envelope.IdempotencyKey,
                    envelope.EntityType,
                    envelope.EntityId,
                    envelope.PayloadHashSha256,
                    envelope.Status));
        })
    .WithName("AcceptSyncEnvelope")
    .AddEndpointFilter<ValidationFilter<SyncEnvelopeRequest>>()
    .RequireDeviceStationMatch<SyncEnvelopeRequest>()
    .RequireSpecProofPermission(PlatformPermissions.SyncWrite);

api.MapPost(
        "/evidence/{evidenceId:guid}/sign",
        async (
            Guid evidenceId,
            SpecProofDbContext database,
            EvidenceSignatureService signatureService,
            CancellationToken cancellationToken) =>
        {
            var evidence = await database.EvidenceRecords.SingleOrDefaultAsync(
                record => record.Id == evidenceId,
                cancellationToken);
            if (evidence is null)
            {
                return Results.NotFound();
            }

            var signature = signatureService.Sign(evidence.EvidenceJson);
            evidence.SignatureAlgorithm = signature.Algorithm;
            evidence.SignatureValueBase64 = signature.SignatureValueBase64;
            evidence.SignedAtUtc = signature.SignedAtUtc;
            evidence.UpdatedAtUtc = DateTimeOffset.UtcNow;
            await database.SaveChangesAsync(cancellationToken);
            return Results.Ok(signature);
        })
    .WithName("SignEvidence")
    .RequireSpecProofPermission(PlatformPermissions.VerifyEvidence);

api.MapPost(
        "/evidence/verify",
        (EvidenceVerifyRequest request, EvidenceSignatureService signatureService) =>
        {
            var verified = signatureService.Verify(request.EvidenceJson, request.SignatureValueBase64);
            return Results.Ok(new { verified });
        })
    .WithName("VerifyEvidence")
    .RequireSpecProofPermission(PlatformPermissions.VerifyEvidence);

api.MapPost(
        "/webhooks",
        async (
            WebhookSubscriptionRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            database.WebhookSubscriptions.Add(
                new WebhookSubscription
                {
                    Id = Guid.NewGuid(),
                    TenantId = request.TenantId,
                    Url = request.Url,
                    EventTypesJson = JsonSerializer.Serialize(request.EventTypes, SpecProofJsonOptions.Canonical),
                    SecretHashSha256 = Convert.ToHexString(
                        System.Security.Cryptography.SHA256.HashData(Encoding.UTF8.GetBytes(request.Secret))).ToLowerInvariant(),
                    Active = true,
                });
            await database.SaveChangesAsync(cancellationToken);
            return Results.Accepted();
        })
    .WithName("CreateWebhookSubscription")
    .RequireTenantMatch<WebhookSubscriptionRequest>()
    .RequireSpecProofPermission(PlatformPermissions.ExportReports);

api.MapPost(
        "/jobs",
        async (
            BackgroundJobRequest request,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
        {
            var job = new BackgroundJobRecord
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                QueueName = request.QueueName,
                JobType = request.JobType,
                PayloadJson = request.PayloadJson,
                Status = "queued",
                AvailableAtUtc = DateTimeOffset.UtcNow,
            };
            database.BackgroundJobs.Add(job);
            await database.SaveChangesAsync(cancellationToken);
            return Results.Accepted($"/api/v1/jobs/{job.Id}");
        })
    .WithName("CreateBackgroundJob")
    .RequireTenantMatch<BackgroundJobRequest>()
    .RequireSpecProofPermission(PlatformPermissions.ManageBackgroundJobs);

api.MapWebApplicationEndpoints();

app.Run();

public sealed record RegisterStationRequest(
    Guid TenantId,
    Guid FactoryId,
    string StationCode,
    string CertificateThumbprintSha256,
    string PublicKeyPem) : ITenantBoundRequest;

public sealed record StationHealthRequest(
    Guid TenantId,
    string Status,
    string CameraStatus,
    string StorageStatus,
    string ClockStatus,
    long OfflineQueueDepth,
    DateTimeOffset CheckedAtUtc) : ITenantBoundRequest;

public sealed record RotateDeviceCertificateRequest(
    string CertificateThumbprintSha256,
    string PublicKeyPem,
    DateTimeOffset NotBeforeUtc,
    DateTimeOffset ExpiresAtUtc);

public sealed record DeviceCertificateRotationResponse(
    Guid DeviceIdentityId,
    Guid StationId,
    string CertificateThumbprintSha256,
    DateTimeOffset NotBeforeUtc,
    DateTimeOffset ExpiresAtUtc);

public sealed record InitiateCaptureUploadRequest(
    Guid TenantId,
    Guid StationId,
    Guid CaptureId,
    long SizeBytes,
    string ChecksumSha256) : ITenantBoundRequest, IStationBoundRequest;

public sealed record InitiateCaptureUploadResponse(Guid AssetId, string ObjectKey);

public sealed record CompleteCaptureUploadRequest(Guid TenantId, string ChecksumSha256) : ITenantBoundRequest;

public partial class Program;
