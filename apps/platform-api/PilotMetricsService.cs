using System.Diagnostics.Metrics;
using Microsoft.EntityFrameworkCore;
using SpecProof.Platform.Data;

namespace SpecProof.Platform.Api;

public sealed record PilotStationHealthSample(
    Guid StationId,
    string Status,
    long OfflineQueueDepth,
    DateTimeOffset CheckedAtUtc);

public sealed record PilotInspectionSample(string Status, DateTimeOffset CreatedAtUtc);

public sealed record PilotMetricSnapshot(
    long OfflineStations,
    long OfflineQueueDepth,
    long ExpiringCalibrations,
    long RecentInspectionFailures,
    long BackgroundJobQueueDepth,
    long DatabaseAvailable)
{
    public static PilotMetricSnapshot Calculate(
        DateTimeOffset nowUtc,
        IReadOnlyCollection<Guid> stationIds,
        IReadOnlyCollection<PilotStationHealthSample> healthSamples,
        IReadOnlyCollection<DateTimeOffset> calibrationExpirations,
        IReadOnlyCollection<PilotInspectionSample> inspections,
        IReadOnlyCollection<string> backgroundJobStatuses,
        bool databaseAvailable)
    {
        var latestHealth = healthSamples
            .GroupBy(sample => sample.StationId)
            .ToDictionary(group => group.Key, group => group.MaxBy(sample => sample.CheckedAtUtc)!);
        var offlineCutoff = nowUtc.AddMinutes(-2);
        var offlineStations = stationIds.Count(stationId =>
            !latestHealth.TryGetValue(stationId, out var health)
            || health.CheckedAtUtc < offlineCutoff
            || !string.Equals(health.Status, "ONLINE", StringComparison.OrdinalIgnoreCase));
        var queueDepth = latestHealth.Values.Sum(health => Math.Max(0, health.OfflineQueueDepth));
        var calibrationCutoff = nowUtc.AddHours(24);
        var expiringCalibrations = calibrationExpirations.Count(expiry => expiry <= calibrationCutoff);
        var failureCutoff = nowUtc.AddMinutes(-15);
        var recentFailures = inspections.Count(inspection =>
            inspection.CreatedAtUtc >= failureCutoff
            && (string.Equals(inspection.Status, "INVALID", StringComparison.OrdinalIgnoreCase)
                || string.Equals(inspection.Status, "FAILED", StringComparison.OrdinalIgnoreCase)));
        var queuedJobs = backgroundJobStatuses.Count(status =>
            !string.Equals(status, "COMPLETED", StringComparison.OrdinalIgnoreCase)
            && !string.Equals(status, "CANCELLED", StringComparison.OrdinalIgnoreCase));

        return new PilotMetricSnapshot(
            offlineStations,
            queueDepth,
            expiringCalibrations,
            recentFailures,
            queuedJobs,
            databaseAvailable ? 1 : 0);
    }
}

public sealed class PilotMetricsService : BackgroundService
{
    public const string MeterName = "SpecProof.Platform.Pilot";

    private readonly IServiceScopeFactory scopeFactory;
    private readonly ILogger<PilotMetricsService> logger;
    private readonly TimeSpan collectionInterval;
    private readonly Meter meter = new(MeterName);
    private PilotMetricSnapshot snapshot = new(0, 0, 0, 0, 0, 0);

    public PilotMetricsService(
        IServiceScopeFactory scopeFactory,
        IConfiguration configuration,
        ILogger<PilotMetricsService> logger)
    {
        this.scopeFactory = scopeFactory;
        this.logger = logger;
        collectionInterval = TimeSpan.FromSeconds(
            Math.Max(5, configuration.GetValue("PilotMetrics:CollectionIntervalSeconds", 30)));
        meter.CreateObservableGauge(
            "specproof.pilot.station.offline.total",
            () => snapshot.OfflineStations,
            description: "Stations without a recent online health report");
        meter.CreateObservableGauge(
            "specproof.pilot.station.queue.depth",
            () => snapshot.OfflineQueueDepth,
            description: "Total durable station queue depth from latest health reports");
        meter.CreateObservableGauge(
            "specproof.pilot.calibration.expiring.total",
            () => snapshot.ExpiringCalibrations,
            description: "Active calibrations expired or expiring within 24 hours");
        meter.CreateObservableGauge(
            "specproof.pilot.inspection.failures.15m",
            () => snapshot.RecentInspectionFailures,
            description: "Invalid or failed inspections created in the last 15 minutes");
        meter.CreateObservableGauge(
            "specproof.pilot.background_job.queue.depth",
            () => snapshot.BackgroundJobQueueDepth,
            description: "Incomplete platform background jobs");
        meter.CreateObservableGauge(
            "specproof.pilot.database.available",
            () => snapshot.DatabaseAvailable,
            description: "Platform database connectivity, where one is available");
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(collectionInterval);
        do
        {
            await CollectAsync(stoppingToken);
        }
        while (await timer.WaitForNextTickAsync(stoppingToken));
    }

    internal async Task CollectAsync(CancellationToken cancellationToken)
    {
        try
        {
            await using var scope = scopeFactory.CreateAsyncScope();
            var database = scope.ServiceProvider.GetRequiredService<SpecProofDbContext>();
            var databaseAvailable = await database.Database.CanConnectAsync(cancellationToken);
            if (!databaseAvailable)
            {
                snapshot = new PilotMetricSnapshot(0, 0, 0, 0, 0, 0);
                return;
            }

            var nowUtc = DateTimeOffset.UtcNow;
            var stationIds = await database.Stations.IgnoreQueryFilters()
                .Select(station => station.Id)
                .ToArrayAsync(cancellationToken);
            var healthSamples = await database.StationHealthReports.IgnoreQueryFilters()
                .Where(report => report.CheckedAtUtc >= nowUtc.AddDays(-1))
                .Select(report => new PilotStationHealthSample(
                    report.StationId,
                    report.Status,
                    report.OfflineQueueDepth,
                    report.CheckedAtUtc))
                .ToArrayAsync(cancellationToken);
            var calibrationExpirations = await database.CalibrationRecords.IgnoreQueryFilters()
                .Where(calibration => calibration.SupersededAtUtc == null)
                .Select(calibration => calibration.ExpiresAtUtc)
                .ToArrayAsync(cancellationToken);
            var inspections = await database.InspectionRecords.IgnoreQueryFilters()
                .Where(inspection => inspection.CreatedAtUtc >= nowUtc.AddMinutes(-15))
                .Select(inspection => new PilotInspectionSample(
                    inspection.Status,
                    inspection.CreatedAtUtc))
                .ToArrayAsync(cancellationToken);
            var backgroundJobStatuses = await database.BackgroundJobs.IgnoreQueryFilters()
                .Select(job => job.Status)
                .ToArrayAsync(cancellationToken);
            snapshot = PilotMetricSnapshot.Calculate(
                nowUtc,
                stationIds,
                healthSamples,
                calibrationExpirations,
                inspections,
                backgroundJobStatuses,
                true);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            snapshot = new PilotMetricSnapshot(0, 0, 0, 0, 0, 0);
            logger.LogWarning(exception, "Pilot metric collection failed");
        }
    }

    public override void Dispose()
    {
        meter.Dispose();
        base.Dispose();
    }
}
