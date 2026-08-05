namespace SpecProof.Platform.Data;

public abstract class Entity
{
    public Guid Id { get; init; }

    public DateTimeOffset CreatedAtUtc { get; init; }

    public DateTimeOffset UpdatedAtUtc { get; set; }
}

public abstract class TenantEntity : Entity
{
    public Guid TenantId { get; init; }
}

public sealed class Tenant : Entity
{
    public required string Name { get; init; }
}

public sealed class Organisation : TenantEntity
{
    public required string Name { get; init; }
}

public sealed class Factory : TenantEntity
{
    public Guid OrganisationId { get; init; }

    public required string Name { get; init; }
}

public sealed class ApplicationUser : TenantEntity
{
    public required string Email { get; init; }

    public required string DisplayName { get; init; }
}

public sealed class ApplicationRole : TenantEntity
{
    public required string Name { get; init; }
}

public sealed class Station : TenantEntity
{
    public Guid FactoryId { get; init; }

    public required string StationCode { get; init; }
}

public sealed class Camera : TenantEntity
{
    public Guid StationId { get; init; }

    public required string SerialNumber { get; init; }
}

public sealed class CalibrationRecord : TenantEntity
{
    public Guid CameraId { get; init; }

    public int Version { get; init; }

    public required string Mode { get; init; }

    public Guid OperatorId { get; init; }

    public required string ArtefactId { get; init; }

    public DateTimeOffset CalibratedAtUtc { get; init; }

    public DateTimeOffset ExpiresAtUtc { get; init; }

    public required string MetricsJson { get; init; }

    public required string CalibrationBlobSha256 { get; init; }

    public DateTimeOffset? SupersededAtUtc { get; init; }
}

public sealed class CaptureAsset : TenantEntity
{
    public Guid StationId { get; init; }

    public Guid CaptureId { get; init; }

    public required string ObjectKey { get; init; }

    public required string ContentType { get; init; }

    public long SizeBytes { get; init; }

    public required string ChecksumSha256 { get; init; }

    public required string RetentionCategory { get; init; }

    public bool Encrypted { get; init; }

    public DateTimeOffset? UploadCompletedAtUtc { get; set; }
}

public sealed class GarmentCategory : TenantEntity
{
    public required string Name { get; init; }
}

public sealed class Style : TenantEntity
{
    public Guid GarmentCategoryId { get; init; }

    public required string StyleCode { get; init; }
}

public sealed class Size : TenantEntity
{
    public Guid StyleId { get; init; }

    public required string SizeCode { get; init; }
}

public sealed class TechPackVersion : TenantEntity
{
    public Guid TechPackId { get; init; }

    public int Version { get; init; }

    public required string Brand { get; init; }

    public required string StyleCode { get; init; }

    public required string GarmentCategory { get; init; }

    public required string DataJson { get; init; }

    public required string VersionHashSha256 { get; init; }

    public bool Approved { get; init; }

    public DateTimeOffset? ReferencedAtUtc { get; init; }
}

public sealed class EvidenceRecord : TenantEntity
{
    public Guid InspectionId { get; init; }

    public Guid CaptureId { get; init; }

    public required string CaptureHashSha256 { get; init; }

    public required string EvidenceJson { get; init; }

    public string? PreviousHashSha256 { get; init; }

    public required string RecordHashSha256 { get; init; }
}

public sealed class AuditEvent
{
    public Guid Id { get; init; }

    public Guid TenantId { get; init; }

    public required string EventType { get; init; }

    public required string EntityType { get; init; }

    public Guid EntityId { get; init; }

    public Guid? ActorId { get; init; }

    public required string PayloadJson { get; init; }

    public DateTimeOffset OccurredAtUtc { get; init; }
}
