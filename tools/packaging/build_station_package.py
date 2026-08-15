"""Build and verify the versioned Linux x64 SpecProof station package."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory


def assemble_station_package(
    *,
    repository_root: Path,
    station_publish_dir: Path,
    python_wheel: Path,
    requirements_lock: Path,
    output_dir: Path,
    version: str,
) -> Path:
    """Assemble host binaries, Python runtime inputs, templates, and a hash manifest."""

    if not version or any(character in version for character in "/\\"):
        raise ValueError("version must be a non-empty filename-safe value")
    for required in (station_publish_dir, python_wheel, requirements_lock):
        if not required.exists():
            raise FileNotFoundError(required)
    templates = repository_root / "installers" / "linux"
    required_templates = (
        templates / "config" / "station.env.example",
        templates / "config" / "appsettings.Pilot.json",
        templates / "systemd" / "specproof-capture.service",
        templates / "systemd" / "specproof-station-host.service",
        templates / "install.sh",
        templates / "README.md",
    )
    for template in required_templates:
        if not template.is_file():
            raise FileNotFoundError(template)

    package_name = f"specproof-station-{version}-linux-x64"
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / f"{package_name}.tar.gz"
    with TemporaryDirectory(prefix="specproof-station-package-") as directory:
        package_root = Path(directory) / package_name
        shutil.copytree(station_publish_dir, package_root / "host")
        python_dir = package_root / "python"
        python_dir.mkdir(parents=True)
        shutil.copy2(python_wheel, python_dir / python_wheel.name)
        shutil.copy2(requirements_lock, python_dir / "requirements.lock")
        shutil.copytree(templates / "config", package_root / "config")
        shutil.copytree(templates / "systemd", package_root / "systemd")
        shutil.copy2(templates / "install.sh", package_root / "install.sh")
        shutil.copy2(templates / "README.md", package_root / "README.md")
        (package_root / "install.sh").chmod(0o755)
        station_executable = package_root / "host" / "SpecProof.Station.Host"
        if station_executable.is_file():
            station_executable.chmod(0o755)
        manifest = {
            "schemaVersion": 1,
            "packageVersion": version,
            "runtimeIdentifier": "linux-x64",
            "generatedAtUtc": datetime.now(UTC).isoformat(),
            "files": _manifest_files(package_root),
        }
        (package_root / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        with tarfile.open(archive_path, "w:gz") as archive:
            archive.add(package_root, arcname=package_name, filter=_archive_filter)
    return archive_path


def verify_station_package(archive_path: Path) -> None:
    """Verify required files and every SHA-256 entry in a station archive."""

    with TemporaryDirectory(prefix="specproof-station-verify-") as directory:
        extraction_root = Path(directory)
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extraction_root, filter="data")
        package_roots = [path for path in extraction_root.iterdir() if path.is_dir()]
        if len(package_roots) != 1:
            raise ValueError("Station archive must contain exactly one package root")
        package_root = package_roots[0]
        manifest_path = package_root / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        required = {
            "config/station.env.example",
            "config/appsettings.Pilot.json",
            "systemd/specproof-capture.service",
            "systemd/specproof-station-host.service",
            "python/requirements.lock",
            "install.sh",
        }
        files = manifest.get("files")
        if not isinstance(files, list):
            raise ValueError("Station manifest files must be a list")
        paths = {str(item["path"]) for item in files}
        if not required.issubset(paths):
            raise ValueError(f"Station archive is missing required files: {required - paths}")
        if not any(path.startswith("host/") for path in paths):
            raise ValueError("Station archive contains no Station Host publish output")
        if not any(path.startswith("python/") and path.endswith(".whl") for path in paths):
            raise ValueError("Station archive contains no Python wheel")
        for item in files:
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


def _archive_filter(member: tarfile.TarInfo) -> tarfile.TarInfo:
    member.uid = 0
    member.gid = 0
    member.uname = "root"
    member.gname = "root"
    normalized = member.name.replace("\\", "/")
    if member.isdir():
        member.mode = 0o755
    elif normalized.endswith("/install.sh") or normalized.endswith(
        "/host/SpecProof.Station.Host"
    ):
        member.mode = 0o755
    else:
        member.mode = 0o644
    return member


def _build_inputs(repository_root: Path, working_root: Path) -> tuple[Path, Path, Path]:
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
            "linux-x64",
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
    return station_publish_dir, wheels[0], requirements_lock


def main(arguments: Sequence[str] | None = None) -> int:
    """Build a Linux x64 station archive and verify its manifest."""

    parser = argparse.ArgumentParser(prog="build-station-package")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/packages"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parsed = parser.parse_args(arguments)
    repository_root = parsed.repository_root.resolve()
    with TemporaryDirectory(prefix="specproof-station-build-") as directory:
        station_publish_dir, python_wheel, requirements_lock = _build_inputs(
            repository_root,
            Path(directory),
        )
        archive_path = assemble_station_package(
            repository_root=repository_root,
            station_publish_dir=station_publish_dir,
            python_wheel=python_wheel,
            requirements_lock=requirements_lock,
            output_dir=parsed.output_dir.resolve(),
            version=parsed.version,
        )
    verify_station_package(archive_path)
    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
