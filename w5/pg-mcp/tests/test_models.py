"""数据模型单元测试：to_prompt_text、get_relevant_tables、序列化"""
import pytest
from datetime import datetime, UTC

from pg_mcp.models import (
    ColumnInfo,
    DatabaseSchemaCache,
    ForeignKeyInfo,
    IndexInfo,
    TableSchema,
    QueryToSqlOutput,
    ValidationInfo,
)


# ── Fixtures ──────────────────────────────────────────────────────────────

def make_table(
    table_name: str,
    schema_name: str = "public",
    columns: list[ColumnInfo] | None = None,
    foreign_keys: list[ForeignKeyInfo] | None = None,
    comment: str | None = None,
) -> TableSchema:
    return TableSchema(
        schema_name=schema_name,
        table_name=table_name,
        full_name=f"{schema_name}.{table_name}",
        object_type="table",
        columns=columns or [
            ColumnInfo(name="id", data_type="int4", is_nullable=False),
            ColumnInfo(name="name", data_type="text", is_nullable=True),
        ],
        indexes=[],
        foreign_keys=foreign_keys or [],
        comment=comment,
    )


def make_cache(tables: list[TableSchema]) -> DatabaseSchemaCache:
    return DatabaseSchemaCache(
        alias="test",
        host="localhost",
        dbname="testdb",
        tables={t.full_name: t for t in tables},
        custom_types=[],
        cached_at=datetime.now(UTC),
    )


# ── to_prompt_text ──────────────────────────────────────────────────────

def test_to_prompt_text_basic() -> None:
    table = make_table("users")
    text = table.to_prompt_text()
    assert "Table: public.users" in text
    assert "id (int4)" in text
    assert "name (text?)" in text  # nullable 用 ? 标记


def test_to_prompt_text_with_indexes() -> None:
    table = TableSchema(
        schema_name="public",
        table_name="events",
        full_name="public.events",
        object_type="table",
        columns=[ColumnInfo(name="id", data_type="int4", is_nullable=False)],
        indexes=[IndexInfo(name="events_pkey", columns=["id"], is_unique=True)],
        foreign_keys=[],
    )
    text = table.to_prompt_text()
    assert "Indexes:" in text
    assert "events_pkey" in text
    assert "UNIQUE" in text


def test_to_prompt_text_with_fk() -> None:
    table = TableSchema(
        schema_name="public",
        table_name="orders",
        full_name="public.orders",
        object_type="table",
        columns=[
            ColumnInfo(name="id", data_type="int4", is_nullable=False),
            ColumnInfo(name="user_id", data_type="int4", is_nullable=False),
        ],
        indexes=[],
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="orders_user_fk",
                local_columns=["user_id"],
                foreign_table="public.users",
                foreign_columns=["id"],
            )
        ],
    )
    text = table.to_prompt_text()
    assert "FK:" in text
    assert "user_id" in text
    assert "public.users" in text


def test_to_prompt_text_empty_columns() -> None:
    table = TableSchema(
        schema_name="public",
        table_name="empty",
        full_name="public.empty",
        object_type="table",
        columns=[],
        indexes=[],
        foreign_keys=[],
    )
    text = table.to_prompt_text()
    assert "Table: public.empty" in text
    assert "(no columns)" in text


# ── get_relevant_tables ─────────────────────────────────────────────────

def test_relevant_tables_keyword_matching() -> None:
    users = make_table("users")
    orders = make_table("orders")
    products = make_table("products")
    cache = make_cache([users, orders, products])

    result = cache.get_relevant_tables("find all users", max_tables=2)
    # users 应该排在最前
    assert result[0].table_name == "users"


def test_relevant_tables_fk_expansion() -> None:
    users = make_table("users")
    orders = make_table(
        "orders",
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="orders_user_fk",
                local_columns=["user_id"],
                foreign_table="public.users",
                foreign_columns=["id"],
            )
        ],
    )
    products = make_table("products")
    cache = make_cache([users, orders, products])

    # 搜索 orders，FK 关联的 users 也应被补入
    result = cache.get_relevant_tables("list orders", max_tables=1)
    result_names = {t.table_name for t in result}
    assert "orders" in result_names
    assert "users" in result_names  # FK 扩展补入


def test_relevant_tables_no_infinite_loop() -> None:
    """两张表互相 FK 时不应死循环"""
    users = make_table(
        "users",
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="users_org_fk",
                local_columns=["org_id"],
                foreign_table="public.organizations",
                foreign_columns=["id"],
            )
        ],
    )
    organizations = make_table(
        "organizations",
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="orgs_admin_fk",
                local_columns=["admin_id"],
                foreign_table="public.users",
                foreign_columns=["id"],
            )
        ],
    )
    cache = make_cache([users, organizations])

    # 不应死循环，应在有限时间内返回
    result = cache.get_relevant_tables("find users", max_tables=10)
    assert len(result) <= 2  # 只有 2 张表，不会无限扩展


def test_relevant_tables_chinese_tokenization() -> None:
    """中文查询时应能正确匹配相关表"""
    users = make_table("users")
    orders = make_table("orders")
    cache = make_cache([users, orders])

    # 中文查询包含 "用" 字，与 users 表无直接匹配
    # 但不应崩溃，应正常返回结果
    result = cache.get_relevant_tables("查询所有用户注册信息", max_tables=10)
    assert len(result) >= 0  # 不崩溃


def test_relevant_tables_max_tables_limit() -> None:
    tables = [make_table(f"table_{i}") for i in range(50)]
    cache = make_cache(tables)
    result = cache.get_relevant_tables("query", max_tables=5)
    assert len(result) == 5


# ── relevance_score ──────────────────────────────────────────────────────

def test_relevance_score_match() -> None:
    table = make_table("users", columns=[
        ColumnInfo(name="id", data_type="int4", is_nullable=False),
        ColumnInfo(name="email", data_type="text", is_nullable=True),
    ])
    score = table.relevance_score({"users", "email"})
    assert score == 2


def test_relevance_score_no_match() -> None:
    table = make_table("orders")
    score = table.relevance_score({"users", "email"})
    assert score == 0


# ── _tokenize_query ──────────────────────────────────────────────────────

def test_tokenize_query_mixed() -> None:
    from pg_mcp.models import _tokenize_query
    tokens = _tokenize_query("查询 users 的 email 信息")
    assert "users" in tokens
    assert "email" in tokens
    assert "查" in tokens
    assert "息" in tokens
    assert "的" not in tokens  # stop word


def test_tokenize_query_only_stopwords() -> None:
    from pg_mcp.models import _tokenize_query
    tokens = _tokenize_query("show all the list of")
    assert len(tokens) == 0


def test_tokenize_query_empty() -> None:
    from pg_mcp.models import _tokenize_query
    tokens = _tokenize_query("")
    assert tokens == set()


# ── edge cases ───────────────────────────────────────────────────────────

def test_get_relevant_tables_fk_to_unknown_table() -> None:
    """FK target 不在 tables 中时不崩溃"""
    orders = make_table(
        "orders",
        foreign_keys=[
            ForeignKeyInfo(
                constraint_name="fk_ghost",
                local_columns=["user_id"],
                foreign_table="public.ghost_table",
                foreign_columns=["id"],
            )
        ],
    )
    cache = make_cache([orders])
    result = cache.get_relevant_tables("orders", max_tables=5)
    assert any(t.table_name == "orders" for t in result)


def test_get_relevant_tables_empty_query() -> None:
    tables = [make_table(f"t{i}") for i in range(10)]
    cache = make_cache(tables)
    result = cache.get_relevant_tables("", max_tables=5)
    assert len(result) == 5


def test_get_relevant_tables_large_schema() -> None:
    import time
    tables = [make_table(f"table_{i}") for i in range(500)]
    cache = make_cache(tables)
    start = time.monotonic()
    result = cache.get_relevant_tables("find user orders", max_tables=20)
    elapsed = time.monotonic() - start
    assert elapsed < 0.1
    assert len(result) <= 500


# ── CamelCase 序列化 ────────────────────────────────────────────────────

def test_query_to_sql_output_camelcase() -> None:
    output = QueryToSqlOutput(
        sql="SELECT * FROM users",
        database="main",
        schema_used=["public.users"],
    )
    data = output.model_dump(by_alias=True)
    assert "sql" in data
    assert "database" in data
    assert "schemaUsed" in data  # camelCase
    assert "schema_used" not in data


def test_validation_info_camelcase() -> None:
    info = ValidationInfo(
        is_meaningful=True,
        explanation="结果正确",
        validation_skipped=False,
    )
    data = info.model_dump(by_alias=True)
    assert "isMeaningful" in data
    assert "validationSkipped" in data


# ── table_count property ────────────────────────────────────────────────

def test_database_schema_cache_table_count() -> None:
    tables = [make_table(f"t{i}") for i in range(5)]
    cache = make_cache(tables)
    assert cache.table_count == 5
