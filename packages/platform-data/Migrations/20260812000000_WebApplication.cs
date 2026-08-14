using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;
using Microsoft.EntityFrameworkCore.Migrations.Operations.Builders;

namespace SpecProof.Platform.Data.Migrations;

[DbContext(typeof(SpecProofDbContext))]
[Migration("20260812000000_WebApplication")]
public sealed class WebApplication : Migration
{
    protected override void Up(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.AddColumn<Guid>(
            name: "capture_id",
            table: "inspection_records",
            type: "uuid",
            nullable: true);
        migrationBuilder.AddColumn<string>(
            name: "order_code",
            table: "inspection_records",
            type: "character varying(100)",
            maxLength: 100,
            nullable: true);
        migrationBuilder.AddColumn<string>(
            name: "style_code",
            table: "inspection_records",
            type: "character varying(100)",
            maxLength: 100,
            nullable: true);
        migrationBuilder.AddColumn<string>(
            name: "size_code",
            table: "inspection_records",
            type: "character varying(50)",
            maxLength: 50,
            nullable: true);

        migrationBuilder.Sql(
            """
            UPDATE inspection_records
            SET capture_id = id,
                order_code = 'UNASSIGNED',
                style_code = 'UNASSIGNED',
                size_code = 'UNASSIGNED';

            ALTER TABLE inspection_records ALTER COLUMN capture_id SET NOT NULL;
            ALTER TABLE inspection_records ALTER COLUMN order_code SET NOT NULL;
            ALTER TABLE inspection_records ALTER COLUMN style_code SET NOT NULL;
            ALTER TABLE inspection_records ALTER COLUMN size_code SET NOT NULL;
            """);

        CreateBrandTable(migrationBuilder);
        CreateProductionOrderTable(migrationBuilder);
        CreateProductionOrderLineTable(migrationBuilder);
        CreateInspectionBatchTable(migrationBuilder);
        CreateTechPackImportDraftTable(migrationBuilder);
        CreateReviewActionTable(migrationBuilder);

        migrationBuilder.CreateIndex(
            name: "ix_inspection_records_tenant_id_order_style_size",
            table: "inspection_records",
            columns: new[] { "tenant_id", "order_code", "style_code", "size_code" });

        migrationBuilder.Sql(
            """
            CREATE OR REPLACE FUNCTION prevent_review_action_modification()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Review actions are append-only';
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER no_update_or_delete_review_actions
                BEFORE UPDATE OR DELETE ON review_actions
                FOR EACH ROW EXECUTE FUNCTION prevent_review_action_modification();

            CREATE OR REPLACE FUNCTION prevent_approved_tech_pack_draft_modification()
            RETURNS trigger AS $$
            BEGIN
                IF OLD.approved_at_utc IS NOT NULL THEN
                    RAISE EXCEPTION 'Approved tech-pack import drafts are immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            CREATE TRIGGER no_update_or_delete_approved_tech_pack_import_drafts
                BEFORE UPDATE OR DELETE ON tech_pack_import_drafts
                FOR EACH ROW EXECUTE FUNCTION prevent_approved_tech_pack_draft_modification();
            """);
    }

    protected override void Down(MigrationBuilder migrationBuilder)
    {
        migrationBuilder.Sql(
            """
            DROP TRIGGER IF EXISTS no_update_or_delete_approved_tech_pack_import_drafts ON tech_pack_import_drafts;
            DROP FUNCTION IF EXISTS prevent_approved_tech_pack_draft_modification();
            DROP TRIGGER IF EXISTS no_update_or_delete_review_actions ON review_actions;
            DROP FUNCTION IF EXISTS prevent_review_action_modification();
            """);

        migrationBuilder.DropTable(name: "review_actions");
        migrationBuilder.DropTable(name: "tech_pack_import_drafts");
        migrationBuilder.DropTable(name: "inspection_batches");
        migrationBuilder.DropTable(name: "production_order_lines");
        migrationBuilder.DropTable(name: "production_orders");
        migrationBuilder.DropTable(name: "brands");
        migrationBuilder.DropIndex(
            name: "ix_inspection_records_tenant_id_order_style_size",
            table: "inspection_records");
        migrationBuilder.DropColumn(name: "capture_id", table: "inspection_records");
        migrationBuilder.DropColumn(name: "order_code", table: "inspection_records");
        migrationBuilder.DropColumn(name: "style_code", table: "inspection_records");
        migrationBuilder.DropColumn(name: "size_code", table: "inspection_records");
    }

    private static void CreateBrandTable(MigrationBuilder migrationBuilder) =>
        CreateTenantTable(
            migrationBuilder,
            "brands",
            table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
            },
            "uq_brands_tenant_id_name",
            new[] { "tenant_id", "name" });

    private static void CreateProductionOrderTable(MigrationBuilder migrationBuilder) =>
        CreateTenantTable(
            migrationBuilder,
            "production_orders",
            table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                brand_id = table.Column<Guid>(type: "uuid", nullable: false),
                order_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                supplier_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
            },
            "uq_production_orders_tenant_id_order_code",
            new[] { "tenant_id", "order_code" });

    private static void CreateProductionOrderLineTable(MigrationBuilder migrationBuilder)
    {
        CreateTenantTable(
            migrationBuilder,
            "production_order_lines",
            table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                production_order_id = table.Column<Guid>(type: "uuid", nullable: false),
                style_id = table.Column<Guid>(type: "uuid", nullable: false),
                size_id = table.Column<Guid>(type: "uuid", nullable: false),
                planned_quantity = table.Column<int>(type: "integer", nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
            });
        migrationBuilder.CreateIndex(
            name: "ix_production_order_lines_tenant_id_production_order_id",
            table: "production_order_lines",
            columns: new[] { "tenant_id", "production_order_id" });
    }

    private static void CreateInspectionBatchTable(MigrationBuilder migrationBuilder) =>
        CreateTenantTable(
            migrationBuilder,
            "inspection_batches",
            table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                production_order_line_id = table.Column<Guid>(type: "uuid", nullable: false),
                batch_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
            },
            "uq_inspection_batches_tenant_id_batch_code",
            new[] { "tenant_id", "batch_code" });

    private static void CreateTechPackImportDraftTable(MigrationBuilder migrationBuilder) =>
        CreateTenantTable(
            migrationBuilder,
            "tech_pack_import_drafts",
            table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                tech_pack_id = table.Column<Guid>(type: "uuid", nullable: false),
                original_file_name = table.Column<string>(type: "character varying(260)", maxLength: 260, nullable: false),
                content_type = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                draft = table.Column<string>(type: "jsonb", nullable: false),
                status = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                source_hash_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                approved_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: true),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
            },
            "uq_tech_pack_import_drafts_tenant_id_tech_pack_id_source_hash",
            new[] { "tenant_id", "tech_pack_id", "source_hash_sha256" });

    private static void CreateReviewActionTable(MigrationBuilder migrationBuilder)
    {
        CreateTenantTable(
            migrationBuilder,
            "review_actions",
            table => new
            {
                id = table.Column<Guid>(type: "uuid", nullable: false, defaultValueSql: "gen_random_uuid()"),
                tenant_id = table.Column<Guid>(type: "uuid", nullable: false),
                inspection_id = table.Column<Guid>(type: "uuid", nullable: false),
                actor_id = table.Column<Guid>(type: "uuid", nullable: true),
                outcome = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                note = table.Column<string>(type: "character varying(4000)", maxLength: 4000, nullable: false),
                created_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
                updated_at_utc = table.Column<DateTimeOffset>(type: "timestamptz", nullable: false, defaultValueSql: "now()"),
            });
        migrationBuilder.CreateIndex(
            name: "ix_review_actions_tenant_id_inspection_id_created_at_utc",
            table: "review_actions",
            columns: new[] { "tenant_id", "inspection_id", "created_at_utc" });
    }

    private static void CreateTenantTable<TColumns>(
        MigrationBuilder migrationBuilder,
        string tableName,
        Func<ColumnsBuilder, TColumns> columns,
        string? uniqueIndexName = null,
        string[]? uniqueIndexColumns = null)
    {
        migrationBuilder.CreateTable(
            name: tableName,
            columns: columns,
            constraints: _ => { });
        migrationBuilder.AddPrimaryKey(
            name: $"pk_{tableName}",
            table: tableName,
            column: "id");
        migrationBuilder.CreateIndex(
            name: $"ix_{tableName}_tenant_id",
            table: tableName,
            column: "tenant_id");
        if (uniqueIndexName is not null && uniqueIndexColumns is not null)
        {
            migrationBuilder.CreateIndex(
                name: uniqueIndexName,
                table: tableName,
                columns: uniqueIndexColumns,
                unique: true);
        }
    }
}
