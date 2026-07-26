using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;

namespace SpecProof.Platform.Data.Migrations;

[DbContext(typeof(SpecProofDbContext))]
public sealed class SpecProofDbContextModelSnapshot : ModelSnapshot
{
    protected override void BuildModel(ModelBuilder modelBuilder)
    {
        modelBuilder.ApplyConfigurationsFromAssembly(typeof(SpecProofDbContext).Assembly);
    }
}
