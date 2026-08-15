using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace SpecProof.Platform.Data.Migrations;

[DbContext(typeof(SpecProofDbContext))]
[Migration("20260815073000_Phase7PerformanceIndexes")]
public sealed class Phase7PerformanceIndexes : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateIndex(
            name: "ix_evidence_records_tenant_id_created_at_utc",
            table: "evidence_records",
            columns: ["tenant_id", "created_at_utc"]);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.DropIndex(
            name: "ix_evidence_records_tenant_id_created_at_utc",
            table: "evidence_records");
    }
}
