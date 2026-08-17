using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using SpecProof.Contracts;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api;

public enum MeasurementEnqueueStatus
{
    Queued,
    Replayed,
    CaptureUnavailable,
    TechPackUnavailable,
}

public sealed record MeasurementProcessingPayload(
    Guid TenantId,
    Guid StationId,
    Guid CaptureId,
    Guid TechPackId,
    int TechPackVersion);

public sealed record MeasurementEnqueueResult(MeasurementEnqueueStatus Status, Guid? JobId = null);

public sealed class MeasurementProcessingQueue
{
    public const string QueueName = "measurements";
    public const string JobType = "measurement.process";

    public async Task<MeasurementEnqueueResult> EnqueueAsync(
        SpecProofDbContext database,
        MeasurementProcessingRequest request,
        CancellationToken cancellationToken)
    {
        var captureAvailable = await database.CaptureAssets.AnyAsync(
            capture =>
                capture.TenantId == request.TenantId
                && capture.StationId == request.StationId
                && capture.CaptureId == request.CaptureId
                && capture.UploadCompletedAtUtc != null,
            cancellationToken);
        if (!captureAvailable)
        {
            return new MeasurementEnqueueResult(MeasurementEnqueueStatus.CaptureUnavailable);
        }

        var techPackAvailable = await database.TechPackVersions.AnyAsync(
            version =>
                version.TenantId == request.TenantId
                && version.TechPackId == request.TechPackId
                && version.Version == request.TechPackVersion
                && version.Approved,
            cancellationToken);
        if (!techPackAvailable)
        {
            return new MeasurementEnqueueResult(MeasurementEnqueueStatus.TechPackUnavailable);
        }

        var jobId = CreateJobId(request);
        var existing = await database.BackgroundJobs.SingleOrDefaultAsync(
            job => job.Id == jobId && job.TenantId == request.TenantId,
            cancellationToken);
        if (existing is not null)
        {
            return new MeasurementEnqueueResult(MeasurementEnqueueStatus.Replayed, existing.Id);
        }

        var payload = new MeasurementProcessingPayload(
            request.TenantId,
            request.StationId,
            request.CaptureId,
            request.TechPackId,
            request.TechPackVersion);
        var nowUtc = DateTimeOffset.UtcNow;
        database.BackgroundJobs.Add(
            new BackgroundJobRecord
            {
                Id = jobId,
                TenantId = request.TenantId,
                QueueName = QueueName,
                JobType = JobType,
                PayloadJson = JsonSerializer.Serialize(payload, SpecProofJsonOptions.Canonical),
                Status = "queued",
                AvailableAtUtc = nowUtc,
                CreatedAtUtc = nowUtc,
                UpdatedAtUtc = nowUtc,
            });
        await database.SaveChangesAsync(cancellationToken);
        return new MeasurementEnqueueResult(MeasurementEnqueueStatus.Queued, jobId);
    }

    private static Guid CreateJobId(MeasurementProcessingRequest request)
    {
        var key = string.Join(
            ':',
            request.TenantId.ToString("N"),
            request.StationId.ToString("N"),
            request.CaptureId.ToString("N"),
            request.TechPackId.ToString("N"),
            request.TechPackVersion);
        var hash = SHA256.HashData(Encoding.UTF8.GetBytes(key));
        return new Guid(hash.AsSpan(0, 16));
    }
}

public sealed record MeasurementProcessingRequest(
    Guid TenantId,
    Guid StationId,
    Guid CaptureId,
    Guid TechPackId,
    int TechPackVersion) : ITenantBoundRequest, IStationBoundRequest;

public sealed record MeasurementProcessingEnqueueResponse(Guid JobId, string Status);
