using System.Globalization;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using FluentValidation;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.EntityFrameworkCore;
using SpecProof.Contracts;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api;

public static class PlatformPermissions
{
    public const string ReadInspections = "inspections.read";
    public const string ManageStations = "stations.manage";
    public const string ReportStationHealth = "stations.health.write";
    public const string VerifyEvidence = "evidence.verify";
    public const string SyncWrite = "sync.write";
    public const string ExportReports = "reports.export";
    public const string ManageBackgroundJobs = "jobs.manage";
    public const string CaptureInspections = "inspections.capture";
    public const string ReviewInspections = "inspections.review";
    public const string ManageSpecs = "specs.manage";
    public const string ManageUsers = "users.manage";
    public const string ReadReports = "reports.read";

    public static readonly IReadOnlyDictionary<string, string[]> RolePermissions =
        new Dictionary<string, string[]>(StringComparer.OrdinalIgnoreCase)
        {
            ["admin"] =
            [
                ReadInspections,
                ManageStations,
                ReportStationHealth,
                VerifyEvidence,
                SyncWrite,
                ExportReports,
                ManageBackgroundJobs,
                CaptureInspections,
                ReviewInspections,
                ManageSpecs,
                ManageUsers,
                ReadReports,
            ],
            ["operator"] =
            [
                ReadInspections,
                ReportStationHealth,
                SyncWrite,
                CaptureInspections,
            ],
            ["station"] =
            [
                ReportStationHealth,
                SyncWrite,
                CaptureInspections,
            ],
            ["auditor"] =
            [
                ReadInspections,
                VerifyEvidence,
                ExportReports,
                ReviewInspections,
                ReadReports,
            ],
        };
}

public sealed class TenantScopeAccessor : ITenantScope
{
    public Guid? TenantId { get; set; }

    public bool Matches(Guid tenantId) => TenantId == tenantId;
}

public sealed class TenantResolutionMiddleware(RequestDelegate next)
{
    public const string TenantHeaderName = "X-SpecProof-Tenant-Id";

    public async Task InvokeAsync(HttpContext context, TenantScopeAccessor tenantScope)
    {
        if (context.User.Identity?.IsAuthenticated != true)
        {
            await next(context);
            return;
        }

        if (!Guid.TryParse(context.User.FindFirstValue("tenant_id"), out var claimTenantId))
        {
            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            return;
        }

        if (context.Request.Headers.TryGetValue(TenantHeaderName, out var tenantHeader)
            && (!Guid.TryParse(tenantHeader.ToString(), out var headerTenantId)
                || headerTenantId != claimTenantId))
        {
            context.Response.StatusCode = StatusCodes.Status403Forbidden;
            return;
        }

        tenantScope.TenantId = claimTenantId;
        await next(context);
    }
}

public sealed class JwtAuthenticationMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext context, SpecProofJwtValidator validator)
    {
        var authorization = context.Request.Headers.Authorization.ToString();
        if (authorization.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            var principal = validator.Validate(authorization["Bearer ".Length..].Trim());
            if (principal is null)
            {
                context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                return;
            }

            context.User = principal;
        }

        await next(context);
    }
}

public sealed class ApiAuthenticationBoundaryMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext context, IWebHostEnvironment environment)
    {
        var isApiRequest = context.Request.Path.StartsWithSegments("/api/v1");
        var isDevelopmentToken = context.Request.Path.Equals("/api/v1/auth/dev-token")
            && (environment.IsDevelopment() || environment.IsEnvironment("Test"));
        if (isApiRequest
            && !isDevelopmentToken
            && context.User.Identity?.IsAuthenticated != true)
        {
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            return;
        }

        await next(context);
    }
}

public sealed class SecurityHeadersMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(HttpContext context)
    {
        context.Response.Headers.XContentTypeOptions = "nosniff";
        context.Response.Headers.XFrameOptions = "DENY";
        context.Response.Headers["Referrer-Policy"] = "no-referrer";
        context.Response.Headers.ContentSecurityPolicy = "default-src 'none'; frame-ancestors 'none'";
        context.Response.Headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()";
        await next(context);
    }
}

public sealed record DeviceAuthenticationResult(Guid IdentityId, Guid TenantId, Guid StationId);

public interface IDeviceCertificateAuthenticator
{
    Task<DeviceAuthenticationResult?> AuthenticateAsync(
        X509Certificate2 certificate,
        SpecProofDbContext database,
        CancellationToken cancellationToken);
}

public interface IDeviceCertificatePolicy
{
    bool IsAccepted(X509Certificate2 certificate);
}

public sealed class DeviceCertificatePolicy(IConfiguration configuration) : IDeviceCertificatePolicy
{
    public const string ClientAuthenticationEnhancedKeyUsageOid = "1.3.6.1.5.5.7.3.2";

    public bool IsAccepted(X509Certificate2 certificate)
    {
        var nowUtc = DateTimeOffset.UtcNow;
        if (certificate.NotBefore.ToUniversalTime() > nowUtc.UtcDateTime
            || certificate.NotAfter.ToUniversalTime() <= nowUtc.UtcDateTime)
        {
            return false;
        }

        var requireClientAuthentication = configuration.GetValue(
            "Security:DeviceCertificates:RequireClientAuthenticationEku",
            false);
        if (requireClientAuthentication && !HasClientAuthenticationUsage(certificate))
        {
            return false;
        }

        if (!configuration.GetValue("Security:DeviceCertificates:RequireChainTrust", false))
        {
            return true;
        }

        using var chain = new X509Chain();
        chain.ChainPolicy.RevocationFlag = X509RevocationFlag.ExcludeRoot;
        chain.ChainPolicy.RevocationMode = ParseRevocationMode(
            configuration["Security:DeviceCertificates:RevocationMode"]);
        chain.ChainPolicy.VerificationFlags = X509VerificationFlags.NoFlag;
        if (!chain.Build(certificate) || chain.ChainElements.Count == 0)
        {
            return false;
        }

        var allowedRoots = configuration
            .GetSection("Security:DeviceCertificates:AllowedRootCertificateSha256")
            .Get<string[]>() ?? [];
        var root = chain.ChainElements[^1].Certificate;
        var rootSha256 = DeviceCertificateThumbprint.Compute(root);
        return allowedRoots.Any(allowed =>
            string.Equals(DeviceCertificateThumbprint.Normalize(allowed), rootSha256, StringComparison.Ordinal));
    }

    private static bool HasClientAuthenticationUsage(X509Certificate2 certificate) =>
        certificate.Extensions
            .OfType<X509EnhancedKeyUsageExtension>()
            .Any(extension => extension.EnhancedKeyUsages
                .OfType<Oid>()
                .Any(usage => usage.Value == ClientAuthenticationEnhancedKeyUsageOid));

    private static X509RevocationMode ParseRevocationMode(string? configured) =>
        Enum.TryParse<X509RevocationMode>(configured, true, out var mode)
            ? mode
            : X509RevocationMode.Online;
}

public sealed class DeviceCertificateAuthenticator(IDeviceCertificatePolicy certificatePolicy)
    : IDeviceCertificateAuthenticator
{
    public async Task<DeviceAuthenticationResult?> AuthenticateAsync(
        X509Certificate2 certificate,
        SpecProofDbContext database,
        CancellationToken cancellationToken)
    {
        if (!certificatePolicy.IsAccepted(certificate))
        {
            return null;
        }

        var thumbprint = DeviceCertificateThumbprint.Compute(certificate);
        var now = DateTimeOffset.UtcNow;
        var matches = await database.DeviceIdentities
            .IgnoreQueryFilters()
            .AsNoTracking()
            .Where(identity =>
                identity.Active
                && identity.NotBeforeUtc <= now
                && identity.ExpiresAtUtc > now
                && identity.CertificateThumbprintSha256.ToLower() == thumbprint)
            .Select(identity => new DeviceAuthenticationResult(identity.Id, identity.TenantId, identity.StationId))
            .Take(2)
            .ToArrayAsync(cancellationToken);
        return matches.Length == 1 ? matches[0] : null;
    }
}

public sealed class DeviceCertificateAuthenticationMiddleware(RequestDelegate next)
{
    public async Task InvokeAsync(
        HttpContext context,
        IDeviceCertificateAuthenticator authenticator,
        SpecProofDbContext database)
    {
        if (context.User.Identity?.IsAuthenticated == true)
        {
            await next(context);
            return;
        }

        var certificate = await context.Connection.GetClientCertificateAsync(context.RequestAborted);
        if (certificate is null)
        {
            await next(context);
            return;
        }

        var identity = await authenticator.AuthenticateAsync(certificate, database, context.RequestAborted);
        if (identity is null)
        {
            context.Response.StatusCode = StatusCodes.Status401Unauthorized;
            return;
        }

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, identity.IdentityId.ToString("D", CultureInfo.InvariantCulture)),
            new("tenant_id", identity.TenantId.ToString("D", CultureInfo.InvariantCulture)),
            new("station_id", identity.StationId.ToString("D", CultureInfo.InvariantCulture)),
            new(ClaimTypes.Role, "station"),
        };
        claims.AddRange(
            PlatformPermissions.RolePermissions["station"]
                .Select(permission => new Claim("permission", permission)));
        context.User = new ClaimsPrincipal(new ClaimsIdentity(claims, "SpecProofDeviceCertificate"));
        await next(context);
    }
}

public static class DeviceCertificateThumbprint
{
    public static string Compute(X509Certificate2 certificate) =>
        Convert.ToHexString(SHA256.HashData(certificate.RawData)).ToLowerInvariant();

    public static string Normalize(string thumbprint) => thumbprint.Trim().ToLowerInvariant();
}

public sealed record DeviceCertificateRotation(DeviceIdentity Replacement, AuditEvent AuditEvent);

public sealed class DeviceCertificateRotationService
{
    public DeviceCertificateRotation Rotate(
        Guid tenantId,
        Guid stationId,
        RotateDeviceCertificateRequest request,
        IReadOnlyCollection<DeviceIdentity> activeIdentities,
        DateTimeOffset rotatedAtUtc)
    {
        foreach (var identity in activeIdentities)
        {
            identity.Active = false;
            identity.RotatedAtUtc = rotatedAtUtc;
            identity.UpdatedAtUtc = rotatedAtUtc;
        }

        var replacement = new DeviceIdentity
        {
            Id = Guid.NewGuid(),
            TenantId = tenantId,
            StationId = stationId,
            CertificateThumbprintSha256 = DeviceCertificateThumbprint.Normalize(
                request.CertificateThumbprintSha256),
            PublicKeyPem = request.PublicKeyPem,
            NotBeforeUtc = request.NotBeforeUtc,
            ExpiresAtUtc = request.ExpiresAtUtc,
            Active = true,
        };
        var auditEvent = new AuditEvent
        {
            Id = Guid.NewGuid(),
            TenantId = tenantId,
            EventType = "station.certificate_rotated",
            EntityType = "station",
            EntityId = stationId,
            PayloadJson = JsonSerializer.Serialize(
                new
                {
                    replacement.Id,
                    replacement.CertificateThumbprintSha256,
                    replacement.NotBeforeUtc,
                    replacement.ExpiresAtUtc,
                    RetiredIdentityIds = activeIdentities.Select(identity => identity.Id),
                },
                SpecProofJsonOptions.Canonical),
            OccurredAtUtc = rotatedAtUtc,
        };
        return new DeviceCertificateRotation(replacement, auditEvent);
    }
}

public sealed class PermissionEndpointFilter(string permission) : IEndpointFilter
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var user = context.HttpContext.User;
        if (user.Identity?.IsAuthenticated != true)
        {
            return Results.Unauthorized();
        }

        if (!user.Claims.Any(claim => claim.Type == "permission" && claim.Value == permission))
        {
            return Results.Forbid();
        }

        return await next(context);
    }
}

public interface ITenantBoundRequest
{
    Guid TenantId { get; }
}

public interface IStationBoundRequest
{
    Guid StationId { get; }
}

public sealed class TenantBoundRequestFilter<TRequest>(TenantScopeAccessor tenantScope) : IEndpointFilter
    where TRequest : class, ITenantBoundRequest
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var request = context.Arguments.OfType<TRequest>().FirstOrDefault();
        if (request is null || !tenantScope.Matches(request.TenantId))
        {
            return Results.Forbid();
        }

        return await next(context);
    }
}

public sealed class DeviceStationRequestFilter<TRequest> : IEndpointFilter
    where TRequest : class, IStationBoundRequest
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var stationClaim = context.HttpContext.User.FindFirstValue("station_id");
        if (stationClaim is null)
        {
            return await next(context);
        }

        var request = context.Arguments.OfType<TRequest>().FirstOrDefault();
        if (!Guid.TryParse(stationClaim, out var stationId)
            || request is null
            || request.StationId != stationId)
        {
            return Results.Forbid();
        }

        return await next(context);
    }
}

public sealed class DeviceStationRouteFilter : IEndpointFilter
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var stationClaim = context.HttpContext.User.FindFirstValue("station_id");
        if (stationClaim is null)
        {
            return await next(context);
        }

        var routeStationId = context.HttpContext.Request.RouteValues["stationId"]?.ToString();
        if (!Guid.TryParse(stationClaim, out var authenticatedStationId)
            || !Guid.TryParse(routeStationId, out var requestedStationId)
            || authenticatedStationId != requestedStationId)
        {
            return Results.Forbid();
        }

        return await next(context);
    }
}

public static class DeviceStationAccess
{
    public static bool Matches(ClaimsPrincipal principal, Guid stationId)
    {
        var stationClaim = principal.FindFirstValue("station_id");
        return stationClaim is null
            || (Guid.TryParse(stationClaim, out var authenticatedStationId)
                && authenticatedStationId == stationId);
    }
}

public static class EndpointRouteBuilderExtensions
{
    public static RouteHandlerBuilder RequireSpecProofPermission(
        this RouteHandlerBuilder builder,
        string permission) =>
        builder.AddEndpointFilter(new PermissionEndpointFilter(permission));

    public static RouteHandlerBuilder RequireTenantMatch<TRequest>(this RouteHandlerBuilder builder)
        where TRequest : class, ITenantBoundRequest =>
        builder.AddEndpointFilter<TenantBoundRequestFilter<TRequest>>();

    public static RouteHandlerBuilder RequireDeviceStationMatch<TRequest>(this RouteHandlerBuilder builder)
        where TRequest : class, IStationBoundRequest =>
        builder.AddEndpointFilter<DeviceStationRequestFilter<TRequest>>();

    public static RouteHandlerBuilder RequireDeviceStationRouteMatch(this RouteHandlerBuilder builder) =>
        builder.AddEndpointFilter<DeviceStationRouteFilter>();
}

public sealed class SpecProofJwtValidator(IConfiguration configuration)
{
    private readonly byte[] secret = Encoding.UTF8.GetBytes(
        configuration["Authentication:JwtSecret"]
        ?? "specproof-development-jwt-secret-change-before-production");

    public string CreateToken(Guid tenantId, string subject, string role, DateTimeOffset expiresAtUtc)
    {
        var header = JsonSerializer.SerializeToUtf8Bytes(new { alg = "HS256", typ = "JWT" });
        var nowUtc = DateTimeOffset.UtcNow;
        var payload = JsonSerializer.SerializeToUtf8Bytes(
            new Dictionary<string, object>
            {
                ["sub"] = subject,
                ["tenant_id"] = tenantId.ToString("D", CultureInfo.InvariantCulture),
                ["role"] = role,
                ["iss"] = configuration["Authentication:Issuer"] ?? "specproof-development",
                ["aud"] = configuration["Authentication:Audience"] ?? "specproof-development",
                ["iat"] = nowUtc.ToUnixTimeSeconds(),
                ["nbf"] = nowUtc.AddSeconds(-30).ToUnixTimeSeconds(),
                ["jti"] = Guid.NewGuid().ToString("D", CultureInfo.InvariantCulture),
                ["exp"] = expiresAtUtc.ToUnixTimeSeconds(),
            });
        var unsignedToken = $"{Base64UrlEncode(header)}.{Base64UrlEncode(payload)}";
        var signature = HMACSHA256.HashData(secret, Encoding.UTF8.GetBytes(unsignedToken));
        return $"{unsignedToken}.{Base64UrlEncode(signature)}";
    }

    public ClaimsPrincipal? Validate(string token)
    {
        try
        {
            var parts = token.Split('.');
            if (parts.Length != 3)
            {
                return null;
            }

            using var header = JsonDocument.Parse(Base64UrlDecode(parts[0]));
            if (header.RootElement.GetProperty("alg").GetString() != "HS256")
            {
                return null;
            }

            var unsignedToken = $"{parts[0]}.{parts[1]}";
            var expectedSignature = HMACSHA256.HashData(secret, Encoding.UTF8.GetBytes(unsignedToken));
            var actualSignature = Base64UrlDecode(parts[2]);
            if (!CryptographicOperations.FixedTimeEquals(expectedSignature, actualSignature))
            {
                return null;
            }

            using var payload = JsonDocument.Parse(Base64UrlDecode(parts[1]));
            var root = payload.RootElement;
            var nowUtc = DateTimeOffset.UtcNow;
            var expiresAt = DateTimeOffset.FromUnixTimeSeconds(root.GetProperty("exp").GetInt64());
            var notBefore = DateTimeOffset.FromUnixTimeSeconds(root.GetProperty("nbf").GetInt64());
            var expectedIssuer = configuration["Authentication:Issuer"] ?? "specproof-development";
            var expectedAudience = configuration["Authentication:Audience"] ?? "specproof-development";
            if (expiresAt <= nowUtc
                || notBefore > nowUtc.AddSeconds(30)
                || root.GetProperty("iss").GetString() != expectedIssuer
                || root.GetProperty("aud").GetString() != expectedAudience)
            {
                return null;
            }

            var role = root.GetProperty("role").GetString() ?? string.Empty;
            if (!PlatformPermissions.RolePermissions.TryGetValue(role, out var permissions))
            {
                return null;
            }

            var tenantId = root.GetProperty("tenant_id").GetString();
            if (!Guid.TryParse(tenantId, out _))
            {
                return null;
            }

            var claims = new List<Claim>
            {
                new(ClaimTypes.NameIdentifier, root.GetProperty("sub").GetString() ?? string.Empty),
                new("tenant_id", tenantId),
                new(ClaimTypes.Role, role),
            };
            claims.AddRange(permissions.Select(permission => new Claim("permission", permission)));
            return new ClaimsPrincipal(new ClaimsIdentity(claims, "SpecProofJwt"));
        }
        catch (Exception exception) when (
            exception is FormatException
            or JsonException
            or KeyNotFoundException
            or ArgumentOutOfRangeException)
        {
            return null;
        }
    }

    private static string Base64UrlEncode(byte[] value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static byte[] Base64UrlDecode(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded = padded.PadRight(padded.Length + ((4 - (padded.Length % 4)) % 4), '=');
        return Convert.FromBase64String(padded);
    }
}

public static class ProductionSecurityPolicy
{
    private const string DevelopmentJwtSecret =
        "specproof-development-jwt-secret-change-before-production";
    private const string DevelopmentSigningSecret =
        "specproof-development-evidence-signing-secret-change-before-production";

    public static void Validate(IHostEnvironment environment, IConfiguration configuration)
    {
        if (!environment.IsProduction())
        {
            return;
        }

        var failures = new List<string>();
        RequireSecret(
            configuration["Authentication:JwtSecret"],
            DevelopmentJwtSecret,
            "Authentication:JwtSecret",
            failures);
        RequireSecret(
            configuration["Trust:SigningSecret"],
            DevelopmentSigningSecret,
            "Trust:SigningSecret",
            failures);
        RequireValue(configuration["Authentication:Issuer"], "Authentication:Issuer", failures);
        RequireValue(configuration["Authentication:Audience"], "Authentication:Audience", failures);
        RequireValue(configuration["Trust:SigningKeyId"], "Trust:SigningKeyId", failures);
        if (!configuration.GetValue("Security:RequireHttps", false))
        {
            failures.Add("Security:RequireHttps must be true");
        }

        if (!configuration.GetValue("Security:DeviceCertificates:RequireChainTrust", false))
        {
            failures.Add("Security:DeviceCertificates:RequireChainTrust must be true");
        }

        if (!configuration.GetValue(
                "Security:DeviceCertificates:RequireClientAuthenticationEku",
                false))
        {
            failures.Add(
                "Security:DeviceCertificates:RequireClientAuthenticationEku must be true");
        }

        var roots = configuration
            .GetSection("Security:DeviceCertificates:AllowedRootCertificateSha256")
            .Get<string[]>() ?? [];
        if (roots.Length == 0 || roots.Any(root => root.Length != 64 || !root.All(Uri.IsHexDigit)))
        {
            failures.Add(
                "Security:DeviceCertificates:AllowedRootCertificateSha256 requires valid SHA-256 values");
        }

        if (failures.Count > 0)
        {
            throw new InvalidOperationException(
                $"Production security configuration is invalid: {string.Join("; ", failures)}");
        }
    }

    private static void RequireSecret(
        string? value,
        string developmentValue,
        string name,
        ICollection<string> failures)
    {
        if (string.IsNullOrWhiteSpace(value)
            || value.Length < 32
            || string.Equals(value, developmentValue, StringComparison.Ordinal))
        {
            failures.Add($"{name} must be a non-development secret of at least 32 characters");
        }
    }

    private static void RequireValue(string? value, string name, ICollection<string> failures)
    {
        if (string.IsNullOrWhiteSpace(value)
            || value.Contains("development", StringComparison.OrdinalIgnoreCase)
            || value.Contains("dev-", StringComparison.OrdinalIgnoreCase))
        {
            failures.Add($"{name} must be explicitly configured for production");
        }
    }
}

public static class CaptureUploadSecurity
{
    public static bool IsAccepted(bool production, bool encrypted) => !production || encrypted;
}

public sealed record EvidenceSignatureResult(
    string KeyId,
    string Algorithm,
    string SignatureValueBase64,
    DateTimeOffset SignedAtUtc);

public sealed class EvidenceSignatureService(IConfiguration configuration)
{
    private readonly string keyId = configuration["Trust:SigningKeyId"] ?? "dev-hmac-key-v1";
    private readonly byte[] secret = Encoding.UTF8.GetBytes(
        configuration["Trust:SigningSecret"]
        ?? "specproof-development-evidence-signing-secret-change-before-production");

    public string KeyId => keyId;

    public EvidenceSignatureResult Sign(string canonicalEvidenceJson)
    {
        var signature = HMACSHA256.HashData(secret, Encoding.UTF8.GetBytes(canonicalEvidenceJson));
        return new EvidenceSignatureResult(
            keyId,
            "HMAC-SHA256",
            Convert.ToBase64String(signature),
            DateTimeOffset.UtcNow);
    }

    public bool Verify(string canonicalEvidenceJson, string signatureValueBase64)
    {
        var expected = HMACSHA256.HashData(secret, Encoding.UTF8.GetBytes(canonicalEvidenceJson));
        var actual = Convert.FromBase64String(signatureValueBase64);
        return CryptographicOperations.FixedTimeEquals(expected, actual);
    }
}

public static class EvidenceHashChain
{
    public static string ComputeRecordHash(string evidenceJson, string? previousHashSha256)
    {
        var payload = JsonSerializer.SerializeToUtf8Bytes(
            new { evidence = JsonDocument.Parse(evidenceJson).RootElement, previousHashSha256 },
            SpecProofJsonOptions.Canonical);
        return Convert.ToHexString(SHA256.HashData(payload)).ToLowerInvariant();
    }
}

public static class SpecProofJsonOptions
{
    public static readonly JsonSerializerOptions Canonical = new(JsonSerializerDefaults.Web)
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        WriteIndented = false,
    };
}

public sealed class TenantObjectStorageNamespace
{
    public static string BuildBucketName(Guid tenantId) =>
        $"specproof-tenant-{tenantId:N}";

    public static string BuildObjectKey(Guid tenantId, Guid stationId, Guid captureId, string extension) =>
        $"{tenantId:N}/{stationId:N}/{captureId:N}{extension}";
}

public sealed class SyncProtocolService
{
    public async Task<SyncEnvelope> AcceptAsync(
        SpecProofDbContext database,
        Guid tenantId,
        SyncEnvelopeRequest request,
        CancellationToken cancellationToken)
    {
        var existing = await database.SyncEnvelopes.SingleOrDefaultAsync(
            envelope =>
                envelope.TenantId == tenantId
                && envelope.StationId == request.StationId
                && envelope.IdempotencyKey == request.IdempotencyKey,
            cancellationToken);
        if (existing is not null)
        {
            existing.Attempts++;
            existing.LastAttemptAtUtc = DateTimeOffset.UtcNow;
            if (!string.Equals(existing.PayloadHashSha256, request.PayloadHashSha256, StringComparison.Ordinal))
            {
                existing.Status = "conflict";
                existing.ConflictJson = JsonSerializer.Serialize(
                    new
                    {
                        expectedHash = existing.PayloadHashSha256,
                        actualHash = request.PayloadHashSha256,
                    },
                    SpecProofJsonOptions.Canonical);
            }

            await database.SaveChangesAsync(cancellationToken);
            return existing;
        }

        var envelope = new SyncEnvelope
        {
            Id = Guid.NewGuid(),
            TenantId = tenantId,
            StationId = request.StationId,
            IdempotencyKey = request.IdempotencyKey,
            EntityType = request.EntityType,
            EntityId = request.EntityId,
            PayloadJson = request.PayloadJson,
            PayloadHashSha256 = request.PayloadHashSha256,
            Status = "accepted",
            Attempts = 1,
            LastAttemptAtUtc = DateTimeOffset.UtcNow,
        };
        database.SyncEnvelopes.Add(envelope);
        await database.SaveChangesAsync(cancellationToken);
        return envelope;
    }
}

public sealed class ReportingExportService
{
    private const int PdfRowsPerPage = 30;

    public string ToInspectionCsv(IEnumerable<InspectionResultDto> inspections)
    {
        var builder = new StringBuilder();
        builder.AppendLine("inspection_id,station_id,captured_at_utc,status,evidence_record_hash");
        foreach (var inspection in inspections)
        {
            builder
                .Append(inspection.InspectionId)
                .Append(',')
                .Append(Escape(inspection.StationId))
                .Append(',')
                .Append(inspection.CapturedAtUtc.ToString("O", CultureInfo.InvariantCulture))
                .Append(',')
                .Append(inspection.Status)
                .Append(',')
                .Append(Escape(inspection.EvidenceRecordHash))
                .AppendLine();
        }

        return builder.ToString();
    }

    public byte[] ToInspectionPdf(IEnumerable<InspectionResultDto> inspections)
    {
        var rows = inspections.ToArray();
        var pageCount = Math.Max(1, (rows.Length + PdfRowsPerPage - 1) / PdfRowsPerPage);
        var pageObjectNumbers = Enumerable.Range(0, pageCount).Select(index => 4 + (index * 2)).ToArray();
        var objects = new SortedDictionary<int, string>
        {
            [1] = "<< /Type /Catalog /Pages 2 0 R >>",
            [2] = $"<< /Type /Pages /Kids [{string.Join(' ', pageObjectNumbers.Select(number => $"{number} 0 R"))}] /Count {pageCount} >>",
            [3] = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        };

        for (var pageIndex = 0; pageIndex < pageCount; pageIndex++)
        {
            var pageObjectNumber = pageObjectNumbers[pageIndex];
            var contentObjectNumber = pageObjectNumber + 1;
            var pageRows = rows
                .Skip(pageIndex * PdfRowsPerPage)
                .Take(PdfRowsPerPage);
            var content = BuildPdfPageContent(pageRows, pageIndex + 1, pageCount);
            var contentLength = Encoding.ASCII.GetByteCount(content);
            objects[pageObjectNumber] =
                $"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {contentObjectNumber} 0 R >>";
            objects[contentObjectNumber] = $"<< /Length {contentLength} >>\nstream\n{content}endstream";
        }

        return BuildPdfDocument(objects);
    }

    private static string BuildPdfPageContent(
        IEnumerable<InspectionResultDto> inspections,
        int pageNumber,
        int pageCount)
    {
        var builder = new StringBuilder();
        builder.AppendLine("BT")
            .AppendLine("/F1 16 Tf")
            .AppendLine("50 750 Td")
            .AppendLine("(SpecProof Inspection Report) Tj")
            .AppendLine("0 -24 Td")
            .AppendLine("/F1 8 Tf")
            .AppendLine("(Inspection ID | Station | Captured UTC | Status | Evidence Hash) Tj");
        foreach (var inspection in inspections)
        {
            var row = string.Join(
                " | ",
                inspection.InspectionId,
                Truncate(inspection.StationId, 18),
                inspection.CapturedAtUtc.ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss 'UTC'", CultureInfo.InvariantCulture),
                inspection.Status,
                Truncate(inspection.EvidenceRecordHash, 12));
            builder.AppendLine("0 -18 Td")
                .Append('(')
                .Append(EscapePdfText(row))
                .AppendLine(") Tj");
        }

        builder.AppendLine("0 -24 Td")
            .Append('(')
            .Append(EscapePdfText($"Page {pageNumber} of {pageCount}"))
            .AppendLine(") Tj")
            .AppendLine("ET");
        return builder.ToString();
    }

    private static byte[] BuildPdfDocument(IReadOnlyDictionary<int, string> objects)
    {
        var builder = new StringBuilder("%PDF-1.4\n");
        var offsets = new int[objects.Count + 1];
        foreach (var (objectNumber, body) in objects)
        {
            offsets[objectNumber] = Encoding.ASCII.GetByteCount(builder.ToString());
            builder.Append(objectNumber)
                .AppendLine(" 0 obj")
                .AppendLine(body)
                .AppendLine("endobj");
        }

        var crossReferenceOffset = Encoding.ASCII.GetByteCount(builder.ToString());
        builder.AppendLine("xref")
            .Append("0 ")
            .AppendLine((objects.Count + 1).ToString(CultureInfo.InvariantCulture))
            .AppendLine("0000000000 65535 f ");
        for (var objectNumber = 1; objectNumber <= objects.Count; objectNumber++)
        {
            builder.Append(offsets[objectNumber].ToString("D10", CultureInfo.InvariantCulture))
                .AppendLine(" 00000 n ");
        }

        builder.AppendLine("trailer")
            .Append("<< /Size ")
            .Append(objects.Count + 1)
            .AppendLine(" /Root 1 0 R >>")
            .AppendLine("startxref")
            .AppendLine(crossReferenceOffset.ToString(CultureInfo.InvariantCulture))
            .AppendLine("%%EOF");
        return Encoding.ASCII.GetBytes(builder.ToString());
    }

    private static string EscapePdfText(string value) =>
        new string(value
            .Select(character => character is >= ' ' and <= '~' ? character : '?')
            .ToArray())
        .Replace("\\", "\\\\", StringComparison.Ordinal)
        .Replace("(", "\\(", StringComparison.Ordinal)
        .Replace(")", "\\)", StringComparison.Ordinal);

    private static string Truncate(string value, int maximumLength) =>
        value.Length <= maximumLength ? value : value[..maximumLength];

    private static string Escape(string value) =>
        value.Contains(',', StringComparison.Ordinal) || value.Contains('"', StringComparison.Ordinal)
            ? $"\"{value.Replace("\"", "\"\"", StringComparison.Ordinal)}\""
            : value;
}

public sealed class RegisterStationRequestValidator : AbstractValidator<RegisterStationRequest>
{
    public RegisterStationRequestValidator()
    {
        RuleFor(request => request.TenantId).NotEmpty();
        RuleFor(request => request.FactoryId).NotEmpty();
        RuleFor(request => request.StationCode).NotEmpty().MaximumLength(100);
        RuleFor(request => request.CertificateThumbprintSha256)
            .Matches("^[0-9a-fA-F]{64}$");
        RuleFor(request => request.PublicKeyPem).NotEmpty();
    }
}

public sealed class RotateDeviceCertificateRequestValidator : AbstractValidator<RotateDeviceCertificateRequest>
{
    public RotateDeviceCertificateRequestValidator()
    {
        RuleFor(request => request.CertificateThumbprintSha256)
            .Matches("^[0-9a-fA-F]{64}$");
        RuleFor(request => request.PublicKeyPem).NotEmpty();
        RuleFor(request => request.NotBeforeUtc)
            .LessThan(request => request.ExpiresAtUtc);
    }
}

public sealed class SyncEnvelopeRequestValidator : AbstractValidator<SyncEnvelopeRequest>
{
    public SyncEnvelopeRequestValidator()
    {
        RuleFor(request => request.StationId).NotEmpty();
        RuleFor(request => request.IdempotencyKey).NotEmpty().MaximumLength(200);
        RuleFor(request => request.EntityType).NotEmpty().MaximumLength(200);
        RuleFor(request => request.EntityId).NotEmpty();
        RuleFor(request => request.PayloadJson).Must(BeValidJson);
        RuleFor(request => request.PayloadHashSha256).Length(64);
    }

    private static bool BeValidJson(string value)
    {
        try
        {
            JsonDocument.Parse(value);
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }
}

public sealed class ValidationFilter<TRequest>(IValidator<TRequest> validator) : IEndpointFilter
    where TRequest : class
{
    public async ValueTask<object?> InvokeAsync(EndpointFilterInvocationContext context, EndpointFilterDelegate next)
    {
        var request = context.Arguments.OfType<TRequest>().FirstOrDefault();
        if (request is null)
        {
            return await next(context);
        }

        var validation = await validator.ValidateAsync(request, context.HttpContext.RequestAborted);
        if (validation.IsValid)
        {
            return await next(context);
        }

        return TypedResults.ValidationProblem(
            validation.Errors
                .GroupBy(error => error.PropertyName)
                .ToDictionary(
                    group => group.Key,
                    group => group.Select(error => error.ErrorMessage).ToArray()));
    }
}

public sealed record SyncEnvelopeRequest(
    Guid StationId,
    string IdempotencyKey,
    string EntityType,
    Guid EntityId,
    string PayloadJson,
    string PayloadHashSha256) : IStationBoundRequest;

public sealed record CreateInspectionRequest(
    Guid TenantId,
    Guid InspectionId,
    Guid CaptureId,
    Guid StationId,
    Guid? BatchId,
    string StationCode,
    string OrderCode,
    string StyleCode,
    string SizeCode,
    InspectionResultDto Result,
    EvidenceRecordDto Evidence) : ITenantBoundRequest, IStationBoundRequest;

public sealed record ReviewInspectionRequest(string Outcome, string Note);

public sealed record ApproveTechPackImportRequest(int Version, string SizeCode);

public sealed record EvidenceVerifyRequest(string EvidenceJson, string SignatureValueBase64);

public sealed record StationDiagnosticsRequest(Guid TenantId, Guid StationId, string DiagnosticsJson) : ITenantBoundRequest, IStationBoundRequest;

public sealed record StationConfigurationPushRequest(Guid TenantId, Guid StationId, int Version, string ConfigurationJson) : ITenantBoundRequest, IStationBoundRequest;

public sealed record StationVersionRequest(Guid TenantId, Guid StationId, string ComponentName, string Version) : ITenantBoundRequest, IStationBoundRequest;

public sealed record WebhookSubscriptionRequest(Guid TenantId, string Url, string[] EventTypes, string Secret) : ITenantBoundRequest;

public sealed record BackgroundJobRequest(Guid TenantId, string QueueName, string JobType, string PayloadJson) : ITenantBoundRequest;
