using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace SpecProof.Platform.Data.Migrations;

[DbContext(typeof(SpecProofDbContext))]
[Migration("20260727170000_CaptureStationCore")]
public sealed class CaptureStationCore : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<string>(
            name: "artefact_id",
            table: "calibration_records",
            type: "character varying(200)",
            maxLength: 200,
            nullable: false,
            defaultValue: "legacy");
        migrationBuilder.AddColumn<DateTimeOffset>(
            name: "expires_at_utc",
            table: "calibration_records",
            type: "timestamptz",
            nullable: false,
            defaultValueSql: "now()");
        migrationBuilder.AddColumn<string>(
            name: "metrics",
            table: "calibration_records",
            type: "jsonb",
            nullable: false,
            defaultValue: "{}");
        migrationBuilder.AddColumn<string>(
            name: "mode",
            table: "calibration_records",
            type: "character varying(20)",
            maxLength: 20,
            nullable: false,
            defaultValue: "full");
        migrationBuilder.AddColumn<Guid>(
            name: "operator_id",
            table: "calibration_records",
            type: "uuid",
            nullable: false,
            defaultValue: Guid.Empty);
        migrationBuilder.AddColumn<DateTimeOffset>(
            name: "superseded_at_utc",
            table: "calibration_records",
            type: "timestamptz",
            nullable: true);
        migrationBuilder.AddColumn<int>(
            name: "version",
            table: "calibration_records",
            type: "integer",
            nullable: false,
            defaultValue: 1);

        migrationBuilder.CreateTable(
            name: "capture_assets",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                capture_id = table.Column<Guid>(type: "uuid", nullable: false),
                object_key = table.Column<string>(type: "character varying(1024)", maxLength: 1024, nullable: false),
                content_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                size_bytes = table.Column<long>(type: "bigint", nullable: false),
                checksum_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                retention_category = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false, defaultValue: "standard"),
                encrypted = table.Column<bool>(type: "boolean", nullable: false, defaultValue: false),
                upload_completed_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_capture_assets", x => x.id);
                table.ForeignKey(
                    name: "fk_capture_assets_stations_station_id",
                    column: x => x.station_id,
                    principalTable: "stations",
                    principalColumn: "id",
                    onDelete: ReferentialAction.Restrict);
                table.ForeignKey(
                    name: "fk_capture_assets_tenants_tenant_id",
                    column: x => x.tenant_id,
                    principalTable: "tenants",
                    principalColumn: "id",
                    onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateIndex(
            name: "uq_calibration_records_camera_id_version",
            table: "calibration_records",
            columns: new[] { "camera_id", "version" },
            unique: true);
        migrationBuilder.CreateIndex(
            name: "ix_capture_assets_station_id",
            table: "capture_assets",
            column: "station_id");
        migrationBuilder.CreateIndex(
            name: "ix_capture_assets_tenant_id",
            table: "capture_assets",
            column: "tenant_id");
        migrationBuilder.CreateIndex(
            name: "uq_capture_assets_object_key",
            table: "capture_assets",
            column: "object_key",
            unique: true);
        migrationBuilder.CreateIndex(
            name: "uq_capture_assets_tenant_id_capture_id",
            table: "capture_assets",
            columns: new[] { "tenant_id", "capture_id" },
            unique: true);

        migrationBuilder.Sql(
            """
            CREATE OR REPLACE FUNCTION prevent_calibration_modification()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Calibration records are append-only';
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER no_update_or_delete_calibration_records
                BEFORE UPDATE OR DELETE ON calibration_records
                FOR EACH ROW EXECUTE FUNCTION prevent_calibration_modification();
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql(
            """
            DROP TRIGGER IF EXISTS no_update_or_delete_calibration_records ON calibration_records;
            DROP FUNCTION IF EXISTS prevent_calibration_modification();
            """);
        migrationBuilder.DropTable(name: "capture_assets");
        migrationBuilder.DropIndex(
            name: "uq_calibration_records_camera_id_version",
            table: "calibration_records");
        migrationBuilder.DropColumn(name: "artefact_id", table: "calibration_records");
        migrationBuilder.DropColumn(name: "expires_at_utc", table: "calibration_records");
        migrationBuilder.DropColumn(name: "metrics", table: "calibration_records");
        migrationBuilder.DropColumn(name: "mode", table: "calibration_records");
        migrationBuilder.DropColumn(name: "operator_id", table: "calibration_records");
        migrationBuilder.DropColumn(name: "superseded_at_utc", table: "calibration_records");
        migrationBuilder.DropColumn(name: "version", table: "calibration_records");
    }
}
