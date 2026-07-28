"""Station identity and credential storage abstractions."""

from __future__ import annotations

import ctypes
import platform
from ctypes import wintypes
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel


class StationIdentity(BaseModel):
    """Platform-issued station identity."""

    station_id: str
    credential: str


class CredentialStore(Protocol):
    """Protected credential persistence."""

    def save(self, identity: StationIdentity) -> None:
        """Persist a station identity."""

    def load(self) -> StationIdentity | None:
        """Load a station identity when present."""


class InMemoryCredentialStore:
    """Credential store for automated tests."""

    def __init__(self) -> None:
        self._identity: StationIdentity | None = None

    def save(self, identity: StationIdentity) -> None:
        """Persist in memory."""

        self._identity = identity.model_copy()

    def load(self) -> StationIdentity | None:
        """Return a copy of the identity."""

        return self._identity.model_copy() if self._identity is not None else None


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("size", wintypes.DWORD),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class WindowsDpapiCredentialStore:
    """Current-user DPAPI-backed station credential store."""

    def __init__(self, path: Path) -> None:
        if platform.system() != "Windows":
            raise OSError("Windows DPAPI is only available on Windows")
        self._path = path
        self._crypt32 = ctypes.windll.crypt32
        self._kernel32 = ctypes.windll.kernel32

    def save(self, identity: StationIdentity) -> None:
        """Encrypt and atomically persist identity data."""

        plaintext = identity.model_dump_json().encode("utf-8")
        input_buffer = ctypes.create_string_buffer(plaintext)
        input_blob = _DataBlob(
            len(plaintext),
            ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte)),
        )
        output_blob = _DataBlob()
        if not self._crypt32.CryptProtectData(
            ctypes.byref(input_blob),
            "SpecProof station identity",
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise ctypes.WinError()
        try:
            encrypted = ctypes.string_at(output_blob.data, output_blob.size)
        finally:
            self._kernel32.LocalFree(output_blob.data)

        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._path.with_suffix(f"{self._path.suffix}.tmp")
        temporary_path.write_bytes(encrypted)
        temporary_path.replace(self._path)

    def load(self) -> StationIdentity | None:
        """Decrypt the persisted identity."""

        if not self._path.exists():
            return None
        encrypted = self._path.read_bytes()
        input_buffer = ctypes.create_string_buffer(encrypted)
        input_blob = _DataBlob(
            len(encrypted),
            ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_ubyte)),
        )
        output_blob = _DataBlob()
        if not self._crypt32.CryptUnprotectData(
            ctypes.byref(input_blob),
            None,
            None,
            None,
            None,
            0,
            ctypes.byref(output_blob),
        ):
            raise ctypes.WinError()
        try:
            plaintext = ctypes.string_at(output_blob.data, output_blob.size)
        finally:
            self._kernel32.LocalFree(output_blob.data)
        return StationIdentity.model_validate_json(plaintext)
