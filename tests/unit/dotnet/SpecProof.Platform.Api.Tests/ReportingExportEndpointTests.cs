using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using Microsoft.Extensions.DependencyInjection;
using SpecProof.Contracts;
using SpecProof.Platform.Data;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class ReportingExportEndpointTests(PlatformApiFactory factory)
    : IClassFixture<PlatformApiFactory>
{
    [Fact]
    public async Task ExportInspectionsPdf_AuthenticatedAdmin_ReturnsTenantReportAttachment()
    {
        var tenantId = Guid.NewGuid();
        var inspection = new InspectionResultDto(
            Guid.NewGuid(),
            $"station-{Guid.NewGuid():N}",
            "camera-1",
            DateTimeOffset.Parse("2026-08-17T12:00:00Z"),
            [],
            InspectionStatus.Pass,
            new string('c', 64));
        await SeedInspectionAsync(tenantId, inspection);

        using var client = factory.CreateClient();
        await AuthenticateAdminAsync(client, tenantId);
        using var response = await client.GetAsync(
            new Uri("/api/v1/reports/inspections.pdf", UriKind.Relative));
        var document = Encoding.ASCII.GetString(await response.Content.ReadAsByteArrayAsync());

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("application/pdf", response.Content.Headers.ContentType?.MediaType);
        Assert.Equal(
            "specproof-inspections.pdf",
            response.Content.Headers.ContentDisposition?.FileNameStar);
        Assert.StartsWith("%PDF-1.4", document, StringComparison.Ordinal);
        Assert.Contains(inspection.StationId[..18], document, StringComparison.Ordinal);
    }

    private async Task SeedInspectionAsync(Guid tenantId, InspectionResultDto inspection)
    {
        await using var scope = factory.Services.CreateAsyncScope();
        var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
        database.InspectionRecords.Add(
            new InspectionRecord
            {
                Id = inspection.InspectionId,
                TenantId = tenantId,
                CaptureId = Guid.NewGuid(),
                StationId = Guid.NewGuid(),
                StationCode = inspection.StationId,
                OrderCode = "order-1",
                StyleCode = "style-1",
                SizeCode = "M",
                InspectionResultJson = JsonSerializer.Serialize(
                    inspection,
                    SpecProofJsonContext.Default.InspectionResultDto),
                Status = inspection.Status.ToString(),
                EvidenceRecordHash = inspection.EvidenceRecordHash,
                CapturedAtUtc = inspection.CapturedAtUtc,
                CreatedAtUtc = inspection.CapturedAtUtc,
                UpdatedAtUtc = inspection.CapturedAtUtc,
            });
        await database.SaveChangesAsync();
    }

    private static async Task AuthenticateAdminAsync(HttpClient client, Guid tenantId)
    {
        var tokenUri = new Uri(
            $"/api/v1/auth/dev-token?tenantId={tenantId}&subject=report-test&role=admin",
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
