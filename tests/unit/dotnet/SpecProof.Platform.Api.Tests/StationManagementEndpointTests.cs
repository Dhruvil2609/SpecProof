using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using SpecProof.Contracts;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class StationManagementEndpointTests(PlatformApiFactory factory)
    : IClassFixture<PlatformApiFactory>
{
    [Fact]
    public async Task RegisterStation_ValidAdminRequest_IsIdempotentAndNormalizesCertificate()
    {
        using var client = factory.CreateClient();
        var tenantId = Guid.NewGuid();
        await AuthenticateAdminAsync(client, tenantId);
        var request = new RegisterStationRequest(
            tenantId,
            Guid.NewGuid(),
            $"station-{Guid.NewGuid():N}",
            new string('A', 64),
            "unit-test-public-key");

        using var firstResponse = await client.PostAsJsonAsync(
            new Uri("/api/v1/stations/register", UriKind.Relative),
            request,
            SpecProofJsonOptions.Canonical);
        var first = await firstResponse.Content.ReadFromJsonAsync<StationRegistrationDto>(
            SpecProofJsonOptions.Canonical);
        using var secondResponse = await client.PostAsJsonAsync(
            new Uri("/api/v1/stations/register", UriKind.Relative),
            request,
            SpecProofJsonOptions.Canonical);
        var second = await secondResponse.Content.ReadFromJsonAsync<StationRegistrationDto>(
            SpecProofJsonOptions.Canonical);

        Assert.Equal(HttpStatusCode.OK, firstResponse.StatusCode);
        Assert.Equal(HttpStatusCode.OK, secondResponse.StatusCode);
        Assert.NotNull(first);
        Assert.NotNull(second);
        Assert.Equal(first.StationId, second.StationId);
        Assert.Equal(new string('a', 64), first.CertificateThumbprintSha256);
        Assert.Equal(TimeSpan.Zero, first.RegisteredAtUtc.Offset);
    }

    [Fact]
    public async Task RegisterStation_CertificateAlreadyBoundToAnotherTenant_ReturnsConflict()
    {
        using var client = factory.CreateClient();
        var certificateThumbprint = new string('b', 64);
        var firstTenantId = Guid.NewGuid();
        await AuthenticateAdminAsync(client, firstTenantId);
        using var firstResponse = await client.PostAsJsonAsync(
            new Uri("/api/v1/stations/register", UriKind.Relative),
            CreateRequest(firstTenantId, certificateThumbprint),
            SpecProofJsonOptions.Canonical);
        Assert.Equal(HttpStatusCode.OK, firstResponse.StatusCode);

        var secondTenantId = Guid.NewGuid();
        await AuthenticateAdminAsync(client, secondTenantId);
        using var conflictingResponse = await client.PostAsJsonAsync(
            new Uri("/api/v1/stations/register", UriKind.Relative),
            CreateRequest(secondTenantId, certificateThumbprint),
            SpecProofJsonOptions.Canonical);

        Assert.Equal(HttpStatusCode.Conflict, conflictingResponse.StatusCode);
    }

    [Fact]
    public async Task RegisterStation_InvalidCertificateThumbprint_ReturnsValidationProblem()
    {
        using var client = factory.CreateClient();
        var tenantId = Guid.NewGuid();
        await AuthenticateAdminAsync(client, tenantId);

        using var response = await client.PostAsJsonAsync(
            new Uri("/api/v1/stations/register", UriKind.Relative),
            CreateRequest(tenantId, "invalid"),
            SpecProofJsonOptions.Canonical);

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
        Assert.Equal("application/problem+json", response.Content.Headers.ContentType?.MediaType);
    }

    private static RegisterStationRequest CreateRequest(Guid tenantId, string thumbprint) =>
        new(
            tenantId,
            Guid.NewGuid(),
            $"station-{Guid.NewGuid():N}",
            thumbprint,
            "unit-test-public-key");

    private static async Task AuthenticateAdminAsync(HttpClient client, Guid tenantId)
    {
        client.DefaultRequestHeaders.Authorization = null;
        var tokenUri = new Uri(
            $"/api/v1/auth/dev-token?tenantId={tenantId}&subject=station-test&role=admin",
            UriKind.Relative);
        using var response = await client.GetAsync(tokenUri);
        var payload = await response.Content.ReadFromJsonAsync<DevelopmentTokenResponse>();
        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(payload);
        client.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", payload.Token);
    }

    private sealed record DevelopmentTokenResponse(string Token, DateTimeOffset ExpiresAtUtc);
}
