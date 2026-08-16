[CmdletBinding()]
param(
    [string]$InstallRoot = "$env:ProgramFiles\SpecProof\Station",
    [string]$DataRoot = "$env:ProgramData\SpecProof\Station",
    [string]$ServiceName = "SpecProofStationHost",
    [switch]$RemoveData
)

$ErrorActionPreference = "Stop"
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run the SpecProof station uninstaller as Administrator."
}

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    & sc.exe delete $ServiceName | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to delete Windows service $ServiceName (exit $LASTEXITCODE)."
    }
}
if (Test-Path -LiteralPath $InstallRoot) {
    Remove-Item -LiteralPath $InstallRoot -Recurse -Force
}
if ($RemoveData -and (Test-Path -LiteralPath $DataRoot)) {
    Remove-Item -LiteralPath $DataRoot -Recurse -Force
}

Write-Host "Uninstalled SpecProof Station. Configuration and data were preserved unless -RemoveData was supplied."
