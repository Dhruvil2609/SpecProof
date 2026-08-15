using System.Security.Cryptography;
using System.Text.Json;
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
        await SeedTenantAsync(context, tenantId, stationId, "STATION-INT-1", [captureId]);
        var signatureService = CreateSignatureService();
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

    [Fact]
    [Trait("Category", "Stress")]
    public async Task ConcurrentPersistence_PostgreSqlAvailable_IsTenantIsolatedAndAudited()
    {
        if (!string.Equals(
            Environment.GetEnvironmentVariable("SPEC_PROOF_RUN_DATABASE_INTEGRATION"),
            "1",
            StringComparison.Ordinal))
        {
            return;
        }

        await using var setup = CreateDatabaseContext();
        await setup.Database.EnsureDeletedAsync();
        await setup.Database.MigrateAsync();
        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();
        var stationA = Guid.NewGuid();
        var stationB = Guid.NewGuid();
        var capturesA = Enumerable.Range(0, 8).Select(_ => Guid.NewGuid()).ToArray();
        var capturesB = Enumerable.Range(0, 8).Select(_ => Guid.NewGuid()).ToArray();
        await SeedTenantAsync(setup, tenantA, stationA, "STATION-LOAD-A", capturesA);
        await SeedTenantAsync(setup, tenantB, stationB, "STATION-LOAD-B", capturesB);
        var persistence = new IntegratedInspectionPersistence(CreateSignatureService());
        var requests = capturesA
            .Select(captureId => CreateRequest(tenantA, stationA, captureId, "STATION-LOAD-A"))
            .Concat(capturesB.Select(
                captureId => CreateRequest(tenantB, stationB, captureId, "STATION-LOAD-B")))
            .ToArray();

        var outcomes = await Task.WhenAll(
            requests.Select(
                async request =>
                {
                    await using var database = CreateDatabaseContext();
                    return await persistence.PersistAsync(
                        database,
                        request,
                        CancellationToken.None);
                }));

        Assert.All(
            outcomes,
            outcome => Assert.Equal(IntegratedInspectionPersistenceStatus.Created, outcome.Status));
        await AssertTenantLoadAsync(tenantA, capturesA.Length);
        await AssertTenantLoadAsync(tenantB, capturesB.Length);
    }

    private static SpecProofDbContext CreateDatabaseContext(Guid? tenantId = null)
    {
        var connectionString =
            Environment.GetEnvironmentVariable("SPEC_PROOF_TEST_DATABASE")
            ?? "Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123";
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql(connectionString)
            .Options;
        return new SpecProofDbContext(
            options,
            tenantId is null ? null : new StaticTenantScope(tenantId.Value));
    }

    private static EvidenceSignatureService CreateSignatureService() =>
        new(
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["Trust:SigningKeyId"] = "integration-key",
                        ["Trust:SigningSecret"] = "integration-signing-secret",
                    })
                .Build());

    private static async Task SeedTenantAsync(
        SpecProofDbContext context,
        Guid tenantId,
        Guid stationId,
        string stationCode,
        IReadOnlyCollection<Guid> captureIds)
    {
        var organisationId = Guid.NewGuid();
        var factoryId = Guid.NewGuid();
        context.Tenants.Add(new Tenant { Id = tenantId, Name = $"Tenant {tenantId:N}" });
        context.Organisations.Add(
            new Organisation
            {
                Id = organisationId,
                TenantId = tenantId,
                Name = "Load Organisation",
            });
        context.Factories.Add(
            new Factory
            {
                Id = factoryId,
                TenantId = tenantId,
                OrganisationId = organisationId,
                Name = "Load Factory",
            });
        context.Stations.Add(
            new SpecProof.Platform.Data.Station
            {
                Id = stationId,
                TenantId = tenantId,
                FactoryId = factoryId,
                StationCode = stationCode,
            });
        context.CaptureAssets.AddRange(
            captureIds.Select(
                captureId => new CaptureAsset
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
                }));
        await context.SaveChangesAsync();
    }

    private static async Task AssertTenantLoadAsync(Guid tenantId, int expectedCount)
    {
        await using var context = CreateDatabaseContext(tenantId);
        var inspections = await context.InspectionRecords.ToArrayAsync();
        var evidence = await context.EvidenceRecords.ToDictionaryAsync(
            record => record.InspectionId);
        var auditEvents = await context.AuditEvents.ToArrayAsync();

        Assert.Equal(expectedCount, inspections.Length);
        Assert.Equal(expectedCount, evidence.Count);
        Assert.Equal(expectedCount, auditEvents.Length);
        Assert.All(
            auditEvents,
            auditEvent =>
            {
                using var payload = JsonDocument.Parse(auditEvent.PayloadJson);
                var evidenceHash = payload.RootElement
                    .GetProperty("evidenceHashSha256")
                    .GetString();
                Assert.Equal(evidence[auditEvent.EntityId].RecordHashSha256, evidenceHash);
            });
    }

    private static CreateInspectionRequest CreateRequest(
        Guid tenantId,
        Guid stationId,
        Guid captureId,
        string stationCode = "STATION-INT-1")
    {
        var inspectionId = Guid.NewGuid();
        var evidenceHash = Convert.ToHexString(
            SHA256.HashData(inspectionId.ToByteArray()))
            .ToLowerInvariant();
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
            stationCode,
            "ORDER-INT-1",
            "STYLE-INT-1",
            "M",
            result,
            evidence);
    }

    private sealed class StaticTenantScope(Guid tenantId) : ITenantScope
    {
        public Guid? TenantId { get; } = tenantId;
    }
}
