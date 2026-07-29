[CmdletBinding()]
param(
    [switch]$KeepInfrastructure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repositoryRoot = $PSScriptRoot
$runtimeRoot = Join-Path $repositoryRoot ".cache/development"
$processManifestPath = Join-Path $runtimeRoot "processes.json"

if (Test-Path -LiteralPath $processManifestPath -PathType Leaf) {
    $processRecords = @(Get-Content -LiteralPath $processManifestPath -Raw | ConvertFrom-Json)
    foreach ($record in $processRecords) {
        $process = Get-Process -Id $record.processId -ErrorAction SilentlyContinue
        if ($null -ne $process) {
            Write-Host "Stopping $($record.name) (PID $($record.processId))"
            $taskkill = Get-Command taskkill.exe -CommandType Application -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($null -ne $taskkill) {
                & $taskkill.Source /PID $record.processId /T /F *> $null
            }
            else {
                Stop-Process -Id $record.processId -Force
            }
        }
    }
    Remove-Item -LiteralPath $processManifestPath -Force
}
else {
    Write-Host "No tracked SpecProof application processes were found."
}

if (-not $KeepInfrastructure) {
    $docker = Get-Command docker.exe -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -eq $docker) {
        throw "docker.exe was not found on PATH."
    }

    Write-Host "Stopping Docker Compose infrastructure"
    Push-Location $repositoryRoot
    try {
        & $docker.Source compose stop
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose infrastructure failed to stop."
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host "SpecProof development environment is stopped." -ForegroundColor Green
