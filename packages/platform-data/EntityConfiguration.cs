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

internal sealed class TenantEntityConfiguration : IEntityTypeConfiguration<Tenant>
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
        builder.Property(entity => entity.ExternalSubject)
            .HasColumnName("external_subject")
            .HasMaxLength(300);
        builder.Property(entity => entity.IsActive)
            .HasColumnName("is_active")
            .HasDefaultValue(true)
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.Email })
            .IsUnique()
            .HasDatabaseName("uq_users_tenant_id_email");
        builder.HasIndex(entity => new { entity.TenantId, entity.ExternalSubject })
            .IsUnique()
            .HasDatabaseName("uq_users_tenant_id_external_subject");
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

internal sealed class ApplicationUserRoleConfiguration : IEntityTypeConfiguration<ApplicationUserRole>
{
    public void Configure(EntityTypeBuilder<ApplicationUserRole> builder)
    {
        builder.ToTable("user_roles");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.UserId).HasColumnName("user_id").IsRequired();
        builder.Property(entity => entity.RoleId).HasColumnName("role_id").IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.UserId, entity.RoleId })
            .IsUnique()
            .HasDatabaseName("uq_user_roles_tenant_id_user_id_role_id");
    }
}

internal sealed class ApplicationRolePermissionConfiguration : IEntityTypeConfiguration<ApplicationRolePermission>
{
    public void Configure(EntityTypeBuilder<ApplicationRolePermission> builder)
    {
        builder.ToTable("role_permissions");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.RoleId).HasColumnName("role_id").IsRequired();
        builder.Property(entity => entity.Permission)
            .HasColumnName("permission")
            .HasMaxLength(200)
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.RoleId, entity.Permission })
            .IsUnique()
            .HasDatabaseName("uq_role_permissions_tenant_id_role_id_permission");
    }
}

internal sealed class TenantConfigurationConfiguration : IEntityTypeConfiguration<TenantConfiguration>
{
    public void Configure(EntityTypeBuilder<TenantConfiguration> builder)
    {
        builder.ToTable("tenant_configurations");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.ConfigurationJson)
            .HasColumnName("configuration")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.ObjectStorageBucket)
            .HasColumnName("object_storage_bucket")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.RetentionDays)
            .HasColumnName("retention_days")
            .HasDefaultValue(365)
            .IsRequired();
        builder.HasIndex(entity => entity.TenantId)
            .IsUnique()
            .HasDatabaseName("uq_tenant_configurations_tenant_id");
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

internal sealed class DeviceIdentityConfiguration : IEntityTypeConfiguration<DeviceIdentity>
{
    public void Configure(EntityTypeBuilder<DeviceIdentity> builder)
    {
        builder.ToTable("device_identities");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.CertificateThumbprintSha256)
            .HasColumnName("certificate_thumbprint_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.PublicKeyPem).HasColumnName("public_key_pem").IsRequired();
        builder.Property(entity => entity.NotBeforeUtc)
            .HasColumnName("not_before_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.ExpiresAtUtc)
            .HasColumnName("expires_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.Active).HasColumnName("active").HasDefaultValue(true).IsRequired();
        builder.Property(entity => entity.RotatedAtUtc)
            .HasColumnName("rotated_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.CertificateThumbprintSha256 })
            .IsUnique()
            .HasDatabaseName("uq_device_identities_tenant_id_certificate_thumbprint_sha256");
    }
}

internal sealed class StationHealthReportConfiguration : IEntityTypeConfiguration<StationHealthReport>
{
    public void Configure(EntityTypeBuilder<StationHealthReport> builder)
    {
        builder.ToTable("station_health_reports");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.CameraStatus).HasColumnName("camera_status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.StorageStatus).HasColumnName("storage_status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.ClockStatus).HasColumnName("clock_status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.OfflineQueueDepth).HasColumnName("offline_queue_depth").IsRequired();
        builder.Property(entity => entity.CheckedAtUtc)
            .HasColumnName("checked_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.StationId, entity.CheckedAtUtc })
            .HasDatabaseName("ix_station_health_reports_tenant_id_station_id_checked_at_utc");
    }
}

internal sealed class StationDiagnosticReportConfiguration : IEntityTypeConfiguration<StationDiagnosticReport>
{
    public void Configure(EntityTypeBuilder<StationDiagnosticReport> builder)
    {
        builder.ToTable("station_diagnostic_reports");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.DiagnosticsJson)
            .HasColumnName("diagnostics")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.RequestedAtUtc)
            .HasColumnName("requested_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.CompletedAtUtc)
            .HasColumnName("completed_at_utc")
            .HasColumnType("timestamptz");
    }
}

internal sealed class StationConfigurationVersionConfiguration
    : IEntityTypeConfiguration<StationConfigurationVersion>
{
    public void Configure(EntityTypeBuilder<StationConfigurationVersion> builder)
    {
        builder.ToTable("station_configuration_versions");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.Version).HasColumnName("version").IsRequired();
        builder.Property(entity => entity.ConfigurationJson)
            .HasColumnName("configuration")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.PushedAtUtc)
            .HasColumnName("pushed_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.AppliedAtUtc)
            .HasColumnName("applied_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.StationId, entity.Version })
            .IsUnique()
            .HasDatabaseName("uq_station_configuration_versions_tenant_id_station_id_version");
    }
}

internal sealed class StationSoftwareVersionConfiguration : IEntityTypeConfiguration<StationSoftwareVersion>
{
    public void Configure(EntityTypeBuilder<StationSoftwareVersion> builder)
    {
        builder.ToTable("station_software_versions");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.ComponentName)
            .HasColumnName("component_name")
            .HasMaxLength(100)
            .IsRequired();
        builder.Property(entity => entity.Version).HasColumnName("version").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.ReportedAtUtc)
            .HasColumnName("reported_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.StationId, entity.ComponentName })
            .IsUnique()
            .HasDatabaseName("uq_station_software_versions_tenant_id_station_id_component_name");
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

internal sealed class BrandConfiguration : IEntityTypeConfiguration<Brand>
{
    public void Configure(EntityTypeBuilder<Brand> builder)
    {
        builder.ToTable("brands");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.Name).HasColumnName("name").HasMaxLength(200).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.Name })
            .IsUnique()
            .HasDatabaseName("uq_brands_tenant_id_name");
    }
}

internal sealed class ProductionOrderConfiguration : IEntityTypeConfiguration<ProductionOrder>
{
    public void Configure(EntityTypeBuilder<ProductionOrder> builder)
    {
        builder.ToTable("production_orders");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.BrandId).HasColumnName("brand_id").IsRequired();
        builder.Property(entity => entity.OrderCode).HasColumnName("order_code").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.SupplierName).HasColumnName("supplier_name").HasMaxLength(200).IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.OrderCode })
            .IsUnique()
            .HasDatabaseName("uq_production_orders_tenant_id_order_code");
    }
}

internal sealed class ProductionOrderLineConfiguration : IEntityTypeConfiguration<ProductionOrderLine>
{
    public void Configure(EntityTypeBuilder<ProductionOrderLine> builder)
    {
        builder.ToTable("production_order_lines");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.ProductionOrderId).HasColumnName("production_order_id").IsRequired();
        builder.Property(entity => entity.StyleId).HasColumnName("style_id").IsRequired();
        builder.Property(entity => entity.SizeId).HasColumnName("size_id").IsRequired();
        builder.Property(entity => entity.PlannedQuantity).HasColumnName("planned_quantity").IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.ProductionOrderId })
            .HasDatabaseName("ix_production_order_lines_tenant_id_production_order_id");
    }
}

internal sealed class InspectionBatchConfiguration : IEntityTypeConfiguration<InspectionBatch>
{
    public void Configure(EntityTypeBuilder<InspectionBatch> builder)
    {
        builder.ToTable("inspection_batches");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.ProductionOrderLineId).HasColumnName("production_order_line_id").IsRequired();
        builder.Property(entity => entity.BatchCode).HasColumnName("batch_code").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.BatchCode })
            .IsUnique()
            .HasDatabaseName("uq_inspection_batches_tenant_id_batch_code");
    }
}

internal sealed class TechPackImportDraftConfiguration : IEntityTypeConfiguration<TechPackImportDraft>
{
    public void Configure(EntityTypeBuilder<TechPackImportDraft> builder)
    {
        builder.ToTable("tech_pack_import_drafts");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.TechPackId).HasColumnName("tech_pack_id").IsRequired();
        builder.Property(entity => entity.OriginalFileName).HasColumnName("original_file_name").HasMaxLength(260).IsRequired();
        builder.Property(entity => entity.ContentType).HasColumnName("content_type").HasMaxLength(200).IsRequired();
        builder.Property(entity => entity.DraftJson).HasColumnName("draft").HasColumnType("jsonb").IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.SourceHashSha256).HasColumnName("source_hash_sha256").HasMaxLength(64).IsRequired();
        builder.Property(entity => entity.ApprovedAtUtc).HasColumnName("approved_at_utc").HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.TechPackId, entity.SourceHashSha256 })
            .IsUnique()
            .HasDatabaseName("uq_tech_pack_import_drafts_tenant_id_tech_pack_id_source_hash");
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
        builder.Property(entity => entity.SigningKeyId).HasColumnName("signing_key_id");
        builder.Property(entity => entity.SignatureAlgorithm)
            .HasColumnName("signature_algorithm")
            .HasMaxLength(100);
        builder.Property(entity => entity.SignatureValueBase64).HasColumnName("signature_value_base64");
        builder.Property(entity => entity.SignedAtUtc)
            .HasColumnName("signed_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.InspectionId })
            .IsUnique()
            .HasDatabaseName("uq_evidence_records_tenant_id_inspection_id");
        builder.HasIndex(entity => entity.RecordHashSha256)
            .IsUnique()
            .HasDatabaseName("uq_evidence_records_record_hash_sha256");
    }
}

internal sealed class EvidenceSigningKeyConfiguration : IEntityTypeConfiguration<EvidenceSigningKey>
{
    public void Configure(EntityTypeBuilder<EvidenceSigningKey> builder)
    {
        builder.ToTable("evidence_signing_keys");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.KeyId).HasColumnName("key_id").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.Algorithm).HasColumnName("algorithm").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.PublicKeyPem).HasColumnName("public_key_pem").IsRequired();
        builder.Property(entity => entity.EncryptedPrivateKeyPem).HasColumnName("encrypted_private_key_pem");
        builder.Property(entity => entity.Active).HasColumnName("active").HasDefaultValue(true).IsRequired();
        builder.Property(entity => entity.RetiredAtUtc)
            .HasColumnName("retired_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.KeyId })
            .IsUnique()
            .HasDatabaseName("uq_evidence_signing_keys_tenant_id_key_id");
    }
}

internal sealed class InspectionRecordConfiguration : IEntityTypeConfiguration<InspectionRecord>
{
    public void Configure(EntityTypeBuilder<InspectionRecord> builder)
    {
        builder.ToTable("inspection_records");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.CaptureId).HasColumnName("capture_id").IsRequired();
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.BatchId).HasColumnName("batch_id");
        builder.Property(entity => entity.StationCode)
            .HasColumnName("station_code")
            .HasMaxLength(100)
            .IsRequired();
        builder.Property(entity => entity.OrderCode).HasColumnName("order_code").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.StyleCode).HasColumnName("style_code").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.SizeCode).HasColumnName("size_code").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.InspectionResultJson)
            .HasColumnName("inspection_result")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.EvidenceRecordHash)
            .HasColumnName("evidence_record_hash")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.CapturedAtUtc)
            .HasColumnName("captured_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.DeletedAtUtc)
            .HasColumnName("deleted_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.CapturedAtUtc })
            .HasDatabaseName("ix_inspection_records_tenant_id_captured_at_utc");
        builder.HasIndex(entity => new { entity.TenantId, entity.BatchId })
            .HasDatabaseName("ix_inspection_records_tenant_id_batch_id");
        builder.HasIndex(entity => new { entity.TenantId, entity.OrderCode, entity.StyleCode, entity.SizeCode })
            .HasDatabaseName("ix_inspection_records_tenant_id_order_style_size");
    }
}

internal sealed class ReviewActionConfiguration : IEntityTypeConfiguration<ReviewAction>
{
    public void Configure(EntityTypeBuilder<ReviewAction> builder)
    {
        builder.ToTable("review_actions");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.InspectionId).HasColumnName("inspection_id").IsRequired();
        builder.Property(entity => entity.ActorId).HasColumnName("actor_id");
        builder.Property(entity => entity.Outcome).HasColumnName("outcome").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.Note).HasColumnName("note").HasMaxLength(4000).IsRequired();
        builder.HasIndex(entity => new { entity.TenantId, entity.InspectionId, entity.CreatedAtUtc })
            .HasDatabaseName("ix_review_actions_tenant_id_inspection_id_created_at_utc");
    }
}

internal sealed class SyncEnvelopeConfiguration : IEntityTypeConfiguration<SyncEnvelope>
{
    public void Configure(EntityTypeBuilder<SyncEnvelope> builder)
    {
        builder.ToTable("sync_envelopes");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.StationId).HasColumnName("station_id").IsRequired();
        builder.Property(entity => entity.IdempotencyKey)
            .HasColumnName("idempotency_key")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.EntityType)
            .HasColumnName("entity_type")
            .HasMaxLength(200)
            .IsRequired();
        builder.Property(entity => entity.EntityId).HasColumnName("entity_id").IsRequired();
        builder.Property(entity => entity.PayloadJson)
            .HasColumnName("payload")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.PayloadHashSha256)
            .HasColumnName("payload_hash_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.Attempts).HasColumnName("attempts").HasDefaultValue(0).IsRequired();
        builder.Property(entity => entity.ConflictJson).HasColumnName("conflict").HasColumnType("jsonb");
        builder.Property(entity => entity.LastAttemptAtUtc)
            .HasColumnName("last_attempt_at_utc")
            .HasColumnType("timestamptz");
        builder.Property(entity => entity.DeadLetteredAtUtc)
            .HasColumnName("dead_lettered_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.StationId, entity.IdempotencyKey })
            .IsUnique()
            .HasDatabaseName("uq_sync_envelopes_tenant_id_station_id_idempotency_key");
    }
}

internal sealed class WebhookSubscriptionConfiguration : IEntityTypeConfiguration<WebhookSubscription>
{
    public void Configure(EntityTypeBuilder<WebhookSubscription> builder)
    {
        builder.ToTable("webhook_subscriptions");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.Url).HasColumnName("url").HasMaxLength(2048).IsRequired();
        builder.Property(entity => entity.EventTypesJson)
            .HasColumnName("event_types")
            .HasColumnType("jsonb")
            .IsRequired();
        builder.Property(entity => entity.SecretHashSha256)
            .HasColumnName("secret_hash_sha256")
            .HasMaxLength(64)
            .IsRequired();
        builder.Property(entity => entity.Active).HasColumnName("active").HasDefaultValue(true).IsRequired();
    }
}

internal sealed class BackgroundJobRecordConfiguration : IEntityTypeConfiguration<BackgroundJobRecord>
{
    public void Configure(EntityTypeBuilder<BackgroundJobRecord> builder)
    {
        builder.ToTable("background_jobs");
        EntityConfiguration.ConfigureTenantEntity(builder);
        builder.Property(entity => entity.QueueName).HasColumnName("queue_name").HasMaxLength(100).IsRequired();
        builder.Property(entity => entity.JobType).HasColumnName("job_type").HasMaxLength(200).IsRequired();
        builder.Property(entity => entity.PayloadJson).HasColumnName("payload").HasColumnType("jsonb").IsRequired();
        builder.Property(entity => entity.Status).HasColumnName("status").HasMaxLength(50).IsRequired();
        builder.Property(entity => entity.Attempts).HasColumnName("attempts").HasDefaultValue(0).IsRequired();
        builder.Property(entity => entity.AvailableAtUtc)
            .HasColumnName("available_at_utc")
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.Property(entity => entity.StartedAtUtc)
            .HasColumnName("started_at_utc")
            .HasColumnType("timestamptz");
        builder.Property(entity => entity.CompletedAtUtc)
            .HasColumnName("completed_at_utc")
            .HasColumnType("timestamptz");
        builder.HasIndex(entity => new { entity.TenantId, entity.QueueName, entity.Status, entity.AvailableAtUtc })
            .HasDatabaseName("ix_background_jobs_tenant_id_queue_name_status_available_at_utc");
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
