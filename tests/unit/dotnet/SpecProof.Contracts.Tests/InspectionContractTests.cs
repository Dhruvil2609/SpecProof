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
            new string('b', 64));

        var json = JsonSerializer.Serialize(expected, SpecProofJsonContext.Default.EvidenceRecordDto);
        var actual = JsonSerializer.Deserialize(json, SpecProofJsonContext.Default.EvidenceRecordDto);

        Assert.NotNull(actual);
        Assert.Equal(expected.EvidenceId, actual.EvidenceId);
        Assert.Equal(expected.Versions.CompilerVersion, actual.Versions.CompilerVersion);
        Assert.Equal(expected.Measurements[0], actual.Measurements[0]);
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
}
