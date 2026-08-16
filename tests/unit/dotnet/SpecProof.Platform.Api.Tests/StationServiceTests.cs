using System.Diagnostics;
using SpecProof.Station.Host;
using Xunit;

namespace SpecProof.Platform.Api.Tests;

public sealed class StationServiceTests
{
    [Fact]
    public void StationEnvironment_ParsesAllowedKeysWithoutExpandingValues()
    {
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(
                path,
                "# station\nSPEC_PROOF_STATION_TOKEN=unit-test-token\nOTEL_EXPORTER_OTLP_ENDPOINT=https://telemetry.example\n");

            var values = StationEnvironment.ParseFile(path);

            Assert.Equal("unit-test-token", values["SPEC_PROOF_STATION_TOKEN"]);
            Assert.Equal("https://telemetry.example", values["OTEL_EXPORTER_OTLP_ENDPOINT"]);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void StationEnvironment_RejectsUnapprovedAndDuplicateKeys()
    {
        var unapproved = Path.GetTempFileName();
        var duplicate = Path.GetTempFileName();
        try
        {
            File.WriteAllText(unapproved, "PATH=C:\\unsafe\n");
            File.WriteAllText(duplicate, "SPEC_PROOF_ID=one\nSPEC_PROOF_ID=two\n");

            Assert.Throws<InvalidDataException>(() => StationEnvironment.ParseFile(unapproved));
            Assert.Throws<InvalidDataException>(() => StationEnvironment.ParseFile(duplicate));
        }
        finally
        {
            File.Delete(unapproved);
            File.Delete(duplicate);
        }
    }

    [Fact]
    public void CaptureSupervisor_BuildsArgumentListWithoutShellParsing()
    {
        var options = new CaptureProcessOptions
        {
            Enabled = true,
            ExecutablePath = "python.exe",
            WorkingDirectory = "C:\\ProgramData\\SpecProof\\Station",
            Arguments = ["-m", "specproof_capture_service.grpc_server"],
        };

        ProcessStartInfo startInfo = CaptureProcessSupervisor.CreateStartInfo(options);

        Assert.False(startInfo.UseShellExecute);
        Assert.True(startInfo.CreateNoWindow);
        Assert.Equal(options.ExecutablePath, startInfo.FileName);
        Assert.Equal(options.Arguments, startInfo.ArgumentList);
    }
}
