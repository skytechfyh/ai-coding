"""结果验证服务单元测试（mock OpenAI）"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import openai

from pg_mcp.result_validator import validate_result
from pg_mcp.models import ValidationInfo


def make_mock_client(is_meaningful: bool = True, explanation: str = "结果正确"):
    """创建模拟 OpenAI 客户端"""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_parsed = MagicMock()
    mock_parsed.is_meaningful = is_meaningful
    mock_parsed.explanation = explanation
    mock_response.choices[0].message.parsed = mock_parsed
    mock_client.chat.completions.parse = AsyncMock(return_value=mock_response)
    return mock_client


async def test_validate_result_success() -> None:
    client = make_mock_client(is_meaningful=True, explanation="查询结果符合预期")
    result = await validate_result(
        client=client,
        model="gpt-4o-mini",
        user_query="all users",
        sql="SELECT * FROM users",
        sample_rows=[[1, "alice"], [2, "bob"]],
        columns=["id", "name"],
    )
    assert result.is_meaningful is True
    assert "查询" in result.explanation
    assert result.validation_skipped is False


async def test_validate_result_not_meaningful() -> None:
    client = make_mock_client(is_meaningful=False, explanation="结果与查询不符")
    result = await validate_result(
        client=client,
        model="gpt-4o-mini",
        user_query="count users",
        sql="SELECT * FROM orders",
        sample_rows=[[1, "order1"]],
        columns=["id", "name"],
    )
    assert result.is_meaningful is False
    assert result.validation_skipped is False


async def test_validate_result_empty_rows() -> None:
    """空结果集应跳过 OpenAI 调用，直接返回 is_meaningful=True（P1修复）"""
    mock_client = MagicMock()
    mock_client.chat.completions.parse = AsyncMock()

    result = await validate_result(
        client=mock_client,
        model="gpt-4o-mini",
        user_query="find deleted users",
        sql="SELECT * FROM users WHERE deleted_at IS NOT NULL",
        sample_rows=[],
        columns=["id", "name"],
    )
    # 空结果集不应调用 OpenAI
    mock_client.chat.completions.parse.assert_not_called()
    # P1修复: 空结果集应返回 is_meaningful=True，不是 False
    assert result.is_meaningful is True
    assert result.validation_skipped is False


async def test_validate_result_timeout_skips() -> None:
    """OpenAI 超时时应返回 validation_skipped=True（P0修复）"""
    mock_client = MagicMock()
    mock_client.chat.completions.parse = AsyncMock(
        side_effect=asyncio.TimeoutError()
    )

    result = await validate_result(
        client=mock_client,
        model="gpt-4o-mini",
        user_query="test",
        sql="SELECT 1",
        sample_rows=[[1]],
        columns=["n"],
        timeout_seconds=0.001,  # 极短超时
    )
    assert result.validation_skipped is True
    assert result.is_meaningful is False


async def test_validate_result_openai_api_error_skips() -> None:
    """OpenAI API 错误时应返回 validation_skipped=True，而非向上抛出（P0修复）"""
    mock_client = MagicMock()
    # 模拟 openai.APIError
    mock_client.chat.completions.parse = AsyncMock(
        side_effect=openai.APIStatusError(
            "Internal Server Error",
            response=MagicMock(status_code=500),
            body={"error": {"message": "Internal Server Error"}},
        )
    )

    result = await validate_result(
        client=mock_client,
        model="gpt-4o-mini",
        user_query="test",
        sql="SELECT 1",
        sample_rows=[[1]],
        columns=["n"],
    )
    assert result.validation_skipped is True


async def test_validate_result_programming_error_propagates() -> None:
    """编程错误（非超时/API错误）应向上抛出，不被静默（P0修复）"""
    mock_client = MagicMock()
    mock_client.chat.completions.parse = AsyncMock(
        side_effect=AttributeError("broken mock attribute")
    )

    with pytest.raises(AttributeError, match="broken mock attribute"):
        await validate_result(
            client=mock_client,
            model="gpt-4o-mini",
            user_query="test",
            sql="SELECT 1",
            sample_rows=[[1]],
            columns=["n"],
        )
