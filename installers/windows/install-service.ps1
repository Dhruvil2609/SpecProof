[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:ProgramFiles\SpecProof\Station",
    [string]$DataRoot = "$env:ProgramData\SpecProof\Station",
    [string]$ServiceName = "SpecProofStationHost"
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $PSScriptRoot

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run the SpecProof station installer as Administrator."
    }
}

function Test-PackageManifest {
    $manifestPath = Join-Path $packageRoot "manifest.json"
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    foreach ($file in $manifest.files) {
        $path = Join-Path $packageRoot $file.path
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Package file is missing: $($file.path)"
        }
        $actual = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $file.sha256) {
            throw "Package hash mismatch: $($file.path)"
        }
    }
    return $manifest
}

function Invoke-ServiceControl {
    param([Parameter(Mandatory)][string[]]$Arguments)

    & sc.exe @Arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "sc.exe failed with exit code $LASTEXITCODE: $($Arguments -join ' ')"
    }
}

Assert-Administrator
$manifest = Test-PackageManifest
$versionRoot = Join-Path $InstallRoot "versions\$($manifest.packageVersion)"
$stagingRoot = "$versionRoot.staging"
$configRoot = Join-Path $DataRoot "config"

if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $stagingRoot, $configRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $packageRoot "host") -Destination $stagingRoot -Recurse
Copy-Item -LiteralPath (Join-Path $packageRoot "python") -Destination $stagingRoot -Recurse
Copy-Item -LiteralPath (Join-Path $packageRoot "config\appsettings.Production.json") -Destination (Join-Path $stagingRoot "host")

$stationEnvironment = Join-Path $configRoot "station.env"
if (-not (Test-Path -LiteralPath $stationEnvironment)) {
    Copy-Item -LiteralPath (Join-Path $packageRoot "config\station.env.example") -Destination $stationEnvironment
}

& py.exe -3.11 -m venv (Join-Path $stagingRoot "python")
$python = Join-Path $stagingRoot "python\Scripts\python.exe"
& $python -m pip install --no-index --find-links (Join-Path $stagingRoot "python\wheelhouse") --requirement (Join-Path $stagingRoot "python\requirements.lock")
& $python -m pip install --no-deps (Get-ChildItem -LiteralPath (Join-Path $stagingRoot "python") -Filter "specproof-*.whl" | Select-Object -First 1 -ExpandProperty FullName)

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
}
if (Test-Path -LiteralPath $versionRoot) {
    Remove-Item -LiteralPath $versionRoot -Recurse -Force
}
Move-Item -LiteralPath $stagingRoot -Destination $versionRoot

$current = Join-Path $InstallRoot "current"
if (Test-Path -LiteralPath $current) {
    Remove-Item -LiteralPath $current -Force
}
New-Item -ItemType Junction -Path $current -Target $versionRoot | Out-Null

$hostExecutable = Join-Path $current "host\SpecProof.Station.Host.exe"
$binaryPath = "`"$hostExecutable`" --environment Production"
if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Invoke-ServiceControl @("config", $ServiceName, "binPath=", $binaryPath, "start=", "auto")
} else {
    Invoke-ServiceControl @(
        "create",
        $ServiceName,
        "binPath=",
        $binaryPath,
        "start=",
        "auto",
        "obj=",
        "NT AUTHORITY\LocalService"
    )
}
Invoke-ServiceControl @(
    "description",
    $ServiceName,
    "SpecProof station host and local capture supervisor"
)
Invoke-ServiceControl @(
    "failure",
    $ServiceName,
    "reset=",
    "86400",
    "actions=",
    "restart/5000/restart/15000/restart/60000"
)

$serviceRegistry = "HKLM:\SYSTEM\CurrentControlSet\Services\$ServiceName"
$serviceEnvironment = @(
    "SPEC_PROOF_STATION_ENV_FILE=$stationEnvironment",
    "ASPNETCORE_ENVIRONMENT=Production",
    "ASPNETCORE_URLS=http://127.0.0.1:5070"
)
New-ItemProperty -Path $serviceRegistry -Name Environment -PropertyType MultiString -Value $serviceEnvironment -Force | Out-Null

Write-Host "Installed SpecProof Station $($manifest.packageVersion). Edit $stationEnvironment before starting $ServiceName."
