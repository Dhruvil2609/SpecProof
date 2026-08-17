from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast


class DevelopmentService(TypedDict, total=False):
    name: str
    command: str
    arguments: list[str]
    workingDirectory: str
    port: int
    healthUrl: str
    environment: dict[str, str]


def load_services() -> list[DevelopmentService]:
    repository_root = Path(__file__).parents[3]
    configuration = json.loads(
        (repository_root / "development-services.json").read_text(encoding="utf-8")
    )
    return cast(list[DevelopmentService], configuration["services"])


def test_development_services_define_expected_processes() -> None:
    services = load_services()

    assert {service["name"] for service in services} == {
        "capture-service",
        "station-host",
        "platform-api",
        "operator-ui",
        "admin-ui",
    }


def test_development_services_use_unique_ports() -> None:
    ports = [
        service["port"]
        for service in load_services()
        if isinstance(service.get("port"), int)
    ]

    assert len(ports) == len(set(ports))


def test_development_service_project_paths_exist() -> None:
    repository_root = Path(__file__).parents[3]
    project_paths = []
    for service in load_services():
        arguments = service["arguments"]
        if "--project" in arguments:
            project_paths.append(arguments[arguments.index("--project") + 1])

    assert project_paths and all((repository_root / path).is_file() for path in project_paths)


def test_development_service_working_directories_exist() -> None:
    repository_root = Path(__file__).parents[3]

    assert all(
        (repository_root / service["workingDirectory"]).is_dir() for service in load_services()
    )


def test_development_launcher_supports_infrastructure_only_mode() -> None:
    repository_root = Path(__file__).parents[3]
    launcher = (repository_root / "start-development.ps1").read_text(encoding="utf-8")

    assert "[switch]$InfrastructureOnly" in launcher
    assert "SpecProof Docker infrastructure is running." in launcher
    assert "-InfrastructureOnly" in launcher
    assert "PostgreSQL:  localhost:55432" in launcher
    assert "MLflow:      http://localhost:5000" in launcher


def test_station_host_uses_dedicated_browser_port() -> None:
    station_host = next(
        service for service in load_services() if service["name"] == "station-host"
    )

    assert station_host["port"] == 5090
    assert station_host["healthUrl"] == "http://127.0.0.1:5090/api/v1/health"
    assert station_host["environment"]["ASPNETCORE_URLS"] == "http://127.0.0.1:5090"


def test_mlflow_image_includes_pinned_postgresql_driver() -> None:
    repository_root = Path(__file__).parents[3]
    compose = (repository_root / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile_path = repository_root / "infra/docker/mlflow/Dockerfile"
    dockerfile = dockerfile_path.read_text(encoding="utf-8")

    assert "dockerfile: infra/docker/mlflow/Dockerfile" in compose
    assert "postgresql+psycopg2://Admin:Admin%40123@postgres:5432/specproof" in compose
    assert '"/opt/mlflow/healthcheck.py"' in compose
    assert "FROM ghcr.io/mlflow/mlflow:v2.22.0" in dockerfile
    assert "psycopg2-binary==2.9.10" in dockerfile
    assert "COPY infra/docker/mlflow/healthcheck.py /opt/mlflow/healthcheck.py" in dockerfile
