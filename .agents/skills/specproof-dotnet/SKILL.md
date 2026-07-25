---
name: specproof-dotnet
description: .NET/C# development skill for SpecProof. ALWAYS ACTIVE for any C#, .NET, ASP.NET Core, API, backend, platform, station host, EF Core, Entity Framework, migration, endpoint, controller, service, middleware, OpenAPI, or authentication task. Covers DTOs, records, DI, FluentValidation, OpenTelemetry, xUnit, and cross-platform publishing.
---

# SpecProof .NET Development Skill

## When to Use
Activate this skill when writing C#/.NET code for SpecProof — platform API, station host, shared contracts, or .NET packages.

## Environment
- .NET LTS SDK (pinned via `global.json`)
- ASP.NET Core for APIs
- EF Core for data access
- PostgreSQL provider

## Code Standards

### Project Configuration
```xml
<!-- Directory.Build.props -->
<Project>
  <PropertyGroup>
    <Nullable>enable</Nullable>
    <TreatWarningsAsErrors>true</TreatWarningsAsErrors>
    <ImplicitUsings>enable</ImplicitUsings>
    <AnalysisLevel>latest</AnalysisLevel>
  </PropertyGroup>
</Project>
```

### Timestamps
```csharp
// CORRECT
var now = DateTime.UtcNow;
var nowOffset = DateTimeOffset.UtcNow;

// WRONG — never use local time
var now = DateTime.Now;           // Local time
var now = DateTimeOffset.Now;     // Local offset
```

### DTOs and Records
```csharp
public record InspectionResultDto(
    Guid InspectionId,
    string StationId,
    string CameraSerial,
    DateTime CapturedAtUtc,
    IReadOnlyList<MeasurementDto> Measurements,
    InspectionStatus Status,
    string EvidenceRecordHash);

public record MeasurementDto(
    string PomId,
    string CanonicalName,
    double MeasuredValueMm,
    double TargetValueMm,
    double LowerToleranceMm,
    double UpperToleranceMm,
    double DeviationMm,
    double Confidence,
    MeasurementStatus Status);
```

### API Endpoints
```csharp
app.MapGet("/api/v1/inspections/{id:guid}", 
    async (Guid id, IInspectionService service, CancellationToken ct) =>
{
    var result = await service.GetByIdAsync(id, ct);
    return result is not null 
        ? Results.Ok(result) 
        : Results.NotFound();
})
.WithName("GetInspection")
.WithOpenApi()
.RequireAuthorization("ReadInspections");
```

### Entity Configuration (EF Core)
```csharp
public class InspectionConfiguration : IEntityTypeConfiguration<Inspection>
{
    public void Configure(EntityTypeBuilder<Inspection> builder)
    {
        builder.ToTable("inspections");
        builder.HasKey(x => x.Id);
        builder.Property(x => x.CapturedAtUtc)
            .HasColumnType("timestamptz")
            .IsRequired();
        builder.HasQueryFilter(x => x.TenantId == _tenantProvider.TenantId);
    }
}
```

### Dependency Injection
```csharp
builder.Services.AddScoped<IInspectionService, InspectionService>();
builder.Services.AddScoped<IMeasurementEngine, MeasurementEngine>();
builder.Services.AddScoped<IEvidenceSigner, EvidenceSigner>();
builder.Services.AddSingleton<ICameraProvider, RealSenseCameraProvider>();
```

### Error Handling (RFC 7807)
```csharp
app.UseExceptionHandler(errorApp =>
{
    errorApp.Run(async context =>
    {
        context.Response.ContentType = "application/problem+json";
        // Return ProblemDetails
    });
});
```

### i18n
```csharp
builder.Services.AddLocalization(options => options.ResourcesPath = "Resources");
builder.Services.Configure<RequestLocalizationOptions>(options =>
{
    var supportedCultures = new[] { "en" };
    options.SetDefaultCulture("en");
    options.AddSupportedCultures(supportedCultures);
    options.AddSupportedUICultures(supportedCultures);
});
```

## Key Packages
- ASP.NET Core (Minimal APIs)
- Entity Framework Core + Npgsql
- FluentValidation
- OpenTelemetry
- Swashbuckle / NSwag (OpenAPI)
- xUnit + NSubstitute (testing)

## Testing Pattern
```csharp
public class MeasurementEngineTests
{
    [Fact]
    public void Execute_StraightLineMeasurement_ReturnsCorrectDistance()
    {
        // Arrange
        var engine = new MeasurementEngine();
        var rule = new CompiledRule("chest_width", PathType.Straight, ...);
        var landmarks = CreateTestLandmarks();

        // Act
        var result = engine.Execute(rule, landmarks);

        // Assert
        Assert.InRange(result.MeasuredValueMm, 499.0, 501.0);
    }
}
```

## Cross-Platform Publishing
```powershell
dotnet publish -c Release -r win-x64 --self-contained true
dotnet publish -c Release -r linux-x64 --self-contained true
```
