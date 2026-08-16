"""Build and verify the offline SpecProof station Debian package."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

VERSION_PATTERN = re.compile(r"^[0-9][0-9A-Za-z.+:~\-]*$")


def assemble_linux_deb(
    *,
    repository_root: Path,
    station_publish_dir: Path,
    python_wheel: Path,
    wheelhouse_dir: Path,
    requirements_lock: Path,
    output_dir: Path,
    version: str,
) -> Path:
    """Assemble an amd64 Debian package from prepared release inputs."""

    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError("version must be a valid Debian package version")
    for required in (station_publish_dir, python_wheel, wheelhouse_dir, requirements_lock):
        if not required.exists():
            raise FileNotFoundError(required)
    if not tuple(wheelhouse_dir.glob("*.whl")):
        raise ValueError("Debian package wheelhouse must contain dependency wheels")
    templates = repository_root / "installers/linux"
    for relative in (
        "config/station.env.example",
        "config/appsettings.Pilot.json",
        "systemd/specproof-capture.service",
        "systemd/specproof-station-host.service",
        "debian/control",
        "debian/conffiles",
        "debian/postinst",
        "debian/prerm",
        "debian/postrm",
    ):
        if not (templates / relative).is_file():
            raise FileNotFoundError(templates / relative)

    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"specproof-station_{version}_amd64.deb"
    with TemporaryDirectory(prefix="specproof-linux-deb-") as directory:
        root = Path(directory)
        data_root = root / "data"
        control_root = root / "control"
        _assemble_data(
            templates,
            data_root,
            station_publish_dir,
            python_wheel,
            wheelhouse_dir,
            requirements_lock,
            version,
        )
        _assemble_control(templates / "debian", control_root, version)
        _write_ar(
            package_path,
            (
                ("debian-binary", b"2.0\n"),
                ("control.tar.gz", _tar_bytes(control_root)),
                ("data.tar.gz", _tar_bytes(data_root)),
            ),
        )
    return package_path


def verify_linux_deb(package_path: Path) -> None:
    """Verify required Debian members and every payload manifest hash."""

    members = _read_ar(package_path)
    if set(members) != {"debian-binary", "control.tar.gz", "data.tar.gz"}:
        raise ValueError("Debian package members are incomplete")
    if members["debian-binary"] != b"2.0\n":
        raise ValueError("Unsupported Debian binary version")
    with TemporaryDirectory(prefix="specproof-linux-deb-verify-") as directory:
        extraction_root = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(members["data.tar.gz"]), mode="r:gz") as archive:
            host_members = [
                member
                for member in archive.getmembers()
                if member.name.endswith("opt/specproof/station/host/SpecProof.Station.Host")
            ]
            if len(host_members) != 1 or not host_members[0].mode & 0o111:
                raise ValueError("Debian Station Host must be executable")
            archive.extractall(extraction_root, filter="data")
        manifest_path = extraction_root / "usr/share/specproof/station/manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("runtimeIdentifier") != "linux-x64":
            raise ValueError("Debian package runtime identifier is invalid")
        raw_files = manifest.get("files")
        if not isinstance(raw_files, list):
            raise ValueError("Debian manifest files must be a list")
        files = _typed_manifest_files(cast(list[object], raw_files))
        paths = {str(item["path"]) for item in files}
        required = {
            "etc/specproof/station.env",
            "lib/systemd/system/specproof-capture.service",
            "lib/systemd/system/specproof-station-host.service",
            "usr/lib/specproof/station/python/requirements.lock",
        }
        if not required.issubset(paths):
            raise ValueError(f"Debian package is missing required files: {required - paths}")
        if not any(path.startswith("opt/specproof/station/host/") for path in paths):
            raise ValueError("Debian package contains no Station Host output")
        if not any("/wheelhouse/" in path for path in paths):
            raise ValueError("Debian package contains no offline wheelhouse")
        for item in files:
            relative_path = Path(str(item["path"]))
            payload_path = extraction_root / relative_path
            if not payload_path.is_file():
                raise ValueError(f"Debian payload file is missing: {relative_path.as_posix()}")
            if _sha256(payload_path) != item["sha256"]:
                raise ValueError(f"Debian payload hash mismatch: {relative_path.as_posix()}")


def _typed_manifest_files(raw_files: list[object]) -> list[dict[str, object]]:
    files: list[dict[str, object]] = []
    for raw_item in raw_files:
        if not isinstance(raw_item, dict):
            raise ValueError("Debian manifest entries must be objects")
        item = cast(dict[str, object], raw_item)
        if not isinstance(item.get("path"), str) or not isinstance(item.get("sha256"), str):
            raise ValueError("Debian manifest entries require path and sha256")
        files.append(item)
    return files


def _assemble_data(
    templates: Path,
    data_root: Path,
    station_publish_dir: Path,
    python_wheel: Path,
    wheelhouse_dir: Path,
    requirements_lock: Path,
    version: str,
) -> None:
    host_root = data_root / "opt/specproof/station/host"
    shutil.copytree(station_publish_dir, host_root)
    shutil.copy2(
        templates / "config/appsettings.Pilot.json",
        host_root / "appsettings.Production.json",
    )
    environment_path = data_root / "etc/specproof/station.env"
    environment_path.parent.mkdir(parents=True)
    shutil.copy2(templates / "config/station.env.example", environment_path)
    systemd_root = data_root / "lib/systemd/system"
    systemd_root.mkdir(parents=True)
    for name in ("specproof-capture.service", "specproof-station-host.service"):
        shutil.copy2(templates / "systemd" / name, systemd_root / name)
    python_root = data_root / "usr/lib/specproof/station/python"
    python_root.mkdir(parents=True)
    shutil.copy2(python_wheel, python_root / python_wheel.name)
    shutil.copy2(requirements_lock, python_root / "requirements.lock")
    shutil.copytree(wheelhouse_dir, python_root / "wheelhouse")
    manifest = {
        "schemaVersion": 1,
        "packageVersion": version,
        "runtimeIdentifier": "linux-x64",
        "generatedAtUtc": datetime.now(UTC).isoformat(),
        "files": _manifest_files(data_root),
    }
    manifest_path = data_root / "usr/share/specproof/station/manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _assemble_control(templates: Path, control_root: Path, version: str) -> None:
    control_root.mkdir()
    control = (templates / "control").read_text(encoding="utf-8").replace(
        "${VERSION}", version
    )
    (control_root / "control").write_text(control, encoding="utf-8", newline="\n")
    shutil.copy2(templates / "conffiles", control_root / "conffiles")
    for name in ("postinst", "prerm", "postrm"):
        target = control_root / name
        shutil.copy2(templates / name, target)
        target.chmod(0o755)


def _manifest_files(root: Path) -> list[dict[str, object]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "sizeBytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]


def _tar_bytes(root: Path) -> bytes:
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for path in sorted(root.rglob("*")):
            archive.add(
                path,
                arcname=path.relative_to(root).as_posix(),
                recursive=False,
                filter=_tar_filter,
            )
    return output.getvalue()


def _tar_filter(member: tarfile.TarInfo) -> tarfile.TarInfo:
    member.uid = member.gid = 0
    member.uname = member.gname = "root"
    executable = member.name in {"postinst", "prerm", "postrm"} or member.name.endswith(
        "opt/specproof/station/host/SpecProof.Station.Host"
    )
    member.mode = 0o755 if member.isdir() or executable else 0o644
    return member


def _write_ar(path: Path, members: Sequence[tuple[str, bytes]]) -> None:
    with path.open("wb") as output:
        output.write(b"!<arch>\n")
        for name, content in members:
            header = (
                f"{f'{name}/':<16}{0:<12}{0:<6}{0:<6}{0o100644:<8o}{len(content):<10}`\n"
            ).encode("ascii")
            if len(header) != 60:
                raise ValueError("Invalid ar member header")
            output.write(header)
            output.write(content)
            if len(content) % 2:
                output.write(b"\n")


def _read_ar(path: Path) -> dict[str, bytes]:
    content = path.read_bytes()
    if not content.startswith(b"!<arch>\n"):
        raise ValueError("Invalid Debian ar archive")
    members: dict[str, bytes] = {}
    offset = 8
    while offset < len(content):
        header = content[offset : offset + 60]
        if len(header) != 60 or header[58:60] != b"`\n":
            raise ValueError("Invalid ar member header")
        name = header[:16].decode("ascii").strip().removesuffix("/")
        size = int(header[48:58].decode("ascii").strip())
        offset += 60
        members[name] = content[offset : offset + size]
        offset += size + (size % 2)
    return members


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_inputs(repository_root: Path, working_root: Path) -> tuple[Path, Path, Path, Path]:
    environment = {**os.environ, "UV_CACHE_DIR": str(repository_root / ".uv-cache")}
    publish_dir = working_root / "station-host"
    subprocess.run(
        [
            "dotnet",
            "publish",
            str(repository_root / "apps/station-host/SpecProof.Station.Host.csproj"),
            "--configuration",
            "Release",
            "--runtime",
            "linux-x64",
            "--self-contained",
            "true",
            "--output",
            str(publish_dir),
        ],
        cwd=repository_root,
        check=True,
        env=environment,
    )
    requirements = working_root / "requirements.lock"
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
            str(requirements),
            "--quiet",
        ],
        cwd=repository_root,
        check=True,
        env=environment,
    )
    wheelhouse = working_root / "wheelhouse"
    wheelhouse.mkdir()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--requirement",
            str(requirements),
            "--dest",
            str(wheelhouse),
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
    return publish_dir, wheels[0], wheelhouse, requirements


def main(arguments: Sequence[str] | None = None) -> int:
    """Build and verify the production Linux amd64 Debian package."""

    parser = argparse.ArgumentParser(prog="build-linux-deb")
    parser.add_argument("--version", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/packages"))
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parsed = parser.parse_args(arguments)
    repository_root = parsed.repository_root.resolve()
    with TemporaryDirectory(prefix="specproof-linux-deb-build-") as directory:
        publish_dir, python_wheel, wheelhouse, requirements = _build_inputs(
            repository_root,
            Path(directory),
        )
        package_path = assemble_linux_deb(
            repository_root=repository_root,
            station_publish_dir=publish_dir,
            python_wheel=python_wheel,
            wheelhouse_dir=wheelhouse,
            requirements_lock=requirements,
            output_dir=parsed.output_dir.resolve(),
            version=parsed.version,
        )
    verify_linux_deb(package_path)
    print(package_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
