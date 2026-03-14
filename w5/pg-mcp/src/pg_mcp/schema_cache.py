from __future__ import annotations

import asyncio
import asyncpg
from dataclasses import dataclass
from datetime import datetime, UTC

from pg_mcp.config import DatabaseConfig
from pg_mcp.models import (
    ColumnInfo, IndexInfo, ForeignKeyInfo,
    CustomTypeInfo, TableSchema, DatabaseSchemaCache,
)


# ── 内部临时结构（不暴露到外部）────────────────────────────────────────────

@dataclass
class _RawTable:
    schema_name: str
    table_name: str
    table_type: str
    comment: str | None


@dataclass
class _RawColumn:
    schema_name: str
    table_name: str
    column_name: str
    data_type: str
    is_nullable: bool
    column_default: str | None
    comment: str | None


@dataclass
class _RawIndex:
    schema_name: str
    table_name: str
    index_name: str
    is_unique: bool
    columns: list[str]


@dataclass
class _RawForeignKey:
    schema_name: str
    table_name: str
    constraint_name: str
    local_columns: list[str]
    foreign_schema: str
    foreign_table: str
    foreign_columns: list[str]


@dataclass
class _RawCustomType:
    schema_name: str
    type_name: str
    enum_values: list[str]


# ── Fetch 函数 ───────────────────────────────────────────────────────────────

async def _fetch_tables(conn: asyncpg.Connection, schemas: list[str]) -> list[_RawTable]:
    rows = await conn.fetch(
        """
        SELECT
            t.table_schema,
            t.table_name,
            t.table_type,
            obj_description(
                (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
                'pg_class'
            ) AS table_comment
        FROM information_schema.tables t
        WHERE t.table_schema = ANY($1)
          AND t.table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY t.table_schema, t.table_name
        """,
        schemas,
    )
    return [
        _RawTable(
            schema_name=r["table_schema"],
            table_name=r["table_name"],
            table_type=r["table_type"],
            comment=r["table_comment"],
        )
        for r in rows
    ]


async def _fetch_columns(conn: asyncpg.Connection, schemas: list[str]) -> list[_RawColumn]:
    rows = await conn.fetch(
        """
        SELECT
            c.table_schema,
            c.table_name,
            c.column_name,
            c.udt_name AS data_type,
            (c.is_nullable = 'YES') AS is_nullable,
            c.column_default,
            col_description(
                (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
                c.ordinal_position
            ) AS column_comment
        FROM information_schema.columns c
        WHERE c.table_schema = ANY($1)
        ORDER BY c.table_schema, c.table_name, c.ordinal_position
        """,
        schemas,
    )
    return [
        _RawColumn(
            schema_name=r["table_schema"],
            table_name=r["table_name"],
            column_name=r["column_name"],
            data_type=r["data_type"],
            is_nullable=r["is_nullable"],
            column_default=r["column_default"],
            comment=r["column_comment"],
        )
        for r in rows
    ]


async def _fetch_indexes(conn: asyncpg.Connection, schemas: list[str]) -> list[_RawIndex]:
    rows = await conn.fetch(
        """
        SELECT
            pi.schemaname,
            pi.tablename,
            pi.indexname,
            ix.indisunique AS is_unique,
            array_agg(a.attname ORDER BY k.pos) AS columns
        FROM pg_indexes pi
        JOIN pg_class ic ON ic.relname = pi.indexname
            AND ic.relnamespace = (
                SELECT oid FROM pg_namespace WHERE nspname = pi.schemaname
            )
        JOIN pg_index ix ON ix.indexrelid = ic.oid
        JOIN pg_class tc ON tc.relname = pi.tablename
            AND tc.relnamespace = ic.relnamespace
        CROSS JOIN LATERAL unnest(ix.indkey::int[]) WITH ORDINALITY AS k(attnum, pos)
        JOIN pg_attribute a ON a.attrelid = tc.oid
            AND a.attnum = k.attnum
            AND a.attnum > 0
        WHERE pi.schemaname = ANY($1)
          AND NOT ix.indisprimary
        GROUP BY pi.schemaname, pi.tablename, pi.indexname, ix.indisunique
        """,
        schemas,
    )
    return [
        _RawIndex(
            schema_name=r["schemaname"],
            table_name=r["tablename"],
            index_name=r["indexname"],
            is_unique=r["is_unique"],
            columns=list(r["columns"]),
        )
        for r in rows
    ]


async def _fetch_foreign_keys(conn: asyncpg.Connection, schemas: list[str]) -> list[_RawForeignKey]:
    rows = await conn.fetch(
        """
        SELECT
            tc.table_schema,
            tc.table_name,
            tc.constraint_name,
            array_agg(kcu.column_name ORDER BY kcu.ordinal_position) AS local_columns,
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            array_agg(ccu.column_name ORDER BY kcu.ordinal_position) AS foreign_columns
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_schema = ANY($1)
        GROUP BY
            tc.table_schema, tc.table_name, tc.constraint_name,
            ccu.table_schema, ccu.table_name
        """,
        schemas,
    )
    return [
        _RawForeignKey(
            schema_name=r["table_schema"],
            table_name=r["table_name"],
            constraint_name=r["constraint_name"],
            local_columns=list(r["local_columns"]),
            foreign_schema=r["foreign_table_schema"],
            foreign_table=r["foreign_table_name"],
            foreign_columns=list(r["foreign_columns"]),
        )
        for r in rows
    ]


async def _fetch_custom_types(conn: asyncpg.Connection, schemas: list[str]) -> list[_RawCustomType]:
    rows = await conn.fetch(
        """
        SELECT
            n.nspname AS schema_name,
            t.typname AS type_name,
            array_agg(e.enumlabel ORDER BY e.enumsortorder) AS enum_values
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        JOIN pg_enum e ON e.enumtypid = t.oid
        WHERE n.nspname = ANY($1)
        GROUP BY n.nspname, t.typname
        """,
        schemas,
    )
    return [
        _RawCustomType(
            schema_name=r["schema_name"],
            type_name=r["type_name"],
            enum_values=list(r["enum_values"]),
        )
        for r in rows
    ]


# ── 主组装函数 ───────────────────────────────────────────────────────────────

async def load_schema(db: DatabaseConfig) -> DatabaseSchemaCache:
    """连接数据库并发现 Schema，返回 DatabaseSchemaCache。失败时返回 is_available=False。"""
    try:
        conn = await asyncpg.connect(
            dsn=db.dsn,
            server_settings={
                "default_transaction_read_only": "true",
                "statement_timeout": "10000",
            },
        )
        try:
            # 建议优化: 并发执行 5 个 fetch（P2 优化）
            raw_tables, raw_columns, raw_indexes, raw_fkeys, raw_types = await asyncio.gather(
                _fetch_tables(conn, db.schemas),
                _fetch_columns(conn, db.schemas),
                _fetch_indexes(conn, db.schemas),
                _fetch_foreign_keys(conn, db.schemas),
                _fetch_custom_types(conn, db.schemas),
            )
        finally:
            await conn.close()
    except Exception as e:
        return DatabaseSchemaCache(
            alias=db.alias, host=db.host, dbname=db.dbname,
            tables={}, custom_types=[], cached_at=datetime.now(UTC),
            is_available=False, error_message=str(e),
        )

    # 按 (schema, table) 分组（修正 D-01, D-02）
    cols_by_table: dict[tuple[str, str], list[_RawColumn]] = {}
    for col in raw_columns:
        cols_by_table.setdefault((col.schema_name, col.table_name), []).append(col)

    idx_by_table: dict[tuple[str, str], list[_RawIndex]] = {}
    for idx in raw_indexes:
        idx_by_table.setdefault((idx.schema_name, idx.table_name), []).append(idx)

    fk_by_table: dict[tuple[str, str], list[_RawForeignKey]] = {}
    for fk in raw_fkeys:
        fk_by_table.setdefault((fk.schema_name, fk.table_name), []).append(fk)

    # 组装 TableSchema
    table_map: dict[str, TableSchema] = {}
    for rt in raw_tables:
        key = (rt.schema_name, rt.table_name)
        full_name = f"{rt.schema_name}.{rt.table_name}"
        table_map[full_name] = TableSchema(
            schema_name=rt.schema_name,
            table_name=rt.table_name,
            full_name=full_name,
            object_type="view" if rt.table_type == "VIEW" else "table",
            columns=[
                ColumnInfo(
                    name=c.column_name,
                    data_type=c.data_type,
                    is_nullable=c.is_nullable,
                    default=c.column_default,
                    comment=c.comment,
                )
                for c in cols_by_table.get(key, [])
            ],
            indexes=[
                IndexInfo(
                    name=i.index_name,
                    columns=i.columns,
                    is_unique=i.is_unique,
                )
                for i in idx_by_table.get(key, [])
            ],
            foreign_keys=[
                ForeignKeyInfo(
                    constraint_name=f.constraint_name,
                    local_columns=f.local_columns,
                    foreign_table=f"{f.foreign_schema}.{f.foreign_table}",
                    foreign_columns=f.foreign_columns,
                )
                for f in fk_by_table.get(key, [])
            ],
            comment=rt.comment,
        )

    return DatabaseSchemaCache(
        alias=db.alias,
        host=db.host,
        dbname=db.dbname,
        tables=table_map,
        custom_types=[
            CustomTypeInfo(
                schema_name=t.schema_name,
                type_name=t.type_name,
                type_category="enum",
                enum_values=t.enum_values,
            )
            for t in raw_types
        ],
        cached_at=datetime.now(UTC),
        is_available=True,
    )
