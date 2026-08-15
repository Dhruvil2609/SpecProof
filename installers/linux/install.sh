#!/usr/bin/env sh
set -eu

PACKAGE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
INSTALL_ROOT=/opt/specproof/station
CONFIG_ROOT=/etc/specproof
DATA_ROOT=/var/lib/specproof/station

if [ "$(id -u)" -ne 0 ]; then
  echo "Run this installer as root." >&2
  exit 1
fi

if ! id specproof >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA_ROOT" --create-home --shell /usr/sbin/nologin specproof
fi

install -d -o specproof -g specproof "$INSTALL_ROOT" "$CONFIG_ROOT" "$DATA_ROOT"
rm -rf "$INSTALL_ROOT/host" "$INSTALL_ROOT/python"
cp -R "$PACKAGE_ROOT/host" "$INSTALL_ROOT/host"
python3.11 -m venv "$INSTALL_ROOT/python"
"$INSTALL_ROOT/python/bin/pip" install --requirement "$PACKAGE_ROOT/python/requirements.lock"
"$INSTALL_ROOT/python/bin/pip" install "$PACKAGE_ROOT"/python/*.whl
install -m 0644 "$PACKAGE_ROOT/config/appsettings.Pilot.json" "$INSTALL_ROOT/host/appsettings.Pilot.json"
if [ ! -f "$CONFIG_ROOT/station.env" ]; then
  install -m 0600 "$PACKAGE_ROOT/config/station.env.example" "$CONFIG_ROOT/station.env"
fi
install -m 0644 "$PACKAGE_ROOT/systemd/specproof-capture.service" /etc/systemd/system/specproof-capture.service
install -m 0644 "$PACKAGE_ROOT/systemd/specproof-station-host.service" /etc/systemd/system/specproof-station-host.service
chown -R specproof:specproof "$INSTALL_ROOT" "$DATA_ROOT"
systemctl daemon-reload
systemctl enable specproof-capture.service specproof-station-host.service

echo "Edit /etc/specproof/station.env, then start the SpecProof services."
