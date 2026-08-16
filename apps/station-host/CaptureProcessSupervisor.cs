using System.Diagnostics;
using Microsoft.Extensions.Options;

namespace SpecProof.Station.Host;

public sealed class CaptureProcessOptions
{
    public const string SectionName = "CaptureProcess";
    public const string ValidationMessage =
        "CaptureProcess requires an executable, working directory, and at least one argument when enabled.";

    public bool Enabled { get; init; }

    public string ExecutablePath { get; init; } = string.Empty;

    public string WorkingDirectory { get; init; } = string.Empty;

    public string[] Arguments { get; init; } = [];

    public int RestartDelaySeconds { get; init; } = 3;

    public static bool IsValid(CaptureProcessOptions options) =>
        !options.Enabled
        || (!string.IsNullOrWhiteSpace(options.ExecutablePath)
            && !string.IsNullOrWhiteSpace(options.WorkingDirectory)
            && options.Arguments.Length > 0
            && options.RestartDelaySeconds is >= 1 and <= 300);
}

public sealed class CaptureProcessSupervisor(
    IOptions<CaptureProcessOptions> options,
    ILogger<CaptureProcessSupervisor> logger) : BackgroundService
{
    private readonly CaptureProcessOptions options = options.Value;
    private Process? process;

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if (!options.Enabled)
        {
            logger.LogInformation("Capture process supervision is disabled");
            return;
        }

        while (!stoppingToken.IsCancellationRequested)
        {
            using var nextProcess = new Process { StartInfo = CreateStartInfo(options) };
            process = nextProcess;
            if (!nextProcess.Start())
            {
                throw new InvalidOperationException("The capture process could not be started.");
            }

            logger.LogInformation("Capture process started with ID {ProcessId}", nextProcess.Id);
            try
            {
                await nextProcess.WaitForExitAsync(stoppingToken);
                logger.LogError(
                    "Capture process exited with code {ExitCode}; restarting",
                    nextProcess.ExitCode);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                StopProcess(nextProcess);
                break;
            }
            finally
            {
                process = null;
            }

            await Task.Delay(TimeSpan.FromSeconds(options.RestartDelaySeconds), stoppingToken);
        }
    }

    public override async Task StopAsync(CancellationToken cancellationToken)
    {
        if (process is { HasExited: false } activeProcess)
        {
            StopProcess(activeProcess);
        }
        await base.StopAsync(cancellationToken);
    }

    internal static ProcessStartInfo CreateStartInfo(CaptureProcessOptions options)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = options.ExecutablePath,
            WorkingDirectory = options.WorkingDirectory,
            UseShellExecute = false,
            CreateNoWindow = true,
        };
        foreach (var argument in options.Arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }
        return startInfo;
    }

    private static void StopProcess(Process activeProcess)
    {
        try
        {
            if (!activeProcess.HasExited)
            {
                activeProcess.Kill(entireProcessTree: true);
                activeProcess.WaitForExit(TimeSpan.FromSeconds(10));
            }
        }
        catch (InvalidOperationException)
        {
        }
    }
}
