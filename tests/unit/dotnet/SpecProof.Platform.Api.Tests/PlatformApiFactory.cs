using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Logging;
using SpecProof.Platform.Api;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api.Tests;

public sealed class PlatformApiFactory : WebApplicationFactory<PlatformApiAssemblyMarker>
{
    private readonly string databaseName = $"platform-api-tests-{Guid.NewGuid():N}";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Test");
        builder.ConfigureLogging(logging => logging.ClearProviders());
        builder.ConfigureServices(services =>
        {
            services.RemoveAll<DbContextOptions<SpecProofDbContext>>();
            services.RemoveAll<IDbContextOptionsConfiguration<SpecProofDbContext>>();
            services.RemoveAll<SpecProofDbContext>();
            services.AddDbContext<SpecProofDbContext>(options =>
                options.UseInMemoryDatabase(databaseName));
        });
    }
}
