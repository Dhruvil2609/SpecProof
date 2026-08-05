using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace SpecProof.Platform.Data;

internal static class EntityConfiguration
{
    public static void ConfigureEntity<TEntity>(EntityTypeBuilder<TEntity> builder)
        where TEntity : Entity
    {
        builder.HasKey(entity => entity.Id);
        builder.Property(entity => entity.Id).HasColumnName("id").HasDefaultValueSql("gen_random_uuid()");
        builder.Property(entity => entity.CreatedAtUtc)
            .HasColumnName("created_at_utc")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();
        builder.Property(entity => entity.UpdatedAtUtc)
            .HasColumnName("updated_at_utc")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();
    }

    public static void ConfigureTenantEntity<TEntity>(EntityTypeBuilder<TEntity> builder)
        where TEntity : TenantEntity
    {
        ConfigureEntity(builder);
        builder.Property(entity => entity.TenantId).HasColumnName("tenant_id").IsRequired();
        builder.HasIndex(entity => entity.TenantId)
            .HasDatabaseName($"ix_{builder.Metadata.GetTableName()}_tenant_id");
    }
}

internal sealed class TenantConfiguration : IEntityTypeConfiguration<Tenant>
{
    public void Configure(EntityTypeBuilder<Tenant> builder)
    {
        builder.ToTable("tenants");
        EntityConfiguration.ConfigureEntity(builder);
        builder.Property(entity => entity.Name).HasColumnName("name").HasMaxLength(200).IsRequired();
        builder.HasIndex(entity => entity.Name).IsUnique().HasDatabaseName("uq_tenants_name");
    }
}

internal sealed class OrganisationConfiguration : IEntityTypeConfiguration<Organisation>
{
    public void Configure(EntityTypeBuilder<Organisation> builder)
    {
        builder.ToTable("organisations");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.Name).HasColumnName("name").HasMaxLength(200).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.Name })
            .IsUnique()
            .HasDatabaseName("uq_organisations_tenant_id_name");
    }
}

internal sealed class FactoryConfiguration : IEntityTypeConfiguration<Factory>
{
    public void Configure(EntityTypeBuilder<Factory> builder)
    {
        builder.ToTable("factories");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.OrganisationId).HasColumnName("organisation_id").IsRequired();
        builder.Property(entity => entity.Name).HasColumnName("name").HasMaxLength(200).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.Name })
            .IsUnique()
            .HasDatabaseName("uq_factories_tenant_id_name");
    }
}

internal sealed class ApplicationUserConfiguration : IEntityTypeConfiguration<ApplicationUser>
{
    public void Configure(EntityTypeBuilder<ApplicationUser> builder)
    {
        builder.ToTable("users");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.Email).HasColumnName("email").HasMaxLength(320).IsRequired();
        builder.Property(entity => entity.DisplayName)
            .HasColumnName("display_name")
            .HasMaxLength(200)
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.Email })
            .IsUnique()
            .HasDatabaseName("uq_users_tenant_id_email");
    }
}

internal sealed class ApplicationRoleConfiguration : IEntityTypeConfiguration<ApplicationRole>
{
    public void Configure(EntityTypeBuilder<ApplicationRole> builder)
    {
        builder.ToTable("roles");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.Name).HasColumnName("name").HasMaxLength(100).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.Name })
            .IsUnique()
            .HasDatabaseName("uq_roles_tenant_id_name");
    }
}

internal sealed class StationConfiguration : IEntityTypeConfiguration<Station>
{
    public void Configure(EntityTypeBuilder<Station> builder)
    {
        builder.ToTable("stations");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.FactoryId).HasColumnName("factory_id").IsRequired();
        builder.Property(entity => entity.StationCode)
            .HasColumnName("station_code")
            .HasMaxLength(100)
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.StationCode })
            .IsUnique()
            .HasDatabaseName("uq_stations_tenant_id_station_code");
    }
}

internal sealed class CameraConfiguration : IEntityTypeConfiguration<Camera>
{
    public void Configure(EntityTypeBuilder<Camera> builder)
    {
        builder.ToTable("cameras");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.SerialNumber)
            .HasColumnName("serial_number")
            .HasMaxLength(200)
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.SerialNumber })
            .IsUnique()
            .HasDatabaseName("uq_cameras_tenant_id_serial_number");
    }
}

internal sealed class CalibrationRecordConfiguration : IEntityTypeConfiguration<CalibrationRecord>
{
    public void Configure(EntityTypeBuilder<CalibrationRecord> builder)
    {
        builder.ToTable("calibration_records");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.CameraId).HasColumnName("camera_id").IsRequired();
        builder.Property(entity => entity.Version).HasColumnName("version").IsRequired();
        builder.Property(entity => entity.Mode).HasColumnName("mode").HasMaxLength(20).IsRequired();
        builder.Property(entity => entity.OperatorId).HasColumnName("operator_id").IsRequired();
        builder.Property(entity => entity.ArtefactId)
            .HasColumnName("artefact_id")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.CalibratedAtUtc)
            .HasColumnName("calibrated_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.ExpiresAtUtc)
            .HasColumnName("expires_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.MetricsJson)
            .HasColumnName("metrics")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.CalibrationBlobSha256)
            .HasColumnName("calibration_blob_sha256")
            .HasMaxLength(128)
            .IsRequired();
        builder.Property(entity => entity.SupersededAtUtc)
            .HasColumnName("superseded_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.CameraId, entity.Version })
            .IsUnique()
            .HasDatabaseName("uq_calibration_records_camera_id_version");
    }
}

internal sealed class CaptureAssetConfiguration : IEntityTypeConfiguration<CaptureAsset>
{
    public void Configure(EntityTypeBuilder<CaptureAsset> builder)
    {
        builder.ToTable("capture_assets");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.CaptureId).HasColumnName("capture_id").IsRequired();
        builder.Property(entity => entity.ObjectKey)
            .HasColumnName("object_key")
            .HasMaxLength(1024)
            .IsRequired();
        builder.Property(entity => entity.ContentType)
            .HasColumnName("content_type")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.SizeBytes).HasColumnName("size_bytes").IsRequired();
        builder.Property(entity => entity.ChecksumSha256)
            .HasColumnName("checksum_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.RetentionCategory)
            .HasColumnName("retention_category")
            .HasMaxLength(50)
            .HasDefaultValue("standard")
            .IsRequired();
        builder.Property(entity => entity.Encrypted)
            .HasColumnName("encrypted")
            .HasDefaultValue(false)
            .IsRequired();
        builder.Property(entity => entity.UploadCompletedAtUtc)
            .HasColumnName("upload_completed_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.CaptureId })
            .IsUnique()
            .HasDatabaseName("uq_capture_assets_tenant_id_capture_id");
        builder.HasIndex(entity => entity.ObjectKey)
            .IsUnique()
            .HasDatabaseName("uq_capture_assets_object_key");
    }
}

internal sealed class GarmentCategoryConfiguration : IEntityTypeConfiguration<GarmentCategory>
{
    public void Configure(EntityTypeBuilder<GarmentCategory> builder)
    {
        builder.ToTable("garment_categories");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.Name).HasColumnName("name").HasMaxLength(200).IsRequired();
    }
}

internal sealed class StyleConfiguration : IEntityTypeConfiguration<Style>
{
    public void Configure(EntityTypeBuilder<Style> builder)
    {
        builder.ToTable("styles");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.GarmentCategoryId)
            .HasColumnName("garment_category_id")
            .IsRequired();
        builder.Property(entity => entity.StyleCode)
            .HasColumnName("style_code")
            .HasMaxLength(100)
            .IsRequired();
    }
}

internal sealed class SizeConfiguration : IEntityTypeConfiguration<Size>
{
    public void Configure(EntityTypeBuilder<Size> builder)
    {
        builder.ToTable("sizes");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StyleId).HasColumnName("style_id").IsRequired();
        builder.Property(entity => entity.SizeCode)
            .HasColumnName("size_code")
            .HasMaxLength(100)
            .IsRequired();
    }
}

internal sealed class TechPackVersionConfiguration : IEntityTypeConfiguration<TechPackVersion>
{
    public void Configure(EntityTypeBuilder<TechPackVersion> builder)
    {
        builder.ToTable("tech_pack_versions");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.TechPackId).HasColumnName("tech_pack_id").IsRequired();
        builder.Property(entity => entity.Version).HasColumnName("version").IsRequired();
        builder.Property(entity => entity.Brand).HasColumnName("brand").HasMaxLength(200).IsRequired();
        builder.Property(entity => entity.StyleCode)
            .HasColumnName("style_code")
            .HasMaxLength(100)
            .IsRequired();
        builder.Property(entity => entity.GarmentCategory)
            .HasColumnName("garment_category")
            .HasMaxLength(100)
            .IsRequired();
        builder.Property(entity => entity.DataJson)
            .HasColumnName("data")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.VersionHashSha256)
            .HasColumnName("version_hash_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.Approved).HasColumnName("approved").IsRequired();
        builder.Property(entity => entity.ReferencedAtUtc)
            .HasColumnName("referenced_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.TechPackId, entity.Version })
            .IsUnique()
            .HasDatabaseName("uq_tech_pack_versions_tenant_id_tech_pack_id_version");
    }
}

internal sealed class EvidenceRecordConfiguration : IEntityTypeConfiguration<EvidenceRecord>
{
    public void Configure(EntityTypeBuilder<EvidenceRecord> builder)
    {
        builder.ToTable("evidence_records");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.InspectionId).HasColumnName("inspection_id").IsRequired();
        builder.Property(entity => entity.CaptureId).HasColumnName("capture_id").IsRequired();
        builder.Property(entity => entity.CaptureHashSha256)
            .HasColumnName("capture_hash_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.EvidenceJson)
            .HasColumnName("evidence")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.PreviousHashSha256)
            .HasColumnName("previous_hash_sha256")
            .HasMaxLength(64);
        builder.Property(entity => entity.RecordHashSha256)
            .HasColumnName("record_hash_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.InspectionId })
            .IsUnique()
            .HasDatabaseName("uq_evidence_records_tenant_id_inspection_id");
        builder.HasIndex(entity => entity.RecordHashSha256)
            .IsUnique()
            .HasDatabaseName("uq_evidence_records_record_hash_sha256");
    }
}

internal sealed class AuditEventConfiguration : IEntityTypeConfiguration<AuditEvent>
{
    public void Configure(EntityTypeBuilder<AuditEvent> builder)
    {
        builder.ToTable("audit_events");
        builder.HasKey(entity => entity.Id);
        builder.Property(entity => entity.Id).HasColumnName("id").HasDefaultValueSql("gen_random_uuid()");
        builder.Property(entity => entity.TenantId).HasColumnName("tenant_id").IsRequired();
        builder.Property(entity => entity.EventType)
            .HasColumnName("event_type")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.EntityType)
            .HasColumnName("entity_type")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.EntityId).HasColumnName("entity_id").IsRequired();
        builder.Property(entity => entity.ActorId).HasColumnName("actor_id");
        builder.Property(entity => entity.PayloadJson)
            .HasColumnName("payload")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.OccurredAtUtc)
            .HasColumnName("occurred_at_utc")
            .HasColumnType("timestamptz")
            .HasDefaultValueSql("now()")
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.OccurredAtUtc })
            .HasDatabaseName("ix_audit_events_tenant_id_occurred_at_utc");
    }
}
