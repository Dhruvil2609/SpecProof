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
            .UseNpgsql("Host=localhost;Database=specproof_test;Username=Admin;Password=Admin@123")
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
            .UseNpgsql("Host=localhost;Database=specproof_test;Username=Admin;Password=Admin@123")
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

    private static bool ShouldRunDatabaseIntegrationTests() =>
        string.Equals(
            Environment.GetEnvironmentVariable("SPEC_PROOF_RUN_DATABASE_INTEGRATION"),
            "1",
            StringComparison.Ordinal);

    private static SpecProofDbContext CreateDatabaseContext()
    {
        var connectionString =
            Environment.GetEnvironmentVariable("SPEC_PROOF_TEST_DATABASE")
            ?? "Host=localhost;Database=specproof_test;Username=Admin;Password=Admin@123";
        var options = new DbContextOptionsBuilder<SpecProofDbContext>()
            .UseNpgsql(connectionString)
            .Options;
        return new SpecProofDbContext(options);
    }
}
