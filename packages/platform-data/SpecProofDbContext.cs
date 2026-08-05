using Microsoft.EntityFrameworkCore;

namespace SpecProof.Platform.Data;

public sealed class SpecProofDbContext(DbContextOptions<SpecProofDbContext> options) : DbContext(options)
{
    public DbSet<Tenant> Tenants => Set<Tenant>();

    public DbSet<Organisation> Organisations => Set<Organisation>();

    public DbSet<Factory> Factories => Set<Factory>();

    public DbSet<ApplicationUser> Users => Set<ApplicationUser>();

    public DbSet<ApplicationRole> Roles => Set<ApplicationRole>();

    public DbSet<Station> Stations => Set<Station>();

    public DbSet<Camera> Cameras => Set<Camera>();

    public DbSet<CalibrationRecord> CalibrationRecords => Set<CalibrationRecord>();

    public DbSet<CaptureAsset> CaptureAssets => Set<CaptureAsset>();

    public DbSet<GarmentCategory> GarmentCategories => Set<GarmentCategory>();

    public DbSet<Style> Styles => Set<Style>();

    public DbSet<Size> Sizes => Set<Size>();

    public DbSet<TechPackVersion> TechPackVersions => Set<TechPackVersion>();

    public DbSet<EvidenceRecord> EvidenceRecords => Set<EvidenceRecord>();

    public DbSet<AuditEvent> AuditEvents => Set<AuditEvent>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(SpecProofDbContext).Assembly);
    }
}
