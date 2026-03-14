"""server.py 单元测试 — _resolve_cache 和四个 MCP tool"""
from __future__ import annotations

from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pg_mcp.server as server_module
from pg_mcp.config import AppConfig, DatabaseConfig, OpenAIConfig, ServerConfig
from pg_mcp.models import (
    ColumnInfo,
    DatabaseSchemaCache,
    ForeignKeyInfo,
    TableSchema,
    ValidationInfo,
)
from pg_mcp.server import (
    _DatabaseAmbiguousError,
    _DatabaseNotFoundError,
    _DatabaseUnavailableError,
    _resolve_cache,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_table(name: str = "users") -> TableSchema:
    return TableSchema(
        schema_name="public",
        table_name=name,
        full_name=f"public.{name}",
        object_type="table",
        columns=[ColumnInfo(name="id", data_type="int4", is_nullable=False)],
        indexes=[],
        foreign_keys=[],
    )


def make_cache(alias: str, available: bool = True) -> DatabaseSchemaCache:
    return DatabaseSchemaCache(
        alias=alias,
        host="localhost",
        dbname="testdb",
        tables={"public.users": make_table()} if available else {},
        custom_types=[],
        cached_at=datetime.now(UTC),
        is_available=available,
        error_message=None if available else "connection refused",
    )


def make_app_config() -> AppConfig:
    return AppConfig.model_construct(
        databases=[
            DatabaseConfig(alias="main", dbname="testdb", user="admin", password="secret"),
        ],
        openai=OpenAIConfig(api_key="sk-test"),
        server=ServerConfig(),
    )


@pytest.fixture(autouse=True)
def reset_server_state():
    """每个测试前后重置 server 全局状态"""
    orig_caches = server_module._caches.copy()
    orig_pools = server_module._pools.copy()
    orig_openai = server_module._openai
    orig_config = server_module._config
    yield
    server_module._caches = orig_caches
    server_module._pools = orig_pools
    server_module._openai = orig_openai
    server_module._config = orig_config


# ── _resolve_cache ────────────────────────────────────────────────────────────

def test_resolve_cache_found() -> None:
    server_module._caches = {"main": make_cache("main")}
    cache = _resolve_cache("main")
    assert cache.alias == "main"


def test_resolve_cache_not_found() -> None:
    server_module._caches = {"main": make_cache("main")}
    with pytest.raises(_DatabaseNotFoundError):
        _resolve_cache("unknown")


def test_resolve_cache_unavailable() -> None:
    server_module._caches = {"broken": make_cache("broken", available=False)}
    with pytest.raises(_DatabaseUnavailableError):
        _resolve_cache("broken")


def test_resolve_cache_single_available() -> None:
    server_module._caches = {"main": make_cache("main")}
    cache = _resolve_cache(None)
    assert cache.alias == "main"


def test_resolve_cache_ambiguous() -> None:
    server_module._caches = {
        "db1": make_cache("db1"),
        "db2": make_cache("db2"),
    }
    with pytest.raises(_DatabaseAmbiguousError):
        _resolve_cache(None)


def test_resolve_cache_no_available() -> None:
    server_module._caches = {"broken": make_cache("broken", available=False)}
    with pytest.raises(_DatabaseUnavailableError):
        _resolve_cache(None)


# ── mock_server_deps fixture ──────────────────────────────────────────────────

@pytest.fixture
def mock_server_deps():
    cache = make_cache("main")
    mock_openai = AsyncMock()
    mock_pool = AsyncMock()

    server_module._caches = {"main": cache}
    server_module._pools = {"main": mock_pool}
    server_module._openai = mock_openai
    server_module._config = make_app_config()

    return {"cache": cache, "openai": mock_openai, "pool": mock_pool}


# ── query_to_sql ──────────────────────────────────────────────────────────────

async def test_query_to_sql_success(mock_server_deps) -> None:
    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="SELECT * FROM users")):
        result = await server_module.query_to_sql("show all users", database="main")
    assert "sql" in result
    assert result["sql"] == "SELECT * FROM users LIMIT 1000"
    assert "schemaUsed" in result


async def test_query_to_sql_database_not_found(mock_server_deps) -> None:
    result = await server_module.query_to_sql("show users", database="nonexistent")
    assert result["errorCode"] == "DATABASE_NOT_FOUND"


async def test_query_to_sql_database_ambiguous(mock_server_deps) -> None:
    server_module._caches["secondary"] = make_cache("secondary")
    result = await server_module.query_to_sql("show users")
    assert result["errorCode"] == "DATABASE_AMBIGUOUS"


async def test_query_to_sql_llm_error(mock_server_deps) -> None:
    with patch("pg_mcp.server.generate_sql", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
        result = await server_module.query_to_sql("show users", database="main")
    assert result["errorCode"] == "LLM_ERROR"


async def test_query_to_sql_validation_failed(mock_server_deps) -> None:
    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="DELETE FROM users")):
        result = await server_module.query_to_sql("delete users", database="main")
    assert result["errorCode"] == "VALIDATION_FAILED"


# ── query_to_result ───────────────────────────────────────────────────────────

async def test_query_to_result_success(mock_server_deps) -> None:
    from pg_mcp.models import ExecutionResult

    exec_result = ExecutionResult(
        columns=["id", "name"], rows=[[1, "alice"]], row_count=1, execution_time_ms=5.0
    )
    validation = ValidationInfo(is_meaningful=True, explanation="ok", validation_skipped=False)

    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="SELECT * FROM users")), \
         patch("pg_mcp.server.execute_query", new=AsyncMock(return_value=exec_result)), \
         patch("pg_mcp.server.validate_result", new=AsyncMock(return_value=validation)):
        result = await server_module.query_to_result("show users", database="main")

    assert "sql" in result
    assert result["rowCount"] == 1
    assert "columns" in result


async def test_query_to_result_db_timeout(mock_server_deps) -> None:
    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="SELECT * FROM users")), \
         patch("pg_mcp.server.execute_query", new=AsyncMock(side_effect=TimeoutError("timed out"))):
        result = await server_module.query_to_result("show users", database="main")
    assert result["errorCode"] == "DB_ERROR"
    assert "timed out" in result["message"]


async def test_query_to_result_db_error(mock_server_deps) -> None:
    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="SELECT * FROM users")), \
         patch("pg_mcp.server.execute_query", new=AsyncMock(side_effect=RuntimeError("pg error"))):
        result = await server_module.query_to_result("show users", database="main")
    assert result["errorCode"] == "DB_ERROR"


async def test_query_to_result_limit_clamped(mock_server_deps) -> None:
    from pg_mcp.models import ExecutionResult

    exec_result = ExecutionResult(columns=["id"], rows=[[1]], row_count=1, execution_time_ms=1.0)
    validation = ValidationInfo(is_meaningful=True, explanation="ok", validation_skipped=False)

    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="SELECT * FROM users")), \
         patch("pg_mcp.server.execute_query", new=AsyncMock(return_value=exec_result)) as mock_exec, \
         patch("pg_mcp.server.validate_result", new=AsyncMock(return_value=validation)):
        await server_module.query_to_result("show users", database="main", limit=9999)
        _, kwargs = mock_exec.call_args
        assert kwargs.get("limit", mock_exec.call_args[0][2] if len(mock_exec.call_args[0]) > 2 else 9999) <= 1000


async def test_query_to_result_validation_skipped(mock_server_deps) -> None:
    from pg_mcp.models import ExecutionResult

    exec_result = ExecutionResult(columns=["id"], rows=[[1]], row_count=1, execution_time_ms=1.0)
    validation = ValidationInfo(is_meaningful=False, explanation="", validation_skipped=True)

    with patch("pg_mcp.server.generate_sql", new=AsyncMock(return_value="SELECT * FROM users")), \
         patch("pg_mcp.server.execute_query", new=AsyncMock(return_value=exec_result)), \
         patch("pg_mcp.server.validate_result", new=AsyncMock(return_value=validation)):
        result = await server_module.query_to_result("show users", database="main")

    assert result["validation"]["validationSkipped"] is True


# ── list_databases ────────────────────────────────────────────────────────────

async def test_list_databases_all(mock_server_deps) -> None:
    result = await server_module.list_databases()
    assert "databases" in result
    assert len(result["databases"]) == 1


async def test_list_databases_camelcase(mock_server_deps) -> None:
    result = await server_module.list_databases()
    db = result["databases"][0]
    assert "isAvailable" in db
    assert "tableCount" in db
    assert "is_available" not in db


async def test_list_databases_includes_unavailable(mock_server_deps) -> None:
    server_module._caches["broken"] = make_cache("broken", available=False)
    result = await server_module.list_databases()
    aliases = [d["alias"] for d in result["databases"]]
    assert "broken" in aliases
    broken = next(d for d in result["databases"] if d["alias"] == "broken")
    assert broken["isAvailable"] is False
    assert broken.get("schemaCachedAt") is None


# ── refresh_schema ────────────────────────────────────────────────────────────

async def test_refresh_schema_all(mock_server_deps) -> None:
    new_cache = make_cache("main")
    new_pool = AsyncMock()
    with patch("pg_mcp.server.load_schema", new=AsyncMock(return_value=new_cache)), \
         patch("pg_mcp.server.create_pool", new=AsyncMock(return_value=new_pool)):
        result = await server_module.refresh_schema()
    assert "refreshed" in result
    assert "main" in result["refreshed"]


async def test_refresh_schema_single_by_alias(mock_server_deps) -> None:
    server_module._caches["secondary"] = make_cache("secondary")
    server_module._config = AppConfig.model_construct(
        databases=[
            DatabaseConfig(alias="main", dbname="testdb", user="admin", password="secret"),
            DatabaseConfig(alias="secondary", dbname="testdb2", user="admin", password="secret"),
        ],
        openai=OpenAIConfig(api_key="sk-test"),
        server=ServerConfig(),
    )
    load_calls = []

    async def mock_load(db):
        load_calls.append(db.alias)
        return make_cache(db.alias)

    with patch("pg_mcp.server.load_schema", new=mock_load), \
         patch("pg_mcp.server.create_pool", new=AsyncMock(return_value=AsyncMock())):
        result = await server_module.refresh_schema(database="main")

    assert load_calls == ["main"]
    assert "main" in result["refreshed"]


async def test_refresh_schema_not_found(mock_server_deps) -> None:
    result = await server_module.refresh_schema(database="nonexistent")
    assert result["errorCode"] == "DATABASE_NOT_FOUND"


async def test_refresh_schema_duration(mock_server_deps) -> None:
    new_cache = make_cache("main")
    with patch("pg_mcp.server.load_schema", new=AsyncMock(return_value=new_cache)), \
         patch("pg_mcp.server.create_pool", new=AsyncMock(return_value=AsyncMock())):
        result = await server_module.refresh_schema()
    assert "durationSeconds" in result
    assert isinstance(result["durationSeconds"], float)
