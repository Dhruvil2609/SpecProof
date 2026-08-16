# SpecProof Windows x64 Station Service Package

The versioned ZIP contains the self-contained Station Host, an offline Python dependency
wheelhouse, the SpecProof Python wheel, production configuration templates, PowerShell
service lifecycle scripts, and a SHA-256 manifest.

On a supported Windows x64 station:

1. Verify the ZIP with `build_windows_station_package.py`.
2. Extract it to a local administrator-controlled directory.
3. Run `install-service.ps1` from an elevated PowerShell session.
4. Edit `C:\ProgramData\SpecProof\Station\config\station.env` and replace every placeholder.
5. Start `SpecProofStationHost` and verify `http://127.0.0.1:5070/api/v1/health`.

Upgrades preserve configuration and station data and activate a new version directory.
`uninstall-service.ps1` preserves data unless `-RemoveData` is explicitly supplied.
