using SpecProof.Platform.Api;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class PilotMetricSnapshotTests
{
    [Fact]
    public void Calculate_MixedPilotState_ReturnsOperationalCounts()
    {
        var nowUtc = new DateTimeOffset(2026, 8, 15, 9, 0, 0, TimeSpan.Zero);
        var onlineStationId = Guid.NewGuid();
        var staleStationId = Guid.NewGuid();
        var missingStationId = Guid.NewGuid();

        var snapshot = PilotMetricSnapshot.Calculate(
            nowUtc,
            [onlineStationId, staleStationId, missingStationId],
            [
                new PilotStationHealthSample(onlineStationId, "ONLINE", 2, nowUtc.AddSeconds(-30)),
                new PilotStationHealthSample(staleStationId, "ONLINE", 3, nowUtc.AddMinutes(-3)),
                new PilotStationHealthSample(onlineStationId, "OFFLINE", 9, nowUtc.AddMinutes(-4)),
            ],
            [nowUtc.AddHours(12), nowUtc.AddHours(30)],
            [
                new PilotInspectionSample("INVALID", nowUtc.AddMinutes(-2)),
                new PilotInspectionSample("FAILED", nowUtc.AddMinutes(-20)),
                new PilotInspectionSample("PASS", nowUtc.AddMinutes(-1)),
            ],
            ["PENDING", "COMPLETED", "RETRYABLE_FAILURE"],
            true);

        Assert.Equal(
            new PilotMetricSnapshot(
                OfflineStations: 2,
                OfflineQueueDepth: 5,
                ExpiringCalibrations: 1,
                RecentInspectionFailures: 1,
                BackgroundJobQueueDepth: 2,
                DatabaseAvailable: 1),
            snapshot);
    }
}
