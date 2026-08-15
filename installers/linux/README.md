# SpecProof Linux x64 Station Package

The versioned archive contains the self-contained Station Host, the SpecProof Python wheel,
locked runtime requirements, configuration templates, systemd service units, and SHA-256
manifest. Verify the archive with `build_station_package.py` before installation.

On a supported Ubuntu x64 station:

1. Extract the archive.
2. Run `sudo ./install.sh`.
3. Edit `/etc/specproof/station.env` with the assigned tenant, station, credentials, storage,
   and camera settings.
4. Start `specproof-capture.service` and `specproof-station-host.service`.
5. Verify both units and the Station Host `/api/v1/health` endpoint.
