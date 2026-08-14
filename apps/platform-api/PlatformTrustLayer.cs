using System.Globalization;
using System.Security.Claims;
using System.Security.Cryptography;
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

public static class EndpointRouteBuilderExtensions
{
    public static RouteHandlerBuilder RequireSpecProofPermission(
        this RouteHandlerBuilder builder,
        string permission) =>
        builder.AddEndpointFilter(new PermissionEndpointFilter(permission));

    public static RouteHandlerBuilder RequireTenantMatch<TRequest>(this RouteHandlerBuilder builder)
        where TRequest : class, ITenantBoundRequest =>
        builder.AddEndpointFilter<TenantBoundRequestFilter<TRequest>>();
}

public sealed class SpecProofJwtValidator(IConfiguration configuration)
{
    private readonly byte[] secret = Encoding.UTF8.GetBytes(
        configuration["Authentication:JwtSecret"]
        ?? "specproof-development-jwt-secret-change-before-production");

    public string CreateToken(Guid tenantId, string subject, string role, DateTimeOffset expiresAtUtc)
    {
        var header = JsonSerializer.SerializeToUtf8Bytes(new { alg = "HS256", typ = "JWT" });
        var payload = JsonSerializer.SerializeToUtf8Bytes(
            new Dictionary<string, object>
            {
                ["sub"] = subject,
                ["tenant_id"] = tenantId.ToString("D", CultureInfo.InvariantCulture),
                ["role"] = role,
                ["exp"] = expiresAtUtc.ToUnixTimeSeconds(),
            });
        var unsignedToken = $"{Base64UrlEncode(header)}.{Base64UrlEncode(payload)}";
        var signature = HMACSHA256.HashData(secret, Encoding.UTF8.GetBytes(unsignedToken));
        return $"{unsignedToken}.{Base64UrlEncode(signature)}";
    }

    public ClaimsPrincipal? Validate(string token)
    {
        var parts = token.Split('.');
        if (parts.Length != 3)
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
        var expiresAt = DateTimeOffset.FromUnixTimeSeconds(payload.RootElement.GetProperty("exp").GetInt64());
        if (expiresAt <= DateTimeOffset.UtcNow)
        {
            return null;
        }

        var role = payload.RootElement.GetProperty("role").GetString() ?? string.Empty;
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, payload.RootElement.GetProperty("sub").GetString() ?? string.Empty),
            new("tenant_id", payload.RootElement.GetProperty("tenant_id").GetString() ?? string.Empty),
            new(ClaimTypes.Role, role),
        };
        if (PlatformPermissions.RolePermissions.TryGetValue(role, out var permissions))
        {
            claims.AddRange(permissions.Select(permission => new Claim("permission", permission)));
        }

        return new ClaimsPrincipal(new ClaimsIdentity(claims, "SpecProofJwt"));
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
        RuleFor(request => request.CertificateThumbprintSha256).Length(64);
        RuleFor(request => request.PublicKeyPem).NotEmpty();
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
    string PayloadHashSha256);

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
    InspectionResultDto Result) : ITenantBoundRequest;

public sealed record ReviewInspectionRequest(string Outcome, string Note);

public sealed record ApproveTechPackImportRequest(int Version, string SizeCode);

public sealed record EvidenceVerifyRequest(string EvidenceJson, string SignatureValueBase64);

public sealed record StationDiagnosticsRequest(Guid TenantId, Guid StationId, string DiagnosticsJson) : ITenantBoundRequest;

public sealed record StationConfigurationPushRequest(Guid TenantId, Guid StationId, int Version, string ConfigurationJson) : ITenantBoundRequest;

public sealed record StationVersionRequest(Guid TenantId, Guid StationId, string ComponentName, string Version) : ITenantBoundRequest;

public sealed record WebhookSubscriptionRequest(Guid TenantId, string Url, string[] EventTypes, string Secret) : ITenantBoundRequest;

public sealed record BackgroundJobRequest(Guid TenantId, string QueueName, string JobType, string PayloadJson) : ITenantBoundRequest;
