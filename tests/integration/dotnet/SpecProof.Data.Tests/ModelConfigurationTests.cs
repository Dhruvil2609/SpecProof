using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.EntityFrameworkCore.Migrations.Operations;
using Microsoft.EntityFrameworkCore.Storage;
using Npgsql;
using SpecProof.Platform.Data;
using SpecProof.Platform.Data.Migrations;
using Xunit;

namespace SpecProof.Data.Tests;

public sealed class ModelConfigurationTests
{
    [Fact]
    public void SpecProofDbContext_Model_UsesUtcTimestampColumnTypes()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options);
        var auditOccurredAt = context.Model.FindEntityType(typeof(AuditEvent))
            ?.FindProperty(nameof(AuditEvent.OccurredAtUtc))
            ?.GetColumnType();

        Assert.Equal("timestamptz", auditOccurredAt);
    }

    [Fact]
    public void SpecProofDbContext_Model_MapsAllEntityTimestampsAsTimestamptz()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options);
        var timestampTypes = context.Model.GetEntityTypes()
            .SelectMany(entityType => entityType.GetProperties())
            .Where(property => property.Name.EndsWith("AtUtc", StringComparison.Ordinal))
            .Select(property => property.GetColumnType())
            .Distinct()
            .ToArray();

        Assert.Single(timestampTypes);
        Assert.Equal("timestamptz", timestampTypes[0]);
    }

    [Fact]
    public void InitialFoundation_Migration_ContainsAppendOnlyAuditTriggerSql()
    {
        var migration = new InitialFoundation();
        var operations = migration.UpOperations.OfType<SqlOperation>().Select(operation => operation.Sql);

        Assert.Contains(operations, sql => sql.Contains("prevent_audit_modification", StringComparison.Ordinal));
    }

    [Fact]
    public void CaptureStationCore_Migration_ContainsAppendOnlyCalibrationTriggerSql()
    {
        var migration = new CaptureStationCore();
        var operations = migration.UpOperations.OfType<SqlOperation>().Select(operation => operation.Sql);

        Assert.Contains(
            operations,
            sql => sql.Contains("prevent_calibration_modification", StringComparison.Ordinal));
    }

    [Fact]
    public void MigrationAssembly_ContainsFoundationAndCaptureMigrations()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options);
        var migrationIds = context.GetService<IMigrationsAssembly>().Migrations.Keys.ToArray();

        Assert.Equal(
            [
                "20260726103000_InitialFoundation",
                "20260727170000_CaptureStationCore",
                "20260805000000_MeasurementEngine",
                "20260806000000_PlatformTrustLayer",
                "20260812000000_WebApplication",
                "20260815073000_Phase7PerformanceIndexes",
            ],
            migrationIds);
    }

    [Fact]
    public void MeasurementEngine_Migration_ContainsReferencedTechPackTriggerSql()
    {
        var migration = new MeasurementEngine();
        var operations = migration.UpOperations.OfType<SqlOperation>().Select(operation => operation.Sql);

        Assert.Contains(
            operations,
            sql => sql.Contains("prevent_tech_pack_referenced_modification", StringComparison.Ordinal));
    }

    [Fact]
    public void SpecProofDbContext_Model_MapsMeasurementEngineJsonAsJsonb()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options);
        var techPackData = context.Model.FindEntityType(typeof(TechPackVersion))
            ?.FindProperty(nameof(TechPackVersion.DataJson))
            ?.GetColumnType();
        var evidence = context.Model.FindEntityType(typeof(EvidenceRecord))
            ?.FindProperty(nameof(EvidenceRecord.EvidenceJson))
            ?.GetColumnType();

        Assert.Equal("jsonb", techPackData);
        Assert.Equal("jsonb", evidence);
    }

    [Fact]
    public void SpecProofDbContext_Model_AppliesTenantFiltersToPhase5Entities()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options, new StaticTenantScope(Guid.NewGuid()));

        Assert.True(context.Model.FindEntityType(typeof(InspectionRecord))?.GetDeclaredQueryFilters().Any());
        Assert.True(context.Model.FindEntityType(typeof(SyncEnvelope))?.GetDeclaredQueryFilters().Any());
        Assert.True(context.Model.FindEntityType(typeof(StationHealthReport))?.GetDeclaredQueryFilters().Any());
        Assert.True(context.Model.FindEntityType(typeof(AuditEvent))?.GetDeclaredQueryFilters().Any());
    }

    [Fact]
    public void SpecProofDbContext_Model_MapsPhase5JsonAsJsonb()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options);

        Assert.Equal(
            "jsonb",
            context.Model.FindEntityType(typeof(TenantConfiguration))
                ?.FindProperty(nameof(TenantConfiguration.ConfigurationJson))
                ?.GetColumnType());
        Assert.Equal(
            "jsonb",
            context.Model.FindEntityType(typeof(SyncEnvelope))
                ?.FindProperty(nameof(SyncEnvelope.PayloadJson))
                ?.GetColumnType());
        Assert.Equal(
            "jsonb",
            context.Model.FindEntityType(typeof(BackgroundJobRecord))
                ?.FindProperty(nameof(BackgroundJobRecord.PayloadJson))
                ?.GetColumnType());
    }

    [Fact]
    public void PlatformTrustLayer_Migration_ContainsSignedEvidenceTriggerSql()
    {
        var migration = new PlatformTrustLayer();
        var operations = migration.UpOperations.OfType<SqlOperation>().Select(operation => operation.Sql);

        Assert.Contains(
            operations,
            sql => sql.Contains("prevent_signed_evidence_modification", StringComparison.Ordinal));
    }

    [Fact]
    public void WebApplication_Migration_ContainsAppendOnlyAndDraftImmutabilityTriggers()
    {
        var migration = new WebApplication();
        var operations = migration.UpOperations.OfType<SqlOperation>().Select(operation => operation.Sql);

        Assert.Contains(operations, sql => sql.Contains("prevent_review_action_modification", StringComparison.Ordinal));
        Assert.Contains(
            operations,
            sql => sql.Contains("prevent_approved_tech_pack_draft_modification", StringComparison.Ordinal));
    }

    [Fact]
    public void SpecProofDbContext_Model_AppliesTenantFiltersAndJsonbToPhase6Entities()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;

        using var context = new SpecProofDbContext(options, new StaticTenantScope(Guid.NewGuid()));

        Assert.True(context.Model.FindEntityType(typeof(Brand))?.GetDeclaredQueryFilters().Any());
        Assert.True(context.Model.FindEntityType(typeof(ProductionOrder))?.GetDeclaredQueryFilters().Any());
        Assert.True(context.Model.FindEntityType(typeof(InspectionBatch))?.GetDeclaredQueryFilters().Any());
        Assert.True(context.Model.FindEntityType(typeof(ReviewAction))?.GetDeclaredQueryFilters().Any());
        Assert.Equal(
            "jsonb",
            context.Model.FindEntityType(typeof(TechPackImportDraft))
                ?.FindProperty(nameof(TechPackImportDraft.DraftJson))
                ?.GetColumnType());
    }

    [Fact]
    public void Phase7Performance_Model_IndexesLatestTenantEvidence()
    {
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql("Host=localhost;Port=55432;Database=specproof_test;Username=Admin;Password=Admin@123")
            .Options;
        using var context = new SpecProofDbContext(options);

        var index = context.Model.FindEntityType(typeof(EvidenceRecord))
            ?.GetIndexes()
            .SingleOrDefault(candidate =>
                candidate.GetDatabaseName() == "ix_evidence_records_tenant_id_created_at_utc");

        Assert.NotNull(index);
        Assert.Equal(
            [nameof(EvidenceRecord.TenantId), nameof(EvidenceRecord.CreatedAtUtc)],
            index.Properties.Select(property => property.Name));
    }

    [Fact]
    public async Task Migrations_PostgreSqlAvailable_ApplyAndRollbackSuccessfully()
    {
        if (!ShouldRunDatabaseIntegrationTests())
        {
            return;
        }

        await using var context = CreateDatabaseContext();
        await context.Database.EnsureDeletedAsync();
        await context.Database.MigrateAsync();

        var tables = await context.Database.SqlQueryRaw<string>(
            """
            SELECT table_name AS "Value"
            FROM information_schema.tables
            WHERE table_schema = 'public'
            """).ToListAsync();

        Assert.Contains("capture_assets", tables);

        var migrator = context.GetService<IMigrator>();
        await migrator.MigrateAsync("0");
    }

    [Fact]
    public async Task AuditEvents_PostgreSqlAvailable_UpdateIsRejected()
    {
        if (!ShouldRunDatabaseIntegrationTests())
        {
            return;
        }

        await using var context = CreateDatabaseContext();
        await context.Database.EnsureDeletedAsync();
        await context.Database.MigrateAsync();
        var tenant = new Tenant
        {
            Id = Guid.NewGuid(),
            Name = "Integration Tenant",
        };
        context.Tenants.Add(tenant);
        await context.SaveChangesAsync();

        var auditEvent = new AuditEvent
        {
            Id = Guid.NewGuid(),
            TenantId = tenant.Id,
            EventType = "integration.created",
            EntityType = "tenant",
            EntityId = tenant.Id,
            PayloadJson = "{}",
            OccurredAtUtc = DateTimeOffset.UtcNow,
        };
        context.AuditEvents.Add(auditEvent);
        await context.SaveChangesAsync();

        await Assert.ThrowsAsync<PostgresException>(
            () => context.Database.ExecuteSqlInterpolatedAsync(
                $"UPDATE audit_events SET payload = '{{}}'::jsonb WHERE id = {auditEvent.Id}"));
    }

    [Fact]
    public async Task ReviewActions_PostgreSqlAvailable_UpdateAndDeleteAreRejected()
    {
        if (!ShouldRunDatabaseIntegrationTests())
        {
            return;
        }

        await using var context = CreateDatabaseContext();
        await context.Database.EnsureDeletedAsync();
        await context.Database.MigrateAsync();
        var tenant = new Tenant { Id = Guid.NewGuid(), Name = "Review Tenant" };
        context.Tenants.Add(tenant);
        var review = new ReviewAction
        {
            Id = Guid.NewGuid(),
            TenantId = tenant.Id,
            InspectionId = Guid.NewGuid(),
            Outcome = "CONFIRM_FAIL",
            Note = "Initial review",
        };
        context.ReviewActions.Add(review);
        await context.SaveChangesAsync();

        await Assert.ThrowsAsync<PostgresException>(
            () => context.Database.ExecuteSqlInterpolatedAsync(
                $"UPDATE review_actions SET note = 'changed' WHERE id = {review.Id}"));

        context.ChangeTracker.Clear();
        await Assert.ThrowsAsync<PostgresException>(
            () => context.Database.ExecuteSqlInterpolatedAsync(
                $"DELETE FROM review_actions WHERE id = {review.Id}"));
    }

    [Fact]
    public async Task ApprovedTechPackDraft_PostgreSqlAvailable_UpdateIsRejected()
    {
        if (!ShouldRunDatabaseIntegrationTests())
        {
            return;
        }

        await using var context = CreateDatabaseContext();
        await context.Database.EnsureDeletedAsync();
        await context.Database.MigrateAsync();
        var tenant = new Tenant { Id = Guid.NewGuid(), Name = "Tech Pack Tenant" };
        context.Tenants.Add(tenant);
        var draft = new TechPackImportDraft
        {
            Id = Guid.NewGuid(),
            TenantId = tenant.Id,
            TechPackId = Guid.NewGuid(),
            OriginalFileName = "core-tee.csv",
            ContentType = "text/csv",
            DraftJson = "{}",
            Status = "APPROVED",
            SourceHashSha256 = new string('a', 64),
            ApprovedAtUtc = DateTimeOffset.UtcNow,
        };
        context.TechPackImportDrafts.Add(draft);
        await context.SaveChangesAsync();

        await Assert.ThrowsAsync<PostgresException>(
            () => context.Database.ExecuteSqlInterpolatedAsync(
                $"UPDATE tech_pack_import_drafts SET status = 'DRAFT' WHERE id = {draft.Id}"));
    }

    private static bool ShouldRunDatabaseIntegrationTests() =>
        string.Equals(
            Environment.GetEnvironmentVariable("SPEC_PROOF_RUN_DATABASE_INTEGRATION"),
            "1",
            StringComparison.Ordinal);

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

    private sealed class StaticTenantScope(Guid tenantId) : ITenantScope
    {
        public Guid? TenantId { get; } = tenantId;
    }
}
