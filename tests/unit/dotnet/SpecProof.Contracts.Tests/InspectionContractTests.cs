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
}
