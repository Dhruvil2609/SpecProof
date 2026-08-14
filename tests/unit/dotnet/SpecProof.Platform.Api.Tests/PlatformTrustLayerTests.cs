using Microsoft.Extensions.Configuration;
using SpecProof.Contracts;
using SpecProof.Platform.Api;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class PlatformTrustLayerTests
{
    [Fact]
    public void SpecProofJwtValidator_ValidToken_ReturnsClaimsWithRolePermissions()
    {
        var validator = CreateJwtValidator();
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var token = validator.CreateToken(tenantId, "user-1", "admin", DateTimeOffset.UtcNow.AddMinutes(5));

        var principal = validator.Validate(token);

        Assert.NotNull(principal);
        Assert.Contains(principal.Claims, claim => claim.Type == "tenant_id" && claim.Value == tenantId.ToString());
        Assert.Contains(principal.Claims, claim => claim.Type == "permission" && claim.Value == PlatformPermissions.ManageStations);
    }

    [Fact]
    public void SpecProofJwtValidator_ExpiredToken_ReturnsNull()
    {
        var validator = CreateJwtValidator();
        var token = validator.CreateToken(
            Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            "user-1",
            "admin",
            DateTimeOffset.UtcNow.AddMinutes(-1));

        var principal = validator.Validate(token);

        Assert.Null(principal);
    }

    [Fact]
    public void PlatformPermissions_OperatorRole_DoesNotIncludeAdminStationManagement()
    {
        var permissions = PlatformPermissions.RolePermissions["operator"];

        Assert.DoesNotContain(PlatformPermissions.ManageStations, permissions);
        Assert.Contains(PlatformPermissions.CaptureInspections, permissions);
        Assert.DoesNotContain(PlatformPermissions.ManageSpecs, permissions);
    }

    [Fact]
    public async Task TechPackImportGateway_ForwardsMultipartAndValidationWithoutMappingLogic()
    {
        var handler = new RecordingHandler();
        var client = new HttpClient(handler) { BaseAddress = new Uri("http://measurement/") };
        var gateway = new TechPackImportGateway(client);

        await gateway.ImportAsync(
            new MemoryStream("pom,size,target_mm\nChest,M,500"u8.ToArray()),
            "tech-pack.csv",
            "text/csv",
            Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            1,
            "Brand",
            "TEE-1",
            "t_shirt",
            CancellationToken.None);
        using var document = System.Text.Json.JsonDocument.Parse(
            """{"approved":true,"imported_poms":[]}""");
        await gateway.ValidateAsync(document.RootElement, "M", CancellationToken.None);

        Assert.Equal(
            ["v1/tech-packs/import", "v1/tech-packs/validate"],
            handler.RequestPaths);
        Assert.Contains("tech-pack.csv", handler.RequestBodies[0], StringComparison.Ordinal);
        Assert.Contains("\"sizeCode\":\"M\"", handler.RequestBodies[1], StringComparison.Ordinal);
    }

    [Fact]
    public void StationPreviewFrame_Create_ReturnsDeterministicBrowserPayload()
    {
        var capturedAtUtc = DateTimeOffset.Parse("2026-08-12T10:00:00Z");

        var frame = StationPreviewFrame.Create(7, capturedAtUtc);

        Assert.Equal(7, frame.Sequence);
        Assert.Equal(capturedAtUtc, frame.CapturedAtUtc);
        Assert.NotEmpty(Convert.FromBase64String(frame.ColorJpegBase64));
        Assert.NotEmpty(Convert.FromBase64String(frame.DepthPngBase64));
    }

    [Fact]
    public async Task InMemoryEvidenceAssetReader_DoesNotCrossTenantBoundary()
    {
        var reader = new InMemoryEvidenceAssetReader();
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var otherTenantId = Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
        var bucket = TenantObjectStorageNamespace.BuildBucketName(tenantId);
        var key = $"{tenantId:N}/station/capture.png";
        reader.Add(tenantId, bucket, key, [1, 2, 3]);

        var asset = await reader.ReadAsync(tenantId, bucket, key, CancellationToken.None);
        var crossTenant = await reader.ReadAsync(otherTenantId, bucket, key, CancellationToken.None);

        Assert.NotNull(asset);
        Assert.Null(crossTenant);
    }

    [Fact]
    public void EvidenceSignatureService_TamperedEvidence_ReturnsFalse()
    {
        var service = CreateSignatureService();
        const string evidenceJson = "{\"inspectionId\":\"i-1\",\"status\":\"PASS\"}";
        var signature = service.Sign(evidenceJson);

        var verified = service.Verify("{\"inspectionId\":\"i-1\",\"status\":\"FAIL\"}", signature.SignatureValueBase64);

        Assert.False(verified);
    }

    [Fact]
    public void EvidenceHashChain_PreviousHashChangesRecordHash()
    {
        const string evidenceJson = "{\"inspectionId\":\"i-1\",\"status\":\"PASS\"}";

        var first = EvidenceHashChain.ComputeRecordHash(evidenceJson, null);
        var second = EvidenceHashChain.ComputeRecordHash(evidenceJson, first);

        Assert.NotEqual(first, second);
    }

    [Fact]
    public void ReportingExportService_ToInspectionCsv_EscapesStationValues()
    {
        var service = new ReportingExportService();
        var inspection = new InspectionResultDto(
            Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            "station,quoted",
            "camera-1",
            DateTimeOffset.Parse("2026-08-06T00:00:00Z"),
            [],
            InspectionStatus.Pass,
            new string('a', 64));

        var csv = service.ToInspectionCsv([inspection]);

        Assert.Contains("\"station,quoted\"", csv, StringComparison.Ordinal);
    }

    [Fact]
    public void TenantObjectStorageNamespace_BuildObjectKey_UsesTenantPrefix()
    {
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var stationId = Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
        var captureId = Guid.Parse("cccccccc-cccc-cccc-cccc-cccccccccccc");

        var key = TenantObjectStorageNamespace.BuildObjectKey(tenantId, stationId, captureId, ".spcapture");

        Assert.StartsWith($"{tenantId:N}/{stationId:N}/", key, StringComparison.Ordinal);
    }

    private static SpecProofJwtValidator CreateJwtValidator() =>
        new(CreateConfiguration());

    private static EvidenceSignatureService CreateSignatureService() =>
        new(CreateConfiguration());

    private static IConfiguration CreateConfiguration() =>
        new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["Authentication:JwtSecret"] = "unit-test-jwt-secret",
                    ["Trust:SigningKeyId"] = "unit-test-key",
                    ["Trust:SigningSecret"] = "unit-test-evidence-secret",
                })
            .Build();

    private sealed class RecordingHandler : HttpMessageHandler
    {
        public List<string> RequestPaths { get; } = [];

        public List<string> RequestBodies { get; } = [];

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken)
        {
            RequestPaths.Add(request.RequestUri?.PathAndQuery.TrimStart('/') ?? string.Empty);
            RequestBodies.Add(await request.Content!.ReadAsStringAsync(cancellationToken));
            return new HttpResponseMessage(System.Net.HttpStatusCode.OK)
            {
                Content = new StringContent("{\"approved\":true}"),
            };
        }
    }
}
