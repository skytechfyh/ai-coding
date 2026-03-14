from __future__ import annotations

import argparse
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

import openai
from mcp.server.fastmcp import FastMCP
from openai import AsyncOpenAI

from pg_mcp.config import AppConfig, DatabaseConfig
from pg_mcp.db_executor import create_pool, execute_query
from pg_mcp.models import (
    DatabaseInfo,
    DatabaseSchemaCache,
    ListDatabasesOutput,
    QueryToResultOutput,
    QueryToSqlOutput,
    RefreshSchemaOutput,
    ValidationInfo,
)
from pg_mcp.nl2sql import build_schema_text, generate_sql
from pg_mcp.result_validator import validate_result
from pg_mcp.schema_cache import load_schema
from pg_mcp.sql_validator import validate_sql

logger = logging.getLogger(__name__)

# ── 全局状态（在 lifespan 中初始化）─────────────────────────────────────────

_caches: dict[str, DatabaseSchemaCache] = {}
_pools: dict[str, Any] = {}
_openai: AsyncOpenAI | None = None
_config: AppConfig | None = None

mcp = FastMCP("pg-mcp")


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastMCP):
    global _caches, _pools, _openai, _config

    # _config 在 main() 中通过 mcp.run() 前已初始化
    assert _config is not None, "AppConfig must be initialized before lifespan"

    # 初始化 OpenAI 客户端
    _openai = AsyncOpenAI(
        api_key=_config.openai.api_key.get_secret_value(),
    )

    # 并发加载所有 DB 的 Schema 和连接池
    async def init_db(db: DatabaseConfig) -> None:
        logger.info("Loading schema for database: %s", db.alias)
        cache = await load_schema(db)
        _caches[db.alias] = cache
        if cache.is_available:
            try:
                pool = await create_pool(db)
                _pools[db.alias] = pool
                logger.info(
                    "Database %s ready: %d tables", db.alias, cache.table_count
                )
            except Exception as e:
                logger.error("Failed to create pool for %s: %s", db.alias, e)
                _caches[db.alias] = cache.model_copy(
                    update={"is_available": False, "error_message": str(e)}
                )
        else:
            logger.warning(
                "Database %s unavailable: %s", db.alias, cache.error_message
            )

    await asyncio.gather(*[init_db(db) for db in _config.databases])

    yield

    # Graceful shutdown: 关闭所有连接池
    for alias, pool in _pools.items():
        logger.info("Closing pool for %s", alias)
        await pool.close()
    _pools.clear()
    logger.info("pg-mcp shutdown complete")


mcp = FastMCP("pg-mcp", lifespan=lifespan)


# ── 内部帮助函数 ──────────────────────────────────────────────────────────────

class _DatabaseNotFoundError(Exception):
    """指定的 database alias 不存在"""


class _DatabaseAmbiguousError(Exception):
    """多个数据库可用，需要明确指定"""


class _DatabaseUnavailableError(Exception):
    """指定的数据库不可用（连接失败）"""


def _resolve_cache(database: str | None) -> DatabaseSchemaCache:
    """根据 alias 解析对应的 DatabaseSchemaCache。"""
    if database is not None:
        cache = _caches.get(database)
        if cache is None:
            available = list(_caches.keys())
            raise _DatabaseNotFoundError(
                f"Database '{database}' not found. Available: {available}"
            )
        if not cache.is_available:
            raise _DatabaseUnavailableError(
                f"Database '{database}' is unavailable: {cache.error_message}"
            )
        return cache

    available = [c for c in _caches.values() if c.is_available]
    if not available:
        raise _DatabaseUnavailableError("No available databases")
    if len(available) == 1:
        return available[0]
    # P1修复: 多个可用库时要求明确指定，不再静默选第一个
    names = [c.alias for c in available]
    raise _DatabaseAmbiguousError(
        f"Multiple databases available ({names}). Please specify the 'database' parameter."
    )


def _get_pool(alias: str) -> Any:
    pool = _pools.get(alias)
    if pool is None:
        raise _DatabaseUnavailableError(f"No connection pool for database '{alias}'")
    return pool


# ── MCP Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def query_to_sql(query: str, database: str | None = None) -> dict[str, Any]:
    """将自然语言查询转换为 PostgreSQL SELECT 语句。

    Args:
        query: 自然语言查询描述，例如：'查询过去30天内注册的用户数量'
        database: 目标数据库别名（在配置文件中定义）。配置了多个数据库时必须指定。
    """
    # 解析 cache
    try:
        cache = _resolve_cache(database)
    except _DatabaseNotFoundError as e:
        return {"errorCode": "DATABASE_NOT_FOUND", "message": str(e)}
    except _DatabaseAmbiguousError as e:
        return {"errorCode": "DATABASE_AMBIGUOUS", "message": str(e)}
    except _DatabaseUnavailableError as e:
        return {"errorCode": "NO_DATABASE_AVAILABLE", "message": str(e)}

    # 生成 SQL
    try:
        assert _openai is not None
        assert _config is not None
        relevant_tables = cache.get_relevant_tables(query, max_tables=20)
        schema_text = build_schema_text(relevant_tables)
        sql = await generate_sql(_openai, _config.openai.model, query, schema_text)
    except Exception as e:
        return {"errorCode": "LLM_ERROR", "message": f"Failed to generate SQL: {e}"}

    # 验证 SQL
    assert _config is not None
    validated_sql, err = validate_sql(sql, _config.server.max_result_rows)
    if err:
        return {"errorCode": "VALIDATION_FAILED", "message": err, "details": sql}

    return QueryToSqlOutput(
        sql=validated_sql,
        database=cache.alias,
        schema_used=[t.full_name for t in relevant_tables],
    ).model_dump(by_alias=True)


@mcp.tool()
async def query_to_result(
    query: str,
    database: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """将自然语言查询转换为 SQL，执行查询并返回结果及语义验证。

    Args:
        query: 自然语言查询描述
        database: 目标数据库别名（可选）
        limit: 最大返回行数，默认 100，最大 1000
    """
    assert _config is not None
    limit = max(1, min(limit, 1000))

    # 解析 cache
    try:
        cache = _resolve_cache(database)
    except _DatabaseNotFoundError as e:
        return {"errorCode": "DATABASE_NOT_FOUND", "message": str(e)}
    except _DatabaseAmbiguousError as e:
        return {"errorCode": "DATABASE_AMBIGUOUS", "message": str(e)}
    except _DatabaseUnavailableError as e:
        return {"errorCode": "NO_DATABASE_AVAILABLE", "message": str(e)}

    # 生成 SQL
    try:
        assert _openai is not None
        relevant_tables = cache.get_relevant_tables(query, max_tables=20)
        schema_text = build_schema_text(relevant_tables)
        sql = await generate_sql(_openai, _config.openai.model, query, schema_text)
    except Exception as e:
        return {"errorCode": "LLM_ERROR", "message": f"Failed to generate SQL: {e}"}

    # 验证 SQL
    validated_sql, err = validate_sql(sql, _config.server.max_result_rows)
    if err:
        return {"errorCode": "VALIDATION_FAILED", "message": err, "details": sql}

    # 执行 SQL
    try:
        pool = _get_pool(cache.alias)
        result = await execute_query(
            pool,
            validated_sql,
            limit=limit,
            timeout_seconds=_config.server.query_timeout_seconds,
        )
    except TimeoutError as e:
        return {"errorCode": "DB_ERROR", "message": str(e)}
    except Exception as e:
        return {"errorCode": "DB_ERROR", "message": f"Query execution failed: {e}"}

    # 语义验证（非阻断）
    sample_rows = result.rows[: _config.server.result_validation_sample_rows]
    validation = await validate_result(
        client=_openai,
        model=_config.openai.model,
        user_query=query,
        sql=validated_sql,
        sample_rows=sample_rows,
        columns=result.columns,
        timeout_seconds=_config.openai.timeout_seconds,
    )

    # auto_retry_on_invalid
    if _config.server.auto_retry_on_invalid and not validation.is_meaningful and not validation.validation_skipped:
        try:
            sql2 = await generate_sql(_openai, _config.openai.model, query, schema_text)
            validated_sql2, err2 = validate_sql(sql2, _config.server.max_result_rows)
            if not err2:
                result = await execute_query(
                    pool, validated_sql2, limit=limit,
                    timeout_seconds=_config.server.query_timeout_seconds,
                )
                validated_sql = validated_sql2
                sample_rows = result.rows[: _config.server.result_validation_sample_rows]
                validation = await validate_result(
                    client=_openai, model=_config.openai.model,
                    user_query=query, sql=validated_sql,
                    sample_rows=sample_rows, columns=result.columns,
                    timeout_seconds=_config.openai.timeout_seconds,
                )
        except Exception:
            pass  # 重试失败时使用第一次结果

    return QueryToResultOutput(
        sql=validated_sql,
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        validation=validation,
    ).model_dump(by_alias=True)


@mcp.tool()
async def list_databases() -> dict[str, Any]:
    """列出所有已配置并完成 Schema 缓存的数据库及其元信息。"""
    databases = [
        DatabaseInfo(
            alias=c.alias,
            host=c.host,
            dbname=c.dbname,
            schema_cached_at=c.cached_at if c.is_available else None,
            table_count=c.table_count,
            is_available=c.is_available,
        )
        for c in _caches.values()
    ]
    return ListDatabasesOutput(databases=databases).model_dump(by_alias=True)


@mcp.tool()
async def refresh_schema(database: str | None = None) -> dict[str, Any]:
    """手动触发一个或所有数据库的 Schema 重新发现与缓存更新。

    Args:
        database: 要刷新的数据库别名。不填则刷新全部。
    """
    assert _config is not None
    start_time = time.monotonic()

    # 修正 D-03: 按 alias 查找而非取 index
    if database is not None:
        targets = [db for db in _config.databases if db.alias == database]
        if not targets:
            return {
                "errorCode": "DATABASE_NOT_FOUND",
                "message": f"Database '{database}' not found",
            }
    else:
        targets = list(_config.databases)

    refreshed: list[str] = []
    failed: list[str] = []

    async def refresh_one(db: DatabaseConfig) -> None:
        cache = await load_schema(db)
        _caches[db.alias] = cache
        if cache.is_available:
            try:
                # 关闭旧连接池并创建新的
                if db.alias in _pools:
                    await _pools[db.alias].close()
                _pools[db.alias] = await create_pool(db)
                refreshed.append(db.alias)
            except Exception as e:
                logger.error("Failed to recreate pool for %s: %s", db.alias, e)
                failed.append(db.alias)
        else:
            failed.append(db.alias)

    await asyncio.gather(*[refresh_one(db) for db in targets])

    return RefreshSchemaOutput(
        refreshed=refreshed,
        failed=failed,
        duration_seconds=time.monotonic() - start_time,
    ).model_dump(by_alias=True)


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    global _config

    # P0修复: 动态构建 AppConfig，支持 --config 参数覆盖 yaml 路径
    parser = argparse.ArgumentParser(description="pg-mcp: PostgreSQL MCP Server")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to YAML config file (default: config.yaml)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # pydantic-settings[yaml] 支持构造时传入 _yaml_file 覆盖类定义路径
    _config = AppConfig(_yaml_file=args.config)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
