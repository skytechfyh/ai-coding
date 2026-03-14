from __future__ import annotations

import sqlglot
from sqlglot import exp


def validate_sql(sql: str, max_rows: int = 1000) -> tuple[str, str | None]:
    """
    四层 SQL 验证并注入 LIMIT 上限。

    Returns:
        (validated_sql, error_message) — error_message is None on success.
    """
    raw = sql.strip()

    # Layer 1: 注释检测（LLM 不应生成注释）
    # 注意：这是简单字符串检测，对字符串字面量中的 "--" 有误报风险
    # 但通过 Prompt 约束 LLM 不生成注释，实际误报极少
    if "--" in raw or "/*" in raw:
        return "", "SQL comments are not allowed"

    # Layer 2: AST 解析 + 多语句检测
    clean = raw.rstrip(";")
    try:
        statements = sqlglot.parse(clean, dialect="postgres")
    except sqlglot.errors.ParseError as e:
        return "", f"SQL parse error: {e}"

    if not statements:
        return "", "Empty SQL"
    if len(statements) > 1:
        return "", f"Multiple statements not allowed ({len(statements)} found)"

    # Layer 3: 只允许 SELECT
    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        return "", f"Only SELECT is allowed (got {type(stmt).__name__})"

    # Layer 4: 注入 LIMIT（用链式 API，修正 D-10）
    if stmt.find(exp.Limit) is None:
        stmt = stmt.limit(max_rows)

    return stmt.sql(dialect="postgres"), None
