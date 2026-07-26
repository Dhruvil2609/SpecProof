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

    public DateTimeOffset CalibratedAtUtc { get; init; }

    public required string CalibrationBlobSha256 { get; init; }
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
