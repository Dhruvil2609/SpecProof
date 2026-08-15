using System.Diagnostics;
using System.Diagnostics.Metrics;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using SpecProof.Contracts;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api;

public enum IntegratedInspectionPersistenceStatus
{
    Created,
    Replayed,
    Conflict,
    Invalid,
}

public sealed record IntegratedInspectionSubmissionResponse(
    InspectionResultDto Result,
    EvidenceRecordDto Evidence);

public sealed record IntegratedInspectionPersistenceResult(
    IntegratedInspectionPersistenceStatus Status,
    IntegratedInspectionSubmissionResponse? Submission = null,
    IReadOnlyDictionary<string, string[]>? Errors = null);

public sealed class IntegratedInspectionPersistence(EvidenceSignatureService signatureService)
{
    private static readonly Meter Meter = new("SpecProof.Platform.Integration");
    private static readonly Histogram<double> PersistenceDuration = Meter.CreateHistogram<double>(
        "specproof.inspection.persistence.duration",
        unit: "ms",
        description: "Atomic integrated inspection persistence duration");

    public async Task<IntegratedInspectionPersistenceResult> PersistAsync(
        SpecProofDbContext database,
        CreateInspectionRequest request,
        CancellationToken cancellationToken)
    {
        var errors = Validate(request);
        if (errors.Count > 0)
        {
            return new IntegratedInspectionPersistenceResult(
                IntegratedInspectionPersistenceStatus.Invalid,
                Errors: errors);
        }

        var resultJson = JsonSerializer.Serialize(
            request.Result,
            SpecProofJsonContext.Default.InspectionResultDto);
        var evidenceJson = JsonSerializer.Serialize(
            request.Evidence,
            SpecProofJsonContext.Default.EvidenceRecordDto);
        var existingInspection = await database.InspectionRecords
            .SingleOrDefaultAsync(
                record => record.Id == request.InspectionId && record.TenantId == request.TenantId,
                cancellationToken);
        if (existingInspection is not null)
        {
            var existingEvidence = await database.EvidenceRecords
                .SingleOrDefaultAsync(
                    record =>
                        record.InspectionId == request.InspectionId
                        && record.TenantId == request.TenantId,
                    cancellationToken);
            if (!IsIdentical(existingInspection, existingEvidence, request, resultJson, evidenceJson))
            {
                return new IntegratedInspectionPersistenceResult(
                    IntegratedInspectionPersistenceStatus.Conflict);
            }

            return new IntegratedInspectionPersistenceResult(
                IntegratedInspectionPersistenceStatus.Replayed,
                new IntegratedInspectionSubmissionResponse(
                    request.Result,
                    request.Evidence with
                    {
                        Signature = existingEvidence is null ? null : ToSignature(existingEvidence),
                    }));
        }

        var capture = await database.CaptureAssets.SingleOrDefaultAsync(
            asset =>
                asset.TenantId == request.TenantId
                && asset.StationId == request.StationId
                && asset.CaptureId == request.CaptureId,
            cancellationToken);
        if (capture is null
            || capture.UploadCompletedAtUtc is null
            || !string.Equals(
                capture.ChecksumSha256,
                request.Evidence.CaptureHashSha256,
                StringComparison.Ordinal))
        {
            return Invalid("captureId", "Capture upload is missing, incomplete, or has a different hash.");
        }

        var stationExists = await database.Stations.AnyAsync(
            station =>
                station.Id == request.StationId
                && station.TenantId == request.TenantId
                && station.StationCode == request.StationCode,
            cancellationToken);
        if (!stationExists)
        {
            return Invalid("stationId", "Station identity and code do not match the tenant.");
        }

        var signature = signatureService.Sign(evidenceJson);
        var now = DateTimeOffset.UtcNow;
        var inspection = new InspectionRecord
        {
            Id = request.InspectionId,
            TenantId = request.TenantId,
            CaptureId = request.CaptureId,
            StationId = request.StationId,
            BatchId = request.BatchId,
            StationCode = request.StationCode,
            OrderCode = request.OrderCode,
            StyleCode = request.StyleCode,
            SizeCode = request.SizeCode,
            InspectionResultJson = resultJson,
            Status = request.Result.Status.ToString(),
            EvidenceRecordHash = request.Result.EvidenceRecordHash,
            CapturedAtUtc = request.Result.CapturedAtUtc,
        };
        var evidence = new EvidenceRecord
        {
            Id = Guid.Parse(request.Evidence.EvidenceId),
            TenantId = request.TenantId,
            InspectionId = request.InspectionId,
            CaptureId = request.CaptureId,
            CaptureHashSha256 = request.Evidence.CaptureHashSha256,
            EvidenceJson = evidenceJson,
            PreviousHashSha256 = request.Evidence.PreviousHashSha256,
            RecordHashSha256 = request.Evidence.RecordHashSha256,
            SignatureAlgorithm = signature.Algorithm,
            SignatureValueBase64 = signature.SignatureValueBase64,
            SignedAtUtc = signature.SignedAtUtc,
        };
        database.InspectionRecords.Add(inspection);
        database.EvidenceRecords.Add(evidence);
        database.AuditEvents.Add(
            new AuditEvent
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                EventType = "inspection.integrated",
                EntityType = "inspection",
                EntityId = request.InspectionId,
                PayloadJson = JsonSerializer.Serialize(
                    new
                    {
                        request.InspectionId,
                        request.CaptureId,
                        EvidenceHashSha256 = request.Evidence.RecordHashSha256,
                        signature.KeyId,
                    },
                    SpecProofJsonOptions.Canonical),
                OccurredAtUtc = now,
            });
        database.BackgroundJobs.Add(
            new BackgroundJobRecord
            {
                Id = Guid.NewGuid(),
                TenantId = request.TenantId,
                QueueName = "reports",
                JobType = "inspection.report.refresh",
                PayloadJson = JsonSerializer.Serialize(
                    new { request.InspectionId },
                    SpecProofJsonOptions.Canonical),
                Status = "queued",
                AvailableAtUtc = now,
            });
        var persistenceStarted = Stopwatch.GetTimestamp();
        await database.SaveChangesAsync(cancellationToken);
        PersistenceDuration.Record(Stopwatch.GetElapsedTime(persistenceStarted).TotalMilliseconds);

        var signedEvidence = request.Evidence with
        {
            Signature = new SignedEvidenceDto(
                signature.KeyId,
                signature.Algorithm,
                signature.SignatureValueBase64,
                signature.SignedAtUtc),
        };
        return new IntegratedInspectionPersistenceResult(
            IntegratedInspectionPersistenceStatus.Created,
            new IntegratedInspectionSubmissionResponse(request.Result, signedEvidence));
    }

    private static Dictionary<string, string[]> Validate(CreateInspectionRequest request)
    {
        var errors = new Dictionary<string, string[]>(StringComparer.Ordinal);
        AddIf(request.TenantId == Guid.Empty, "tenantId", "Tenant ID is required.");
        AddIf(request.StationId == Guid.Empty, "stationId", "Station ID is required.");
        AddIf(request.CaptureId == Guid.Empty, "captureId", "Capture ID is required.");
        AddIf(request.InspectionId == Guid.Empty, "inspectionId", "Inspection ID is required.");
        AddIf(string.IsNullOrWhiteSpace(request.StationCode), "stationCode", "Station code is required.");
        AddIf(string.IsNullOrWhiteSpace(request.OrderCode), "orderCode", "Order code is required.");
        AddIf(string.IsNullOrWhiteSpace(request.StyleCode), "styleCode", "Style code is required.");
        AddIf(string.IsNullOrWhiteSpace(request.SizeCode), "sizeCode", "Size code is required.");
        AddIf(request.Result.InspectionId != request.InspectionId, "result.inspectionId", "Inspection IDs do not match.");
        AddIf(request.Evidence.TenantId != request.TenantId, "evidence.tenantId", "Tenant IDs do not match.");
        AddIf(request.Evidence.InspectionId != request.InspectionId, "evidence.inspectionId", "Inspection IDs do not match.");
        AddIf(request.Evidence.CaptureId != request.CaptureId, "evidence.captureId", "Capture IDs do not match.");
        AddIf(
            !Guid.TryParse(request.Result.StationId, out var resultStationId)
                || resultStationId != request.StationId,
            "result.stationId",
            "Station IDs do not match.");
        AddIf(
            !Guid.TryParse(request.Evidence.EvidenceId, out _),
            "evidence.evidenceId",
            "Evidence ID must be a UUID.");
        AddIf(
            !IsSha256(request.Evidence.CaptureHashSha256),
            "evidence.captureHashSha256",
            "Capture hash must be lowercase SHA-256.");
        AddIf(
            !IsSha256(request.Evidence.RecordHashSha256),
            "evidence.recordHashSha256",
            "Evidence hash must be lowercase SHA-256.");
        AddIf(
            !string.Equals(
                request.Result.EvidenceRecordHash,
                request.Evidence.RecordHashSha256,
                StringComparison.Ordinal),
            "result.evidenceRecordHash",
            "Result and evidence hashes do not match.");
        AddIf(
            request.Evidence.Versions.TechPackId is null
                || request.Evidence.Versions.TechPackVersion is null
                || request.Evidence.Versions.TechPackVersion <= 0,
            "evidence.versions",
            "Tech-pack ID and version bindings are required.");
        AddIf(
            request.Result.Status != request.Evidence.Status,
            "evidence.status",
            "Result and evidence statuses do not match.");
        AddIf(
            !JsonEquivalent(
                JsonSerializer.Serialize(request.Result.Measurements, SpecProofJsonOptions.Canonical),
                JsonSerializer.Serialize(request.Evidence.Measurements, SpecProofJsonOptions.Canonical)),
            "evidence.measurements",
            "Result and evidence measurements do not match.");
        return errors;

        void AddIf(bool condition, string key, string message)
        {
            if (condition)
            {
                errors[key] = [message];
            }
        }
    }

    private static bool IsIdentical(
        InspectionRecord inspection,
        EvidenceRecord? evidence,
        CreateInspectionRequest request,
        string resultJson,
        string evidenceJson) =>
        evidence is not null
        && inspection.CaptureId == request.CaptureId
        && inspection.StationId == request.StationId
        && inspection.BatchId == request.BatchId
        && inspection.StationCode == request.StationCode
        && inspection.OrderCode == request.OrderCode
        && inspection.StyleCode == request.StyleCode
        && inspection.SizeCode == request.SizeCode
        && JsonEquivalent(inspection.InspectionResultJson, resultJson)
        && JsonEquivalent(evidence.EvidenceJson, evidenceJson)
        && evidence.RecordHashSha256 == request.Evidence.RecordHashSha256;

    private SignedEvidenceDto? ToSignature(EvidenceRecord evidence) =>
        evidence.SignatureAlgorithm is null
        || evidence.SignatureValueBase64 is null
        || evidence.SignedAtUtc is null
            ? null
            : new SignedEvidenceDto(
                signatureService.KeyId,
                evidence.SignatureAlgorithm,
                evidence.SignatureValueBase64,
                evidence.SignedAtUtc.Value);

    private static bool IsSha256(string value) =>
        value.Length == 64 && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');

    private static bool JsonEquivalent(string left, string right)
    {
        using var leftDocument = JsonDocument.Parse(left);
        using var rightDocument = JsonDocument.Parse(right);
        return JsonElement.DeepEquals(leftDocument.RootElement, rightDocument.RootElement);
    }

    private static IntegratedInspectionPersistenceResult Invalid(string key, string message) =>
        new(
            IntegratedInspectionPersistenceStatus.Invalid,
            Errors: new Dictionary<string, string[]>(StringComparer.Ordinal)
            {
                [key] = [message],
            });
}
