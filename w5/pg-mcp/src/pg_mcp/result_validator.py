from __future__ import annotations

import asyncio
import logging

import openai
from openai import AsyncOpenAI
from pydantic import BaseModel

from pg_mcp.models import ValidationInfo

logger = logging.getLogger(__name__)


VALIDATION_SYSTEM_PROMPT = """\
You are a data quality validator. Given:
1. A user's natural language query
2. The SQL that was generated from the query
3. A sample of the query results

Determine whether the results are meaningful and correctly answer the user's intent.

Respond with:
- is_meaningful: true if results answer the user's question, false otherwise
- explanation: brief explanation in Chinese (1-2 sentences)
"""


class _ValidationResult(BaseModel):
    is_meaningful: bool
    explanation: str


async def validate_result(
    client: AsyncOpenAI,
    model: str,
    user_query: str,
    sql: str,
    sample_rows: list[list],
    columns: list[str],
    timeout_seconds: float = 10.0,
) -> ValidationInfo:
    """对查询结果进行语义验证。超时或 OpenAI 错误时返回 validation_skipped=True。"""
    if not sample_rows:
        # P1修复: 空结果集本身不代表查询无意义
        return ValidationInfo(
            is_meaningful=True,
            explanation="查询成功执行，但当前无匹配数据。",
            validation_skipped=False,
        )

    sample_text = f"Columns: {columns}\nSample rows (first {len(sample_rows)}):\n"
    sample_text += "\n".join(str(row) for row in sample_rows)
    user_msg = (
        f"User query: {user_query}\n\n"
        f"Generated SQL:\n{sql}\n\n"
        f"Query results:\n{sample_text}"
    )

    try:
        coro = client.chat.completions.parse(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format=_ValidationResult,
        )
        response = await asyncio.wait_for(coro, timeout=timeout_seconds)
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("null parsed response")
        return ValidationInfo(
            is_meaningful=parsed.is_meaningful,
            explanation=parsed.explanation,
        )
    except asyncio.TimeoutError:
        # 超时是预期情况（验证是可选的），正常跳过
        return ValidationInfo(
            is_meaningful=False,
            explanation="",
            validation_skipped=True,
        )
    except openai.APIError as e:
        # OpenAI 服务端错误，记录日志后跳过（不阻断主流程）
        logger.warning("OpenAI validation call failed: %s", e)
        return ValidationInfo(
            is_meaningful=False,
            explanation="",
            validation_skipped=True,
        )
    # 其他未预期异常（编程错误）继续向上抛出
