using System.Security.Claims;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.FileProviders;
using SpecProof.Contracts;
using SpecProof.Platform.Api;
using SpecProof.Platform.Data;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class PlatformTrustLayerTests
{
    [Fact]
    public void DeviceCertificateThumbprint_Compute_ReturnsCanonicalSha256()
    {
        using var certificate = CreateCertificate();

        var thumbprint = DeviceCertificateThumbprint.Compute(certificate);

        Assert.Equal(64, thumbprint.Length);
        Assert.Equal(thumbprint.ToLowerInvariant(), thumbprint);
        Assert.Equal(
            Convert.ToHexString(SHA256.HashData(certificate.RawData)).ToLowerInvariant(),
            thumbprint);
    }

    [Fact]
    public async Task DeviceCertificateAuthenticationMiddleware_ValidCertificate_CreatesStationPrincipal()
    {
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var stationId = Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
        using var certificate = CreateCertificate();
        var context = new DefaultHttpContext();
        context.Connection.ClientCertificate = certificate;
        var authenticator = new StubDeviceCertificateAuthenticator(
            new DeviceAuthenticationResult(Guid.NewGuid(), tenantId, stationId));
        var nextCalled = false;
        var middleware = new DeviceCertificateAuthenticationMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });
        await using var database = CreateDatabase();

        await middleware.InvokeAsync(context, authenticator, database);

        Assert.True(nextCalled);
        Assert.True(context.User.Identity?.IsAuthenticated);
        Assert.Contains(context.User.Claims, claim => claim.Type == "tenant_id" && claim.Value == tenantId.ToString());
        Assert.Contains(context.User.Claims, claim => claim.Type == "station_id" && claim.Value == stationId.ToString());
        Assert.Contains(
            context.User.Claims,
            claim => claim.Type == "permission" && claim.Value == PlatformPermissions.SyncWrite);
    }

    [Fact]
    public async Task DeviceCertificateAuthenticationMiddleware_UnknownCertificate_ReturnsUnauthorized()
    {
        using var certificate = CreateCertificate();
        var context = new DefaultHttpContext();
        context.Connection.ClientCertificate = certificate;
        var authenticator = new StubDeviceCertificateAuthenticator(null);
        var nextCalled = false;
        var middleware = new DeviceCertificateAuthenticationMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });
        await using var database = CreateDatabase();

        await middleware.InvokeAsync(context, authenticator, database);

        Assert.False(nextCalled);
        Assert.Equal(StatusCodes.Status401Unauthorized, context.Response.StatusCode);
    }

    [Fact]
    public void DeviceCertificatePolicy_ClientAuthenticationRequired_RejectsCertificateWithoutEku()
    {
        using var certificate = CreateCertificate();
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["Security:DeviceCertificates:RequireClientAuthenticationEku"] = "true",
                })
            .Build();
        var policy = new DeviceCertificatePolicy(configuration);

        Assert.False(policy.IsAccepted(certificate));
    }

    [Fact]
    public async Task ApiAuthenticationBoundaryMiddleware_AnonymousApiRequest_ReturnsUnauthorized()
    {
        var context = new DefaultHttpContext();
        context.Request.Path = "/api/v1/inspections";
        var nextCalled = false;
        var middleware = new ApiAuthenticationBoundaryMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });

        await middleware.InvokeAsync(context, new StubHostEnvironment("Production"));

        Assert.False(nextCalled);
        Assert.Equal(StatusCodes.Status401Unauthorized, context.Response.StatusCode);
    }

    [Fact]
    public async Task SecurityHeadersMiddleware_ResponseStarting_AddsRestrictiveHeaders()
    {
        var context = new DefaultHttpContext();
        context.Response.Body = new MemoryStream();
        var middleware = new SecurityHeadersMiddleware(
            async httpContext => await httpContext.Response.StartAsync());

        await middleware.InvokeAsync(context);

        Assert.Equal("nosniff", context.Response.Headers.XContentTypeOptions);
        Assert.Equal("DENY", context.Response.Headers.XFrameOptions);
        Assert.Contains("default-src 'none'", context.Response.Headers.ContentSecurityPolicy.ToString());
    }

    [Fact]
    public void ProductionSecurityPolicy_MissingProtectedConfiguration_FailsClosed()
    {
        var configuration = new ConfigurationBuilder().Build();

        var exception = Assert.Throws<InvalidOperationException>(() =>
            ProductionSecurityPolicy.Validate(
                new StubHostEnvironment("Production"),
                configuration));

        Assert.Contains("Authentication:JwtSecret", exception.Message, StringComparison.Ordinal);
        Assert.Contains("RequireHttps", exception.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void ProductionSecurityPolicy_CompleteProtectedConfiguration_Passes()
    {
        var configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(
                new Dictionary<string, string?>
                {
                    ["Authentication:JwtSecret"] = new string('a', 40),
                    ["Authentication:Issuer"] = "specproof-platform",
                    ["Authentication:Audience"] = "specproof-clients",
                    ["Trust:SigningSecret"] = new string('b', 40),
                    ["Trust:SigningKeyId"] = "production-key-v1",
                    ["Security:RequireHttps"] = "true",
                    ["Security:DeviceCertificates:RequireChainTrust"] = "true",
                    ["Security:DeviceCertificates:RequireClientAuthenticationEku"] = "true",
                    ["Security:DeviceCertificates:AllowedRootCertificateSha256:0"] = new string('c', 64),
                })
            .Build();

        ProductionSecurityPolicy.Validate(new StubHostEnvironment("Production"), configuration);
    }

    [Fact]
    public void CaptureUploadSecurity_ProductionUnencryptedUpload_RejectsRequest()
    {
        Assert.False(CaptureUploadSecurity.IsAccepted(production: true, encrypted: false));
        Assert.True(CaptureUploadSecurity.IsAccepted(production: true, encrypted: true));
        Assert.True(CaptureUploadSecurity.IsAccepted(production: false, encrypted: false));
    }

    [Fact]
    public async Task DeviceStationRequestFilter_MismatchedStation_ReturnsForbidden()
    {
        var context = new DefaultHttpContext
        {
            User = CreateStationPrincipal("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        };
        var request = new SyncEnvelopeRequest(
            Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            "key",
            "inspection",
            Guid.NewGuid(),
            "{}",
            new string('a', 64));
        var invocation = new DefaultEndpointFilterInvocationContext(context, request);
        var nextCalled = false;
        var filter = new DeviceStationRequestFilter<SyncEnvelopeRequest>();

        var result = await filter.InvokeAsync(
            invocation,
            _ =>
            {
                nextCalled = true;
                return ValueTask.FromResult<object?>(Results.Ok());
            });

        Assert.False(nextCalled);
        Assert.IsType<ForbidHttpResult>(result);
    }

    [Fact]
    public async Task DeviceStationRouteFilter_MismatchedStation_ReturnsForbidden()
    {
        var context = new DefaultHttpContext
        {
            User = CreateStationPrincipal("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        };
        context.Request.RouteValues["stationId"] = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
        var invocation = new DefaultEndpointFilterInvocationContext(context);
        var nextCalled = false;
        var filter = new DeviceStationRouteFilter();

        var result = await filter.InvokeAsync(
            invocation,
            _ =>
            {
                nextCalled = true;
                return ValueTask.FromResult<object?>(Results.Ok());
            });

        Assert.False(nextCalled);
        Assert.IsType<ForbidHttpResult>(result);
    }

    [Fact]
    public void RotateDeviceCertificateRequestValidator_InvalidWindowAndThumbprint_ReturnsErrors()
    {
        var now = DateTimeOffset.UtcNow;
        var request = new RotateDeviceCertificateRequest("not-a-thumbprint", "public-key", now, now.AddMinutes(-1));
        var validator = new RotateDeviceCertificateRequestValidator();

        var result = validator.Validate(request);

        Assert.False(result.IsValid);
        Assert.Contains(result.Errors, error => error.PropertyName == nameof(request.CertificateThumbprintSha256));
        Assert.Contains(result.Errors, error => error.PropertyName == nameof(request.NotBeforeUtc));
    }

    [Fact]
    public void DeviceCertificateRotationService_Rotate_RetiresOldIdentityAndCreatesAuditEvent()
    {
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var stationId = Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb");
        var oldIdentity = new DeviceIdentity
        {
            Id = Guid.NewGuid(),
            TenantId = tenantId,
            StationId = stationId,
            CertificateThumbprintSha256 = new string('a', 64),
            PublicKeyPem = "old-public-key",
            NotBeforeUtc = DateTimeOffset.Parse("2026-01-01T00:00:00Z"),
            ExpiresAtUtc = DateTimeOffset.Parse("2026-12-31T00:00:00Z"),
            Active = true,
        };
        var rotatedAtUtc = DateTimeOffset.Parse("2026-08-14T18:50:00Z");
        var request = new RotateDeviceCertificateRequest(
            new string('B', 64),
            "new-public-key",
            rotatedAtUtc,
            rotatedAtUtc.AddDays(90));
        var service = new DeviceCertificateRotationService();

        var rotation = service.Rotate(tenantId, stationId, request, [oldIdentity], rotatedAtUtc);

        Assert.False(oldIdentity.Active);
        Assert.Equal(rotatedAtUtc, oldIdentity.RotatedAtUtc);
        Assert.True(rotation.Replacement.Active);
        Assert.Equal(new string('b', 64), rotation.Replacement.CertificateThumbprintSha256);
        Assert.Equal("station.certificate_rotated", rotation.AuditEvent.EventType);
        Assert.Contains(oldIdentity.Id.ToString(), rotation.AuditEvent.PayloadJson, StringComparison.Ordinal);
    }

    [Fact]
    public async Task TenantResolutionMiddleware_AuthenticatedClaim_SetsTenantScope()
    {
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var context = new DefaultHttpContext
        {
            User = CreatePrincipal(tenantId.ToString()),
        };
        var tenantScope = new TenantScopeAccessor();
        var nextCalled = false;
        var middleware = new TenantResolutionMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });

        await middleware.InvokeAsync(context, tenantScope);

        Assert.True(nextCalled);
        Assert.Equal(tenantId, tenantScope.TenantId);
    }

    [Fact]
    public async Task TenantResolutionMiddleware_MismatchedTenantHeader_ReturnsForbidden()
    {
        var context = new DefaultHttpContext
        {
            User = CreatePrincipal("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        };
        context.Request.Headers[TenantResolutionMiddleware.TenantHeaderName] =
            "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
        var tenantScope = new TenantScopeAccessor();
        var nextCalled = false;
        var middleware = new TenantResolutionMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });

        await middleware.InvokeAsync(context, tenantScope);

        Assert.False(nextCalled);
        Assert.Equal(StatusCodes.Status403Forbidden, context.Response.StatusCode);
        Assert.Null(tenantScope.TenantId);
    }

    [Fact]
    public async Task TenantResolutionMiddleware_MissingTenantClaim_ReturnsForbidden()
    {
        var context = new DefaultHttpContext
        {
            User = CreatePrincipal(null),
        };
        var tenantScope = new TenantScopeAccessor();
        var nextCalled = false;
        var middleware = new TenantResolutionMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });

        await middleware.InvokeAsync(context, tenantScope);

        Assert.False(nextCalled);
        Assert.Equal(StatusCodes.Status403Forbidden, context.Response.StatusCode);
        Assert.Null(tenantScope.TenantId);
    }

    [Fact]
    public async Task TenantResolutionMiddleware_AnonymousTenantHeader_DoesNotEstablishTenantScope()
    {
        var context = new DefaultHttpContext();
        context.Request.Headers[TenantResolutionMiddleware.TenantHeaderName] =
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
        var tenantScope = new TenantScopeAccessor();
        var nextCalled = false;
        var middleware = new TenantResolutionMiddleware(
            _ =>
            {
                nextCalled = true;
                return Task.CompletedTask;
            });

        await middleware.InvokeAsync(context, tenantScope);

        Assert.True(nextCalled);
        Assert.Null(tenantScope.TenantId);
    }

    [Fact]
    public async Task TenantBoundRequestFilter_MismatchedRequestTenant_ReturnsForbidden()
    {
        var tenantScope = new TenantScopeAccessor
        {
            TenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        };
        var request = new WebhookSubscriptionRequest(
            Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            "https://example.test/webhook",
            ["inspection.completed"],
            "secret");
        var context = new DefaultEndpointFilterInvocationContext(new DefaultHttpContext(), request);
        var nextCalled = false;
        var filter = new TenantBoundRequestFilter<WebhookSubscriptionRequest>(tenantScope);

        var result = await filter.InvokeAsync(
            context,
            _ =>
            {
                nextCalled = true;
                return ValueTask.FromResult<object?>(Results.Accepted());
            });

        Assert.False(nextCalled);
        Assert.IsType<ForbidHttpResult>(result);
    }

    [Fact]
    public async Task TenantBoundRequestFilter_MatchingRequestTenant_InvokesEndpoint()
    {
        var tenantId = Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
        var tenantScope = new TenantScopeAccessor { TenantId = tenantId };
        var request = new WebhookSubscriptionRequest(
            tenantId,
            "https://example.test/webhook",
            ["inspection.completed"],
            "secret");
        var context = new DefaultEndpointFilterInvocationContext(new DefaultHttpContext(), request);
        var nextCalled = false;
        var filter = new TenantBoundRequestFilter<WebhookSubscriptionRequest>(tenantScope);

        var result = await filter.InvokeAsync(
            context,
            _ =>
            {
                nextCalled = true;
                return ValueTask.FromResult<object?>(Results.Accepted());
            });

        Assert.True(nextCalled);
        Assert.IsType<Accepted>(result);
    }

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
    public void SpecProofJwtValidator_MalformedToken_ReturnsNull()
    {
        var validator = CreateJwtValidator();

        Assert.Null(validator.Validate("not-a.valid.jwt"));
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
    public void ReportingExportService_ToInspectionPdf_WritesValidMultiPageDocument()
    {
        var service = new ReportingExportService();
        var inspections = Enumerable.Range(0, 31)
            .Select(index => new InspectionResultDto(
                Guid.Parse($"bbbbbbbb-bbbb-bbbb-bbbb-{index:D12}"),
                $"station-{index}",
                "camera-1",
                DateTimeOffset.Parse("2026-08-06T00:00:00Z").AddMinutes(index),
                [],
                InspectionStatus.Pass,
                new string('a', 64)))
            .ToArray();

        var pdf = service.ToInspectionPdf(inspections);
        var document = Encoding.ASCII.GetString(pdf);

        Assert.StartsWith("%PDF-1.4", document, StringComparison.Ordinal);
        Assert.Contains("/Type /Pages", document, StringComparison.Ordinal);
        Assert.Contains("/Count 2", document, StringComparison.Ordinal);
        Assert.Contains("SpecProof Inspection Report", document, StringComparison.Ordinal);
        Assert.Contains("station-30", document, StringComparison.Ordinal);
        Assert.EndsWith($"%%EOF{Environment.NewLine}", document, StringComparison.Ordinal);
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
                    ["Authentication:Issuer"] = "unit-test-issuer",
                    ["Authentication:Audience"] = "unit-test-audience",
                    ["Trust:SigningKeyId"] = "unit-test-key",
                    ["Trust:SigningSecret"] = "unit-test-evidence-secret",
                })
            .Build();

    private static ClaimsPrincipal CreatePrincipal(string? tenantId)
    {
        var claims = tenantId is null ? [] : new[] { new Claim("tenant_id", tenantId) };
        return new ClaimsPrincipal(new ClaimsIdentity(claims, "UnitTest"));
    }

    private static ClaimsPrincipal CreateStationPrincipal(string stationId) =>
        new(
            new ClaimsIdentity(
                [new Claim("station_id", stationId)],
                "SpecProofDeviceCertificate"));

    private static SpecProofDbContext CreateDatabase() =>
        new(new DbContextOptionsBuilder<SpecProofDbContext>().Options);

    private static X509Certificate2 CreateCertificate()
    {
        using var key = RSA.Create(2048);
        var request = new CertificateRequest(
            "CN=SpecProof Unit Test Station",
            key,
            HashAlgorithmName.SHA256,
            RSASignaturePadding.Pkcs1);
        return request.CreateSelfSigned(
            DateTimeOffset.UtcNow.AddMinutes(-1),
            DateTimeOffset.UtcNow.AddMinutes(5));
    }

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

    private sealed class StubDeviceCertificateAuthenticator(DeviceAuthenticationResult? result)
        : IDeviceCertificateAuthenticator
    {
        public Task<DeviceAuthenticationResult?> AuthenticateAsync(
            X509Certificate2 certificate,
            SpecProofDbContext database,
            CancellationToken cancellationToken) =>
            Task.FromResult(result);
    }

    private sealed class StubHostEnvironment(string environmentName) : IWebHostEnvironment
    {
        public string ApplicationName { get; set; } = "SpecProof.Platform.Api.Tests";

        public IFileProvider WebRootFileProvider { get; set; } = new NullFileProvider();

        public string WebRootPath { get; set; } = string.Empty;

        public string EnvironmentName { get; set; } = environmentName;

        public string ContentRootPath { get; set; } = string.Empty;

        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }
}
