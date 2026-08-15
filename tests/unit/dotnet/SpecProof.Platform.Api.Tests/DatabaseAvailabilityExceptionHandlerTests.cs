using System.Data.Common;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using SpecProof.Platform.Api;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class DatabaseAvailabilityExceptionHandlerTests
{
    [Fact]
    public async Task TryHandleAsync_DatabaseUnavailable_ReturnsControlled503Problem()
    {
        var handler = new DatabaseAvailabilityExceptionHandler(
            NullLogger<DatabaseAvailabilityExceptionHandler>.Instance);
        var context = new DefaultHttpContext();
        context.Response.Body = new MemoryStream();
        var exception = new DbUpdateException(
            "Persistence failed",
            new SimulatedDatabaseUnavailableException());

        var handled = await handler.TryHandleAsync(
            context,
            exception,
            CancellationToken.None);

        context.Response.Body.Position = 0;
        using var body = await JsonDocument.ParseAsync(context.Response.Body);
        Assert.True(handled);
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, context.Response.StatusCode);
        Assert.Equal("5", context.Response.Headers.RetryAfter);
        Assert.Equal(
            "Database temporarily unavailable",
            body.RootElement.GetProperty("title").GetString());
        Assert.DoesNotContain("Persistence failed", body.RootElement.GetRawText());
    }

    [Fact]
    public async Task TryHandleAsync_NonDatabaseFailure_DoesNotHandle()
    {
        var handler = new DatabaseAvailabilityExceptionHandler(
            NullLogger<DatabaseAvailabilityExceptionHandler>.Instance);

        var handled = await handler.TryHandleAsync(
            new DefaultHttpContext(),
            new InvalidOperationException("application error"),
            CancellationToken.None);

        Assert.False(handled);
    }

    private sealed class SimulatedDatabaseUnavailableException()
        : DbException("Simulated database unavailable");
}
