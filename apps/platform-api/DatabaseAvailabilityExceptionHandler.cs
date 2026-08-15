using System.Data.Common;
using System.Text.Json;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace SpecProof.Platform.Api;

public sealed class DatabaseAvailabilityExceptionHandler(
    ILogger<DatabaseAvailabilityExceptionHandler> logger) : IExceptionHandler
{
    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        if (!IsDatabaseAvailabilityFailure(exception))
        {
            return false;
        }

        logger.LogError(exception, "Database operation unavailable");
        httpContext.Response.StatusCode = StatusCodes.Status503ServiceUnavailable;
        httpContext.Response.ContentType = "application/problem+json";
        httpContext.Response.Headers.RetryAfter = "5";
        var problem = new ProblemDetails
        {
            Type = "https://specproof.example/problems/database-unavailable",
            Title = "Database temporarily unavailable",
            Status = StatusCodes.Status503ServiceUnavailable,
        };
        await JsonSerializer.SerializeAsync(
            httpContext.Response.Body,
            problem,
            cancellationToken: cancellationToken);
        return true;
    }

    internal static bool IsDatabaseAvailabilityFailure(Exception exception) =>
        exception is DbException
        || exception is DbUpdateException { InnerException: DbException };
}
