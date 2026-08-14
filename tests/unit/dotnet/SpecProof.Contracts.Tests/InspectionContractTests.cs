using System.Text.Json;
using SpecProof.Contracts;
using Xunit;

namespace SpecProof.Contracts.Tests;

public sealed class InspectionContractTests
{
    [Fact]
    public void InspectionResultDto_RoundTripSerialisation_ReturnsEquivalentValue()
    {
        var capturedAtUtc = DateTimeOffset.Parse("2026-07-25T14:40:00Z");
        var expected = new InspectionResultDto(
            Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            "station-001",
            "camera-001",
            capturedAtUtc,
            [
                new MeasurementDto(
                    "chest_width",
                    "Chest Width",
                    500.0,
                    498.0,
                    493.0,
                    503.0,
                    2.0,
                    0.98,
                    MeasurementStatus.Pass)
            ],
            InspectionStatus.Pass,
            "sha256:demo");

        var json = JsonSerializer.Serialize(expected, SpecProofJsonContext.Default.InspectionResultDto);
        var actual = JsonSerializer.Deserialize(json, SpecProofJsonContext.Default.InspectionResultDto);

        Assert.NotNull(actual);
        Assert.Equal(expected.InspectionId, actual.InspectionId);
        Assert.Equal(expected.CapturedAtUtc, actual.CapturedAtUtc);
        Assert.Equal(expected.Status, actual.Status);
        Assert.Single(actual.Measurements);
        Assert.Equal(expected.Measurements[0], actual.Measurements[0]);
    }

    [Fact]
    public void EvidenceRecordDto_RoundTripSerialisation_ReturnsEquivalentValue()
    {
        var expected = new EvidenceRecordDto(
            "evidence-1",
            Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            Guid.Parse("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            new string('a', 64),
            DateTimeOffset.Parse("2026-08-05T00:00:00Z"),
            new EvidenceVersionsDto(
                "calibration-1",
                "phase-3-deterministic-v1",
                "1.0.0",
                "phase-4-compiler-v1"),
            [
                new MeasurementDto(
                    "chest_width",
                    "Chest Width",
                    100.0,
                    100.0,
                    2.0,
                    2.0,
                    0.0,
                    0.99,
                    MeasurementStatus.Pass)
            ],
            InspectionStatus.Pass,
            null,
            new string('b', 64),
            new SignedEvidenceDto(
                "phase-5-key",
                "HMAC-SHA256",
                Convert.ToBase64String([1, 2, 3, 4]),
                DateTimeOffset.Parse("2026-08-06T00:00:01Z")));

        var json = JsonSerializer.Serialize(expected, SpecProofJsonContext.Default.EvidenceRecordDto);
        var actual = JsonSerializer.Deserialize(json, SpecProofJsonContext.Default.EvidenceRecordDto);

        Assert.NotNull(actual);
        Assert.Equal(expected.EvidenceId, actual.EvidenceId);
        Assert.Equal(expected.Versions.CompilerVersion, actual.Versions.CompilerVersion);
        Assert.Equal(expected.Measurements[0], actual.Measurements[0]);
        Assert.Equal(expected.Signature, actual.Signature);
    }

    [Fact]
    public void TechPackVersionDto_RoundTripSerialisation_ReturnsEquivalentValue()
    {
        var expected = new TechPackVersionDto(
            Guid.Parse("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            1,
            "Brand",
            "TEE-001",
            "t_shirt",
            true,
            new string('c', 64));

        var json = JsonSerializer.Serialize(expected, SpecProofJsonContext.Default.TechPackVersionDto);
        var actual = JsonSerializer.Deserialize(json, SpecProofJsonContext.Default.TechPackVersionDto);

        Assert.Equal(expected, actual);
    }

    [Fact]
    public void Phase5PlatformDtos_RoundTripSerialisation_ReturnEquivalentValues()
    {
        var station = new StationRegistrationDto(
            Guid.Parse("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            Guid.Parse("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            Guid.Parse("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            "station-001",
            new string('d', 64),
            DateTimeOffset.Parse("2026-08-06T00:00:00Z"));
        var health = new StationHealthDto(
            station.StationId,
            "ok",
            "ok",
            "ok",
            "ok",
            0,
            DateTimeOffset.Parse("2026-08-06T00:00:00Z"));
        var sync = new SyncEnvelopeDto(
            Guid.Parse("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            station.TenantId,
            station.StationId,
            "sync-1",
            "inspection",
            Guid.Parse("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
            new string('e', 64),
            "accepted");
        var batch = new BatchSummaryDto(
            Guid.Parse("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            3,
            1,
            1,
            1,
            0);

        var stationJson = JsonSerializer.Serialize(station, SpecProofJsonContext.Default.StationRegistrationDto);
        var healthJson = JsonSerializer.Serialize(health, SpecProofJsonContext.Default.StationHealthDto);
        var syncJson = JsonSerializer.Serialize(sync, SpecProofJsonContext.Default.SyncEnvelopeDto);
        var batchJson = JsonSerializer.Serialize(batch, SpecProofJsonContext.Default.BatchSummaryDto);

        Assert.Equal(station, JsonSerializer.Deserialize(stationJson, SpecProofJsonContext.Default.StationRegistrationDto));
        Assert.Equal(health, JsonSerializer.Deserialize(healthJson, SpecProofJsonContext.Default.StationHealthDto));
        Assert.Equal(sync, JsonSerializer.Deserialize(syncJson, SpecProofJsonContext.Default.SyncEnvelopeDto));
        Assert.Equal(batch, JsonSerializer.Deserialize(batchJson, SpecProofJsonContext.Default.BatchSummaryDto));
    }

    [Fact]
    public void Phase6WebDashboardDto_RoundTripSerialisation_PreservesNormalizedOverlay()
    {
        var inspectionId = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var expected = new WebDashboardDto(
            [
                new InspectionDetailDto(
                    inspectionId,
                    Guid.Parse("22222222-2222-2222-2222-222222222222"),
                    "PO-2408",
                    "CORE-TEE",
                    "M",
                    "station-001",
                    DateTimeOffset.Parse("2026-08-12T10:00:00Z"),
                    "review",
                    new string('a', 64),
                    [
                        new WebMeasurementDto(
                            "chest_width",
                            "Chest Width",
                            501.2,
                            500.0,
                            -5.0,
                            5.0,
                            1.2,
                            0.97,
                            "pass",
                            [new NormalizedPointDto(0.2, 0.4), new NormalizedPointDto(0.8, 0.4)])
                    ])
            ],
            [],
            [],
            [],
            []);

        var json = JsonSerializer.Serialize(expected, SpecProofJsonContext.Default.WebDashboardDto);
        var actual = JsonSerializer.Deserialize(json, SpecProofJsonContext.Default.WebDashboardDto);

        Assert.NotNull(actual);
        Assert.Equal(inspectionId, actual.Inspections[0].Id);
        Assert.Equal(expected.Inspections[0].Measurements[0].Overlay, actual.Inspections[0].Measurements[0].Overlay);
    }

    [Fact]
    public void Phase6ReviewActionDto_RoundTripSerialisation_ReturnsEquivalentValue()
    {
        var expected = new ReviewActionDto(
            Guid.Parse("33333333-3333-3333-3333-333333333333"),
            Guid.Parse("11111111-1111-1111-1111-111111111111"),
            Guid.Parse("44444444-4444-4444-4444-444444444444"),
            "confirm_fail",
            "Manual review confirmed the deviation.",
            DateTimeOffset.Parse("2026-08-12T10:05:00Z"));

        var json = JsonSerializer.Serialize(expected, SpecProofJsonContext.Default.ReviewActionDto);
        var actual = JsonSerializer.Deserialize(json, SpecProofJsonContext.Default.ReviewActionDto);

        Assert.Equal(expected, actual);
    }
}
