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
    MeasurementStatus Status);

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
    string RecordHashSha256);

public sealed record TechPackVersionDto(
    Guid TechPackId,
    int Version,
    string Brand,
    string StyleCode,
    string GarmentCategory,
    bool Approved,
    string VersionHashSha256);

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
[JsonSerializable(typeof(TechPackVersionDto))]
[JsonSerializable(typeof(CaptureCompletedEvent))]
[JsonSourceGenerationOptions(
    PropertyNamingPolicy = JsonKnownNamingPolicy.CamelCase,
    WriteIndented = false,
    UseStringEnumConverter = true)]
public sealed partial class SpecProofJsonContext : JsonSerializerContext;
