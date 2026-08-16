"""Generate a deterministic CycloneDX SBOM for the SpecProof workspace."""

from __future__ import annotations

import argparse
import base64
import json
import re
import tomllib
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import quote

PNPM_PACKAGE_PATTERN = re.compile(
    r"^  (?P<coordinate>'[^']+'|\"[^\"]+\"|[^'\"\s][^:]*):$"
)
PNPM_INTEGRITY_PATTERN = re.compile(r"integrity:\s*(?P<algorithm>sha\d+)-(?P<digest>[^,}\s]+)")
DOCKER_FROM_PATTERN = re.compile(r"^FROM\s+(?P<image>\S+)", re.IGNORECASE)


@dataclass(frozen=True, order=True)
class Component:
    """One normalized software component."""

    ecosystem: str
    name: str
    version: str
    component_type: str = "library"
    source: str = ""
    hash_algorithm: str | None = None
    hash_value: str | None = None

    @property
    def reference(self) -> str:
        return f"{self.ecosystem}:{self.name}@{self.version}"


def collect_components(
    repository_root: Path,
    *,
    require_dotnet_assets: bool = True,
) -> tuple[Component, ...]:
    """Collect locked Python, .NET, Node, and container components."""

    components = [
        *_python_components(repository_root / "uv.lock"),
        *_dotnet_components(repository_root, require_assets=require_dotnet_assets),
        *_node_components(repository_root / "pnpm-lock.yaml"),
        *_container_components(repository_root),
    ]
    unique = {component.reference: component for component in components}
    return tuple(sorted(unique.values()))


def generate_sbom(
    repository_root: Path,
    *,
    timestamp: datetime | None = None,
    require_dotnet_assets: bool = True,
) -> dict[str, object]:
    """Generate a CycloneDX 1.6 document with stable component ordering."""

    components = collect_components(
        repository_root,
        require_dotnet_assets=require_dotnet_assets,
    )
    if not components:
        raise ValueError("No dependency components were discovered")
    generated_at = (timestamp or datetime.now(UTC)).astimezone(UTC)
    fingerprint = "\n".join(component.reference for component in components)
    serial = uuid.uuid5(uuid.NAMESPACE_URL, f"https://specproof.local/sbom/{fingerprint}")
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "timestamp": generated_at.isoformat().replace("+00:00", "Z"),
            "component": {
                "type": "application",
                "bom-ref": "pkg:generic/specproof@0.1.0",
                "name": "specproof",
                "version": "0.1.0",
                "purl": "pkg:generic/specproof@0.1.0",
            },
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": "specproof-sbom-generator",
                        "version": "1",
                    }
                ]
            },
        },
        "components": [_cyclonedx_component(component) for component in components],
    }


def write_sbom(document: dict[str, object], output_path: Path) -> None:
    """Write canonical JSON with normalized newlines."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _python_components(lock_path: Path) -> Iterable[Component]:
    lock = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    raw_packages = lock.get("package", [])
    if not isinstance(raw_packages, list):
        raise ValueError(f"Invalid package list in {lock_path}")
    for raw_package in cast(list[object], raw_packages):
        if not isinstance(raw_package, dict):
            raise ValueError(f"Invalid package entry in {lock_path}")
        package = cast(dict[str, object], raw_package)
        name = str(package["name"])
        version = str(package["version"])
        source = package.get("source", {})
        if name == "specproof" or not isinstance(source, dict) or "registry" not in source:
            continue
        digest = _first_python_hash(package)
        yield Component(
            ecosystem="pypi",
            name=name,
            version=version,
            source=lock_path.name,
            hash_algorithm="SHA-256" if digest else None,
            hash_value=digest,
        )


def _first_python_hash(package: dict[str, object]) -> str | None:
    source_distribution = package.get("sdist")
    if not isinstance(source_distribution, dict):
        return None
    digest = cast(dict[str, object], source_distribution).get("hash")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        return None
    return digest.removeprefix("sha256:").upper()


def _dotnet_components(repository_root: Path, *, require_assets: bool) -> Iterable[Component]:
    project_paths = sorted(repository_root.rglob("*.csproj"))
    missing_assets: list[Path] = []
    for project_path in project_paths:
        assets_path = project_path.parent / "obj" / "project.assets.json"
        if not assets_path.is_file():
            missing_assets.append(project_path.relative_to(repository_root))
            continue
        assets = json.loads(assets_path.read_text(encoding="utf-8"))
        libraries = assets.get("libraries", {})
        if not isinstance(libraries, dict):
            continue
        typed_libraries = cast(dict[str, object], libraries)
        for coordinate, raw_details in typed_libraries.items():
            details = (
                cast(dict[str, object], raw_details)
                if isinstance(raw_details, dict)
                else {}
            )
            if details.get("type") != "package":
                continue
            name, version = coordinate.rsplit("/", maxsplit=1)
            yield Component(
                ecosystem="nuget",
                name=name,
                version=version,
                source=project_path.relative_to(repository_root).as_posix(),
            )
    if require_assets and missing_assets:
        paths = ", ".join(path.as_posix() for path in missing_assets)
        raise FileNotFoundError(
            f"Run dotnet restore before SBOM generation; missing assets: {paths}"
        )


def _node_components(lock_path: Path) -> Iterable[Component]:
    lines = lock_path.read_text(encoding="utf-8").splitlines()
    in_packages = False
    current: tuple[str, str] | None = None
    integrity: tuple[str, str] | None = None
    for line in [*lines, "snapshots:"]:
        if line == "packages:":
            in_packages = True
            continue
        if not in_packages:
            continue
        if line == "snapshots:":
            if current:
                yield _node_component(*current, integrity=integrity, source=lock_path.name)
            break
        match = PNPM_PACKAGE_PATTERN.match(line)
        if match:
            if current:
                yield _node_component(*current, integrity=integrity, source=lock_path.name)
            current = _split_pnpm_coordinate(match.group("coordinate").strip("'\""))
            integrity = None
            continue
        integrity_match = PNPM_INTEGRITY_PATTERN.search(line)
        if current and integrity_match:
            integrity = _decode_integrity(
                integrity_match.group("algorithm"),
                integrity_match.group("digest"),
            )


def _split_pnpm_coordinate(coordinate: str) -> tuple[str, str]:
    name, version = coordinate.rsplit("@", maxsplit=1)
    if not name or not version:
        raise ValueError(f"Invalid pnpm package coordinate: {coordinate}")
    return name, version


def _decode_integrity(algorithm: str, digest: str) -> tuple[str, str]:
    normalized = algorithm.upper().replace("SHA", "SHA-")
    return normalized, base64.b64decode(digest).hex().upper()


def _node_component(
    name: str,
    version: str,
    *,
    integrity: tuple[str, str] | None,
    source: str,
) -> Component:
    return Component(
        ecosystem="npm",
        name=name,
        version=version,
        source=source,
        hash_algorithm=integrity[0] if integrity else None,
        hash_value=integrity[1] if integrity else None,
    )


def _container_components(repository_root: Path) -> Iterable[Component]:
    for dockerfile in sorted(repository_root.rglob("Dockerfile")):
        relative_path = dockerfile.relative_to(repository_root).as_posix()
        for line in dockerfile.read_text(encoding="utf-8").splitlines():
            match = DOCKER_FROM_PATTERN.match(line.strip())
            if not match:
                continue
            image = match.group("image")
            if image.startswith("$"):
                raise ValueError(f"Unresolved container base image in {relative_path}: {image}")
            name, version = _split_image(image)
            yield Component(
                ecosystem="oci",
                name=name,
                version=version,
                component_type="container",
                source=relative_path,
            )


def _split_image(image: str) -> tuple[str, str]:
    if "@" in image:
        name, version = image.rsplit("@", maxsplit=1)
        return name, version
    last_segment = image.rsplit("/", maxsplit=1)[-1]
    if ":" not in last_segment:
        raise ValueError(f"Container base image must be pinned: {image}")
    name, version = image.rsplit(":", maxsplit=1)
    return name, version


def _cyclonedx_component(component: Component) -> dict[str, object]:
    result: dict[str, object] = {
        "type": component.component_type,
        "bom-ref": component.reference,
        "name": component.name,
        "version": component.version,
        "properties": [{"name": "specproof:source", "value": component.source}],
    }
    if component.ecosystem != "oci":
        namespace = quote(component.name, safe="/")
        version = quote(component.version, safe=".-_+")
        result["purl"] = f"pkg:{component.ecosystem}/{namespace}@{version}"
    if component.hash_algorithm and component.hash_value:
        result["hashes"] = [
            {"alg": component.hash_algorithm, "content": component.hash_value}
        ]
    return result


def main(arguments: Sequence[str] | None = None) -> int:
    """Generate the workspace SBOM."""

    parser = argparse.ArgumentParser(prog="generate-sbom")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/sbom/specproof.cdx.json"),
    )
    parser.add_argument("--allow-missing-dotnet-assets", action="store_true")
    parsed = parser.parse_args(arguments)
    document = generate_sbom(
        parsed.repository_root.resolve(),
        require_dotnet_assets=not parsed.allow_missing_dotnet_assets,
    )
    write_sbom(document, parsed.output.resolve())
    components = document["components"]
    if not isinstance(components, list):
        raise TypeError("Generated SBOM components must be a list")
    print(f"Wrote {len(cast(list[object], components))} components to {parsed.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
