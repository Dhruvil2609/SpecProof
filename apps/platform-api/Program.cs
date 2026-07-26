using System.Globalization;
using Microsoft.AspNetCore.Localization;
using SpecProof.Contracts;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddLocalization(options => options.ResourcesPath = "Resources");
builder.Services.Configure<RequestLocalizationOptions>(options =>
{
    var supportedCultures = new[] { new CultureInfo("en") };
    options.DefaultRequestCulture = new RequestCulture("en");
    options.SupportedCultures = supportedCultures;
    options.SupportedUICultures = supportedCultures;
});

builder.Services.AddProblemDetails();

var app = builder.Build();

app.UseRequestLocalization();
app.UseExceptionHandler();

app.MapGet("/healthz", () => Results.Ok(new { status = "ok", checkedAtUtc = DateTimeOffset.UtcNow }))
    .WithName("HealthCheck");

app.MapGet("/api/v1/openapi.json", () => Results.Json(OpenApiDocument.Create()))
    .WithName("GetOpenApiDocument");

app.MapGet("/api/v1/inspections/{id:guid}", (Guid id) =>
    {
        var result = new InspectionResultDto(
            id,
            "station-demo",
            "camera-demo",
            DateTimeOffset.UtcNow,
            [],
            InspectionStatus.Pending,
            "not-yet-signed");

        return Results.Ok(result);
    })
    .WithName("GetInspection");

app.Run();

internal static class OpenApiDocument
{
    public static object Create()
    {
        return new
        {
            openapi = "3.1.0",
            info = new { title = "SpecProof Platform API", version = "0.1.0" },
            paths = new Dictionary<string, object>
            {
                ["/healthz"] = new
                {
                    get = new
                    {
                        operationId = "HealthCheck",
                        responses = new Dictionary<string, object>
                        {
                            ["200"] = new { description = "Service health status" }
                        }
                    }
                },
                ["/api/v1/inspections/{id}"] = new
                {
                    get = new
                    {
                        operationId = "GetInspection",
                        responses = new Dictionary<string, object>
                        {
                            ["200"] = new { description = "Inspection result" }
                        }
                    }
                }
            }
        };
    }
}

public partial class Program;
