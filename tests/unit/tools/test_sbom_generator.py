from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.security.generate_sbom import collect_components, generate_sbom


def _write_fixture(repository: Path) -> None:
    (repository / "uv.lock").write_text(
        """version = 1
[[package]]
name = "specproof"
version = "0.1.0"
[[package]]
name = "example-python"
version = "1.2.3"
source = { registry = "https://pypi.org/simple" }
sdist = { hash = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
""",
        encoding="utf-8",
    )
    (repository / "pnpm-lock.yaml").write_text(
        """lockfileVersion: '9.0'
packages:
  '@scope/example@2.0.0':
    resolution: {integrity: sha512-YWJj}
    peerDependencies:
      nested-package: ^1.0.0
snapshots:
""",
        encoding="utf-8",
    )
    project = repository / "service" / "Service.csproj"
    project.parent.mkdir()
    project.write_text("<Project />", encoding="utf-8")
    assets = project.parent / "obj" / "project.assets.json"
    assets.parent.mkdir()
    assets.write_text(
        json.dumps(
            {
                "libraries": {
                    "Example.DotNet/3.0.0": {"type": "package"},
                    "Service/1.0.0": {"type": "project"},
                }
            }
        ),
        encoding="utf-8",
    )
    dockerfile = repository / "service" / "Dockerfile"
    dockerfile.write_text("FROM example/service:4.0.0\n", encoding="utf-8")


@pytest.mark.unit
def test_sbom_collects_every_supported_ecosystem(tmp_path: Path) -> None:
    _write_fixture(tmp_path)

    components = collect_components(tmp_path)

    coordinates = {
        (component.ecosystem, component.name, component.version) for component in components
    }
    assert coordinates == {
        ("pypi", "example-python", "1.2.3"),
        ("nuget", "Example.DotNet", "3.0.0"),
        ("npm", "@scope/example", "2.0.0"),
        ("oci", "example/service", "4.0.0"),
    }


@pytest.mark.unit
def test_sbom_is_deterministic_and_cyclonedx_compatible(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    timestamp = datetime(2026, 8, 16, tzinfo=UTC)

    first = generate_sbom(tmp_path, timestamp=timestamp)
    second = generate_sbom(tmp_path, timestamp=timestamp)

    assert first == second
    assert first["bomFormat"] == "CycloneDX"
    assert first["specVersion"] == "1.6"
    assert str(first["serialNumber"]).startswith("urn:uuid:")
    assert first["metadata"]["timestamp"] == "2026-08-16T00:00:00Z"  # type: ignore[index]
    components = first["components"]
    assert isinstance(components, list)
    npm = next(component for component in components if component["bom-ref"].startswith("npm:"))
    oci = next(component for component in components if component["bom-ref"].startswith("oci:"))
    assert npm["purl"] == "pkg:npm/%40scope/example@2.0.0"
    assert "purl" not in oci


@pytest.mark.unit
def test_sbom_requires_restored_dotnet_assets(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    (tmp_path / "service" / "obj" / "project.assets.json").unlink()

    with pytest.raises(FileNotFoundError, match="dotnet restore"):
        collect_components(tmp_path)
