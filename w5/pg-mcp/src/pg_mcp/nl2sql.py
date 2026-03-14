from __future__ import annotations

from openai import AsyncOpenAI
from pydantic import BaseModel

from pg_mcp.models import TableSchema


# P1修复: 使用 {schema_text} 作为占位符标记，但替换时用 str.replace 而非 str.format
_SCHEMA_PLACEHOLDER = "{schema_text}"

NL2SQL_SYSTEM_PROMPT_TEMPLATE = """\
You are a PostgreSQL SQL expert. Generate ONLY a valid SQL SELECT statement.

Rules:
1. Output ONLY a SQL SELECT statement — no explanations, no markdown, no code blocks
2. Use ONLY tables and columns that exist in the schema provided below
3. Do NOT include SQL comments (-- or /* */)
4. Do NOT generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or TRUNCATE
5. If the query requires a JOIN, use the foreign key relationships shown in the schema

Database Schema:
{schema_text}
"""


class SQLOutput(BaseModel):
    sql: str


async def generate_sql(
    client: AsyncOpenAI,
    model: str,
    user_query: str,
    schema_text: str,
) -> str:
    """调用 OpenAI 将自然语言查询转换为 SQL。"""
    # P1修复: str.replace 防止 schema_text 中的 {...} 破坏格式化
    system_prompt = NL2SQL_SYSTEM_PROMPT_TEMPLATE.replace(_SCHEMA_PLACEHOLDER, schema_text)

    response = await client.chat.completions.parse(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        response_format=SQLOutput,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("OpenAI returned null parsed response (possibly filtered by safety policy)")
    return parsed.sql


def build_schema_text(tables: list[TableSchema]) -> str:
    """将 TableSchema 列表转为 LLM Prompt 文本"""
    if not tables:
        return "(no schema available)"
    return "\n\n".join(t.to_prompt_text() for t in tables)
