using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.EntityFrameworkCore.Migrations.Operations;
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
}
