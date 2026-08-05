using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace SpecProof.Platform.Data.Migrations;

[DbContext(typeof(SpecProofDbContext))]
[Migration("20260805000000_MeasurementEngine")]
public sealed class MeasurementEngine : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "tech_pack_versions",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                tech_pack_id = table.Column<Guid>(type: "uuid", nullable: false),
                version = table.Column<int>(type: "integer", nullable: false),
                brand = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                style_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                garment_category = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                data = table.Column<string>(type: "jsonb", nullable: false),
                version_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                approved = table.Column<bool>(type: "boolean", nullable: false),
                referenced_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_tech_pack_versions", x => x.id);
                table.ForeignKey(
                    name: "fk_tech_pack_versions_tenants_tenant_id",
                    column: x => x.tenant_id,
                    principalTable: "tenants",
                    principalColumn: "id",
                    onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "evidence_records",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                inspection_id = table.Column<Guid>(type: "uuid", nullable: false),
                capture_id = table.Column<Guid>(type: "uuid", nullable: false),
                capture_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                evidence = table.Column<string>(type: "jsonb", nullable: false),
                previous_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: true),
                record_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_evidence_records", x => x.id);
                table.ForeignKey(
                    name: "fk_evidence_records_tenants_tenant_id",
                    column: x => x.tenant_id,
                    principalTable: "tenants",
                    principalColumn: "id",
                    onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateIndex(
            name: "ix_tech_pack_versions_tenant_id",
            table: "tech_pack_versions",
            column: "tenant_id");
        migrationBuilder.CreateIndex(
            name: "uq_tech_pack_versions_tenant_id_tech_pack_id_version",
            table: "tech_pack_versions",
            columns: new[] { "tenant_id", "tech_pack_id", "version" },
            unique: true);
        migrationBuilder.CreateIndex(
            name: "ix_evidence_records_tenant_id",
            table: "evidence_records",
            column: "tenant_id");
        migrationBuilder.CreateIndex(
            name: "uq_evidence_records_tenant_id_inspection_id",
            table: "evidence_records",
            columns: new[] { "tenant_id", "inspection_id" },
            unique: true);
        migrationBuilder.CreateIndex(
            name: "uq_evidence_records_record_hash_sha256",
            table: "evidence_records",
            column: "record_hash_sha256",
            unique: true);

        migrationBuilder.Sql(
            """
            CREATE OR REPLACE FUNCTION prevent_tech_pack_referenced_modification()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.referenced_at_utc IS NOT NULL THEN
                    RAISE EXCEPTION 'Referenced tech-pack versions are immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER no_update_referenced_tech_pack_versions
                BEFORE UPDATE OR DELETE ON tech_pack_versions
                FOR EACH ROW EXECUTE FUNCTION prevent_tech_pack_referenced_modification();
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql(
            """
            DROP TRIGGER IF EXISTS no_update_referenced_tech_pack_versions ON tech_pack_versions;
            DROP FUNCTION IF EXISTS prevent_tech_pack_referenced_modification();
            """);
        migrationBuilder.DropTable(name: "evidence_records");
        migrationBuilder.DropTable(name: "tech_pack_versions");
    }
}
