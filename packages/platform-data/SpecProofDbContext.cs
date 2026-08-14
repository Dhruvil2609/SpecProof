using Microsoft.EntityFrameworkCore;

namespace SpecProof.Platform.Data;

public sealed class SpecProofDbContext(
    DbContextOptions<SpecProofDbContext> options,
    ITenantScope? tenantScope = null) : DbContext(options)
{
    public Guid? CurrentTenantId => tenantScope?.TenantId;

    public DbSet<Tenant> Tenants => Set<Tenant>();

    public DbSet<Organisation> Organisations => Set<Organisation>();

    public DbSet<Factory> Factories => Set<Factory>();

    public DbSet<ApplicationUser> Users => Set<ApplicationUser>();

    public DbSet<ApplicationRole> Roles => Set<ApplicationRole>();

    public DbSet<ApplicationUserRole> UserRoles => Set<ApplicationUserRole>();

    public DbSet<ApplicationRolePermission> RolePermissions => Set<ApplicationRolePermission>();

    public DbSet<TenantConfiguration> TenantConfigurations => Set<TenantConfiguration>();

    public DbSet<Station> Stations => Set<Station>();

    public DbSet<DeviceIdentity> DeviceIdentities => Set<DeviceIdentity>();

    public DbSet<StationHealthReport> StationHealthReports => Set<StationHealthReport>();

    public DbSet<StationDiagnosticReport> StationDiagnosticReports => Set<StationDiagnosticReport>();

    public DbSet<StationConfigurationVersion> StationConfigurationVersions => Set<StationConfigurationVersion>();

    public DbSet<StationSoftwareVersion> StationSoftwareVersions => Set<StationSoftwareVersion>();

    public DbSet<Camera> Cameras => Set<Camera>();

    public DbSet<CalibrationRecord> CalibrationRecords => Set<CalibrationRecord>();

    public DbSet<CaptureAsset> CaptureAssets => Set<CaptureAsset>();

    public DbSet<GarmentCategory> GarmentCategories => Set<GarmentCategory>();

    public DbSet<Style> Styles => Set<Style>();

    public DbSet<Size> Sizes => Set<Size>();

    public DbSet<Brand> Brands => Set<Brand>();

    public DbSet<ProductionOrder> ProductionOrders => Set<ProductionOrder>();

    public DbSet<ProductionOrderLine> ProductionOrderLines => Set<ProductionOrderLine>();

    public DbSet<InspectionBatch> InspectionBatches => Set<InspectionBatch>();

    public DbSet<TechPackImportDraft> TechPackImportDrafts => Set<TechPackImportDraft>();

    public DbSet<TechPackVersion> TechPackVersions => Set<TechPackVersion>();

    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();

    public DbSet<EvidenceSigningKey> EvidenceSigningKeys => Set<EvidenceSigningKey>();

    public DbSet<InspectionRecord> InspectionRecords => Set<InspectionRecord>();

    public DbSet<ReviewAction> ReviewActions => Set<ReviewAction>();

    public DbSet<SyncEnvelope> SyncEnvelopes => Set<SyncEnvelope>();

    public DbSet<WebhookSubscription> WebhookSubscriptions => Set<WebhookSubscription>();

    public DbSet<BackgroundJobRecord> BackgroundJobs => Set<BackgroundJobRecord>();

    public DbSet<AuditEvent> AuditEvents => Set<AuditEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(SpecProofDbContext).Assembly);
        ApplyTenantFilters(modelBuilder);
    }

    private void ApplyTenantFilters(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Organisation>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<Factory>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ApplicationUser>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ApplicationRole>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ApplicationUserRole>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ApplicationRolePermission>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<TenantConfiguration>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<Station>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<DeviceIdentity>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<StationHealthReport>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<StationDiagnosticReport>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<StationConfigurationVersion>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<StationSoftwareVersion>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<Camera>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<CalibrationRecord>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<CaptureAsset>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<GarmentCategory>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<Style>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<Size>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<Brand>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ProductionOrder>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ProductionOrderLine>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<InspectionBatch>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<TechPackImportDraft>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<TechPackVersion>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<EvidenceRecord>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<EvidenceSigningKey>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<InspectionRecord>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<ReviewAction>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<SyncEnvelope>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<WebhookSubscription>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
        modelBuilder.Entity<BackgroundJobRecord>().HasQueryFilter(entity => CurrentTenantId == null || entity.TenantId == CurrentTenantId);
    }
}
