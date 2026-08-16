from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from tools.packaging.build_windows_station_package import (
    assemble_windows_station_package,
    verify_windows_station_package,
)

WORKSPACE = Path(__file__).resolve().parents[3]


def _assemble(tmp_path: Path) -> Path:
    publish = tmp_path / "publish"
    publish.mkdir()
    (publish / "SpecProof.Station.Host.exe").write_bytes(b"windows-host")
    wheel = tmp_path / "specproof-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"specproof-wheel")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "pydantic-2.11.0-py3-none-any.whl").write_bytes(b"dependency")
    requirements = tmp_path / "requirements.lock"
    requirements.write_text("pydantic==2.11.0\n", encoding="utf-8")
    return assemble_windows_station_package(
        repository_root=WORKSPACE,
        station_publish_dir=publish,
        python_wheel=wheel,
        wheelhouse_dir=wheelhouse,
        requirements_lock=requirements,
        output_dir=tmp_path / "artifacts",
        version="0.1.0-test",
    )


@pytest.mark.unit
def test_windows_service_package_contains_offline_runtime_and_lifecycle_scripts(
    tmp_path: Path,
) -> None:
    archive_path = _assemble(tmp_path)

    verify_windows_station_package(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        manifest_name = next(name for name in archive.namelist() if name.endswith("manifest.json"))
        manifest = json.loads(archive.read(manifest_name))

    assert manifest["runtimeIdentifier"] == "win-x64"
    assert manifest["packageVersion"] == "0.1.0-test"
    assert any(item["path"].startswith("python/wheelhouse/") for item in manifest["files"])


@pytest.mark.unit
def test_windows_service_package_rejects_tampered_file(tmp_path: Path) -> None:
    archive_path = _assemble(tmp_path)
    extraction_root = tmp_path / "extracted"
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extraction_root)
    package_root = next(extraction_root.iterdir())
    (package_root / "config" / "station.env.example").write_text(
        "tampered=true\n",
        encoding="utf-8",
    )
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(tampered, "w") as archive:
        for path in package_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(package_root.parent).as_posix())

    with pytest.raises(ValueError, match="hash mismatch"):
        verify_windows_station_package(tampered)


@pytest.mark.unit
def test_windows_lifecycle_scripts_preserve_data_by_default() -> None:
    installer = (WORKSPACE / "installers/windows/install-service.ps1").read_text(
        encoding="utf-8"
    )
    uninstaller = (WORKSPACE / "installers/windows/uninstall-service.ps1").read_text(
        encoding="utf-8"
    )

    assert "--no-index" in installer
    assert "PropertyType MultiString" in installer
    assert "-RemoveData" in uninstaller
    assert "if ($RemoveData" in uninstaller
