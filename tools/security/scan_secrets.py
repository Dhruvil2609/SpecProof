"""Scan tracked source files for private keys and credential-shaped values."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = {
    ".cs",
    ".css",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".ts",
    ".tsx",
    ".xml",
    ".yaml",
    ".yml",
}
FORBIDDEN_KEY_SUFFIXES = {".key", ".p12", ".pfx"}
ALLOWED_VALUE_MARKERS = (
    "admin@123",
    "change-before-production",
    "development",
    "example",
    "placeholder",
    "replace-at-deployment",
    "specproof_dev_password",
    "unit-test",
)
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
TOKEN_PATTERNS = (
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
)
ASSIGNMENT_PATTERN = re.compile(
    r"(?i)(?:password|passwd|secret|token|api[_-]?key|private[_-]?key)"
    r"[\"']?\s*(?::|=)\s*[\"']([^\"'\s]{16,})[\"']"
)


@dataclass(frozen=True)
class SecretFinding:
    """One credential-shaped value discovered in source."""

    path: Path
    line: int
    kind: str


def scan_paths(paths: Iterable[Path], repository_root: Path) -> tuple[SecretFinding, ...]:
    """Return secret findings from the supplied repository-relative paths."""

    findings: list[SecretFinding] = []
    for relative_path in paths:
        path = repository_root / relative_path
        if relative_path.suffix.lower() in FORBIDDEN_KEY_SUFFIXES:
            findings.append(SecretFinding(relative_path, 1, "private_key_file"))
            continue
        if not path.is_file() or not _is_text_path(relative_path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if PRIVATE_KEY_PATTERN.search(line):
                findings.append(SecretFinding(relative_path, line_number, "private_key"))
            for kind, pattern in TOKEN_PATTERNS:
                if pattern.search(line):
                    findings.append(SecretFinding(relative_path, line_number, kind))
            for match in ASSIGNMENT_PATTERN.finditer(line):
                value = match.group(1).lower()
                if not any(marker in value for marker in ALLOWED_VALUE_MARKERS):
                    findings.append(SecretFinding(relative_path, line_number, "assigned_secret"))
    return tuple(findings)


def tracked_paths(repository_root: Path) -> tuple[Path, ...]:
    """List Git-tracked files without inspecting ignored build output."""

    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository_root,
        check=True,
        capture_output=True,
    )
    return tuple(
        Path(value.decode("utf-8"))
        for value in completed.stdout.split(b"\0")
        if value
    )


def _is_text_path(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES or path.name.startswith(".env")


def main(arguments: Sequence[str] | None = None) -> int:
    """Scan tracked files and return a failing exit code when findings exist."""

    parser = argparse.ArgumentParser(prog="scan-secrets")
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parsed = parser.parse_args(arguments)
    repository_root = parsed.repository_root.resolve()
    findings = scan_paths(tracked_paths(repository_root), repository_root)
    for finding in findings:
        print(f"{finding.path.as_posix()}:{finding.line}: {finding.kind}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
