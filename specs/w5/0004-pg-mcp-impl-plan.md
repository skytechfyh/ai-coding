# Implementation Plan: pg-mcp

**版本**: 1.0
**日期**: 2026-03-14
**基于设计**: `./specs/w5/0002-pg-mcp-design.md`

---

## 设计文档问题清单（实现前需修正）

在正式实施前，以下设计文档中的问题必须在实现层面修正：

| # | 位置 | 问题描述 | 修正方案 |
|---|------|---------|---------|
| D-01 | `schema_cache.py` § 6 | `columns=[c for c in columns if c.startswith(full_name)]` — `c` 是 `ColumnInfo` 对象而非字符串，`startswith` 调用会 `AttributeError` | 改为按 `(schema_name, table_name)` 分组的中间 dict，再映射到 `TableSchema` |
| D-02 | `schema_cache.py` § 6 | `[i for i in indexes if i.table == full_name]` — `IndexInfo` 模型中没有 `table` 字段 | `_fetch_indexes` 返回带 `(schema, table, ...)` 的临时结构，组装时 filter，不污染最终模型 |
| D-03 | `server.py` § 11 | `refresh_schema` 中 `targets = [_config.databases[0]]` — 当 `database` 有值时应按 alias 查找而非取第一个 | 改为 `next(db for db in _config.databases if db.alias == database)` |
| D-04 | `server.py` § 11 | `_resolve_cache` 末尾注释 `多 DB 时合并 Schema（v2）`，当前返回 `available[0]` 但没有跨库查询能力说明 | v1 限定为"若未指定 database 且有多个 DB 则返回第一个，并在 tool 描述中说明" |
| D-05 | `db_executor.py` § 7 | `SET statement_timeout = '{timeout_seconds * 1000}'` — PostgreSQL SET 数字参数不需要字符串引号，应为 `f"SET statement_timeout = {int(timeout_seconds * 1000)}"` | 去掉引号；改用整数毫秒 |
| D-06 | `db_executor.py` § 7 | 零行结果处理时重新 `pool.acquire()` 二次连接，但 `elapsed_ms` 在第一次 fetch 之后计算，第二次 prepare 的耗时未计入 | 将 prepare 逻辑合并进第一次 `acquire` 块内 |
| D-07 | `config.py` § 4 | `pydantic-settings` 的 `yaml_file` 需要额外安装 `pydantic-settings[yaml]`，设计文档依赖清单未体现 | `pyproject.toml` 改为 `pydantic-settings[yaml]>=2.0` |
| D-08 | `server.py` § 11 | FastMCP `lifespan` 签名：设计中为无参数 `async def lifespan():`，但 FastMCP >= 2.x 的 lifespan 接受 `app` 参数 | 实现时查阅当前 mcp 版本 API，按实际签名编写 |
| D-09 | `nl2sql.py` § 9 | `client.beta.chat.completions.parse()` 在 `openai>=1.50` 中已移至 `client.chat.completions.parse()` （beta 前缀废弃）| 实现时根据安装的 openai 版本选择正确路径，加版本注释 |
| D-10 | `validate_sql` § 8 | 设计中 LIMIT 注入使用 `stmt.set("limit", ...)` 后直接 `stmt.sql()`，但 sqlglot 的 Select 节点 `set()` 方法修改的是属性名 `"limit"`，需确认 API 正确性 | 实现时用 `stmt = stmt.limit(max_rows)` 替代，这是 sqlglot 推荐链式 API |

---

## 实施阶段总览

```
Phase 0 ─ 脚手架         (T-01)          ← 无依赖
Phase 1 ─ 基础层         (T-02, T-03)    ← 依赖 Phase 0
Phase 2 ─ 工具层         (T-04, T-05)    ← 依赖 Phase 1
Phase 3 ─ 数据层         (T-06, T-07)    ← 依赖 Phase 1
Phase 4 ─ AI 层          (T-08, T-09)    ← 依赖 Phase 1
Phase 5 ─ Server 集成    (T-10)          ← 依赖 T-04~T-09
Phase 6 ─ 测试           (T-11, T-12)    ← 依赖 T-02~T-10
```

---

## Task T-01: 项目脚手架

**文件**: `pyproject.toml`, `config.yaml.example`, `src/pg_mcp/__init__.py`, `tests/conftest.py`
**依赖**: 无
**预计工作量**: 小

### 实现要点

**pyproject.toml** — 修正 D-07，添加 yaml extra：

```toml
[project]
name = "pg-mcp"
version = "0.1.0"
description = "PostgreSQL MCP Server — Natural language to SQL"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.8.0",
    "asyncpg>=0.29",
    "openai>=1.30.0",
    "sqlglot>=23.0",
    "pydantic>=2.0",
    "pydantic-settings[yaml]>=2.0",  # [yaml] extra 必须
    "pyyaml>=6.0",
]

[project.scripts]
pg-mcp = "pg_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.3",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**目录创建**:

```
src/pg_mcp/__init__.py     # 空文件
tests/__init__.py           # 空文件
tests/conftest.py           # pytest fixtures（见 T-11）
```

### 验收标准
- [ ] `uv sync` 无错误
- [ ] `uv run python -c "import pg_mcp"` 成功
- [ ] `uv run pytest --collect-only` 无 import 错误

---

## Task T-02: 数据模型（models.py）

**文件**: `src/pg_mcp/models.py`
**依赖**: T-01
**预计工作量**: 中

### 实现要点

全部 Pydantic V2 模型，按以下顺序定义以避免前向引用：

1. **基础信息模型**（无内部依赖）
   - `ColumnInfo`, `IndexInfo`, `ForeignKeyInfo`, `CustomTypeInfo`

2. **TableSchema** — 包含 `to_prompt_text()` 和 `relevance_score()` 方法
   - `to_prompt_text()` 格式参见设计 §5.1，注意处理 `columns` 为空的边界情况
   - `relevance_score()` 停用词应同时包含中文常见词（如：查询、所有、找到）

3. **DatabaseSchemaCache**
   - `get_relevant_tables()` 补 FK 关联表时防止无限循环（FK 可能互指）
   - 正确实现：先计算 top_names set，再一次性补充直接 FK 关联

4. **MCP Tool I/O 模型** — 全部使用 `ConfigDict(alias_generator=to_camel, populate_by_name=True)`

5. **内部服务模型** — `SQLOutput`, `ValidationResult`, `ExecutionResult`（不需要 camelCase）

**关键实现细节 - `get_relevant_tables` 的 FK 补充**:

```python
def get_relevant_tables(self, query: str, max_tables: int = 20) -> list[TableSchema]:
    stop_words = {
        # 英文
        "the", "a", "an", "of", "in", "for", "by", "with", "from",
        "get", "find", "show", "list", "all", "me",
        # 中文常见查询词
        "查询", "所有", "找到", "显示", "列出", "获取", "的", "中", "在",
    }
    keywords = {w.lower() for w in query.split() if w.lower() not in stop_words}

    scored = sorted(
        self.tables.values(),
        key=lambda t: t.relevance_score(keywords),
        reverse=True,
    )
    top = list(scored[:max_tables])

    # 补入 FK 关联表（只扩展一层，避免无限递归）
    top_names = {t.full_name for t in top}
    for table in list(top):  # 遍历原 top，不遍历补入的新表
        for fk in table.foreign_keys:
            if fk.foreign_table not in top_names and fk.foreign_table in self.tables:
                top.append(self.tables[fk.foreign_table])
                top_names.add(fk.foreign_table)

    return top
```

### 验收标准
- [ ] 所有模型可正确实例化
- [ ] `model_dump(by_alias=True)` 输出 camelCase 键名（仅 I/O 模型）
- [ ] `TableSchema.to_prompt_text()` 输出符合设计格式
- [ ] `get_relevant_tables()` 在 FK 互指时不死循环

---

## Task T-03: 配置管理（config.py）

**文件**: `src/pg_mcp/config.py`, `config.yaml.example`
**依赖**: T-01
**预计工作量**: 小

### 实现要点

```python
from __future__ import annotations
from pydantic import BaseModel, SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):        # 注意：BaseModel 不是 BaseSettings
    alias: str
    host: str = "localhost"
    port: int = 5432
    dbname: str
    user: str
    password: SecretStr
    schemas: list[str] = Field(default_factory=lambda: ["public"])
    min_pool_size: int = 1
    max_pool_size: int = 5

    @property
    def dsn(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql://{self.user}:{pwd}@{self.host}:{self.port}/{self.dbname}"
```

**注意**:
- `schemas` 默认值必须用 `Field(default_factory=...)` 而非 `Field(default=[...])` 避免可变默认值共享
- `AppConfig` 加载顺序：环境变量 > `.env` > `config.yaml`（pydantic-settings 默认行为）
- 若 `config.yaml` 不存在，pydantic-settings 不报错（graceful fallback）
- `yaml_file` 路径支持通过 `PG_MCP_CONFIG` 环境变量覆盖，实现方式：在 `main()` 中解析 `--config` 参数后动态构建 `AppConfig`

**CLI 参数支持**（在 server.py 的 `main()` 中实现）:

```python
import argparse, os

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    os.environ.setdefault("PG_MCP__YAML_FILE", args.config)  # 传给 pydantic-settings
    mcp.run(transport="stdio")
```

### 验收标准
- [ ] `AppConfig()` 从 `config.yaml` 正确加载
- [ ] `OPENAI__API_KEY=xxx` 环境变量覆盖生效
- [ ] `dsn` property 不在日志中暴露密码（SecretStr 保护）

---

## Task T-04: SQL 验证器（sql_validator.py）

**文件**: `src/pg_mcp/sql_validator.py`
**依赖**: T-01（无模型依赖）
**预计工作量**: 小

### 实现要点

修正 D-10，使用 sqlglot 推荐的链式 API 注入 LIMIT：

```python
import sqlglot
from sqlglot import exp


def validate_sql(sql: str, max_rows: int = 1000) -> tuple[str, str | None]:
    """
    四层 SQL 验证并注入 LIMIT 上限。
    Returns: (validated_sql, error_message)
    error_message is None on success.
    """
    raw = sql.strip()

    # Layer 1: 注释检测（LLM 不应生成注释）
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

    # Layer 4: 注入 LIMIT（用链式 API，更可靠）
    if stmt.find(exp.Limit) is None:
        stmt = stmt.limit(max_rows)

    return stmt.sql(dialect="postgres"), None
```

**边界情况**:
- `WITH ... SELECT` (CTE)：sqlglot 将其解析为 `exp.Select`，通过验证 ✓
- `SELECT` inside `UNION`：整体仍是 `exp.Select`，通过验证 ✓
- `SELECT` into 变量：PostgreSQL 语法 `SELECT INTO`，sqlglot 解析为 `exp.Create`，被正确拒绝 ✓

### 验收标准
- [ ] `SELECT * FROM users` → 通过，输出带 LIMIT
- [ ] `SELECT * FROM users LIMIT 5` → 通过，LIMIT 不被覆盖（已有 LIMIT 时不注入）
- [ ] `SELECT * FROM users; DELETE FROM users` → 拒绝（多语句）
- [ ] `INSERT INTO t VALUES (1)` → 拒绝
- [ ] `SELECT * FROM users -- comment` → 拒绝（注释）
- [ ] `WITH cte AS (SELECT 1) SELECT * FROM cte` → 通过

---

## Task T-05: Schema 发现与缓存（schema_cache.py）

**文件**: `src/pg_mcp/schema_cache.py`
**依赖**: T-02, T-03
**预计工作量**: 大（最复杂）

### 实现要点

修正 D-01、D-02：使用中间临时结构分离 fetch 与组装，避免模型字段污染。

**总体结构**:

```python
import asyncpg
from dataclasses import dataclass
from pg_mcp.models import (
    ColumnInfo, IndexInfo, ForeignKeyInfo,
    CustomTypeInfo, TableSchema, DatabaseSchemaCache,
)
from pg_mcp.config import DatabaseConfig
from datetime import datetime, UTC


# ── 内部临时结构（不暴露到外部）────────────────────────────────────────────

@dataclass
class _RawTable:
    schema_name: str
    table_name: str
    table_type: str       # "BASE TABLE" | "VIEW"
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
```

**组装逻辑**（修正 D-01、D-02）:

```python
async def load_schema(db: DatabaseConfig) -> DatabaseSchemaCache:
    conn = await asyncpg.connect(
        dsn=db.dsn,
        server_settings={
            "default_transaction_read_only": "true",
            "statement_timeout": "10000",
        },
    )
    try:
        raw_tables = await _fetch_tables(conn, db.schemas)
        raw_columns = await _fetch_columns(conn, db.schemas)
        raw_indexes = await _fetch_indexes(conn, db.schemas)
        raw_fkeys = await _fetch_foreign_keys(conn, db.schemas)
        raw_types = await _fetch_custom_types(conn, db.schemas)

        # 按 (schema, table) 分组 columns
        cols_by_table: dict[tuple[str, str], list[_RawColumn]] = {}
        for col in raw_columns:
            key = (col.schema_name, col.table_name)
            cols_by_table.setdefault(key, []).append(col)

        # 按 (schema, table) 分组 indexes
        idx_by_table: dict[tuple[str, str], list[_RawIndex]] = {}
        for idx in raw_indexes:
            key = (idx.schema_name, idx.table_name)
            idx_by_table.setdefault(key, []).append(idx)

        # 按 (schema, table) 分组 foreign keys
        fk_by_table: dict[tuple[str, str], list[_RawForeignKey]] = {}
        for fk in raw_fkeys:
            key = (fk.schema_name, fk.table_name)
            fk_by_table.setdefault(key, []).append(fk)

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
            alias=db.alias, host=db.host, dbname=db.dbname,
            tables=table_map,
            custom_types=[
                CustomTypeInfo(
                    schema_name=t["schema_name"],
                    type_name=t["type_name"],
                    type_category="enum",
                    enum_values=list(t["enum_values"]),
                )
                for t in raw_types
            ],
            cached_at=datetime.now(UTC),
            is_available=True,
        )
    except Exception as e:
        return DatabaseSchemaCache(
            alias=db.alias, host=db.host, dbname=db.dbname,
            tables={}, custom_types=[], cached_at=datetime.now(UTC),
            is_available=False, error_message=str(e),
        )
    finally:
        await conn.close()
```

**Index 查询注意事项**:

设计文档中的 index SQL 使用了 `array_position(ix.indkey, a.attnum)`，但 `array_position` 要求 `ix.indkey` 为 integer[]，而 `pg_index.indkey` 是 `int2vector` 类型，需要转换：

```sql
SELECT pi.schemaname, pi.tablename, pi.indexname,
       ix.indisunique AS is_unique,
       array_agg(a.attname ORDER BY k.pos) AS columns
FROM pg_indexes pi
JOIN pg_class ic ON ic.relname = pi.indexname AND ic.relnamespace = (
    SELECT oid FROM pg_namespace WHERE nspname = pi.schemaname
)
JOIN pg_index ix ON ix.indexrelid = ic.oid
JOIN pg_class tc ON tc.relname = pi.tablename AND tc.relnamespace = ic.relnamespace
CROSS JOIN LATERAL unnest(ix.indkey::int[]) WITH ORDINALITY AS k(attnum, pos)
JOIN pg_attribute a ON a.attrelid = tc.oid AND a.attnum = k.attnum AND a.attnum > 0
WHERE pi.schemaname = ANY($1)
  AND NOT ix.indisprimary  -- 可选：排除主键索引减少噪音
GROUP BY pi.schemaname, pi.tablename, pi.indexname, ix.indisunique;
```

### 验收标准
- [ ] 对含 tables/views/indexes/FK/enum 的测试 DB 能正确加载 Schema
- [ ] 列信息、索引列顺序正确
- [ ] 数据库连接失败时返回 `is_available=False` 的 cache，不抛出异常
- [ ] 多个 schema（如 `public` + `analytics`）都能加载

---

## Task T-06: asyncpg 连接池与查询执行（db_executor.py）

**文件**: `src/pg_mcp/db_executor.py`
**依赖**: T-02, T-03
**预计工作量**: 中

### 实现要点

修正 D-05、D-06：

```python
import time
import asyncpg
from asyncpg import Pool
from pg_mcp.config import DatabaseConfig
from pg_mcp.models import ExecutionResult


async def create_pool(db: DatabaseConfig) -> Pool:
    return await asyncpg.create_pool(
        dsn=db.dsn,
        min_size=db.min_pool_size,
        max_size=db.max_pool_size,
        server_settings={
            "default_transaction_read_only": "true",
        },
    )


async def execute_query(
    pool: Pool,
    sql: str,
    limit: int,
    timeout_seconds: int,
) -> ExecutionResult:
    start = time.monotonic()

    async with pool.acquire() as conn:
        # 修正 D-05: 整数毫秒，无引号
        await conn.execute(f"SET statement_timeout = {int(timeout_seconds * 1000)}")

        try:
            records = await conn.fetch(sql, timeout=float(timeout_seconds))
        except asyncpg.exceptions.QueryCanceledError:
            raise TimeoutError(f"Query timed out after {timeout_seconds}s")

        elapsed_ms = (time.monotonic() - start) * 1000

        if not records:
            # 修正 D-06: 在同一 acquire 块内处理零行结果
            stmt = await conn.prepare(sql)
            columns = [attr.name for attr in stmt.get_attributes()]
            return ExecutionResult(
                columns=columns, rows=[], row_count=0,
                execution_time_ms=elapsed_ms,
            )

        columns = list(records[0].keys())
        rows = [list(r.values()) for r in records[:limit]]

    return ExecutionResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=(time.monotonic() - start) * 1000,
    )
```

**LIMIT 双重限制说明**:

- sqlglot 在 SQL 中注入的 LIMIT 是 `max_result_rows`（默认 1000）— 数据库执行层面的上限
- `execute_query` 的 `limit` 参数是工具调用时的 `limit`（默认 100）— Python 层面的截断
- 因此：数据库最多返回 1000 行，Python 再截断到用户指定的 limit

这两层是互补而非重复：一个控制 DB I/O，一个控制 tool 响应大小。实现时 `validate_sql(sql, max_rows=config.server.max_result_rows)` 而 `execute_query(..., limit=tool_limit)`。

**asyncpg Row values 序列化**:

asyncpg 的 `Record` 值可能包含不可 JSON 序列化的类型（datetime、Decimal、UUID 等）。需要在 `rows` 列表构建时转换：

```python
import decimal
from datetime import date, datetime

def _serialize_value(v: object) -> object:
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (bytes, memoryview)):
        return "<binary>"
    return v

rows = [[_serialize_value(v) for v in r.values()] for r in records[:limit]]
```

### 验收标准
- [ ] 正常查询返回正确的 columns + rows
- [ ] 零行查询返回 `rows=[]` 及正确 columns（通过 prepare 获取）
- [ ] `statement_timeout` 触发后抛出 `TimeoutError`
- [ ] datetime/Decimal 类型正确序列化

---

## Task T-07: NL2SQL 服务（nl2sql.py）

**文件**: `src/pg_mcp/nl2sql.py`
**依赖**: T-02
**预计工作量**: 小

### 实现要点

修正 D-09，兼容 `openai>=1.50`（`beta` 前缀已废弃）：

```python
from openai import AsyncOpenAI
from pydantic import BaseModel
from pg_mcp.models import TableSchema


NL2SQL_SYSTEM_PROMPT = """\
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
    response = await client.chat.completions.parse(   # openai>=1.50 去掉 beta
        model=model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": NL2SQL_SYSTEM_PROMPT.format(schema_text=schema_text),
            },
            {"role": "user", "content": user_query},
        ],
        response_format=SQLOutput,
    )
    parsed = response.choices[0].message.parsed
    if parsed is None:
        raise ValueError("OpenAI returned null parsed response")
    return parsed.sql


def build_schema_text(tables: list[TableSchema]) -> str:
    if not tables:
        return "(no schema available)"
    return "\n\n".join(t.to_prompt_text() for t in tables)
```

**parsed is None 边界情况**: 当 OpenAI 因安全过滤拒绝输出时，`parsed` 可能为 `None`。需显式检查并抛出 `ValueError` 供上层捕获。

### 验收标准
- [ ] 正常输入返回合法 SQL 字符串
- [ ] `parsed is None` 时抛出 `ValueError`
- [ ] `schema_text` 为空时使用占位符字符串（不崩溃）

---

## Task T-08: 结果验证服务（result_validator.py）

**文件**: `src/pg_mcp/result_validator.py`
**依赖**: T-02
**预计工作量**: 小

### 实现要点

```python
import asyncio
from openai import AsyncOpenAI
from pydantic import BaseModel
from pg_mcp.models import ValidationInfo


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
    if not sample_rows:
        # 空结果集：直接判定为不有意义（或无数据）
        return ValidationInfo(
            is_meaningful=False,
            explanation="查询返回零行结果，可能查询条件过于严格或数据不存在。",
        )

    sample_text = f"Columns: {columns}\nSample rows (first {len(sample_rows)}):\n"
    sample_text += "\n".join(str(row) for row in sample_rows)
    user_msg = f"User query: {user_query}\n\nGenerated SQL:\n{sql}\n\nQuery results:\n{sample_text}"

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
    except (asyncio.TimeoutError, Exception):
        return ValidationInfo(
            is_meaningful=False,
            explanation="",
            validation_skipped=True,
        )
```

**空结果集处理**: 零行结果时跳过 OpenAI 调用，直接返回 `is_meaningful=False` 并给出中文说明。

### 验收标准
- [ ] 正常情况返回 `ValidationInfo` 含中文 explanation
- [ ] OpenAI 超时时返回 `validation_skipped=True`
- [ ] 空结果集时不调用 OpenAI，直接返回 `is_meaningful=False`

---

## Task T-09: MCP Server 入口（server.py）

**文件**: `src/pg_mcp/server.py`
**依赖**: T-03, T-04, T-05, T-06, T-07, T-08
**预计工作量**: 中

### 实现要点

修正 D-03、D-04、D-08：

**lifespan 签名** — 检查实际 FastMCP API：

```python
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP

# FastMCP lifespan 接受 FastMCP 实例或无参数，视版本而定
# 安全写法：使用 @asynccontextmanager 并接受可选参数
@asynccontextmanager
async def lifespan(app: FastMCP):   # 若报错改为 async def lifespan():
    ...
    yield
    ...
```

**_resolve_cache 修正** (D-03, D-04):

```python
def _resolve_cache(database: str | None) -> DatabaseSchemaCache:
    if database is not None:
        cache = _caches.get(database)
        if cache is None:
            available = list(_caches.keys())
            raise ValueError(
                f"Database '{database}' not found. Available: {available}"
            )
        if not cache.is_available:
            raise RuntimeError(
                f"Database '{database}' is unavailable: {cache.error_message}"
            )
        return cache

    # 未指定 database：使用唯一可用库，否则报错要求明确指定
    available = [c for c in _caches.values() if c.is_available]
    if not available:
        raise RuntimeError("No available databases")
    if len(available) == 1:
        return available[0]
    # 多个可用库时要求用户明确指定
    names = [c.alias for c in available]
    raise ValueError(
        f"Multiple databases available ({names}). "
        "Please specify the 'database' parameter."
    )
```

**refresh_schema 修正** (D-03):

```python
@mcp.tool()
async def refresh_schema(database: str | None = None) -> dict[str, Any]:
    """手动刷新一个或所有数据库的 Schema 缓存。

    Args:
        database: 要刷新的数据库别名。不填则刷新全部。
    """
    import time

    if database is not None:
        # 修正 D-03: 按 alias 查找
        targets = [db for db in _config.databases if db.alias == database]
        if not targets:
            return {"errorCode": "NOT_FOUND", "message": f"Database '{database}' not found"}
    else:
        targets = list(_config.databases)

    ...
```

**错误处理统一**：tool 函数中所有 `ValueError` 和 `RuntimeError` 统一捕获并返回错误字典：

```python
@mcp.tool()
async def query_to_sql(query: str, database: str | None = None) -> dict[str, Any]:
    """..."""
    try:
        cache = _resolve_cache(database)
    except (ValueError, RuntimeError) as e:
        return {"errorCode": "NO_DATABASE_AVAILABLE", "message": str(e)}

    try:
        relevant_tables = cache.get_relevant_tables(query, max_tables=20)
        schema_text = build_schema_text(relevant_tables)
        sql = await generate_sql(_openai, _config.openai.model, query, schema_text)
    except Exception as e:
        return {"errorCode": "LLM_ERROR", "message": f"Failed to generate SQL: {e}"}

    validated_sql, err = validate_sql(sql, _config.server.max_result_rows)
    if err:
        return {"errorCode": "VALIDATION_FAILED", "message": err}

    return QueryToSqlOutput(
        sql=validated_sql,
        database=cache.alias,
        schema_used=[t.full_name for t in relevant_tables],
    ).model_dump(by_alias=True)
```

### 验收标准
- [ ] `mcp.run(transport="stdio")` 正常启动，日志输出到 stderr
- [ ] lifespan 中 Schema 加载失败不阻塞 server 启动（返回 is_available=False）
- [ ] 多 DB 且未指定 database 时返回明确错误信息
- [ ] refresh_schema 按 alias 正确定位目标 DB
- [ ] Graceful shutdown 关闭所有连接池

---

## Task T-10: 集成连线验证（smoke test）

**文件**: `tests/test_smoke.py`
**依赖**: T-09（所有组件）
**预计工作量**: 小

### 目标

验证各模块正确导入、连线无误，无需真实 PG/OpenAI 连接。

```python
# 验证导入链路无循环依赖
from pg_mcp.models import TableSchema, DatabaseSchemaCache
from pg_mcp.config import AppConfig
from pg_mcp.sql_validator import validate_sql
from pg_mcp.nl2sql import build_schema_text
from pg_mcp.server import mcp
```

---

## Task T-11: 单元测试

**文件**: `tests/test_sql_validator.py`, `tests/test_models.py`, `tests/test_nl2sql.py`, `tests/test_result_validator.py`
**依赖**: T-02~T-08

### test_sql_validator.py（纯函数，无 mock 需求）

```python
import pytest
from pg_mcp.sql_validator import validate_sql

PASS_CASES = [
    ("SELECT * FROM users", True),
    ("SELECT id, name FROM orders WHERE status = 'active'", True),
    ("SELECT * FROM users LIMIT 5", True),                       # 已有 LIMIT 不被覆盖
    ("WITH cte AS (SELECT 1 AS n) SELECT * FROM cte", True),    # CTE
    ("SELECT a.id FROM users a JOIN orders b ON a.id = b.uid",  True),
]

FAIL_CASES = [
    ("INSERT INTO users VALUES (1, 'x')", "Only SELECT"),
    ("UPDATE users SET name='x'", "Only SELECT"),
    ("DROP TABLE users", "Only SELECT"),
    ("SELECT * FROM users; DELETE FROM users", "Multiple"),
    ("SELECT * FROM users -- comment", "comments"),
    ("SELECT * FROM users /* block */", "comments"),
    ("", "Empty SQL"),
]

@pytest.mark.parametrize("sql, expected_pass", PASS_CASES)
def test_valid_sql(sql: str, expected_pass: bool):
    _, err = validate_sql(sql)
    assert err is None

@pytest.mark.parametrize("sql, err_substring", FAIL_CASES)
def test_invalid_sql(sql: str, err_substring: str):
    _, err = validate_sql(sql)
    assert err is not None
    assert err_substring.lower() in err.lower()

def test_limit_injection():
    out, _ = validate_sql("SELECT * FROM t", max_rows=50)
    assert "LIMIT 50" in out.upper()

def test_existing_limit_preserved():
    out, _ = validate_sql("SELECT * FROM t LIMIT 5", max_rows=1000)
    assert "LIMIT 5" in out.upper()
    assert "LIMIT 1000" not in out.upper()
```

### test_models.py

```python
def test_table_schema_to_prompt_text():
    # 验证 to_prompt_text 格式正确

def test_get_relevant_tables_keyword_matching():
    # 包含 "users" 关键词时，users 表应排在最前

def test_get_relevant_tables_fk_expansion():
    # users 表的 FK 指向 orders 时，orders 也应被包含

def test_get_relevant_tables_no_infinite_loop():
    # 两张表互相 FK 时不应死循环
```

### test_nl2sql.py（需 mock OpenAI）

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pg_mcp.nl2sql import generate_sql, build_schema_text

@pytest.mark.asyncio
async def test_generate_sql_success():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed.sql = "SELECT * FROM users"
    mock_client.chat.completions.parse.return_value = mock_response

    result = await generate_sql(mock_client, "gpt-4o-mini", "all users", "Table: public.users\n  ...")
    assert result == "SELECT * FROM users"

@pytest.mark.asyncio
async def test_generate_sql_null_parsed():
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices[0].message.parsed = None
    mock_client.chat.completions.parse.return_value = mock_response

    with pytest.raises(ValueError):
        await generate_sql(mock_client, "gpt-4o-mini", "query", "schema")
```

### 验收标准
- [ ] `uv run pytest tests/test_sql_validator.py` 全部通过
- [ ] `uv run pytest tests/test_models.py` 全部通过
- [ ] `uv run pytest tests/test_nl2sql.py` 全部通过（mock）

---

## Task T-12: 集成测试（需真实 PG + OpenAI）

**文件**: `tests/test_integration.py`, `tests/conftest.py`
**依赖**: T-11
**预计工作量**: 中

### conftest.py

```python
import pytest
import asyncpg
import os

@pytest.fixture(scope="session")
def pg_dsn():
    dsn = os.environ.get("TEST_PG_DSN")
    if not dsn:
        pytest.skip("TEST_PG_DSN not set")
    return dsn

@pytest.fixture(scope="session")
async def pg_pool(pg_dsn):
    pool = await asyncpg.create_pool(pg_dsn, server_settings={
        "default_transaction_read_only": "true",
    })
    yield pool
    await pool.close()
```

### test_integration.py

```python
@pytest.mark.integration
async def test_schema_load(pg_dsn):
    from pg_mcp.config import DatabaseConfig
    from pg_mcp.schema_cache import load_schema
    from pydantic import SecretStr

    db = DatabaseConfig(alias="test", host="...", dbname="...", user="...",
                        password=SecretStr("..."), schemas=["public"])
    cache = await load_schema(db)
    assert cache.is_available
    assert cache.table_count > 0

@pytest.mark.integration
async def test_execute_query(pg_pool):
    from pg_mcp.db_executor import execute_query
    result = await execute_query(pg_pool, "SELECT 1 AS n", limit=10, timeout_seconds=5)
    assert result.columns == ["n"]
    assert result.rows == [[1]]

@pytest.mark.integration
async def test_full_pipeline():
    # 端到端：自然语言 → SQL → 执行 → 验证
    ...
```

**运行集成测试**:

```bash
TEST_PG_DSN="postgresql://user:pass@localhost/testdb" \
OPENAI_API_KEY=sk-... \
uv run pytest tests/test_integration.py -m integration -v
```

---

## 实施顺序与依赖图

```
T-01 (脚手架)
  ├── T-02 (models)
  │     ├── T-04 (sql_validator) ──────────────────────────────────────┐
  │     ├── T-05 (schema_cache)  ───────────────────────────────────┐  │
  │     ├── T-06 (db_executor)   ─────────────────────────────────┐ │  │
  │     ├── T-07 (nl2sql)        ───────────────────────────────┐  │ │  │
  │     └── T-08 (result_validator) ─────────────────────────┐  │  │ │  │
  └── T-03 (config)                                          │  │  │ │  │
        ├── T-05 (schema_cache)  ─────────────────────────┘  │  │ │  │
        └── T-06 (db_executor)   ──────────────────────────┘  │  │ │  │
                                                               │  │ │  │
  T-09 (server) ←──────────────────────────────────────────────┘  └─┘  └─┘
        │
  T-10 (smoke test)
        │
  T-11 (unit tests) ── T-12 (integration tests)
```

**推荐实施顺序**: T-01 → T-02 → T-03 → T-04 → T-07 → T-08 → T-05 → T-06 → T-09 → T-10 → T-11 → T-12

理由：先完成无 I/O 依赖的纯逻辑层（T-02~T-04, T-07, T-08），再处理需要 DB 连接的复杂层（T-05, T-06），最后集成组装（T-09）。

---

## 潜在风险与应对

| 风险 | 可能性 | 影响 | 应对方案 |
|------|--------|------|---------|
| asyncpg `get_attributes()` 在某些 PG 版本返回空 | 低 | 零行查询列名缺失 | 回退到执行 `SELECT * FROM (...) sub LIMIT 0` 再取 description |
| openai SDK 版本 `beta` vs 正式路径不一致 | 中 | `AttributeError` | 启动时检测 openai 版本，选择正确路径；或统一用 `try/except` |
| pydantic-settings yaml_file 路径解析问题 | 中 | 配置加载失败 | 实现自定义 YAML 加载 fallback（手动 `yaml.safe_load` + `AppConfig.model_validate()`） |
| FastMCP lifespan API 变更 | 低 | server 启动失败 | 实现时确认 `mcp` 包版本对应的 lifespan 签名 |
| LLM 生成包含注释的 SQL（`/* */`） | 中 | 被 layer-1 拒绝 | Prompt 中明确禁止，若触发频率高可在 `generate_sql` 后预处理去除注释再验证 |
| 大型数据库（>500 表）Schema 加载超时 | 低 | 启动失败 | 增加 Schema 加载超时配置项（独立于 query_timeout），默认 60s |

---

## 完成标准（Definition of Done）

- [ ] 所有 T-01 ~ T-09 实现完毕
- [ ] `uv run pytest tests/ -m "not integration"` 全绿
- [ ] `uv run python -m pg_mcp --config config.yaml` 正常启动（可无真实 DB）
- [ ] Claude Code `claude mcp add` 注册后，`list_databases` tool 可调用
- [ ] 集成测试（T-12）在有 PG + OpenAI 的环境下全绿
