---
name: specproof-database
description: Database development skill for SpecProof. ALWAYS ACTIVE for any PostgreSQL, database, schema, migration, EF Core, Entity Framework, SQL, query, table, column, index, tenant, audit, data access, repository, or storage task. Covers timestamptz, snake_case naming, append-only audit, Row-Level Security, and versioned entities.
---

# SpecProof Database Development Skill

## When to Use
Activate this skill when designing schemas, writing migrations, or implementing data access for SpecProof.

## Database Engine
- PostgreSQL (latest stable)
- Run in Docker for development
- EF Core for .NET data access
- SQLAlchemy or raw psycopg for Python (if needed)

## Schema Rules

### 1. Naming
- Tables: `snake_case` plural (e.g., `inspections`, `calibration_records`)
- Columns: `snake_case` (e.g., `created_at_utc`, `station_id`)
- Primary keys: `id` (UUID)
- Foreign keys: `{table_singular}_id` (e.g., `tenant_id`)
- Indexes: `ix_{table}_{columns}`
- Constraints: `ck_{table}_{description}`, `uq_{table}_{columns}`

### 2. Timestamps
```sql
-- ALWAYS use timestamptz (stores UTC internally)
created_at_utc    timestamptz NOT NULL DEFAULT now(),
updated_at_utc    timestamptz NOT NULL DEFAULT now(),
captured_at_utc   timestamptz NOT NULL,

-- NEVER use timestamp without time zone
-- NEVER store local times
```

### 3. Audit Tables (Append-Only)
```sql
CREATE TABLE audit_events (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id),
    event_type      text NOT NULL,
    entity_type     text NOT NULL,
    entity_id       uuid NOT NULL,
    actor_id        uuid,
    payload         jsonb NOT NULL,
    occurred_at_utc timestamptz NOT NULL DEFAULT now()
);

-- Prevent modification
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit events cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER no_update_audit
    BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

### 4. Tenant Isolation
```sql
-- Every business table includes tenant_id
-- Row-Level Security (RLS) or application-level query filters
ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON inspections
    USING (tenant_id = current_setting('app.current_tenant')::uuid);
```

### 5. Versioned Entities
```sql
-- Entities referenced by evidence records must be versioned
CREATE TABLE tech_pack_versions (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tech_pack_id    uuid NOT NULL REFERENCES tech_packs(id),
    version         integer NOT NULL,
    data            jsonb NOT NULL,
    created_at_utc  timestamptz NOT NULL DEFAULT now(),
    created_by      uuid NOT NULL REFERENCES users(id),
    UNIQUE(tech_pack_id, version)
);
```

### 6. Object Storage References
```sql
-- Large binary data → object storage, metadata → PostgreSQL
CREATE TABLE capture_assets (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    inspection_id   uuid NOT NULL REFERENCES inspections(id),
    object_key      text NOT NULL,
    content_type    text NOT NULL,
    size_bytes      bigint NOT NULL,
    checksum_sha256 text NOT NULL,
    station_id      uuid NOT NULL,
    capture_id      uuid NOT NULL,
    retention_category text NOT NULL DEFAULT 'standard',
    encrypted       boolean NOT NULL DEFAULT false,
    created_at_utc  timestamptz NOT NULL DEFAULT now()
);
```

## EF Core Migration Rules

### Creating Migrations
```powershell
dotnet ef migrations add {DescriptiveName} --project src/Infrastructure --startup-project src/Api
```

### Migration Rules
1. Every migration must be reversible (`Down` method implemented)
2. Test migration forward AND backward
3. No data loss in `Down` unless explicitly documented
4. Use `migrationBuilder.Sql()` for complex DDL
5. Never modify an existing migration — create a new one
6. Run in CI on both Windows and Linux

## Testing
```csharp
[Fact]
public async Task Migrations_ApplyAndRollback_Successfully()
{
    await using var db = CreateTestDatabase();
    await db.Database.MigrateAsync();
    // Verify tables exist
    // Rollback
    await db.Database.ExecuteSqlRawAsync("SELECT 1"); // verify connection
}
```

```csharp
[Fact]
public async Task AuditEvent_CannotBeDeleted()
{
    await using var db = CreateTestDatabase();
    var evt = new AuditEvent { ... };
    db.AuditEvents.Add(evt);
    await db.SaveChangesAsync();
    
    db.AuditEvents.Remove(evt);
    await Assert.ThrowsAsync<DbUpdateException>(() => db.SaveChangesAsync());
}
```
