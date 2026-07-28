from __future__ import annotations

import subprocess

import pytest
from specproof_doctor import checks
from specproof_doctor.checks import CheckStatus, DoctorConfig


def completed(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_parse_semver_valid_text_returns_tuple() -> None:
    result = checks.parse_semver("git version 2.53.0.windows.1")

    assert result == (2, 53, 0)


@pytest.mark.parametrize(
    ("version_text", "expected"),
    [
        ("git version 2.40.0", True),
        ("git version 2.39.9", False),
        ("not a version", False),
    ],
)
def test_is_git_supported_evaluates_minimum_version(version_text: str, expected: bool) -> None:
    result = checks.is_git_supported(version_text)

    assert result is expected


@pytest.mark.parametrize(
    ("version_text", "expected"),
    [
        ("Python 3.11.9", True),
        ("Python 3.12.1", False),
        ("Python 3.10.14", False),
    ],
)
def test_is_python_311_requires_pinned_minor(version_text: str, expected: bool) -> None:
    result = checks.is_python_311(version_text)

    assert result is expected


def test_is_dotnet_lts_accepts_dotnet_10_sdk() -> None:
    output = ".NET SDK:\n Version: 10.0.301\n"

    result = checks.is_dotnet_lts(output)

    assert result is True


@pytest.mark.parametrize(
    ("version_text", "expected"),
    [
        ("v24.13.0", True),
        ("v22.23.1", False),
        ("v26.5.0", False),
    ],
)
def test_is_node_lts_requires_node_24(version_text: str, expected: bool) -> None:
    result = checks.is_node_lts(version_text)

    assert result is expected


def test_command_check_missing_command_returns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)

    result = checks.command_check(
        "Missing",
        ["missing-tool", "--version"],
        lambda _: True,
        lambda _: "ok",
        "missing",
        runner=lambda _, __: completed(),
        timeout_seconds=1,
    )

    assert result.status == CheckStatus.FAIL


def test_command_check_valid_output_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda command: command)

    result = checks.command_check(
        "Tool",
        ["tool", "--version"],
        lambda output: output == "tool 1.0.0",
        lambda output: output,
        "invalid",
        runner=lambda _, __: completed("tool 1.0.0"),
        timeout_seconds=1,
    )

    assert result.status == CheckStatus.PASS and result.detail == "tool 1.0.0"


def test_command_check_invalid_output_returns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda command: command)

    result = checks.command_check(
        "Tool",
        ["tool", "--version"],
        lambda _: False,
        lambda _: "ok",
        "invalid",
        runner=lambda _, __: completed("unexpected"),
        timeout_seconds=1,
    )

    assert result.status == CheckStatus.FAIL and result.detail == "invalid"


@pytest.mark.parametrize(
    ("required", "expected"),
    [(False, CheckStatus.SKIP), (True, CheckStatus.FAIL)],
)
def test_optional_command_check_missing_respects_requirement(
    monkeypatch: pytest.MonkeyPatch,
    required: bool,
    expected: CheckStatus,
) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda _: None)

    result = checks.optional_command_check(
        "Optional",
        ["optional", "--version"],
        lambda _: True,
        lambda _: "ok",
        "not installed",
        runner=lambda _, __: completed(),
        timeout_seconds=1,
        required=required,
    )

    assert result.status == expected


def test_optional_command_check_valid_output_returns_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda command: command)

    result = checks.optional_command_check(
        "Optional",
        ["optional", "--version"],
        lambda output: output == "optional 1.0.0",
        lambda output: output,
        "not installed",
        runner=lambda _, __: completed("optional 1.0.0"),
        timeout_seconds=1,
        required=False,
    )

    assert result.status == CheckStatus.PASS


@pytest.mark.parametrize(
    ("version_text", "expected"),
    [("v24.13.0", 24), ("invalid", None)],
)
def test_parse_major_handles_valid_and_invalid_versions(
    version_text: str,
    expected: int | None,
) -> None:
    assert checks.parse_major(version_text) == expected


def test_run_checks_uses_injected_probe_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.platform, "system", lambda: "Windows")
    monkeypatch.setattr(checks.platform, "release", lambda: "11")
    monkeypatch.setattr(checks.platform, "version", lambda: "10.0.26100")
    monkeypatch.setattr(checks.platform, "machine", lambda: "AMD64")
    monkeypatch.setattr(checks.shutil, "which", lambda command: command)

    command_outputs = {
        "git --version": completed("git version 2.53.0.windows.1\n"),
        "git lfs version": completed("git-lfs/3.7.1\n"),
        f"{checks.sys.executable} --version": completed("Python 3.11.9\n"),
        "uv --version": completed("uv 0.8.3\n"),
        "dotnet --info": completed(".NET SDK:\n Version: 10.0.301\n"),
        "node --version": completed("v24.13.0\n"),
        "pnpm --version": completed("10.33.0\n"),
        "docker info": completed("Server Version: 29.1.3\n"),
        "docker compose ps --format json": completed('[{"Name":"specproof-postgres"}]\n'),
        "nvidia-smi": completed("", "", 1),
    }

    def runner(command: checks.Sequence[str], _: float) -> subprocess.CompletedProcess[str]:
        return command_outputs[" ".join(command)]

    results = checks.run_checks(
        DoctorConfig(),
        runner=runner,
        tcp_connector=lambda _host, _port, _timeout: True,
        http_getter=lambda _url, _timeout: 200,
        import_finder=lambda module_name: module_name != "pyrealsense2",
        postgres_probe=lambda _timeout: True,
        redis_probe=lambda _timeout: True,
        rabbitmq_probe=lambda _timeout: True,
    )

    assert checks.has_required_failures(results) is False


def test_required_realsense_missing_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.shutil, "which", lambda command: command)

    result = checks.import_check(
        "RealSense Python",
        "pyrealsense2",
        lambda _: False,
        required=True,
        missing_detail="missing",
    )

    assert result.status == CheckStatus.FAIL


def test_check_os_windows_10_build_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(checks.platform, "system", lambda: "Windows")
    monkeypatch.setattr(checks.platform, "release", lambda: "10")
    monkeypatch.setattr(checks.platform, "version", lambda: "10.0.19045")
    monkeypatch.setattr(checks.platform, "machine", lambda: "AMD64")

    result = checks.check_os()

    assert result.status == CheckStatus.FAIL


def test_protocol_service_check_calls_probe_once() -> None:
    calls = 0

    def probe(_: float) -> bool:
        nonlocal calls
        calls += 1
        return True

    result = checks.protocol_service_check("Service", probe, 1.0, "ok", "failed")

    assert result.status == CheckStatus.PASS and calls == 1


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ('[{"Name":"specproof-postgres"}]', True),
        ("[]", False),
        ("specproof-postgres", True),
    ],
)
def test_compose_service_detection_handles_json_and_text(
    output: str,
    expected: bool,
) -> None:
    assert checks._compose_has_services(output) is expected
