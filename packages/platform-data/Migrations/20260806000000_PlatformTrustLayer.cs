using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

namespace SpecProof.Platform.Data.Migrations;

[DbContext(typeof(SpecProofDbContext))]
[Migration("20260806000000_PlatformTrustLayer")]
public sealed class PlatformTrustLayer : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<string>(
            name: "external_subject",
            table: "users",
            type: "character varying(300)",
            maxLength: 300,
            nullable: true);
        migrationBuilder.AddColumn<bool>(
            name: "is_active",
            table: "users",
            type: "boolean",
            nullable: false,
            defaultValue: true);
        migrationBuilder.AddColumn<Guid>(
            name: "signing_key_id",
            table: "evidence_records",
            type: "uuid",
            nullable: true);
        migrationBuilder.AddColumn<string>(
            name: "signature_algorithm",
            table: "evidence_records",
            type: "character varying(100)",
            maxLength: 100,
            nullable: true);
        migrationBuilder.AddColumn<string>(
            name: "signature_value_base64",
            table: "evidence_records",
            type: "text",
            nullable: true);
        migrationBuilder.AddColumn<DateTimeOffset>(
            name: "signed_at_utc",
            table: "evidence_records",
            type: "timestamptz",
            nullable: true);

        CreateTenantConfigurationTable(migrationBuilder);
        CreateRbacTables(migrationBuilder);
        CreateStationManagementTables(migrationBuilder);
        CreateTrustAndReportingTables(migrationBuilder);
        CreateSyncAndJobTables(migrationBuilder);

        migrationBuilder.CreateIndex(
            name: "uq_users_tenant_id_external_subject",
            table: "users",
            columns: new[] { "tenant_id", "external_subject" },
            unique: true);

        migrationBuilder.Sql(
            """
            CREATE OR REPLACE FUNCTION prevent_signed_evidence_modification()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.signed_at_utc IS NOT NULL THEN
                    RAISE EXCEPTION 'Signed evidence records cannot be modified or deleted';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER no_update_or_delete_signed_evidence_records
                BEFORE UPDATE OR DELETE ON evidence_records
                FOR EACH ROW EXECUTE FUNCTION prevent_signed_evidence_modification();
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql(
            """
            DROP TRIGGER IF EXISTS no_update_or_delete_signed_evidence_records ON evidence_records;
            DROP FUNCTION IF EXISTS prevent_signed_evidence_modification();
            """);

        migrationBuilder.DropTable("background_jobs");
        migrationBuilder.DropTable("webhook_subscriptions");
        migrationBuilder.DropTable("sync_envelopes");
        migrationBuilder.DropTable("inspection_records");
        migrationBuilder.DropTable("evidence_signing_keys");
        migrationBuilder.DropTable("station_software_versions");
        migrationBuilder.DropTable("station_configuration_versions");
        migrationBuilder.DropTable("station_diagnostic_reports");
        migrationBuilder.DropTable("station_health_reports");
        migrationBuilder.DropTable("device_identities");
        migrationBuilder.DropTable("tenant_configurations");
        migrationBuilder.DropTable("role_permissions");
        migrationBuilder.DropTable("user_roles");

        migrationBuilder.DropIndex("uq_users_tenant_id_external_subject", "users");
        migrationBuilder.DropColumn("external_subject", "users");
        migrationBuilder.DropColumn("is_active", "users");
        migrationBuilder.DropColumn("signing_key_id", "evidence_records");
        migrationBuilder.DropColumn("signature_algorithm", "evidence_records");
        migrationBuilder.DropColumn("signature_value_base64", "evidence_records");
        migrationBuilder.DropColumn("signed_at_utc", "evidence_records");
    }

    private static void CreateTenantConfigurationTable(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "tenant_configurations",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                configuration = table.Column<string>(type: "jsonb", nullable: false),
                object_storage_bucket = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                retention_days = table.Column<int>(type: "integer", nullable: false, defaultValue: 365),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table =>
            {
                table.PrimaryKey("pk_tenant_configurations", x => x.id);
                table.ForeignKey(
                    "fk_tenant_configurations_tenants_tenant_id",
                    x => x.tenant_id,
                    "tenants",
                    "id",
                    onDelete: ReferentialAction.Cascade);
            });
        migrationBuilder.CreateIndex(
            "uq_tenant_configurations_tenant_id",
            "tenant_configurations",
            "tenant_id",
            unique: true);
    }

    private static void CreateRbacTables(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "user_roles",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                user_id = table.Column<Guid>(type: "uuid", nullable: false),
                role_id = table.Column<Guid>(type: "uuid", nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_user_roles", x => x.id));
        migrationBuilder.CreateTable(
            name: "role_permissions",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                role_id = table.Column<Guid>(type: "uuid", nullable: false),
                permission = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_role_permissions", x => x.id));
        migrationBuilder.CreateIndex(
            "uq_user_roles_tenant_id_user_id_role_id",
            "user_roles",
            new[] { "tenant_id", "user_id", "role_id" },
            unique: true);
        migrationBuilder.CreateIndex(
            "uq_role_permissions_tenant_id_role_id_permission",
            "role_permissions",
            new[] { "tenant_id", "role_id", "permission" },
            unique: true);
    }

    private static void CreateStationManagementTables(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "device_identities",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                certificate_thumbprint_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                public_key_pem = table.Column<string>(type: "text", nullable: false),
                not_before_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                expires_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                active = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                rotated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_device_identities", x => x.id));
        migrationBuilder.CreateTable(
            name: "station_health_reports",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                camera_status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                storage_status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                clock_status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                offline_queue_depth = table.Column<long>(type: "bigint", nullable: false),
                checked_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_station_health_reports", x => x.id));
        migrationBuilder.CreateTable(
            name: "station_diagnostic_reports",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                diagnostics = table.Column<string>(type: "jsonb", nullable: false),
                requested_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                completed_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_station_diagnostic_reports", x => x.id));
        migrationBuilder.CreateTable(
            name: "station_configuration_versions",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                version = table.Column<int>(type: "integer", nullable: false),
                configuration = table.Column<string>(type: "jsonb", nullable: false),
                pushed_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                applied_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_station_configuration_versions", x => x.id));
        migrationBuilder.CreateTable(
            name: "station_software_versions",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                component_name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                version = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                reported_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_station_software_versions", x => x.id));
        migrationBuilder.CreateIndex("uq_device_identities_tenant_id_certificate_thumbprint_sha256", "device_identities", new[] { "tenant_id", "certificate_thumbprint_sha256" }, unique: true);
        migrationBuilder.CreateIndex("ix_station_health_reports_tenant_id_station_id_checked_at_utc", "station_health_reports", new[] { "tenant_id", "station_id", "checked_at_utc" });
        migrationBuilder.CreateIndex("uq_station_configuration_versions_tenant_id_station_id_version", "station_configuration_versions", new[] { "tenant_id", "station_id", "version" }, unique: true);
        migrationBuilder.CreateIndex("uq_station_software_versions_tenant_id_station_id_component_name", "station_software_versions", new[] { "tenant_id", "station_id", "component_name" }, unique: true);
    }

    private static void CreateTrustAndReportingTables(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "evidence_signing_keys",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                key_id = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                algorithm = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                public_key_pem = table.Column<string>(type: "text", nullable: false),
                encrypted_private_key_pem = table.Column<string>(type: "text", nullable: true),
                active = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                retired_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_evidence_signing_keys", x => x.id));
        migrationBuilder.CreateTable(
            name: "inspection_records",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                batch_id = table.Column<Guid>(type: "uuid", nullable: true),
                station_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                inspection_result = table.Column<string>(type: "jsonb", nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                evidence_record_hash = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                captured_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                deleted_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_inspection_records", x => x.id));
        migrationBuilder.CreateIndex("uq_evidence_signing_keys_tenant_id_key_id", "evidence_signing_keys", new[] { "tenant_id", "key_id" }, unique: true);
        migrationBuilder.CreateIndex("ix_inspection_records_tenant_id_captured_at_utc", "inspection_records", new[] { "tenant_id", "captured_at_utc" });
        migrationBuilder.CreateIndex("ix_inspection_records_tenant_id_batch_id", "inspection_records", new[] { "tenant_id", "batch_id" });
    }

    private static void CreateSyncAndJobTables(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.CreateTable(
            name: "sync_envelopes",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                station_id = table.Column<Guid>(type: "uuid", nullable: false),
                idempotency_key = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                entity_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                entity_id = table.Column<Guid>(type: "uuid", nullable: false),
                payload = table.Column<string>(type: "jsonb", nullable: false),
                payload_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                attempts = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                conflict = table.Column<string>(type: "jsonb", nullable: true),
                last_attempt_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                dead_lettered_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_sync_envelopes", x => x.id));
        migrationBuilder.CreateTable(
            name: "webhook_subscriptions",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                url = table.Column<string>(type: "character varying(2048)", maxLength: 2048, nullable: false),
                event_types = table.Column<string>(type: "jsonb", nullable: false),
                secret_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                active = table.Column<bool>(type: "boolean", nullable: false, defaultValue: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_webhook_subscriptions", x => x.id));
        migrationBuilder.CreateTable(
            name: "background_jobs",
            columns: table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                queue_name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                job_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                payload = table.Column<string>(type: "jsonb", nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                attempts = table.Column<int>(type: "integer", nullable: false, defaultValue: 0),
                available_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false),
                started_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                completed_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()")
            },
            constraints: table => table.PrimaryKey("pk_background_jobs", x => x.id));
        migrationBuilder.CreateIndex("uq_sync_envelopes_tenant_id_station_id_idempotency_key", "sync_envelopes", new[] { "tenant_id", "station_id", "idempotency_key" }, unique: true);
        migrationBuilder.CreateIndex("ix_background_jobs_tenant_id_queue_name_status_available_at_utc", "background_jobs", new[] { "tenant_id", "queue_name", "status", "available_at_utc" });
    }
}
