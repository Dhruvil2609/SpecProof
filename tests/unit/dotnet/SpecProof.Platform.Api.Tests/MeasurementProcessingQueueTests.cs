using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using SpecProof.Contracts;
using SpecProof.Platform.Api;
using SpecProof.Platform.Data;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class MeasurementProcessingQueueTests(PlatformApiFactory factory)
    : IClassFixture<PlatformApiFactory>
{
    [Fact]
    public async Task EnqueueAsync_CompletedCaptureAndApprovedTechPack_IsIdempotent()
    {
        var request = CreateRequest();
        await SeedDependenciesAsync(request, uploadCompleted: true, techPackApproved: true);

        var first = await EnqueueInNewScopeAsync(request);
        var replay = await EnqueueInNewScopeAsync(request);

        Assert.Equal(MeasurementEnqueueStatus.Queued, first.Status);
        Assert.Equal(MeasurementEnqueueStatus.Replayed, replay.Status);
        Assert.NotNull(first.JobId);
        Assert.Equal(first.JobId, replay.JobId);
        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        var job = await database.BackgroundJobs.SingleAsync(candidate => candidate.Id == first.JobId);
        Assert.Equal(MeasurementProcessingQueue.QueueName, job.QueueName);
        Assert.Equal(MeasurementProcessingQueue.JobType, job.JobType);
        Assert.Equal("queued", job.Status);
        var payload = JsonSerializer.Deserialize<MeasurementProcessingPayload>(
            job.PayloadJson,
            SpecProofJsonOptions.Canonical);
        Assert.NotNull(payload);
        Assert.Equal(request.CaptureId, payload.CaptureId);
        Assert.Equal(request.TechPackVersion, payload.TechPackVersion);
    }

    [Theory]
    [InlineData(false, true, MeasurementEnqueueStatus.CaptureUnavailable)]
    [InlineData(true, false, MeasurementEnqueueStatus.TechPackUnavailable)]
    public async Task EnqueueAsync_UnavailableDependency_DoesNotCreateJob(
        bool uploadCompleted,
        bool techPackApproved,
        MeasurementEnqueueStatus expectedStatus)
    {
        var request = CreateRequest();
        await SeedDependenciesAsync(request, uploadCompleted, techPackApproved);

        var result = await EnqueueInNewScopeAsync(request);

        Assert.Equal(expectedStatus, result.Status);
        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        Assert.False(await database.BackgroundJobs.AnyAsync(job => job.TenantId == request.TenantId));
    }

    private async Task<MeasurementEnqueueResult> EnqueueInNewScopeAsync(
        MeasurementProcessingRequest request)
    {
        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        var queue = scope.ServiceProvider.GetRequiredService<MeasurementProcessingQueue>();
        return await queue.EnqueueAsync(database, request, CancellationToken.None);
    }

    private async Task SeedDependenciesAsync(
        MeasurementProcessingRequest request,
        bool uploadCompleted,
        bool techPackApproved)
    {
        var nowUtc = DateTimeOffset.UtcNow;
        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        database.CaptureAssets.Add(
            new CaptureAsset
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                StationId = request.StationId,
                CaptureId = request.CaptureId,
                ObjectKey = $"{request.TenantId:N}/{request.CaptureId:N}.spcapture",
                ContentType = "application/vnd.specproof.capture",
                SizeBytes = 1024,
                ChecksumSha256 = new string('a', 64),
                RetentionCategory = "standard",
                UploadCompletedAtUtc = uploadCompleted ? nowUtc : null,
                CreatedAtUtc = nowUtc,
                UpdatedAtUtc = nowUtc,
            });
        database.TechPackVersions.Add(
            new TechPackVersion
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                TechPackId = request.TechPackId,
                Version = request.TechPackVersion,
                Brand = "brand-1",
                StyleCode = "style-1",
                GarmentCategory = "shirt",
                DataJson = "{}",
                VersionHashSha256 = new string('b', 64),
                Approved = techPackApproved,
                CreatedAtUtc = nowUtc,
                UpdatedAtUtc = nowUtc,
            });
        await database.SaveChangesAsync();
    }

    private static MeasurementProcessingRequest CreateRequest() =>
        new(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), 3);
}
