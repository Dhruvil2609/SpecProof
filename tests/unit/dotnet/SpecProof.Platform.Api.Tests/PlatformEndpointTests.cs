using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using SpecProof.Platform.Api;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class PlatformEndpointTests(WebApplicationFactory<PlatformApiAssemblyMarker> factory)
    : IClassFixture<WebApplicationFactory<PlatformApiAssemblyMarker>>
{
    [Fact]
    public async Task HealthEndpoint_AnonymousRequest_ReturnsUtcStatusAndSecurityHeaders()
    {
        using var client = factory.CreateClient();

        using var response = await client.GetAsync(new Uri("/healthz", UriKind.Relative));
        var payload = await response.Content.ReadFromJsonAsync<HealthResponse>();

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.NotNull(payload);
        Assert.Equal("ok", payload.Status);
        Assert.Equal(TimeSpan.Zero, payload.CheckedAtUtc.Offset);
        Assert.Equal("nosniff", response.Headers.GetValues("X-Content-Type-Options").Single());
        Assert.Equal("DENY", response.Headers.GetValues("X-Frame-Options").Single());
    }

    [Fact]
    public async Task ProtectedApiEndpoint_AnonymousRequest_ReturnsUnauthorized()
    {
        using var client = factory.CreateClient();

        using var response = await client.GetAsync(
            new Uri($"/api/v1/inspections/{Guid.NewGuid()}", UriKind.Relative));

        Assert.Equal(HttpStatusCode.Unauthorized, response.StatusCode);
    }

    [Fact]
    public async Task OpenApiEndpoint_ValidDevelopmentToken_ReturnsVersionedDocument()
    {
        using var client = factory.CreateClient();
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var tokenUri = new Uri(
            $"/api/v1/auth/dev-token?tenantId={tenantId}&subject=endpoint-test&role=admin",
            UriKind.Relative);
        using var tokenResponse = await client.GetAsync(tokenUri);
        var tokenPayload = await tokenResponse.Content.ReadFromJsonAsync<DevelopmentTokenResponse>();
        Assert.Equal(HttpStatusCode.OK, tokenResponse.StatusCode);
        Assert.NotNull(tokenPayload);

        client.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", tokenPayload.Token);
        using var response = await client.GetAsync(
            new Uri("/api/v1/openapi.json", UriKind.Relative));
        await using var stream = await response.Content.ReadAsStreamAsync();
        using var document = await JsonDocument.ParseAsync(stream);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("3.1.1", document.RootElement.GetProperty("openapi").GetString());
        Assert.True(document.RootElement.GetProperty("paths").TryGetProperty("/api/v1/inspections", out _));
    }

    private sealed record HealthResponse(string Status, DateTimeOffset CheckedAtUtc);

    private sealed record DevelopmentTokenResponse(string Token, DateTimeOffset ExpiresAtUtc);
}
