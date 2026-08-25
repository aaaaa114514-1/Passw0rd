"""Encrypted local storage and session management for P@ssw0rd."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

APP_NAME = "P@ssw0rd"
PBKDF2_ITERATIONS = 600_000
CONFIG_NAME = "vault_config.json"
DATABASE_NAME = "vault.db"


class VaultError(Exception):
    """Base vault error."""


class InvalidPasswordError(VaultError):
    """Raised when master password verification fails."""


class ValidationError(VaultError):
    """Raised for invalid user-provided entry data."""


@dataclass(slots=True)
class VaultEntry:
    id: str
    title: str
    username: str = ""
    phone: str = ""
    email: str = ""
    url: str = ""
    password: str = ""
    category: str = ""
    tags: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


class CryptoBox:
    """AES-GCM helpers. Every payload receives an independent random nonce."""

    def __init__(self, key: bytes) -> None:
        self._aes = AESGCM(key)

    def encrypt(self, value: str) -> bytes:
        nonce = os.urandom(12)
        encrypted = self._aes.encrypt(nonce, value.encode("utf-8"), None)
        return nonce + encrypted

    def decrypt(self, value: bytes) -> str:
        return self._aes.decrypt(value[:12], value[12:], None).decode("utf-8")


def application_data_directory() -> Path:
    root = os.environ.get("LOCALAPPDATA")
    if root:
        return Path(root) / APP_NAME
    return Path.home() / "AppData" / "Local" / APP_NAME


def _derive_keys(password: str, salt: bytes, iterations: int) -> tuple[bytes, bytes]:
    material = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, 64)
    return material[:32], material[32:]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class VaultService:
    """Owns the encrypted SQLite file and the key for the current unlocked session."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or application_data_directory()
        self.config_path = self.data_dir / CONFIG_NAME
        self.database_path = self.data_dir / DATABASE_NAME
        self._box: CryptoBox | None = None
        self._connection: sqlite3.Connection | None = None

    @property
    def is_initialized(self) -> bool:
        return self.config_path.exists() and self.database_path.exists()

    @property
    def is_unlocked(self) -> bool:
        return self._connection is not None and self._box is not None

    def initialize(self, password: str) -> None:
        if not password:
            raise ValidationError("Master password cannot be empty.")
        if self.is_initialized:
            raise VaultError("Vault is already initialized.")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        salt = os.urandom(32)
        encryption_key, verifier_key = _derive_keys(password, salt, PBKDF2_ITERATIONS)
        config = {
            "version": 1,
            "salt": base64.b64encode(salt).decode("ascii"),
            "iterations": PBKDF2_ITERATIONS,
            "verifier": base64.b64encode(hmac.new(verifier_key, b"P@ssw0rd verifier v1", hashlib.sha256).digest()).decode("ascii"),
        }
        self.config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        self._open(encryption_key)
        self._create_schema()

    def unlock(self, password: str) -> None:
        if not self.is_initialized:
            raise VaultError("Vault has not been initialized.")
        if not password:
            raise InvalidPasswordError("Enter the master password.")
        config = self._read_config()
        salt = base64.b64decode(config["salt"])
        encryption_key, verifier_key = _derive_keys(password, salt, int(config["iterations"]))
        expected = base64.b64decode(config["verifier"])
        actual = hmac.new(verifier_key, b"P@ssw0rd verifier v1", hashlib.sha256).digest()
        if not hmac.compare_digest(expected, actual):
            raise InvalidPasswordError("Incorrect master password.")
        self._open(encryption_key)
        self._create_schema()

    def lock(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._connection = None
        self._box = None

    def change_master_password(self, current_password: str, new_password: str) -> None:
        if not new_password:
            raise ValidationError("New master password cannot be empty.")
        self._ensure_unlocked()
        self.lock()
        self.unlock(current_password)
        entries = self.list_entries()
        salt = os.urandom(32)
        encryption_key, verifier_key = _derive_keys(new_password, salt, PBKDF2_ITERATIONS)
        config = {
            "version": 1,
            "salt": base64.b64encode(salt).decode("ascii"),
            "iterations": PBKDF2_ITERATIONS,
            "verifier": base64.b64encode(hmac.new(verifier_key, b"P@ssw0rd verifier v1", hashlib.sha256).digest()).decode("ascii"),
        }
        temporary_path = self.config_path.with_suffix(".new")
        temporary_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        self._connection.execute("BEGIN")
        try:
            old_box = self._box
            self._box = CryptoBox(encryption_key)
            for entry in entries:
                self._write_entry(entry)
            self._connection.commit()
            temporary_path.replace(self.config_path)
        except Exception:
            self._connection.rollback()
            self._box = old_box
            temporary_path.unlink(missing_ok=True)
            raise

    def list_entries(self, query: str = "") -> list[VaultEntry]:
        self._ensure_unlocked()
        rows = self._connection.execute("SELECT id, payload FROM entries ORDER BY updated_at DESC").fetchall()
        normalized = query.casefold().strip()
        entries = [self._decrypt_entry(row[0], row[1]) for row in rows]
        if not normalized:
            return entries
        return [entry for entry in entries if normalized in " ".join(asdict(entry).values()).casefold()]

    def categories(self) -> list[str]:
        return sorted({entry.category.strip() for entry in self.list_entries() if entry.category.strip()}, key=str.casefold)

    def get_entry(self, entry_id: str) -> VaultEntry | None:
        self._ensure_unlocked()
        row = self._connection.execute("SELECT id, payload FROM entries WHERE id = ?", (entry_id,)).fetchone()
        return self._decrypt_entry(row[0], row[1]) if row else None

    def save_entry(self, entry: VaultEntry) -> VaultEntry:
        self._ensure_unlocked()
        title = entry.title.strip()
        if not title:
            raise ValidationError("Entry name cannot be empty.")
        now = _now()
        entry.title = title
        entry.id = entry.id or str(uuid4())
        entry.created_at = entry.created_at or now
        entry.updated_at = now
        self._write_entry(entry)
        self._connection.commit()
        return entry

    def delete_entry(self, entry_id: str) -> None:
        self._ensure_unlocked()
        self._connection.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        self._connection.commit()

    def _write_entry(self, entry: VaultEntry) -> None:
        payload = self._box.encrypt(json.dumps(asdict(entry), ensure_ascii=False))
        self._connection.execute(
            "INSERT INTO entries(id, payload, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at",
            (entry.id, payload, entry.updated_at),
        )

    def _decrypt_entry(self, entry_id: str, payload: bytes) -> VaultEntry:
        data = json.loads(self._box.decrypt(payload))
        data["id"] = entry_id
        return VaultEntry(**data)

    def _open(self, encryption_key: bytes) -> None:
        self.lock()
        self._box = CryptoBox(encryption_key)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.execute("PRAGMA foreign_keys = ON")

    def _create_schema(self) -> None:
        self._connection.execute(
            "CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, payload BLOB NOT NULL, updated_at TEXT NOT NULL)"
        )
        self._connection.commit()

    def _read_config(self) -> dict[str, object]:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise VaultError("Vault configuration is invalid.") from exc

    def _ensure_unlocked(self) -> None:
        if not self.is_unlocked:
            raise VaultError("Unlock the vault first.")
