import json

import pytest

from vault import InvalidPasswordError, ValidationError, VaultEntry, VaultService


def test_initialize_unlock_and_entry_round_trip(tmp_path):
    vault = VaultService(tmp_path / "data")
    vault.initialize("master")
    saved = vault.save_entry(VaultEntry(id="", title="Example", username="alice", password="secret", email="a@example.com"))
    assert saved.id
    vault.lock()

    with pytest.raises(InvalidPasswordError):
        vault.unlock("wrong")

    vault.unlock("master")
    loaded = vault.get_entry(saved.id)
    assert loaded is not None
    assert loaded.password == "secret"
    assert loaded.email == "a@example.com"
    assert vault.list_entries("alice")[0].id == saved.id


def test_database_payload_does_not_expose_values(tmp_path):
    vault = VaultService(tmp_path / "data")
    vault.initialize("master")
    vault.save_entry(VaultEntry(id="", title="Private Account", password="not-visible-on-disk"))
    raw = vault.database_path.read_bytes()
    assert b"Private Account" not in raw
    assert b"not-visible-on-disk" not in raw


def test_change_master_password_reencrypts_entries(tmp_path):
    vault = VaultService(tmp_path / "data")
    vault.initialize("old")
    entry = vault.save_entry(VaultEntry(id="", title="Entry", password="keep-me"))
    vault.change_master_password("old", "new")
    vault.lock()
    with pytest.raises(InvalidPasswordError):
        vault.unlock("old")
    vault.unlock("new")
    assert vault.get_entry(entry.id).password == "keep-me"


def test_empty_master_and_empty_title_are_rejected(tmp_path):
    vault = VaultService(tmp_path / "data")
    with pytest.raises(ValidationError):
        vault.initialize("")
    vault.initialize("x")
    with pytest.raises(ValidationError):
        vault.save_entry(VaultEntry(id="", title=""))
