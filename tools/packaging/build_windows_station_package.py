"""Build and verify the offline Windows x64 SpecProof station service package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast


def assemble_windows_station_package(
    *,
    repository_root: Path,
    station_publish_dir: Path,
    python_wheel: Path,
    wheelhouse_dir: Path,
    requirements_lock: Path,
    output_dir: Path,
    version: str,
) -> Path:
    """Assemble the Windows service package and immutable file manifest."""

    if not version or any(character in version for character in "/\\"):
        raise ValueError("version must be a non-empty filename-safe value")
    for required in (
        station_publish_dir,
        python_wheel,
        wheelhouse_dir,
        requirements_lock,
    ):
        if not required.exists():
            raise FileNotFoundError(required)
    templates = repository_root / "installers" / "windows"
    required_templates = (
        templates / "config" / "station.env.example",
        templates / "config" / "appsettings.Production.json",
        templates / "install-service.ps1",
        templates / "uninstall-service.ps1",
        templates / "README.md",
    )
    for template in required_templates:
        if not template.is_file():
            raise FileNotFoundError(template)
    wheelhouse_files = tuple(wheelhouse_dir.glob("*.whl"))
    if not wheelhouse_files:
        raise ValueError("Windows package wheelhouse must contain dependency wheels")

    package_name = f"specproof-station-{version}-win-x64"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{package_name}.zip"
    with TemporaryDirectory(prefix="specproof-windows-station-package-") as directory:
        package_root = Path(directory) / package_name
        shutil.copytree(station_publish_dir, package_root / "host")
        python_dir = package_root / "python"
        python_dir.mkdir(parents=True)
        shutil.copy2(python_wheel, python_dir / python_wheel.name)
        shutil.copy2(requirements_lock, python_dir / "requirements.lock")
        shutil.copytree(wheelhouse_dir, python_dir / "wheelhouse")
        shutil.copytree(templates / "config", package_root / "config")
        for name in ("install-service.ps1", "uninstall-service.ps1", "README.md"):
            shutil.copy2(templates / name, package_root / name)
        manifest = {
            "schemaVersion": 1,
            "packageVersion": version,
            "runtimeIdentifier": "win-x64",
            "generatedAtUtc": datetime.now(UTC).isoformat(),
            "files": _manifest_files(package_root),
        }
        (package_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package_root.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(package_root.parent).as_posix())
    return archive_path


def verify_windows_station_package(archive_path: Path) -> None:
    """Verify required Windows service files and every SHA-256 entry."""

    with TemporaryDirectory(prefix="specproof-windows-station-verify-") as directory:
        extraction_root = Path(directory)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extraction_root)
        package_roots = [path for path in extraction_root.iterdir() if path.is_dir()]
        if len(package_roots) != 1:
            raise ValueError("Windows archive must contain exactly one package root")
        package_root = package_roots[0]
        manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("runtimeIdentifier") != "win-x64":
            raise ValueError("Windows package runtime identifier is invalid")
        files = manifest.get("files")
        if not isinstance(files, list):
            raise ValueError("Windows package manifest files must be a list")
        typed_files: list[dict[str, object]] = []
        for raw_item in cast(list[object], files):
            if not isinstance(raw_item, dict):
                raise ValueError("Windows package manifest entries must be objects")
            item = cast(dict[str, object], raw_item)
            if not isinstance(item.get("path"), str) or not isinstance(
                item.get("sha256"), str
            ):
                raise ValueError("Windows package manifest entries require path and sha256")
            typed_files.append(item)
        paths = {str(item["path"]) for item in typed_files}
        required = {
            "config/appsettings.Production.json",
            "config/station.env.example",
            "install-service.ps1",
            "uninstall-service.ps1",
            "python/requirements.lock",
        }
        if not required.issubset(paths):
            raise ValueError(f"Windows package is missing required files: {required - paths}")
        if not any(path.startswith("host/") and path.endswith(".exe") for path in paths):
            raise ValueError("Windows package contains no Station Host executable")
        if not any(path.startswith("python/") and path.endswith(".whl") for path in paths):
            raise ValueError("Windows package contains no SpecProof Python wheel")
        if not any(path.startswith("python/wheelhouse/") for path in paths):
            raise ValueError("Windows package contains no offline dependency wheelhouse")
        for item in typed_files:
            relative_path = Path(str(item["path"]))
            file_path = package_root / relative_path
            if not file_path.is_file():
                raise ValueError(f"Manifest file is missing: {relative_path.as_posix()}")
            if _sha256(file_path) != item["sha256"]:
                raise ValueError(f"Manifest hash mismatch: {relative_path.as_posix()}")


def _manifest_files(package_root: Path) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(package_root).as_posix(),
            "sizeBytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(package_root.rglob("*"))
        if path.is_file()
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_inputs(repository_root: Path, working_root: Path) -> tuple[Path, Path, Path, Path]:
    environment = {**os.environ, "UV_CACHE_DIR": str(repository_root / ".uv-cache")}
    station_publish_dir = working_root / "station-host"
    subprocess.run(
        [
            "dotnet",
            "publish",
            str(repository_root / "apps" / "station-host" / "SpecProof.Station.Host.csproj"),
            "--configuration",
            "Release",
            "--runtime",
            "win-x64",
            "--self-contained",
            "true",
            "--output",
            str(station_publish_dir),
        ],
        cwd=repository_root,
        check=True,
        env=environment,
    )
    requirements_lock = working_root / "requirements.lock"
    subprocess.run(
        [
            "uv",
            "export",
            "--frozen",
            "--group",
            "runtime",
            "--group",
            "station",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements_lock),
            "--quiet",
        ],
        cwd=repository_root,
        check=True,
        env=environment,
    )
    wheelhouse_dir = working_root / "wheelhouse"
    wheelhouse_dir.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--requirement",
            str(requirements_lock),
            "--dest",
            str(wheelhouse_dir),
        ],
        cwd=repository_root,
        check=True,
        env=environment,
    )
    wheel_dir = working_root / "wheel"
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(wheel_dir)],
        cwd=repository_root,
        check=True,
        env=environment,
    )
    wheels = tuple(wheel_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one SpecProof Python wheel")
    return station_publish_dir, wheels[0], wheelhouse_dir, requirements_lock


def main(arguments: Sequence[str] | None = None) -> int:
    """Build and verify the Windows x64 service archive."""

    parser = argparse.ArgumentParser(prog="build-windows-station-package")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/packages"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parsed = parser.parse_args(arguments)
    repository_root = parsed.repository_root.resolve()
    with TemporaryDirectory(prefix="specproof-windows-station-build-") as directory:
        publish_dir, python_wheel, wheelhouse, requirements = _build_inputs(
            repository_root,
            Path(directory),
        )
        archive_path = assemble_windows_station_package(
            repository_root=repository_root,
            station_publish_dir=publish_dir,
            python_wheel=python_wheel,
            wheelhouse_dir=wheelhouse,
            requirements_lock=requirements,
            output_dir=parsed.output_dir.resolve(),
            version=parsed.version,
        )
    verify_windows_station_package(archive_path)
    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
