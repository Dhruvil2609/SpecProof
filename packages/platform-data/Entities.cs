namespace SpecProof.Platform.Data;

public interface ITenantScope
{
    Guid? TenantId { get; }
}

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

    public string? ExternalSubject { get; init; }

    public bool IsActive { get; init; } = true;
}

public sealed class ApplicationRole : TenantEntity
{
    public required string Name { get; init; }
}

public sealed class ApplicationUserRole : TenantEntity
{
    public Guid UserId { get; init; }

    public Guid RoleId { get; init; }
}

public sealed class ApplicationRolePermission : TenantEntity
{
    public Guid RoleId { get; init; }

    public required string Permission { get; init; }
}

public sealed class TenantConfiguration : TenantEntity
{
    public required string ConfigurationJson { get; init; }

    public required string ObjectStorageBucket { get; init; }

    public int RetentionDays { get; init; }
}

public sealed class Station : TenantEntity
{
    public Guid FactoryId { get; init; }

    public required string StationCode { get; init; }
}

public sealed class DeviceIdentity : TenantEntity
{
    public Guid StationId { get; init; }

    public required string CertificateThumbprintSha256 { get; init; }

    public required string PublicKeyPem { get; init; }

    public DateTimeOffset NotBeforeUtc { get; init; }

    public DateTimeOffset ExpiresAtUtc { get; init; }

    public bool Active { get; set; }

    public DateTimeOffset? RotatedAtUtc { get; set; }
}

public sealed class StationHealthReport : TenantEntity
{
    public Guid StationId { get; init; }

    public required string Status { get; init; }

    public required string CameraStatus { get; init; }

    public required string StorageStatus { get; init; }

    public required string ClockStatus { get; init; }

    public long OfflineQueueDepth { get; init; }

    public DateTimeOffset CheckedAtUtc { get; init; }
}

public sealed class StationDiagnosticReport : TenantEntity
{
    public Guid StationId { get; init; }

    public required string DiagnosticsJson { get; init; }

    public DateTimeOffset RequestedAtUtc { get; init; }

    public DateTimeOffset? CompletedAtUtc { get; init; }
}

public sealed class StationConfigurationVersion : TenantEntity
{
    public Guid StationId { get; init; }

    public int Version { get; init; }

    public required string ConfigurationJson { get; init; }

    public DateTimeOffset PushedAtUtc { get; init; }

    public DateTimeOffset? AppliedAtUtc { get; init; }
}

public sealed class StationSoftwareVersion : TenantEntity
{
    public Guid StationId { get; init; }

    public required string ComponentName { get; init; }

    public required string Version { get; init; }

    public DateTimeOffset ReportedAtUtc { get; init; }
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

public sealed class Brand : TenantEntity
{
    public required string Name { get; init; }
}

public sealed class ProductionOrder : TenantEntity
{
    public Guid BrandId { get; init; }

    public required string OrderCode { get; init; }

    public required string SupplierName { get; init; }

    public required string Status { get; set; }
}

public sealed class ProductionOrderLine : TenantEntity
{
    public Guid ProductionOrderId { get; init; }

    public Guid StyleId { get; init; }

    public Guid SizeId { get; init; }

    public int PlannedQuantity { get; init; }
}

public sealed class InspectionBatch : TenantEntity
{
    public Guid ProductionOrderLineId { get; init; }

    public required string BatchCode { get; init; }

    public required string Status { get; set; }
}

public sealed class TechPackImportDraft : TenantEntity
{
    public Guid TechPackId { get; init; }

    public required string OriginalFileName { get; init; }

    public required string ContentType { get; init; }

    public required string DraftJson { get; set; }

    public required string Status { get; set; }

    public required string SourceHashSha256 { get; init; }

    public DateTimeOffset? ApprovedAtUtc { get; set; }
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

    public Guid? SigningKeyId { get; set; }

    public string? SignatureAlgorithm { get; set; }

    public string? SignatureValueBase64 { get; set; }

    public DateTimeOffset? SignedAtUtc { get; set; }
}

public sealed class EvidenceSigningKey : TenantEntity
{
    public required string KeyId { get; init; }

    public required string Algorithm { get; init; }

    public required string PublicKeyPem { get; init; }

    public string? EncryptedPrivateKeyPem { get; init; }

    public bool Active { get; init; }

    public DateTimeOffset? RetiredAtUtc { get; init; }
}

public sealed class InspectionRecord : TenantEntity
{
    public Guid CaptureId { get; init; }

    public Guid StationId { get; init; }

    public Guid? BatchId { get; init; }

    public required string StationCode { get; init; }

    public required string OrderCode { get; init; }

    public required string StyleCode { get; init; }

    public required string SizeCode { get; init; }

    public required string InspectionResultJson { get; init; }

    public required string Status { get; init; }

    public required string EvidenceRecordHash { get; init; }

    public DateTimeOffset CapturedAtUtc { get; init; }

    public DateTimeOffset? DeletedAtUtc { get; set; }
}

public sealed class ReviewAction : TenantEntity
{
    public Guid InspectionId { get; init; }

    public Guid? ActorId { get; init; }

    public required string Outcome { get; init; }

    public required string Note { get; init; }
}

public sealed class SyncEnvelope : TenantEntity
{
    public Guid StationId { get; init; }

    public required string IdempotencyKey { get; init; }

    public required string EntityType { get; init; }

    public Guid EntityId { get; init; }

    public required string PayloadJson { get; init; }

    public required string PayloadHashSha256 { get; init; }

    public required string Status { get; set; }

    public int Attempts { get; set; }

    public string? ConflictJson { get; set; }

    public DateTimeOffset? LastAttemptAtUtc { get; set; }

    public DateTimeOffset? DeadLetteredAtUtc { get; set; }
}

public sealed class WebhookSubscription : TenantEntity
{
    public required string Url { get; init; }

    public required string EventTypesJson { get; init; }

    public required string SecretHashSha256 { get; init; }

    public bool Active { get; init; }
}

public sealed class BackgroundJobRecord : TenantEntity
{
    public required string QueueName { get; init; }

    public required string JobType { get; init; }

    public required string PayloadJson { get; init; }

    public required string Status { get; set; }

    public int Attempts { get; set; }

    public DateTimeOffset AvailableAtUtc { get; init; }

    public DateTimeOffset? StartedAtUtc { get; set; }

    public DateTimeOffset? CompletedAtUtc { get; set; }
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
