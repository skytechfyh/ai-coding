"""config.py 单元测试"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from pg_mcp.config import AppConfig, DatabaseConfig, OpenAIConfig, ServerConfig


def make_db(**kwargs) -> DatabaseConfig:
    defaults = dict(alias="main", host="localhost", port=5432, dbname="mydb", user="admin", password="secret")
    defaults.update(kwargs)
    return DatabaseConfig(**defaults)


# ── DatabaseConfig.dsn ───────────────────────────────────────────────────────

def test_database_config_dsn_basic() -> None:
    db = make_db()
    assert db.dsn == "postgresql://admin:secret@localhost:5432/mydb"


def test_database_config_dsn_password_special_chars() -> None:
    db = make_db(password="p@ss/w?rd&more")
    assert "p%40ss%2Fw%3Frd%26more" in db.dsn
    assert "@" not in db.dsn.split("@")[0].split(":")[-1]  # encoded in password part


def test_database_config_dsn_username_special_chars() -> None:
    db = make_db(user="admin@corp")
    assert "admin%40corp" in db.dsn


def test_database_config_password_not_in_repr() -> None:
    db = make_db(password="supersecret")
    r = repr(db)
    assert "supersecret" not in r
    assert "**" in r


def test_database_config_default_schemas() -> None:
    db = make_db()
    assert db.schemas == ["public"]


def test_database_config_multiple_schemas() -> None:
    db = make_db(schemas=["public", "analytics"])
    assert db.schemas == ["public", "analytics"]


def test_database_config_pool_size_defaults() -> None:
    db = make_db()
    assert db.min_pool_size == 1
    assert db.max_pool_size == 5


# ── ServerConfig defaults ────────────────────────────────────────────────────

def test_server_config_defaults() -> None:
    cfg = ServerConfig()
    assert cfg.query_timeout_seconds == 30
    assert cfg.result_validation_sample_rows == 5
    assert cfg.max_result_rows == 1000
    assert cfg.auto_retry_on_invalid is False


# ── OpenAIConfig defaults ────────────────────────────────────────────────────

def test_openai_config_default_model() -> None:
    cfg = OpenAIConfig(api_key="sk-test")
    assert cfg.model == "gpt-4o-mini"


# ── AppConfig YAML loading ──────────────────────────────────────────────���────

def _make_app_config_from_yaml(yaml_path: str) -> AppConfig:
    """Helper: create AppConfig with a custom yaml_file path via model_config override."""
    from pydantic_settings import YamlConfigSettingsSource

    class _TempConfig(AppConfig):
        model_config = AppConfig.model_config.copy()

        @classmethod
        def settings_customise_sources(cls, settings_cls, **kwargs):
            return (YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path),)

    return _TempConfig()


def test_app_config_from_yaml(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "databases:\n"
        "  - alias: main\n"
        "    dbname: mydb\n"
        "    user: admin\n"
        "    password: secret\n"
        "openai:\n"
        "  api_key: sk-test\n"
    )
    cfg = _make_app_config_from_yaml(str(config_file))
    assert cfg.databases[0].alias == "main"
    assert cfg.openai.model == "gpt-4o-mini"


def test_app_config_env_override(tmp_path, monkeypatch) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "databases:\n"
        "  - alias: main\n"
        "    dbname: mydb\n"
        "    user: admin\n"
        "    password: secret\n"
        "openai:\n"
        "  api_key: yaml-key\n"
    )
    monkeypatch.setenv("OPENAI__API_KEY", "env-key")

    from pydantic_settings import EnvSettingsSource, YamlConfigSettingsSource

    class _TempConfig(AppConfig):
        @classmethod
        def settings_customise_sources(cls, settings_cls, **kwargs):
            return (
                EnvSettingsSource(settings_cls),
                YamlConfigSettingsSource(settings_cls, yaml_file=str(config_file)),
            )

    cfg = _TempConfig()
    assert cfg.openai.api_key.get_secret_value() == "env-key"


def test_app_config_missing_required_fields(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("openai:\n  api_key: sk-test\n")
    with pytest.raises(ValidationError):
        _make_app_config_from_yaml(str(config_file))


# ── Edge cases ───────────────────────────────────────────────────────────────

def test_database_config_empty_schemas() -> None:
    db = make_db(schemas=[])
    assert db.schemas == []


def test_database_config_long_password() -> None:
    long_pwd = "x" * 512
    db = make_db(password=long_pwd)
    assert "x" * 512 in db.dsn or "x" * 10 in db.dsn  # encoded but present


def test_app_config_missing_yaml(tmp_path) -> None:
    """不存在的 yaml 文件缺少必填字段会 ValidationError"""
    missing = str(tmp_path / "nonexistent.yaml")
    with pytest.raises((ValidationError, Exception)):
        _make_app_config_from_yaml(missing)
