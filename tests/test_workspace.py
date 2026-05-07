"""Tests for workspace configuration and invite key cryptography."""

import json

import pytest
from engram.workspace import (
    GlobalConfig,
    WorkspaceConfig,
    read_global_config,
    set_global_config_setting,
    write_global_config,
    generate_invite_key,
    decode_invite_key,
    generate_team_id,
)


def test_workspace_config_with_schema():
    """Test that WorkspaceConfig includes schema field."""
    config = WorkspaceConfig(
        engram_id="ENG-TEST-1234",
        db_url="postgres://localhost/test",
        schema="custom_schema",
    )
    assert config.schema == "custom_schema"


def test_workspace_config_default_schema():
    """Test that schema defaults to 'engram'."""
    config = WorkspaceConfig(
        engram_id="ENG-TEST-1234",
        db_url="postgres://localhost/test",
    )
    assert config.schema == "engram"


def test_generate_team_id():
    """Test team ID generation format."""
    team_id = generate_team_id()
    assert team_id.startswith("ENG-")
    parts = team_id.split("-")
    assert len(parts) == 3
    assert len(parts[1]) == 4
    assert len(parts[2]) == 4


def test_invite_key_roundtrip():
    """Test invite key generation and decoding."""
    db_url = "postgres://user:pass@host:5432/db"
    engram_id = "ENG-TEST-1234"
    schema = "test_schema"

    invite_key, key_hash = generate_invite_key(
        db_url=db_url,
        engram_id=engram_id,
        expires_days=90,
        uses_remaining=10,
        schema=schema,
    )

    # Verify format
    assert invite_key.startswith("ek_live_")
    assert len(key_hash) == 64  # SHA256 hex

    # Decode and verify
    payload = decode_invite_key(invite_key)
    assert payload["db_url"] == db_url
    assert payload["engram_id"] == engram_id
    assert payload["schema"] == schema
    assert payload["uses_remaining"] == 10


def test_invite_key_backward_compatibility():
    """Test that old invite keys without schema still work."""
    # Generate a key with schema
    invite_key, _ = generate_invite_key(
        db_url="postgres://localhost/test",
        engram_id="ENG-TEST-1234",
        schema="engram",
    )

    # Decode should include schema
    payload = decode_invite_key(invite_key)
    assert "schema" in payload
    assert payload["schema"] == "engram"


def test_invite_key_invalid_format():
    """Test that invalid invite keys raise ValueError."""
    with pytest.raises(ValueError, match="Invalid invite key format"):
        decode_invite_key("invalid_key")

    with pytest.raises(ValueError, match="Invalid invite key format"):
        decode_invite_key("ek_test_invalid")


def test_invite_key_tampered():
    """Test that tampered invite keys are rejected."""
    invite_key, _ = generate_invite_key(
        db_url="postgres://localhost/test",
        engram_id="ENG-TEST-1234",
    )

    # Tamper with the key
    tampered = invite_key[:-10] + "XXXXXXXXXX"

    with pytest.raises(ValueError, match="authentication failed|encoding"):
        decode_invite_key(tampered)


def test_workspace_config_serialization():
    """Test that WorkspaceConfig can be serialized to dict."""
    from dataclasses import asdict

    config = WorkspaceConfig(
        engram_id="ENG-TEST-1234",
        db_url="postgres://localhost/test",
        schema="custom",
        anonymous_mode=True,
        anon_agents=False,
    )

    data = asdict(config)
    assert data["engram_id"] == "ENG-TEST-1234"
    assert data["schema"] == "custom"
    assert data["anonymous_mode"] is True
    assert data["anon_agents"] is False

    # Verify it can be reconstructed
    config2 = WorkspaceConfig(**data)
    assert config2.schema == "custom"


def test_global_config_defaults_to_auto_init_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr("engram.workspace.GLOBAL_CONFIG_PATH", tmp_path / "config.json")

    config = read_global_config()

    assert config.auto_initialize_new_repos is False


def test_global_config_roundtrip(monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("engram.workspace.GLOBAL_CONFIG_PATH", config_path)

    write_global_config(GlobalConfig(auto_initialize_new_repos=True))

    assert read_global_config().auto_initialize_new_repos is True
    assert json.loads(config_path.read_text()) == {"auto_initialize_new_repos": True}


def test_set_global_config_setting_updates_auto_init(monkeypatch, tmp_path):
    monkeypatch.setattr("engram.workspace.GLOBAL_CONFIG_PATH", tmp_path / "config.json")

    config = set_global_config_setting("auto_initialize_new_repos", "true")

    assert config.auto_initialize_new_repos is True
