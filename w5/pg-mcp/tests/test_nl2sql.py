"""NL2SQL 服务单元测试（mock OpenAI）"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from pg_mcp.nl2sql import generate_sql, build_schema_text
from pg_mcp.models import TableSchema, ColumnInfo


def make_mock_client(sql_result: str | None = "SELECT * FROM users"):
    """创建模拟 OpenAI 客户端"""
    mock_client = MagicMock()
    mock_response = MagicMock()

    if sql_result is None:
        mock_response.choices[0].message.parsed = None
    else:
        mock_parsed = MagicMock()
        mock_parsed.sql = sql_result
        mock_response.choices[0].message.parsed = mock_parsed

    # chat.completions.parse 是 async 方法
    mock_client.chat.completions.parse = AsyncMock(return_value=mock_response)
    return mock_client


async def test_generate_sql_success() -> None:
    client = make_mock_client("SELECT id, email FROM users LIMIT 1000")
    result = await generate_sql(client, "gpt-4o-mini", "all users", "Table: public.users\n  Columns: id (int4), email (text?)")
    assert result == "SELECT id, email FROM users LIMIT 1000"


async def test_generate_sql_null_parsed_raises() -> None:
    """当 OpenAI 返回 null parsed 时应抛出 ValueError"""
    client = make_mock_client(None)
    with pytest.raises(ValueError, match="null parsed response"):
        await generate_sql(client, "gpt-4o-mini", "query", "schema")


async def test_generate_sql_calls_correct_model() -> None:
    client = make_mock_client()
    await generate_sql(client, "gpt-4o-mini", "test", "schema")
    call_kwargs = client.chat.completions.parse.call_args
    assert call_kwargs.kwargs["model"] == "gpt-4o-mini"


async def test_generate_sql_uses_zero_temperature() -> None:
    client = make_mock_client()
    await generate_sql(client, "gpt-4o-mini", "test", "schema")
    call_kwargs = client.chat.completions.parse.call_args
    assert call_kwargs.kwargs["temperature"] == 0


async def test_generate_sql_schema_text_injected() -> None:
    """schema_text 应该出现在系统 prompt 中"""
    client = make_mock_client()
    schema_text = "Table: public.special_{id}_table\n  Columns: id (int4)"
    await generate_sql(client, "gpt-4o-mini", "test", schema_text)

    call_kwargs = client.chat.completions.parse.call_args
    messages = call_kwargs.kwargs["messages"]
    system_content = messages[0]["content"]
    # P1修复验证: schema_text 中的 {id} 不应破坏 prompt（使用 str.replace 而非 str.format）
    assert "special_{id}_table" in system_content


def test_build_schema_text_empty() -> None:
    result = build_schema_text([])
    assert result == "(no schema available)"


def test_build_schema_text_single_table() -> None:
    table = TableSchema(
        schema_name="public",
        table_name="users",
        full_name="public.users",
        object_type="table",
        columns=[ColumnInfo(name="id", data_type="int4", is_nullable=False)],
        indexes=[],
        foreign_keys=[],
    )
    result = build_schema_text([table])
    assert "public.users" in result
    assert "id" in result


def test_build_schema_text_multiple_tables_separator() -> None:
    tables = [
        TableSchema(
            schema_name="public",
            table_name=f"t{i}",
            full_name=f"public.t{i}",
            object_type="table",
            columns=[],
            indexes=[],
            foreign_keys=[],
        )
        for i in range(3)
    ]
    result = build_schema_text(tables)
    # 多个表应该用 "\n\n" 分隔
    assert "\n\n" in result
