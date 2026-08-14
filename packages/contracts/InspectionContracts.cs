using System.Text.Json.Serialization;

namespace SpecProof.Contracts;

public enum InspectionStatus
{
    Pending,
    Pass,
    Fail,
    Review,
    Invalid
}

public enum MeasurementStatus
{
    Pass,
    Fail,
    Review,
    Invalid
}

public sealed record MeasurementDto(
    string PomId,
    string CanonicalName,
    double MeasuredValueMm,
    double TargetValueMm,
    double LowerToleranceMm,
    double UpperToleranceMm,
    double DeviationMm,
    double Confidence,
    MeasurementStatus Status,
    IReadOnlyList<NormalizedPointDto>? Overlay = null);

public sealed record InspectionResultDto(
    Guid InspectionId,
    string StationId,
    string CameraSerial,
    DateTimeOffset CapturedAtUtc,
    IReadOnlyList<MeasurementDto> Measurements,
    InspectionStatus Status,
    string EvidenceRecordHash);

public sealed record EvidenceVersionsDto(
    string CalibrationRecordId,
    string ModelVersion,
    string OntologyVersion,
    string CompilerVersion);

public sealed record EvidenceRecordDto(
    string EvidenceId,
    Guid TenantId,
    Guid InspectionId,
    Guid CaptureId,
    string CaptureHashSha256,
    DateTimeOffset ProducedAtUtc,
    EvidenceVersionsDto Versions,
    IReadOnlyList<MeasurementDto> Measurements,
    InspectionStatus Status,
    string? PreviousHashSha256,
    string RecordHashSha256,
    SignedEvidenceDto? Signature = null);

public sealed record SignedEvidenceDto(
    string KeyId,
    string Algorithm,
    string SignatureValueBase64,
    DateTimeOffset SignedAtUtc);

public sealed record TechPackVersionDto(
    Guid TechPackId,
    int Version,
    string Brand,
    string StyleCode,
    string GarmentCategory,
    bool Approved,
    string VersionHashSha256);

public sealed record StationRegistrationDto(
    Guid StationId,
    Guid TenantId,
    Guid FactoryId,
    string StationCode,
    string CertificateThumbprintSha256,
    DateTimeOffset RegisteredAtUtc);

public sealed record StationHealthDto(
    Guid StationId,
    string Status,
    string CameraStatus,
    string StorageStatus,
    string ClockStatus,
    long OfflineQueueDepth,
    DateTimeOffset CheckedAtUtc);

public sealed record SyncEnvelopeDto(
    Guid EnvelopeId,
    Guid TenantId,
    Guid StationId,
    string IdempotencyKey,
    string EntityType,
    Guid EntityId,
    string PayloadHashSha256,
    string Status);

public sealed record BatchSummaryDto(
    Guid BatchId,
    int TotalInspections,
    int PassCount,
    int FailCount,
    int ReviewCount,
    int InvalidCount);

public sealed record NormalizedPointDto(double X, double Y);

public sealed record MeasurementOverlayDto(
    string PomId,
    IReadOnlyList<NormalizedPointDto> Points);

public sealed record WebMeasurementDto(
    string PomId,
    string CanonicalName,
    double MeasuredValueMm,
    double TargetValueMm,
    double LowerToleranceMm,
    double UpperToleranceMm,
    double DeviationMm,
    double Confidence,
    string Status,
    IReadOnlyList<NormalizedPointDto> Overlay);

public sealed record CaptureContextDto(
    Guid CaptureId,
    string OrderCode,
    string StyleCode,
    string SizeCode,
    string? BatchCode);

public sealed record InspectionDetailDto(
    Guid Id,
    Guid CaptureId,
    string OrderCode,
    string StyleCode,
    string SizeCode,
    string StationCode,
    DateTimeOffset CapturedAtUtc,
    string Status,
    string EvidenceHash,
    IReadOnlyList<WebMeasurementDto> Measurements);

public sealed record StationDetailDto(
    Guid Id,
    string Code,
    string Factory,
    string Status,
    string CameraStatus,
    string StorageStatus,
    string ClockStatus,
    long QueueDepth,
    DateTimeOffset CalibrationExpiresAtUtc,
    string SoftwareVersion);

public sealed record TechPackMappingDto(
    string OriginalTerm,
    string? CanonicalPomId,
    string Status);

public sealed record TechPackDetailDto(
    Guid Id,
    string Brand,
    string StyleCode,
    string Category,
    int Version,
    string Status,
    string Hash,
    IReadOnlyList<TechPackMappingDto> Mappings);

public sealed record UserAccountDto(
    Guid Id,
    string Name,
    string Email,
    string Role,
    bool Active);

public sealed record EvidenceDetailDto(
    Guid Id,
    Guid InspectionId,
    string RecordHash,
    string? PreviousHash,
    string SignatureAlgorithm,
    bool SignatureValid,
    string ModelVersion,
    string OntologyVersion,
    string CompilerVersion,
    DateTimeOffset ProducedAtUtc);

public sealed record WebDashboardDto(
    IReadOnlyList<InspectionDetailDto> Inspections,
    IReadOnlyList<StationDetailDto> Stations,
    IReadOnlyList<TechPackDetailDto> TechPacks,
    IReadOnlyList<UserAccountDto> Users,
    IReadOnlyList<EvidenceDetailDto> Evidence);

public sealed record ReviewActionDto(
    Guid Id,
    Guid InspectionId,
    Guid? ActorId,
    string Outcome,
    string Note,
    DateTimeOffset CreatedAtUtc);

public sealed record PagedResultDto<T>(
    IReadOnlyList<T> Items,
    int Page,
    int PageSize,
    int TotalCount);

public sealed record CaptureCompletedEvent(
    Guid CaptureId,
    Guid TenantId,
    string StationId,
    string CameraSerial,
    DateTimeOffset CapturedAtUtc,
    string ObjectKey,
    string ChecksumSha256);

[JsonSerializable(typeof(InspectionResultDto))]
[JsonSerializable(typeof(EvidenceRecordDto))]
[JsonSerializable(typeof(SignedEvidenceDto))]
[JsonSerializable(typeof(TechPackVersionDto))]
[JsonSerializable(typeof(StationRegistrationDto))]
[JsonSerializable(typeof(StationHealthDto))]
[JsonSerializable(typeof(SyncEnvelopeDto))]
[JsonSerializable(typeof(BatchSummaryDto))]
[JsonSerializable(typeof(WebDashboardDto))]
[JsonSerializable(typeof(InspectionDetailDto))]
[JsonSerializable(typeof(ReviewActionDto))]
[JsonSerializable(typeof(PagedResultDto<InspectionDetailDto>))]
[JsonSerializable(typeof(CaptureCompletedEvent))]
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    WriteIndented = false,
    UseStringEnumConverter = true)]
public sealed partial class SpecProofJsonContext : JsonSerializerContext;
