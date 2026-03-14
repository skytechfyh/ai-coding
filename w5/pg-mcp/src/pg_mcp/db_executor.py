from __future__ import annotations

import decimal
import time
import uuid
from datetime import date, datetime

import asyncpg
from asyncpg import Pool

from pg_mcp.config import DatabaseConfig
from pg_mcp.models import ExecutionResult


def _serialize_value(v: object) -> object:
    """将 asyncpg 不可 JSON 序列化的类型转为基本类型（P0 修复）"""
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, memoryview)):
        return "<binary>"
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


async def create_pool(db: DatabaseConfig) -> Pool:
    """创建 asyncpg 连接池，会话级别强制只读"""
    return await asyncpg.create_pool(
        dsn=db.dsn,
        min_size=db.min_pool_size,
        max_size=db.max_pool_size,
        server_settings={
            "default_transaction_read_only": "true",
        },
    )


async def execute_query(
    pool: Pool,
    sql: str,
    limit: int,
    timeout_seconds: int,
) -> ExecutionResult:
    """执行 SQL 查询，返回结果。超时时抛出 TimeoutError。"""
    start = time.monotonic()

    async with pool.acquire() as conn:
        # 修正 D-05: 整数毫秒，无字符串引号
        await conn.execute(f"SET statement_timeout = {int(timeout_seconds * 1000)}")

        try:
            records = await conn.fetch(sql, timeout=float(timeout_seconds))
        except asyncpg.exceptions.QueryCanceledError:
            raise TimeoutError(f"Query timed out after {timeout_seconds}s")

        elapsed_ms = (time.monotonic() - start) * 1000

        if not records:
            # 修正 D-06: 在同一 acquire 块内处理零行结果，通过 prepare 获取列名
            stmt = await conn.prepare(sql)
            columns = [attr.name for attr in stmt.get_attributes()]
            return ExecutionResult(
                columns=columns,
                rows=[],
                row_count=0,
                execution_time_ms=elapsed_ms,
            )

        columns = list(records[0].keys())
        # P0 修复: 集成 _serialize_value，处理 datetime/Decimal/UUID/bytes 类型
        rows = [[_serialize_value(v) for v in r.values()] for r in records[:limit]]

    return ExecutionResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=(time.monotonic() - start) * 1000,
    )
