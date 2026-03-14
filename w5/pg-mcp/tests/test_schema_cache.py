"""schema_cache.py 单元测试（Mock asyncpg，无需真实 DB）"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.config import DatabaseConfig
from pg_mcp.schema_cache import load_schema


def make_db_config(**kwargs) -> DatabaseConfig:
    defaults = dict(alias="main", host="localhost", port=5432, dbname="testdb",
                    user="admin", password="secret", schemas=["public"])
    defaults.update(kwargs)
    return DatabaseConfig(**defaults)


def _rec(data: dict):
    """Minimal asyncpg Record-like mock."""
    r = MagicMock()
    r.__getitem__ = lambda self, k: data[k]
    return r


def _make_conn(tables=None, columns=None, indexes=None, fkeys=None, types=None):
    """Build a mock asyncpg connection whose fetch() dispatches by SQL content."""
    tables = tables or []
    columns = columns or []
    indexes = indexes or []
    fkeys = fkeys or []
    types = types or []

    async def fetch_dispatch(sql, *args, **kwargs):
        sql_stripped = sql.strip()
        if "information_schema.tables" in sql_stripped:
            return tables
        if "information_schema.columns" in sql_stripped:
            return columns
        if "pg_indexes" in sql_stripped:
            return indexes
        if "FOREIGN KEY" in sql_stripped:
            return fkeys
        if "pg_enum" in sql_stripped:
            return types
        return []

    conn = AsyncMock()
    conn.fetch = fetch_dispatch
    conn.close = AsyncMock()
    return conn


# ── TC-SCHEMA-01: connection error ───────────────────────────────────────────

async def test_load_schema_connection_error() -> None:
    db = make_db_config()
    with patch("pg_mcp.schema_cache.asyncpg.connect", side_effect=ConnectionRefusedError("refused")):
        cache = await load_schema(db)
    assert cache.is_available is False
    assert cache.error_message is not None


# ── TC-SCHEMA-02: happy path ─────────────────────────────────────────────────

async def test_load_schema_happy_path() -> None:
    db = make_db_config()
    tables = [_rec({"table_schema": "public", "table_name": "users",
                    "table_type": "BASE TABLE", "table_comment": None})]
    columns = [_rec({"table_schema": "public", "table_name": "users",
                     "column_name": "id", "data_type": "int4",
                     "is_nullable": False, "column_default": None, "column_comment": None})]
    conn = _make_conn(tables=tables, columns=columns)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    assert cache.is_available is True
    assert cache.table_count == 1


# ── TC-SCHEMA-03: column grouping ────────────────────────────────────────────

async def test_load_schema_column_grouping() -> None:
    db = make_db_config()
    tables = [
        _rec({"table_schema": "public", "table_name": "users",
              "table_type": "BASE TABLE", "table_comment": None}),
        _rec({"table_schema": "public", "table_name": "orders",
              "table_type": "BASE TABLE", "table_comment": None}),
    ]
    columns = [
        _rec({"table_schema": "public", "table_name": "users", "column_name": "id",
              "data_type": "int4", "is_nullable": False, "column_default": None, "column_comment": None}),
        _rec({"table_schema": "public", "table_name": "users", "column_name": "name",
              "data_type": "text", "is_nullable": True, "column_default": None, "column_comment": None}),
        _rec({"table_schema": "public", "table_name": "orders", "column_name": "id",
              "data_type": "int4", "is_nullable": False, "column_default": None, "column_comment": None}),
        _rec({"table_schema": "public", "table_name": "orders", "column_name": "total",
              "data_type": "numeric", "is_nullable": True, "column_default": None, "column_comment": None}),
    ]
    conn = _make_conn(tables=tables, columns=columns)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    users_cols = [c.name for c in cache.tables["public.users"].columns]
    orders_cols = [c.name for c in cache.tables["public.orders"].columns]
    assert users_cols == ["id", "name"]
    assert orders_cols == ["id", "total"]
    assert "total" not in users_cols


# ── TC-SCHEMA-04: index grouping ─────────────────────────────────────────────

async def test_load_schema_index_grouping() -> None:
    db = make_db_config()
    tables = [
        _rec({"table_schema": "public", "table_name": "users",
              "table_type": "BASE TABLE", "table_comment": None}),
        _rec({"table_schema": "public", "table_name": "orders",
              "table_type": "BASE TABLE", "table_comment": None}),
    ]
    indexes = [
        _rec({"schemaname": "public", "tablename": "users", "indexname": "users_email_idx",
              "is_unique": True, "columns": ["email"]}),
        _rec({"schemaname": "public", "tablename": "orders", "indexname": "orders_user_idx",
              "is_unique": False, "columns": ["user_id"]}),
    ]
    conn = _make_conn(tables=tables, indexes=indexes)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    users_idx = [i.name for i in cache.tables["public.users"].indexes]
    orders_idx = [i.name for i in cache.tables["public.orders"].indexes]
    assert "users_email_idx" in users_idx
    assert "orders_user_idx" not in users_idx
    assert "orders_user_idx" in orders_idx


# ── TC-SCHEMA-05: FK grouping ────────────────────────────────────────────────

async def test_load_schema_fk_grouping() -> None:
    db = make_db_config()
    tables = [
        _rec({"table_schema": "public", "table_name": "orders",
              "table_type": "BASE TABLE", "table_comment": None}),
    ]
    fkeys = [
        _rec({"table_schema": "public", "table_name": "orders",
              "constraint_name": "orders_user_fk",
              "local_columns": ["user_id"],
              "foreign_table_schema": "public", "foreign_table_name": "users",
              "foreign_columns": ["id"]}),
    ]
    conn = _make_conn(tables=tables, fkeys=fkeys)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    fks = cache.tables["public.orders"].foreign_keys
    assert len(fks) == 1
    assert fks[0].constraint_name == "orders_user_fk"


# ── TC-SCHEMA-06: custom type uses dataclass attrs ───────────────────────────

async def test_load_schema_custom_type_dataclass() -> None:
    db = make_db_config()
    types = [
        _rec({"schema_name": "public", "type_name": "status_enum",
              "enum_values": ["active", "inactive"]}),
    ]
    conn = _make_conn(types=types)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    assert len(cache.custom_types) == 1
    ct = cache.custom_types[0]
    assert ct.type_name == "status_enum"
    assert ct.enum_values == ["active", "inactive"]


# ── TC-SCHEMA-07: VIEW type mapping ──────────────────────────────────────────

async def test_load_schema_view_type() -> None:
    db = make_db_config()
    tables = [
        _rec({"table_schema": "public", "table_name": "active_users",
              "table_type": "VIEW", "table_comment": None}),
    ]
    conn = _make_conn(tables=tables)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    assert cache.tables["public.active_users"].object_type == "view"


# ── TC-SCHEMA-08: empty database ─────────────────────────────────────────────

async def test_load_schema_empty_database() -> None:
    db = make_db_config()
    conn = _make_conn()
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    assert cache.is_available is True
    assert cache.table_count == 0


# ── TC-SCHEMA-09: multiple schemas ───────────────────────────────────────────

async def test_load_schema_multiple_schemas() -> None:
    db = make_db_config(schemas=["public", "analytics"])
    tables = [
        _rec({"table_schema": "public", "table_name": "users",
              "table_type": "BASE TABLE", "table_comment": None}),
        _rec({"table_schema": "analytics", "table_name": "events",
              "table_type": "BASE TABLE", "table_comment": None}),
    ]
    conn = _make_conn(tables=tables)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    assert "public.users" in cache.tables
    assert "analytics.events" in cache.tables


# ── TC-SCHEMA-10: FK foreign_table format ────────────────────────────────────

async def test_load_schema_fk_full_name_format() -> None:
    db = make_db_config()
    tables = [
        _rec({"table_schema": "public", "table_name": "orders",
              "table_type": "BASE TABLE", "table_comment": None}),
    ]
    fkeys = [
        _rec({"table_schema": "public", "table_name": "orders",
              "constraint_name": "fk_user",
              "local_columns": ["user_id"],
              "foreign_table_schema": "public", "foreign_table_name": "users",
              "foreign_columns": ["id"]}),
    ]
    conn = _make_conn(tables=tables, fkeys=fkeys)
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    fk = cache.tables["public.orders"].foreign_keys[0]
    assert fk.foreign_table == "public.users"


# ── TC-SCHEMA-12: table without indexes ──────────────────────────────────────

async def test_load_schema_table_without_indexes() -> None:
    db = make_db_config()
    tables = [
        _rec({"table_schema": "public", "table_name": "users",
              "table_type": "BASE TABLE", "table_comment": None}),
    ]
    conn = _make_conn(tables=tables, indexes=[])
    with patch("pg_mcp.schema_cache.asyncpg.connect", return_value=conn):
        cache = await load_schema(db)
    assert cache.tables["public.users"].indexes == []
