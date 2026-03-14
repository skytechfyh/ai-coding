from __future__ import annotations

import re
from typing import Any, Literal
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ── Schema 缓存模型 ─────────────────────────────────────────────────────────

class ColumnInfo(BaseModel):
    name: str
    data_type: str
    is_nullable: bool
    default: str | None = None
    comment: str | None = None


class IndexInfo(BaseModel):
    name: str
    columns: list[str]
    is_unique: bool


class ForeignKeyInfo(BaseModel):
    constraint_name: str
    local_columns: list[str]
    foreign_table: str       # "public.orders"
    foreign_columns: list[str]


class CustomTypeInfo(BaseModel):
    schema_name: str
    type_name: str
    type_category: Literal["enum", "composite", "domain", "other"]
    enum_values: list[str] | None = None


class TableSchema(BaseModel):
    schema_name: str
    table_name: str
    full_name: str
    object_type: Literal["table", "view"]
    columns: list[ColumnInfo]
    indexes: list[IndexInfo]
    foreign_keys: list[ForeignKeyInfo]
    comment: str | None = None

    def to_prompt_text(self) -> str:
        """生成注入 LLM Prompt 的紧凑摘要"""
        if self.columns:
            cols = ", ".join(
                f"{c.name} ({c.data_type}{'?' if c.is_nullable else ''})"
                for c in self.columns
            )
        else:
            cols = "(no columns)"
        lines = [f"Table: {self.full_name}", f"  Columns: {cols}"]
        if self.comment:
            lines.append(f"  Comment: {self.comment}")
        if self.indexes:
            idx = ", ".join(
                f"{i.name}({'UNIQUE ' if i.is_unique else ''}{'+'.join(i.columns)})"
                for i in self.indexes
            )
            lines.append(f"  Indexes: {idx}")
        for fk in self.foreign_keys:
            lines.append(
                f"  FK: {'.'.join(fk.local_columns)} → {fk.foreign_table}.{'.'.join(fk.foreign_columns)}"
            )
        return "\n".join(lines)

    def relevance_score(self, keywords: set[str]) -> int:
        """关键词匹配分数，用于 Schema 裁剪"""
        tokens: set[str] = {self.table_name.lower(), self.schema_name.lower()}
        tokens |= {c.name.lower() for c in self.columns}
        if self.comment:
            tokens |= set(self.comment.lower().split())
        return len(tokens & keywords)


# ── Stop words 模块级常量（P1修复: 避免每次调用重建）────────────────────────

_STOP_WORDS: frozenset[str] = frozenset({
    # 英文
    "the", "a", "an", "of", "in", "for", "by", "with", "from",
    "get", "find", "show", "list", "all", "me",
    # 中文常见查询词
    "查询", "所有", "找到", "显示", "列出", "获取", "的", "中", "在",
})


def _tokenize_query(query: str) -> set[str]:
    """
    P1修复: 支持中文字符级分词。
    英文: 按单词分割；中文: 逐字分割。
    """
    # 英文单词
    en_words = {w.lower() for w in re.findall(r'[a-zA-Z_]\w*', query.lower())}
    # 中文字符（逐字）
    zh_chars = set(re.findall(r'[\u4e00-\u9fff]', query))
    return (en_words | zh_chars) - _STOP_WORDS


class DatabaseSchemaCache(BaseModel):
    alias: str
    host: str
    dbname: str
    tables: dict[str, TableSchema]
    custom_types: list[CustomTypeInfo]
    cached_at: datetime
    is_available: bool = True
    error_message: str | None = None

    @property
    def table_count(self) -> int:
        return len(self.tables)

    def get_relevant_tables(self, query: str, max_tables: int = 20) -> list[TableSchema]:
        """关键词匹配，返回最相关的表，并补入直接 FK 关联表（不递归，防止循环）"""
        keywords = _tokenize_query(query)

        scored = sorted(
            self.tables.values(),
            key=lambda t: t.relevance_score(keywords),
            reverse=True,
        )
        top = list(scored[:max_tables])

        # 补入 FK 关联表（只扩展一层，遍历原 top 防止无限递归）
        top_names = {t.full_name for t in top}
        for table in list(top):  # list(top) 固定原始集合，补入的新表不再被遍历
            for fk in table.foreign_keys:
                if fk.foreign_table not in top_names and fk.foreign_table in self.tables:
                    top.append(self.tables[fk.foreign_table])
                    top_names.add(fk.foreign_table)

        return top


# ── MCP Tool I/O 模型（全部 camelCase）──────────────────────────────────────

class QueryToSqlOutput(BaseModel):
    sql: str
    database: str
    schema_used: list[str]

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ValidationInfo(BaseModel):
    is_meaningful: bool
    explanation: str
    validation_skipped: bool = False

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class QueryToResultOutput(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    validation: ValidationInfo

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DatabaseInfo(BaseModel):
    alias: str
    host: str
    dbname: str
    schema_cached_at: datetime | None = None
    table_count: int
    is_available: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ListDatabasesOutput(BaseModel):
    databases: list[DatabaseInfo]


class RefreshSchemaOutput(BaseModel):
    refreshed: list[str]
    failed: list[str]
    duration_seconds: float

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ── 内部服务模型（不需要 camelCase）─────────────────────────────────────────

class ExecutionResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float


# ── 错误模型 ──────────────────────────────────────────────────────────────

class PgMcpError(BaseModel):
    error_code: str
    message: str
    details: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
