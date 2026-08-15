using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using SpecProof.Contracts;
using SpecProof.Platform.Data;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class IntegratedInspectionPostgreSqlTests
{
    [Fact]
    [Trait("Category", "Integration")]
    public async Task EndpointPersistence_PostgreSqlAvailable_IsAtomicAndIdempotent()
    {
        if (!string.Equals(
            Environment.GetEnvironmentVariable("SPEC_PROOF_RUN_DATABASE_INTEGRATION"),
            "1",
            StringComparison.Ordinal))
        {
            return;
        }

        await using var context = CreateDatabaseContext();
        await context.Database.EnsureDeletedAsync();
        await context.Database.MigrateAsync();
        var tenantId = Guid.NewGuid();
        var stationId = Guid.NewGuid();
        var captureId = Guid.NewGuid();
        context.Tenants.Add(new Tenant { Id = tenantId, Name = "Integrated Tenant" });
        context.Stations.Add(
            new SpecProof.Platform.Data.Station
            {
                Id = stationId,
                TenantId = tenantId,
                FactoryId = Guid.NewGuid(),
                StationCode = "STATION-INT-1",
            });
        context.CaptureAssets.Add(
            new CaptureAsset
            {
                Id = Guid.NewGuid(),
                TenantId = tenantId,
                StationId = stationId,
                CaptureId = captureId,
                ObjectKey = $"{tenantId:N}/{stationId:N}/{captureId:N}.spcapture",
                ContentType = "application/vnd.specproof.capture+zip",
                SizeBytes = 1024,
                ChecksumSha256 = new string('a', 64),
                RetentionCategory = "inspection-evidence",
                Encrypted = true,
                UploadCompletedAtUtc = DateTimeOffset.UtcNow,
            });
        await context.SaveChangesAsync();
        var signatureService = new EvidenceSignatureService(
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["Trust:SigningKeyId"] = "integration-key",
                        ["Trust:SigningSecret"] = "integration-signing-secret",
                    })
                .Build());
        var persistence = new IntegratedInspectionPersistence(signatureService);
        var request = CreateRequest(tenantId, stationId, captureId);

        var created = await persistence.PersistAsync(context, request, CancellationToken.None);

        Assert.Equal(IntegratedInspectionPersistenceStatus.Created, created.Status);
        Assert.NotNull(created.Submission?.Evidence.Signature);
        Assert.Single(await context.InspectionRecords.ToListAsync());
        var storedEvidence = Assert.Single(await context.EvidenceRecords.ToListAsync());
        Assert.True(
            signatureService.Verify(
                storedEvidence.EvidenceJson,
                storedEvidence.SignatureValueBase64!));
        Assert.Single(await context.AuditEvents.ToListAsync());
        Assert.Single(await context.BackgroundJobs.ToListAsync());

        context.ChangeTracker.Clear();
        var replayed = await persistence.PersistAsync(context, request, CancellationToken.None);
        Assert.Equal(IntegratedInspectionPersistenceStatus.Replayed, replayed.Status);

        context.ChangeTracker.Clear();
        var conflicted = await persistence.PersistAsync(
            context,
            request with { OrderCode = "ORDER-CONFLICT" },
            CancellationToken.None);
        Assert.Equal(IntegratedInspectionPersistenceStatus.Conflict, conflicted.Status);
        Assert.Single(await context.InspectionRecords.ToListAsync());
        Assert.Single(await context.EvidenceRecords.ToListAsync());
        Assert.Single(await context.AuditEvents.ToListAsync());
        Assert.Single(await context.BackgroundJobs.ToListAsync());
    }

    private static SpecProofDbContext CreateDatabaseContext()
    {
        var connectionString =
            Environment.GetEnvironmentVariable("SPEC_PROOF_TEST_DATABASE")
            ?? "Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123";
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql(connectionString)
            .Options;
        return new SpecProofDbContext(options);
    }

    private static CreateInspectionRequest CreateRequest(
        Guid tenantId,
        Guid stationId,
        Guid captureId)
    {
        var inspectionId = Guid.NewGuid();
        var evidenceHash = new string('b', 64);
        var measurement = new MeasurementDto(
            "chest_width",
            "Chest Width",
            500,
            500,
            5,
            5,
            0,
            0.99,
            MeasurementStatus.Pass,
            []);
        var result = new InspectionResultDto(
            inspectionId,
            stationId.ToString(),
            "CAMERA-INT-1",
            DateTimeOffset.UtcNow,
            [measurement],
            InspectionStatus.Pass,
            evidenceHash);
        var evidence = new EvidenceRecordDto(
            Guid.NewGuid().ToString(),
            tenantId,
            inspectionId,
            captureId,
            new string('a', 64),
            DateTimeOffset.UtcNow,
            new EvidenceVersionsDto(
                Guid.NewGuid().ToString(),
                "perception-v1",
                "ontology-v1",
                "compiler-v1",
                Guid.NewGuid(),
                1),
            [measurement],
            InspectionStatus.Pass,
            null,
            evidenceHash);
        return new CreateInspectionRequest(
            tenantId,
            inspectionId,
            captureId,
            stationId,
            null,
            "STATION-INT-1",
            "ORDER-INT-1",
            "STYLE-INT-1",
            "M",
            result,
            evidence);
    }
}
