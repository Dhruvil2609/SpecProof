"""Environment checks for SpecProof Phase 0."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, cast

CommandRunner = Callable[[Sequence[str], float], subprocess.CompletedProcess[str]]
TcpConnector = Callable[[str, int, float], bool]
HttpGetter = Callable[[str, float], int]
ImportFinder = Callable[[str], bool]
ServiceProbe = Callable[[float], bool]


class _QueryResult(Protocol):
    def fetchone(self) -> object: ...


class _PostgresConnection(Protocol):
    def execute(self, query: str) -> _QueryResult: ...

    def close(self) -> None: ...


class CheckStatus(StrEnum):
    """Status emitted for each diagnostic check."""

    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass(frozen=True)
class CheckResult:
    """Single diagnostic result."""

    name: str
    status: CheckStatus
    detail: str
    required: bool = True


@dataclass(frozen=True)
class DoctorConfig:
    """Runtime options for diagnostics."""

    require_gpu: bool = False
    require_realsense: bool = False
    require_camera_stream: bool = False
    command_timeout_seconds: float = 10.0
    network_timeout_seconds: float = 1.5


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""

    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_command_runner(
    command: Sequence[str], timeout_seconds: float
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture text output."""

    resolved_executable = shutil.which(command[0]) or command[0]
    return subprocess.run(
        [resolved_executable, *command[1:]],
        capture_output=True,
        check=False,
        text=True,
        timeout=timeout_seconds,
    )


def default_tcp_connector(host: str, port: int, timeout_seconds: float) -> bool:
    """Return true when a TCP endpoint accepts a connection."""

    try:
        with socket.create_connection((host, port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def default_http_getter(url: str, timeout_seconds: float) -> int:
    """Return an HTTP status code for a URL."""

    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)
    except urllib.error.URLError:
        return 0


def default_import_finder(module_name: str) -> bool:
    """Return true when a Python module can be imported."""

    return importlib.util.find_spec(module_name) is not None


def parse_semver(text: str) -> tuple[int, int, int] | None:
    """Extract the first semantic version tuple from text."""

    match = re.search(r"(?<!\d)(\d+)\.(\d+)\.(\d+)(?!\d)", text)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def parse_major(text: str) -> int | None:
    """Extract a major version from a version string."""

    match = re.search(r"v?(\d+)(?:\.|$)", text.strip())
    if match is None:
        return None
    return int(match.group(1))


def is_git_supported(text: str) -> bool:
    """Return true when Git is at least 2.40."""

    version = parse_semver(text)
    return version is not None and version >= (2, 40, 0)


def is_python_311(text: str) -> bool:
    """Return true when Python reports version 3.11."""

    version = parse_semver(text)
    return version is not None and version[0:2] == (3, 11)


def is_dotnet_lts(text: str) -> bool:
    """Return true when .NET 10 SDK is available."""

    versions = [
        tuple(int(part) for part in match) for match in re.findall(r"\b(10)\.(\d+)\.(\d+)\b", text)
    ]
    return bool(versions)


def is_node_lts(text: str) -> bool:
    """Return true when Node.js major version is 24."""

    major = parse_major(text)
    return major == 24


def command_check(
    name: str,
    command: Sequence[str],
    validate: Callable[[str], bool],
    detail_on_success: Callable[[str], str],
    detail_on_failure: str,
    *,
    runner: CommandRunner,
    timeout_seconds: float,
    required: bool = True,
) -> CheckResult:
    """Run a command-backed check."""

    executable = command[0]
    if shutil.which(executable) is None:
        return CheckResult(name, CheckStatus.FAIL, f"{executable} was not found", required)

    try:
        completed = runner(command, timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as error:
        return CheckResult(name, CheckStatus.FAIL, str(error), required)

    output = f"{completed.stdout}\n{completed.stderr}".strip()
    if completed.returncode == 0 and validate(output):
        return CheckResult(name, CheckStatus.PASS, detail_on_success(output), required)

    return CheckResult(name, CheckStatus.FAIL, detail_on_failure, required)


def optional_command_check(
    name: str,
    command: Sequence[str],
    validate: Callable[[str], bool],
    detail_on_success: Callable[[str], str],
    detail_on_skip: str,
    *,
    runner: CommandRunner,
    timeout_seconds: float,
    required: bool,
) -> CheckResult:
    """Run a command-backed check that may be optional."""

    executable = command[0]
    if shutil.which(executable) is None:
        status = CheckStatus.FAIL if required else CheckStatus.SKIP
        return CheckResult(name, status, detail_on_skip, required)

    try:
        completed = runner(command, timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as error:
        status = CheckStatus.FAIL if required else CheckStatus.SKIP
        return CheckResult(name, status, str(error), required)

    output = f"{completed.stdout}\n{completed.stderr}".strip()
    if completed.returncode == 0 and validate(output):
        return CheckResult(name, CheckStatus.PASS, detail_on_success(output), required)

    status = CheckStatus.FAIL if required else CheckStatus.SKIP
    return CheckResult(name, status, detail_on_skip, required)


def check_os() -> CheckResult:
    """Check the operating system baseline."""

    system = platform.system()
    release = platform.release()
    version = platform.version()
    machine = platform.machine().lower()
    build_match = re.search(r"(?:^|\.)(\d{5})(?:\.|$)", version)
    build = int(build_match.group(1)) if build_match is not None else 0
    is_windows_11 = release == "11" or build >= 22000
    if system == "Windows" and is_windows_11 and machine in {"amd64", "x86_64"}:
        return CheckResult(
            "Windows 11 x64",
            CheckStatus.PASS,
            f"{system} build {build or release} {machine}",
        )
    return CheckResult(
        "Windows 11 x64", CheckStatus.FAIL, f"Expected Windows x64, got {system} {machine}"
    )


def default_postgres_probe(timeout_seconds: float) -> bool:
    """Execute `SELECT 1` against the configured development database."""

    try:
        import psycopg

        connection_string = os.getenv(
            "SPEC_PROOF_POSTGRES",
            "host=localhost port=55432 dbname=specproof user=Admin password=Admin@123",
        )
        connection = cast(
            _PostgresConnection,
            psycopg.connect(connection_string, connect_timeout=max(1, int(timeout_seconds))),
        )
        try:
            return connection.execute("SELECT 1").fetchone() == (1,)
        finally:
            connection.close()
    except Exception:
        return False


def default_redis_probe(timeout_seconds: float) -> bool:
    """Execute Redis PING."""

    try:
        import redis

        client = redis.Redis(
            host="localhost",
            port=6379,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )
        return bool(client.ping())
    except Exception:
        return False


def default_rabbitmq_probe(timeout_seconds: float) -> bool:
    """Open and close an authenticated RabbitMQ channel."""

    try:
        import pika

        credentials = pika.PlainCredentials("specproof", "specproof_dev_password")
        parameters = pika.ConnectionParameters(
            "localhost",
            5672,
            "/",
            credentials,
            socket_timeout=timeout_seconds,
            blocked_connection_timeout=timeout_seconds,
        )
        connection = pika.BlockingConnection(parameters)
        connection.channel()
        connection.close()
        return True
    except Exception:
        return False


def default_realsense_stream_probe(_: float) -> bool:
    """Return whether at least one RealSense device can be enumerated."""

    try:
        import pyrealsense2 as rs

        devices = cast(
            Sequence[object],
            rs.context().query_devices(),  # pyright: ignore[reportAttributeAccessIssue]
        )
        return len(devices) > 0
    except (ImportError, RuntimeError):
        return False


def protocol_service_check(
    name: str,
    probe: ServiceProbe,
    timeout_seconds: float,
    success_detail: str,
    failure_detail: str,
) -> CheckResult:
    """Run a protocol-level service probe."""

    succeeded = probe(timeout_seconds)
    return CheckResult(
        name,
        CheckStatus.PASS if succeeded else CheckStatus.FAIL,
        success_detail if succeeded else failure_detail,
    )


def check_docker_daemon(runner: CommandRunner, timeout_seconds: float) -> CheckResult:
    """Check whether Docker daemon responds."""

    return command_check(
        "Docker daemon",
        ["docker", "info"],
        lambda output: "Server Version" in output or "Containers:" in output,
        lambda _: "Docker daemon is reachable",
        "Docker CLI exists but daemon is not reachable",
        runner=runner,
        timeout_seconds=timeout_seconds,
    )


def check_compose_services(runner: CommandRunner, timeout_seconds: float) -> CheckResult:
    """Check whether compose services are visible."""

    return command_check(
        "Docker compose services",
        ["docker", "compose", "ps", "--format", "json"],
        lambda output: _compose_has_services(output),
        lambda _: "Compose project has running service records",
        "No running SpecProof compose services were found",
        runner=runner,
        timeout_seconds=timeout_seconds,
    )


def _compose_has_services(output: str) -> bool:
    if not output:
        return False
    try:
        parsed: object = json.loads(output)
    except json.JSONDecodeError:
        return "specproof-" in output
    if isinstance(parsed, list):
        return len(cast(list[object], parsed)) > 0
    return isinstance(parsed, dict) and len(cast(dict[object, object], parsed)) > 0


def tcp_service_check(
    name: str,
    host: str,
    port: int,
    connector: TcpConnector,
    timeout_seconds: float,
) -> CheckResult:
    """Check a TCP service endpoint."""

    if connector(host, port, timeout_seconds):
        return CheckResult(name, CheckStatus.PASS, f"{host}:{port} is reachable")
    return CheckResult(name, CheckStatus.FAIL, f"{host}:{port} is not reachable")


def http_service_check(
    name: str,
    url: str,
    getter: HttpGetter,
    timeout_seconds: float,
    expected_statuses: set[int],
) -> CheckResult:
    """Check an HTTP endpoint."""

    status_code = getter(url, timeout_seconds)
    if status_code in expected_statuses:
        return CheckResult(name, CheckStatus.PASS, f"{url} returned HTTP {status_code}")
    return CheckResult(
        name, CheckStatus.FAIL, f"{url} returned HTTP {status_code or 'no response'}"
    )


def import_check(
    name: str,
    module_name: str,
    finder: ImportFinder,
    *,
    required: bool,
    missing_detail: str,
) -> CheckResult:
    """Check whether a Python module is available."""

    if finder(module_name):
        return CheckResult(name, CheckStatus.PASS, f"{module_name} is available", required)
    status = CheckStatus.FAIL if required else CheckStatus.SKIP
    return CheckResult(name, status, missing_detail, required)


def run_checks(
    config: DoctorConfig | None = None,
    *,
    runner: CommandRunner = default_command_runner,
    tcp_connector: TcpConnector = default_tcp_connector,
    http_getter: HttpGetter = default_http_getter,
    import_finder: ImportFinder = default_import_finder,
    postgres_probe: ServiceProbe = default_postgres_probe,
    redis_probe: ServiceProbe = default_redis_probe,
    rabbitmq_probe: ServiceProbe = default_rabbitmq_probe,
    realsense_stream_probe: ServiceProbe = default_realsense_stream_probe,
) -> list[CheckResult]:
    """Run the Phase 0 environment checks."""

    settings = config or DoctorConfig()
    command_timeout = settings.command_timeout_seconds
    network_timeout = settings.network_timeout_seconds

    results = [
        check_os(),
        command_check(
            "Git",
            ["git", "--version"],
            is_git_supported,
            lambda output: output.splitlines()[0],
            "Git must be installed and at least version 2.40",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        command_check(
            "Git LFS",
            ["git", "lfs", "version"],
            lambda output: "git-lfs/" in output,
            lambda output: output.splitlines()[0],
            "Git LFS must be installed",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        command_check(
            "Python 3.11",
            [sys.executable, "--version"],
            is_python_311,
            lambda output: output.splitlines()[0],
            "Python 3.11 is required",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        command_check(
            "uv",
            ["uv", "--version"],
            lambda output: output.startswith("uv "),
            lambda output: output.splitlines()[0],
            "uv must be installed",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        command_check(
            ".NET LTS SDK",
            ["dotnet", "--info"],
            is_dotnet_lts,
            lambda _: ".NET 10 SDK is available",
            ".NET 10 LTS SDK is required",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        command_check(
            "Node.js LTS",
            ["node", "--version"],
            is_node_lts,
            lambda output: output.splitlines()[0],
            "Node.js 24 LTS is required",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        command_check(
            "pnpm",
            ["pnpm", "--version"],
            lambda output: parse_semver(output) is not None or parse_major(output) is not None,
            lambda output: output.splitlines()[0],
            "pnpm must be installed",
            runner=runner,
            timeout_seconds=command_timeout,
        ),
        check_docker_daemon(runner, command_timeout),
        check_compose_services(runner, command_timeout),
        protocol_service_check(
            "PostgreSQL",
            postgres_probe,
            network_timeout,
            "SELECT 1 succeeded",
            "PostgreSQL query failed",
        ),
        protocol_service_check(
            "Redis",
            redis_probe,
            network_timeout,
            "PING returned PONG",
            "Redis PING failed",
        ),
        http_service_check(
            "MinIO", "http://localhost:9000/minio/health/live", http_getter, network_timeout, {200}
        ),
        protocol_service_check(
            "RabbitMQ",
            rabbitmq_probe,
            network_timeout,
            "Authenticated channel opened",
            "RabbitMQ channel probe failed",
        ),
        http_service_check(
            "Prometheus", "http://localhost:9090/-/healthy", http_getter, network_timeout, {200}
        ),
        http_service_check(
            "Grafana", "http://localhost:3000/api/health", http_getter, network_timeout, {200}
        ),
        http_service_check(
            "Loki", "http://localhost:3100/ready", http_getter, network_timeout, {200}
        ),
        import_check(
            "RealSense Python",
            "pyrealsense2",
            import_finder,
            required=settings.require_realsense,
            missing_detail="RealSense Python binding is optional until camera work is required",
        ),
        *[
            import_check(
                name,
                module,
                import_finder,
                required=True,
                missing_detail=f"{module} is required",
            )
            for name, module in (
                ("NumPy", "numpy"),
                ("OpenCV", "cv2"),
                ("Open3D", "open3d"),
                ("PyTorch", "torch"),
            )
        ],
        (
            protocol_service_check(
                "RealSense camera stream",
                realsense_stream_probe,
                network_timeout,
                "RealSense device enumeration succeeded",
                "No RealSense camera stream is available",
            )
            if settings.require_camera_stream
            else CheckResult(
                "RealSense camera stream",
                CheckStatus.SKIP,
                "Physical camera validation is optional",
                required=False,
            )
        ),
        optional_command_check(
            "NVIDIA GPU",
            ["nvidia-smi"],
            lambda output: "NVIDIA-SMI" in output,
            lambda _: "NVIDIA GPU tooling is available",
            "NVIDIA GPU tooling is optional on non-GPU workstations",
            runner=runner,
            timeout_seconds=command_timeout,
            required=settings.require_gpu,
        ),
    ]

    return results


def has_required_failures(results: Sequence[CheckResult]) -> bool:
    """Return true when any required check failed."""

    return any(result.required and result.status == CheckStatus.FAIL for result in results)
