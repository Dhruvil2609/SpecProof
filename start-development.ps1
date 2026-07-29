[CmdletBinding()]
param(
    [ValidateSet("mock", "replay", "realsense")]
    [string]$CameraProvider = "mock",
    [string]$ReplayPath,
    [ValidateRange(10, 600)]
    [int]$StartupTimeoutSeconds = 120,
    [switch]$SkipInfrastructure,
    [switch]$InfrastructureOnly,
    [switch]$ValidateOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = $PSScriptRoot
$configurationPath = Join-Path $repositoryRoot "development-services.json"
$runtimeRoot = Join-Path $repositoryRoot ".cache/development"
$logRoot = Join-Path $runtimeRoot "logs"
$processManifestPath = Join-Path $runtimeRoot "processes.json"
$startedProcesses = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()

function Write-Step {
    param([Parameter(Mandatory)][string]$Message)

    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Resolve-RequiredCommand {
    param([Parameter(Mandatory)][string]$Name)

    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $command) {
        throw "Required command '$Name' was not found on PATH."
    }
    return $command.Source
}

function Test-LocalPort {
    param([Parameter(Mandatory)][int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.ConnectAsync("127.0.0.1", $Port)
        return $connection.Wait(250) -and $client.Connected
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ServiceReady {
    param(
        [Parameter(Mandatory)][pscustomobject]$Service,
        [Parameter(Mandatory)][System.Diagnostics.Process]$Process
    )

    if ($null -eq $Service.port) {
        Start-Sleep -Seconds 2
        if ($Process.HasExited) {
            throw "$($Service.name) exited during startup with code $($Process.ExitCode)."
        }
        return
    }

    $deadline = [DateTimeOffset]::UtcNow.AddSeconds($StartupTimeoutSeconds)
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        if ($Process.HasExited) {
            throw "$($Service.name) exited during startup with code $($Process.ExitCode)."
        }

        if (Test-LocalPort -Port ([int]$Service.port)) {
            if ($null -eq $Service.healthUrl) {
                return
            }
            try {
                $response = Invoke-WebRequest -Uri $Service.healthUrl -TimeoutSec 3
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 400) {
                    return
                }
            }
            catch {
                Start-Sleep -Milliseconds 500
                continue
            }
        }
        Start-Sleep -Milliseconds 500
    }

    throw "$($Service.name) was not ready within $StartupTimeoutSeconds seconds."
}

function Start-ConfiguredService {
    param([Parameter(Mandatory)][pscustomobject]$Service)

    $executable = Resolve-RequiredCommand -Name $Service.command
    $workingDirectory = [System.IO.Path]::GetFullPath(
        (Join-Path $repositoryRoot $Service.workingDirectory)
    )
    $standardOutputPath = Join-Path $logRoot "$($Service.name).stdout.log"
    $standardErrorPath = Join-Path $logRoot "$($Service.name).stderr.log"
    $previousEnvironment = @{}

    try {
        foreach ($property in $Service.environment.psobject.Properties) {
            $previousEnvironment[$property.Name] =
                [System.Environment]::GetEnvironmentVariable($property.Name, "Process")
            [System.Environment]::SetEnvironmentVariable(
                $property.Name,
                [string]$property.Value,
                "Process"
            )
        }

        if ($Service.name -eq "capture-service") {
            $previousEnvironment["SPEC_PROOF_CAMERA_PROVIDER"] =
                [System.Environment]::GetEnvironmentVariable(
                    "SPEC_PROOF_CAMERA_PROVIDER",
                    "Process"
                )
            [System.Environment]::SetEnvironmentVariable(
                "SPEC_PROOF_CAMERA_PROVIDER",
                $CameraProvider,
                "Process"
            )
            if ($CameraProvider -eq "replay") {
                $previousEnvironment["SPEC_PROOF_REPLAY_PATH"] =
                    [System.Environment]::GetEnvironmentVariable(
                        "SPEC_PROOF_REPLAY_PATH",
                        "Process"
                    )
                [System.Environment]::SetEnvironmentVariable(
                    "SPEC_PROOF_REPLAY_PATH",
                    $ReplayPath,
                    "Process"
                )
            }
        }

        $process = Start-Process `
            -FilePath $executable `
            -ArgumentList ([string[]]$Service.arguments) `
            -WorkingDirectory $workingDirectory `
            -WindowStyle Hidden `
            -RedirectStandardOutput $standardOutputPath `
            -RedirectStandardError $standardErrorPath `
            -PassThru
        $startedProcesses.Add($process)
        return $process
    }
    finally {
        foreach ($entry in $previousEnvironment.GetEnumerator()) {
            [System.Environment]::SetEnvironmentVariable(
                $entry.Key,
                $entry.Value,
                "Process"
            )
        }
    }
}

function Stop-StartedProcesses {
    foreach ($process in $startedProcesses) {
        if (-not $process.HasExited) {
            $taskkill = Get-Command taskkill.exe -CommandType Application -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($null -ne $taskkill) {
                & $taskkill.Source /PID $process.Id /T /F *> $null
            }
            else {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

if (-not (Test-Path -LiteralPath $configurationPath -PathType Leaf)) {
    throw "Development service configuration was not found: $configurationPath"
}

if ($CameraProvider -eq "replay") {
    if ([string]::IsNullOrWhiteSpace($ReplayPath)) {
        throw "-ReplayPath is required when -CameraProvider replay is selected."
    }
    $ReplayPath = [System.IO.Path]::GetFullPath($ReplayPath)
    if (-not (Test-Path -LiteralPath $ReplayPath)) {
        throw "Replay path does not exist: $ReplayPath"
    }
}

$configuration = Get-Content -LiteralPath $configurationPath -Raw | ConvertFrom-Json
if ($configuration.services.Count -eq 0) {
    throw "No development services are configured."
}

Write-Step "Validating development prerequisites"
if (-not $InfrastructureOnly) {
    foreach ($service in $configuration.services) {
        $null = Resolve-RequiredCommand -Name $service.command
        if ($null -ne $service.port -and (Test-LocalPort -Port ([int]$service.port))) {
            throw "Port $($service.port) for $($service.name) is already in use."
        }
    }

    $uv = Resolve-RequiredCommand -Name "uv.exe"
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $pythonValidation = & $uv run python -c "import asyncio, ssl; print('Python native modules OK')" 2>&1
        $pythonValidationExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($pythonValidationExitCode -ne 0) {
        throw (
            "Python 3.11 native module validation failed. " +
            "Resolve Windows Application Control approval for _overlapped.pyd and _ssl.pyd, " +
            "or run '.\start-development.ps1 -InfrastructureOnly' to start Docker services only. " +
            ($pythonValidation -join [Environment]::NewLine)
        )
    }
}

if (-not $SkipInfrastructure) {
    $docker = Resolve-RequiredCommand -Name "docker.exe"
    & $docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not running or the daemon is not reachable."
    }
}

if ($ValidateOnly) {
    Write-Host "Development startup validation passed." -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
Remove-Item -LiteralPath $processManifestPath -Force -ErrorAction SilentlyContinue

try {
    if (-not $SkipInfrastructure) {
        Write-Step "Starting Docker Compose infrastructure"
        Push-Location $repositoryRoot
        try {
            & $docker compose up -d --wait --wait-timeout $StartupTimeoutSeconds
            if ($LASTEXITCODE -ne 0) {
                throw "Docker Compose infrastructure failed to start."
            }
        }
        finally {
            Pop-Location
        }
    }

    if ($InfrastructureOnly) {
        Write-Host ""
        Write-Host "SpecProof Docker infrastructure is running." -ForegroundColor Green
        Write-Host "PostgreSQL:  localhost:5432"
        Write-Host "MinIO:       http://localhost:9001"
        Write-Host "RabbitMQ:    http://localhost:15672"
        Write-Host "Prometheus:  http://localhost:9090"
        Write-Host "Grafana:     http://localhost:3000"
        Write-Host "Loki:        http://localhost:3100/ready"
        Write-Host ""
        Write-Host "Stop infrastructure with: .\stop-development.ps1"
        exit 0
    }

    $processRecords = foreach ($service in $configuration.services) {
        Write-Step "Starting $($service.name)"
        $process = Start-ConfiguredService -Service $service
        Wait-ServiceReady -Service $service -Process $process
        [pscustomobject]@{
            name = $service.name
            processId = $process.Id
            startedAtUtc = [DateTimeOffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
        }
    }

    $processRecords | ConvertTo-Json | Set-Content -LiteralPath $processManifestPath -Encoding utf8

    Write-Host ""
    Write-Host "SpecProof development environment is running." -ForegroundColor Green
    Write-Host "Platform API: http://127.0.0.1:5080"
    Write-Host "OpenAPI:      http://127.0.0.1:5080/api/v1/openapi.json"
    Write-Host "Operator UI:  http://127.0.0.1:5173"
    Write-Host "Admin UI:     http://127.0.0.1:5174"
    Write-Host "Logs:         $logRoot"
    Write-Host ""
    Write-Host "Stop everything with: .\stop-development.ps1"
}
catch {
    Stop-StartedProcesses
    Remove-Item -LiteralPath $processManifestPath -Force -ErrorAction SilentlyContinue
    Write-Error "$($_.Exception.Message) Review logs in $logRoot."
    exit 1
}
