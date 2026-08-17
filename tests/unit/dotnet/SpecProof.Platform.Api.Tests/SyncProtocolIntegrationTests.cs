using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using SpecProof.Platform.Api;
using SpecProof.Platform.Data;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class SyncProtocolIntegrationTests(PlatformApiFactory factory)
    : IClassFixture<PlatformApiFactory>
{
    [Fact]
    public async Task AcceptAsync_IdenticalReplay_PersistsOneEnvelopeAndAttemptCount()
    {
        var tenantId = Guid.NewGuid();
        var request = CreateRequest(Guid.NewGuid(), $"sync-{Guid.NewGuid():N}", 'a');

        await AcceptInNewScopeAsync(tenantId, request);
        await AcceptInNewScopeAsync(tenantId, request);

        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        var envelopes = await database.SyncEnvelopes
            .Where(envelope => envelope.TenantId == tenantId)
            .ToArrayAsync();
        var envelope = Assert.Single(envelopes);
        Assert.Equal("accepted", envelope.Status);
        Assert.Equal(2, envelope.Attempts);
        Assert.Null(envelope.ConflictJson);
    }

    [Fact]
    public async Task AcceptAsync_DifferentPayloadHash_PersistsConflictAcrossScopes()
    {
        var tenantId = Guid.NewGuid();
        var stationId = Guid.NewGuid();
        var idempotencyKey = $"sync-{Guid.NewGuid():N}";
        await AcceptInNewScopeAsync(tenantId, CreateRequest(stationId, idempotencyKey, 'a'));

        await AcceptInNewScopeAsync(tenantId, CreateRequest(stationId, idempotencyKey, 'b'));

        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        var envelope = await database.SyncEnvelopes.SingleAsync(candidate =>
            candidate.TenantId == tenantId && candidate.IdempotencyKey == idempotencyKey);
        Assert.Equal("conflict", envelope.Status);
        Assert.Equal(2, envelope.Attempts);
        Assert.Contains(new string('b', 64), envelope.ConflictJson, StringComparison.Ordinal);
    }

    [Fact]
    public async Task AcceptAsync_SameIdempotencyKeyAcrossTenants_PersistsSeparateEnvelopes()
    {
        var idempotencyKey = $"sync-{Guid.NewGuid():N}";
        await AcceptInNewScopeAsync(
            Guid.NewGuid(),
            CreateRequest(Guid.NewGuid(), idempotencyKey, 'a'));
        await AcceptInNewScopeAsync(
            Guid.NewGuid(),
            CreateRequest(Guid.NewGuid(), idempotencyKey, 'a'));

        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        Assert.Equal(
            2,
            await database.SyncEnvelopes.CountAsync(envelope =>
                envelope.IdempotencyKey == idempotencyKey));
    }

    private async Task AcceptInNewScopeAsync(Guid tenantId, SyncEnvelopeRequest request)
    {
        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        var service = scope.ServiceProvider.GetRequiredService<SyncProtocolService>();
        await service.AcceptAsync(database, tenantId, request, CancellationToken.None);
    }

    private static SyncEnvelopeRequest CreateRequest(
        Guid stationId,
        string idempotencyKey,
        char hashCharacter) =>
        new(
            stationId,
            idempotencyKey,
            "inspection",
            Guid.NewGuid(),
            "{}",
            new string(hashCharacter, 64));
}
