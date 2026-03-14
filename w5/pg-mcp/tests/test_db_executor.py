"""db_executor.py 单元测试"""
from __future__ import annotations

import decimal
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from pg_mcp.db_executor import _serialize_value, execute_query


# ── _serialize_value ─────────────────────────────────────────────────────────

def test_serialize_value_datetime() -> None:
    v = datetime(2026, 3, 14, 10, 30, 0)
    assert _serialize_value(v) == "2026-03-14T10:30:00"


def test_serialize_value_datetime_with_tz() -> None:
    v = datetime(2026, 3, 14, 10, 30, 0, tzinfo=timezone.utc)
    result = _serialize_value(v)
    assert isinstance(result, str)
    assert "2026-03-14" in result
    assert "+00:00" in result


def test_serialize_value_date() -> None:
    v = date(2026, 3, 14)
    assert _serialize_value(v) == "2026-03-14"


def test_serialize_value_decimal() -> None:
    v = decimal.Decimal("123.456")
    result = _serialize_value(v)
    assert isinstance(result, float)
    assert abs(result - 123.456) < 0.001


def test_serialize_value_bytes() -> None:
    assert _serialize_value(b"\x00\x01") == "<binary>"


def test_serialize_value_memoryview() -> None:
    assert _serialize_value(memoryview(b"\x00\x01")) == "<binary>"


def test_serialize_value_uuid() -> None:
    """uuid.UUID 应转为字符串（HINT-04 已修复）"""
    v = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    result = _serialize_value(v)
    assert result == "550e8400-e29b-41d4-a716-446655440000"
    assert isinstance(result, str)


def test_serialize_value_none() -> None:
    assert _serialize_value(None) is None


@pytest.mark.parametrize("v,expected", [
    (42, 42),
    ("hello", "hello"),
    (True, True),
    (3.14, 3.14),
])
def test_serialize_value_passthrough(v, expected) -> None:
    assert _serialize_value(v) == expected


# ── execute_query helpers ────────────────────────────────────────────────────

def _make_record(data: dict):
    """Create a minimal asyncpg-like Record mock."""
    rec = MagicMock()
    rec.keys.return_value = list(data.keys())
    rec.values.return_value = list(data.values())
    return rec


def _make_mock_pool(fetch_return=None, fetch_side_effect=None):
    """Build a mock asyncpg Pool with acquire() context manager."""
    conn = AsyncMock()
    conn.execute = AsyncMock()

    if fetch_side_effect is not None:
        conn.fetch = AsyncMock(side_effect=fetch_side_effect)
    else:
        conn.fetch = AsyncMock(return_value=fetch_return or [])

    # prepare() for empty-result column detection
    stmt_mock = MagicMock()
    attr1 = MagicMock(); attr1.name = "id"
    attr2 = MagicMock(); attr2.name = "email"
    stmt_mock.get_attributes.return_value = [attr1, attr2]
    conn.prepare = AsyncMock(return_value=stmt_mock)

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=_AsyncContextManager(conn))
    return pool, conn


class _AsyncContextManager:
    def __init__(self, value):
        self._value = value

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, *args):
        pass


# ── execute_query tests ──────────────────────────────────────────────────────

async def test_execute_query_returns_result() -> None:
    records = [
        _make_record({"id": 1, "name": "alice"}),
        _make_record({"id": 2, "name": "bob"}),
    ]
    pool, _ = _make_mock_pool(fetch_return=records)
    result = await execute_query(pool, "SELECT id, name FROM users", limit=10, timeout_seconds=5)
    assert result.columns == ["id", "name"]
    assert result.rows == [[1, "alice"], [2, "bob"]]
    assert result.row_count == 2


async def test_execute_query_empty_result_uses_prepare() -> None:
    pool, conn = _make_mock_pool(fetch_return=[])
    result = await execute_query(pool, "SELECT id, email FROM users WHERE 1=0", limit=10, timeout_seconds=5)
    assert result.rows == []
    assert result.columns == ["id", "email"]
    conn.prepare.assert_called_once()


async def test_execute_query_timeout_raises() -> None:
    pool, _ = _make_mock_pool(
        fetch_side_effect=asyncpg.exceptions.QueryCanceledError("cancelled")
    )
    with pytest.raises(TimeoutError, match="timed out"):
        await execute_query(pool, "SELECT pg_sleep(10)", limit=1, timeout_seconds=1)


async def test_execute_query_sets_statement_timeout() -> None:
    pool, conn = _make_mock_pool(fetch_return=[])
    await execute_query(pool, "SELECT 1", limit=10, timeout_seconds=5)
    conn.execute.assert_called_once_with("SET statement_timeout = 5000")


async def test_execute_query_serializes_datetime() -> None:
    dt = datetime(2026, 3, 14, 12, 0, 0)
    records = [_make_record({"ts": dt})]
    pool, _ = _make_mock_pool(fetch_return=records)
    result = await execute_query(pool, "SELECT ts FROM t", limit=10, timeout_seconds=5)
    assert result.rows[0][0] == "2026-03-14T12:00:00"


async def test_execute_query_respects_limit() -> None:
    records = [_make_record({"id": i}) for i in range(200)]
    pool, _ = _make_mock_pool(fetch_return=records)
    result = await execute_query(pool, "SELECT id FROM t", limit=10, timeout_seconds=5)
    assert result.row_count == 10
    assert len(result.rows) == 10
