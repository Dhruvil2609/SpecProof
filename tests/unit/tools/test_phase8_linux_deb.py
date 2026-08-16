from __future__ import annotations

from pathlib import Path

import pytest

from tools.packaging.build_linux_deb import assemble_linux_deb, verify_linux_deb

WORKSPACE = Path(__file__).resolve().parents[3]


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    publish = tmp_path / "publish"
    publish.mkdir()
    (publish / "SpecProof.Station.Host").write_bytes(b"linux-host")
    wheel = tmp_path / "specproof-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"specproof-wheel")
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "pydantic-2.11.0-py3-none-any.whl").write_bytes(b"dependency")
    requirements = tmp_path / "requirements.lock"
    requirements.write_text("pydantic==2.11.0\n", encoding="utf-8")
    return publish, wheel, wheelhouse, requirements


@pytest.mark.unit
def test_linux_deb_contains_offline_runtime_systemd_and_valid_manifest(tmp_path: Path) -> None:
    publish, wheel, wheelhouse, requirements = _inputs(tmp_path)
    package = assemble_linux_deb(
        repository_root=WORKSPACE,
        station_publish_dir=publish,
        python_wheel=wheel,
        wheelhouse_dir=wheelhouse,
        requirements_lock=requirements,
        output_dir=tmp_path / "artifacts",
        version="0.1.0-1",
    )

    assert package.name == "specproof-station_0.1.0-1_amd64.deb"
    verify_linux_deb(package)


@pytest.mark.unit
def test_linux_deb_rejects_missing_wheelhouse(tmp_path: Path) -> None:
    publish, wheel, wheelhouse, requirements = _inputs(tmp_path)
    next(wheelhouse.iterdir()).unlink()

    with pytest.raises(ValueError, match="wheelhouse"):
        assemble_linux_deb(
            repository_root=WORKSPACE,
            station_publish_dir=publish,
            python_wheel=wheel,
            wheelhouse_dir=wheelhouse,
            requirements_lock=requirements,
            output_dir=tmp_path / "artifacts",
            version="0.1.0-1",
        )


@pytest.mark.unit
def test_linux_systemd_units_apply_production_sandbox() -> None:
    for name in ("specproof-capture.service", "specproof-station-host.service"):
        unit = (WORKSPACE / "installers/linux/systemd" / name).read_text(encoding="utf-8")
        for control in (
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectHome=true",
            "ProtectKernelTunables=true",
            "RestrictSUIDSGID=true",
            "UMask=0077",
        ):
            assert control in unit
