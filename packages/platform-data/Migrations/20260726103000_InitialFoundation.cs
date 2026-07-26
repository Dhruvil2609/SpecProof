using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace SpecProof.Platform.Data.Migrations;

public partial class InitialFoundation : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql("CREATE EXTENSION IF NOT EXISTS pgcrypto;");

        migrationBuilder.CreateTable(
            name: "tenants",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_tenants", x => x.id));

        migrationBuilder.CreateTable(
            name: "organisations",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_organisations", x => x.id);
                table.ForeignKey("fk_organisations_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "roles",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_roles", x => x.id);
                table.ForeignKey("fk_roles_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "users",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                email = table.Column<string>(type: "character varying(320)", maxLength: 320, nullable: false),
                display_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_users", x => x.id);
                table.ForeignKey("fk_users_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "audit_events",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                event_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                entity_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                entity_id = table.Column<Guid>(type: "uuid", nullable: false),
                actor_id = table.Column<Guid>(type: "uuid", nullable: true),
                payload = table.Column<string>(type: "jsonb", nullable: false),
                occurred_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_audit_events", x => x.id);
                table.ForeignKey("fk_audit_events_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "factories",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                organisation_id = table.Column<Guid>(type: "uuid", nullable: false),
                name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_factories", x => x.id);
                table.ForeignKey("fk_factories_organisations_organisation_id", x => x.organisation_id, "organisations", "id", onDelete: ReferentialAction.Cascade);
                table.ForeignKey("fk_factories_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "garment_categories",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_garment_categories", x => x.id);
                table.ForeignKey("fk_garment_categories_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "stations",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                factory_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_stations", x => x.id);
                table.ForeignKey("fk_stations_factories_factory_id", x => x.factory_id, "factories", "id", onDelete: ReferentialAction.Cascade);
                table.ForeignKey("fk_stations_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "styles",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                garment_category_id = table.Column<Guid>(type: "uuid", nullable: false),
                style_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_styles", x => x.id);
                table.ForeignKey("fk_styles_garment_categories_garment_category_id", x => x.garment_category_id, "garment_categories", "id", onDelete: ReferentialAction.Cascade);
                table.ForeignKey("fk_styles_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "cameras",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                serial_number = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_cameras", x => x.id);
                table.ForeignKey("fk_cameras_stations_station_id", x => x.station_id, "stations", "id", onDelete: ReferentialAction.Cascade);
                table.ForeignKey("fk_cameras_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "sizes",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                style_id = table.Column<Guid>(type: "uuid", nullable: false),
                size_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_sizes", x => x.id);
                table.ForeignKey("fk_sizes_styles_style_id", x => x.style_id, "styles", "id", onDelete: ReferentialAction.Cascade);
                table.ForeignKey("fk_sizes_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        migrationBuilder.CreateTable(
            name: "calibration_records",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                camera_id = table.Column<Guid>(type: "uuid", nullable: false),
                calibrated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                calibration_blob_sha256 = table.Column<string>(type: "character varying(128)", maxLength: 128, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_calibration_records", x => x.id);
                table.ForeignKey("fk_calibration_records_cameras_camera_id", x => x.camera_id, "cameras", "id", onDelete: ReferentialAction.Cascade);
                table.ForeignKey("fk_calibration_records_tenants_tenant_id", x => x.tenant_id, "tenants", "id", onDelete: ReferentialAction.Cascade);
            });

        CreateIndexes(migrationBuilder);

        migrationBuilder.Sql(
            """
            CREATE OR REPLACE FUNCTION prevent_audit_modification()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'Audit events cannot be modified or deleted';
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER no_update_or_delete_audit_events
                BEFORE UPDATE OR DELETE ON audit_events
                FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql("DROP TRIGGER IF EXISTS no_update_or_delete_audit_events ON audit_events;");
        migrationBuilder.Sql("DROP FUNCTION IF EXISTS prevent_audit_modification();");

        migrationBuilder.DropTable("calibration_records");
        migrationBuilder.DropTable("audit_events");
        migrationBuilder.DropTable("roles");
        migrationBuilder.DropTable("sizes");
        migrationBuilder.DropTable("users");
        migrationBuilder.DropTable("cameras");
        migrationBuilder.DropTable("styles");
        migrationBuilder.DropTable("stations");
        migrationBuilder.DropTable("garment_categories");
        migrationBuilder.DropTable("factories");
        migrationBuilder.DropTable("organisations");
        migrationBuilder.DropTable("tenants");
    }

    private static void CreateIndexes(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateIndex("uq_tenants_name", "tenants", "name", unique: true);
        migrationBuilder.CreateIndex("uq_organisations_tenant_id_name", "organisations", new[] { "tenant_id", "name" }, unique: true);
        migrationBuilder.CreateIndex("uq_factories_tenant_id_name", "factories", new[] { "tenant_id", "name" }, unique: true);
        migrationBuilder.CreateIndex("uq_users_tenant_id_email", "users", new[] { "tenant_id", "email" }, unique: true);
        migrationBuilder.CreateIndex("uq_roles_tenant_id_name", "roles", new[] { "tenant_id", "name" }, unique: true);
        migrationBuilder.CreateIndex("uq_stations_tenant_id_station_code", "stations", new[] { "tenant_id", "station_code" }, unique: true);
        migrationBuilder.CreateIndex("uq_cameras_tenant_id_serial_number", "cameras", new[] { "tenant_id", "serial_number" }, unique: true);
        migrationBuilder.CreateIndex("ix_audit_events_tenant_id_occurred_at_utc", "audit_events", new[] { "tenant_id", "occurred_at_utc" });
        migrationBuilder.CreateIndex("ix_calibration_records_tenant_id", "calibration_records", "tenant_id");
        migrationBuilder.CreateIndex("ix_factories_organisation_id", "factories", "organisation_id");
        migrationBuilder.CreateIndex("ix_stations_factory_id", "stations", "factory_id");
        migrationBuilder.CreateIndex("ix_cameras_station_id", "cameras", "station_id");
        migrationBuilder.CreateIndex("ix_styles_garment_category_id", "styles", "garment_category_id");
        migrationBuilder.CreateIndex("ix_sizes_style_id", "sizes", "style_id");
        migrationBuilder.CreateIndex("ix_calibration_records_camera_id", "calibration_records", "camera_id");
    }
}
