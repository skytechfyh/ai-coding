"""集成测试：需要真实 PostgreSQL 连接（TEST_PG_DSN 环境变量）"""
import os
from urllib.parse import urlparse

import asyncpg
import pytest
from pydantic import SecretStr

# 标记为集成测试，默认不运行
pytestmark = pytest.mark.integration


async def test_pg_connection(pg_dsn: str) -> None:
    """基本连接测试"""
    conn = await asyncpg.connect(pg_dsn)
    try:
        result = await conn.fetchval("SELECT 1")
        assert result == 1
    finally:
        await conn.close()


async def test_execute_select_one(pg_pool) -> None:
    """执行简单查询"""
    from pg_mcp.db_executor import execute_query
    result = await execute_query(pg_pool, "SELECT 1 AS n", limit=10, timeout_seconds=5)
    assert result.columns == ["n"]
    assert result.rows == [[1]]
    assert result.row_count == 1
    assert result.execution_time_ms > 0


async def test_execute_readonly_enforced(pg_pool) -> None:
    """只读连接不允许写操作"""
    from pg_mcp.db_executor import execute_query
    with pytest.raises(Exception):  # asyncpg.exceptions.ReadOnlySQLTransactionError
        await execute_query(
            pg_pool,
            "CREATE TEMP TABLE _test_forbidden (id int)",
            limit=10,
            timeout_seconds=5,
        )


async def test_schema_load(pg_dsn: str) -> None:
    """Schema 加载测试"""
    from pg_mcp.config import DatabaseConfig
    from pg_mcp.schema_cache import load_schema

    parsed = urlparse(pg_dsn)
    db = DatabaseConfig(
        alias="test",
        host=parsed.hostname or "localhost",
        port=parsed.port or 5432,
        dbname=(parsed.path or "/test").lstrip("/"),
        user=parsed.username or "postgres",
        password=SecretStr(parsed.password or ""),
        schemas=["public"],
    )
    cache = await load_schema(db)
    assert cache.is_available, f"Schema load failed: {cache.error_message}"
    # information_schema 和 pg_catalog 不应出现
    for table_name in cache.tables:
        assert not table_name.startswith("information_schema.")
        assert not table_name.startswith("pg_catalog.")


async def test_schema_load_unavailable_db() -> None:
    """数据库不可达时应返回 is_available=False 而非抛出异常"""
    from pg_mcp.config import DatabaseConfig
    from pg_mcp.schema_cache import load_schema

    db = DatabaseConfig(
        alias="invalid",
        host="127.0.0.1",
        port=19999,  # 不存在的端口
        dbname="nonexistent",
        user="nobody",
        password=SecretStr("wrong"),
    )
    cache = await load_schema(db)
    assert cache.is_available is False
    assert cache.error_message is not None
