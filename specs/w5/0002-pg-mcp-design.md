# Design: pg-mcp

**版本**: 1.0
**日期**: 2026-03-14
**基于 PRD**: `./specs/w5/0001-pg-mcp-prd.md`
**技术栈**: FastMCP · asyncpg · sqlglot · Pydantic V2 · OpenAI

---

## 1. 技术选型

| 层 | 选型 | 版本 | 理由 |
|----|------|------|------|
| MCP 框架 | `FastMCP` | `mcp[cli]>=1.8.0` | `@mcp.tool()` 自动生成 JSON Schema，`asynccontextmanager` lifespan 支持异步启动初始化 |
| PG 驱动 | `asyncpg` | `>=0.29` | 原生 async-first，内置连接池（`asyncpg.create_pool()`），通过 `server_settings` 在连接层强制只读，零依赖外部池包 |
| SQL 验证 | `sqlglot` | `>=23.0` | AST 级解析，`dialect="postgres"`，可检测多语句/非 SELECT/注入，可自动注入 LIMIT |
| 数据模型 | `Pydantic V2` | `>=2.0` | 类型安全，camelCase JSON 序列化，`pydantic-settings` 统一配置管理 |
| AI 服务 | `AsyncOpenAI` | `openai>=1.30.0` | 异步客户端，Structured Outputs（`.parse()`）保证输出格式 |
| 配置 | `pydantic-settings` + YAML | `>=2.0` | 环境变量覆盖，敏感字段 `SecretStr` |

---

## 2. 项目结构

```
specs/w5/pg-mcp/
├── pyproject.toml
├── config.yaml.example
├── src/
│   └── pg_mcp/
│       ├── __init__.py
│       ├── server.py            # FastMCP 入口，lifespan，4 个 tool 注册
│       ├── config.py            # AppConfig (pydantic-settings)
│       ├── models.py            # 所有 Pydantic 数据模型
│       ├── schema_cache.py      # Schema 发现（asyncpg）与内存缓存
│       ├── nl2sql.py            # OpenAI NL2SQL：Prompt 构建 + structured output
│       ├── sql_validator.py     # sqlglot 四层 SQL 验证
│       ├── db_executor.py       # asyncpg 只读查询执行
│       └── result_validator.py  # OpenAI 结果语义验证
└── tests/
    ├── test_schema_cache.py
    ├── test_sql_validator.py
    ├── test_nl2sql.py
    └── test_result_validator.py
```

---

## 3. 依赖清单（pyproject.toml）

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
    "pydantic-settings>=2.0",
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
```

---

## 4. 配置设计（config.py）

```python
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    alias: str                           # 逻辑别名，如 "main"
    host: str = "localhost"
    port: int = 5432
    dbname: str
    user: str
    password: SecretStr
    schemas: list[str] = Field(default=["public"])  # 要发现的 PG schema 白名单
    min_pool_size: int = 1
    max_pool_size: int = 5

    @property
    def dsn(self) -> str:
        pwd = self.password.get_secret_value()
        return f"postgresql://{self.user}:{pwd}@{self.host}:{self.port}/{self.dbname}"


class OpenAIConfig(BaseModel):
    api_key: SecretStr
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 10.0


class ServerConfig(BaseModel):
    query_timeout_seconds: int = 30
    result_validation_sample_rows: int = 5
    max_result_rows: int = 1000
    auto_retry_on_invalid: bool = False


class AppConfig(BaseSettings):
    databases: list[DatabaseConfig]
    openai: OpenAIConfig
    server: ServerConfig = ServerConfig()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",   # OPENAI__API_KEY=sk-xxx
        yaml_file="config.yaml",
    )
```

**config.yaml.example**:

```yaml
databases:
  - alias: "main"
    host: "localhost"
    port: 5432
    dbname: "mydb"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    schemas: ["public"]

openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o-mini"

server:
  query_timeout_seconds: 30
  result_validation_sample_rows: 5
  max_result_rows: 1000
  auto_retry_on_invalid: false
```

---

## 5. 数据模型（models.py）

Pydantic V2，JSON 序列化使用 camelCase（Constitution §IV）。

### 5.1 Schema 缓存模型

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from typing import Literal, Any
from datetime import datetime


class ColumnInfo(BaseModel):
    name: str
    data_type: str        # "int4" | "text" | "timestamptz" | ...
    is_nullable: bool
    default: str | None
    comment: str | None


class IndexInfo(BaseModel):
    name: str
    columns: list[str]
    is_unique: bool


class ForeignKeyInfo(BaseModel):
    constraint_name: str
    local_columns: list[str]
    foreign_table: str    # "public.orders"
    foreign_columns: list[str]


class TableSchema(BaseModel):
    schema_name: str      # "public"
    table_name: str       # "users"
    full_name: str        # "public.users"
    object_type: Literal["table", "view"]
    columns: list[ColumnInfo]
    indexes: list[IndexInfo]
    foreign_keys: list[ForeignKeyInfo]
    comment: str | None

    def to_prompt_text(self) -> str:
        """生成注入 LLM Prompt 的紧凑摘要"""
        cols = ", ".join(
            f"{c.name} ({c.data_type}{'?' if c.is_nullable else ''})"
            for c in self.columns
        )
        lines = [f"Table: {self.full_name}", f"  Columns: {cols}"]
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
        tokens = {self.table_name.lower(), self.schema_name.lower()}
        tokens |= {c.name.lower() for c in self.columns}
        if self.comment:
            tokens |= set(self.comment.lower().split())
        return len(tokens & keywords)


class CustomTypeInfo(BaseModel):
    schema_name: str
    type_name: str
    type_category: Literal["enum", "composite", "domain", "other"]
    enum_values: list[str] | None


class DatabaseSchemaCache(BaseModel):
    alias: str
    host: str
    dbname: str
    tables: dict[str, TableSchema]     # key: "public.users"
    custom_types: list[CustomTypeInfo]
    cached_at: datetime
    is_available: bool = True
    error_message: str | None = None

    @property
    def table_count(self) -> int:
        return len(self.tables)

    def get_relevant_tables(self, query: str, max_tables: int = 20) -> list[TableSchema]:
        """关键词匹配，返回最相关的表，并补入直接 FK 关联表"""
        stop_words = {"the", "a", "an", "of", "in", "for", "by", "with", "from", "get", "find", "show", "list"}
        keywords = {w.lower() for w in query.split() if w.lower() not in stop_words}

        scored = sorted(
            self.tables.values(),
            key=lambda t: t.relevance_score(keywords),
            reverse=True,
        )
        top = scored[:max_tables]

        # 补入 FK 关联表
        top_names = {t.full_name for t in top}
        for table in list(top):
            for fk in table.foreign_keys:
                if fk.foreign_table not in top_names and fk.foreign_table in self.tables:
                    top.append(self.tables[fk.foreign_table])
                    top_names.add(fk.foreign_table)

        return top
```

### 5.2 MCP Tool 输入/输出模型

```python
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
    schema_cached_at: datetime | None
    table_count: int
    is_available: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RefreshSchemaOutput(BaseModel):
    refreshed: list[str]
    failed: list[str]
    duration_seconds: float

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

### 5.3 内部服务模型（OpenAI structured output）

```python
class SQLOutput(BaseModel):
    """NL2SQL structured output"""
    sql: str

class ValidationResult(BaseModel):
    """Result validation structured output"""
    is_meaningful: bool
    explanation: str

class ExecutionResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
```

---

## 6. Schema 发现（schema_cache.py）

asyncpg 连接配置为**只读**，通过 `server_settings` 在连接层强制禁止写操作：

```python
import asyncio
import asyncpg
from datetime import datetime, UTC


async def load_schema(db: DatabaseConfig) -> DatabaseSchemaCache:
    """连接数据库并发现 Schema，返回 DatabaseSchemaCache"""
    # server_settings 在 session 级别设置只读，statement_timeout 防止慢查询
    conn = await asyncpg.connect(
        dsn=db.dsn,
        server_settings={
            "default_transaction_read_only": "true",
            "statement_timeout": "10000",  # 10s，Schema 加载专用超时
        },
    )
    try:
        schemas_param = db.schemas   # e.g. ["public", "analytics"]
        tables = await _fetch_tables(conn, schemas_param)
        columns = await _fetch_columns(conn, schemas_param)
        indexes = await _fetch_indexes(conn, schemas_param)
        fkeys = await _fetch_foreign_keys(conn, schemas_param)
        custom_types = await _fetch_custom_types(conn, schemas_param)

        # 组装 TableSchema
        table_map: dict[str, TableSchema] = {}
        for row in tables:
            full_name = f"{row['table_schema']}.{row['table_name']}"
            table_map[full_name] = TableSchema(
                schema_name=row["table_schema"],
                table_name=row["table_name"],
                full_name=full_name,
                object_type="view" if row["table_type"] == "VIEW" else "table",
                columns=[c for c in columns if c.startswith(full_name)],  # 简化
                indexes=[i for i in indexes if i.table == full_name],
                foreign_keys=[f for f in fkeys if f.source_table == full_name],
                comment=row.get("table_comment"),
            )

        return DatabaseSchemaCache(
            alias=db.alias,
            host=db.host,
            dbname=db.dbname,
            tables=table_map,
            custom_types=custom_types,
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

**关键 SQL 查询**（asyncpg 使用 `$1` 占位符）:

```sql
-- 查询表和视图
SELECT t.table_schema, t.table_name, t.table_type,
       obj_description(
           (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
           'pg_class'
       ) AS table_comment
FROM information_schema.tables t
WHERE t.table_schema = ANY($1)
  AND t.table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY t.table_schema, t.table_name;

-- 查询列信息
SELECT c.table_schema, c.table_name, c.column_name,
       c.udt_name AS data_type,
       (c.is_nullable = 'YES') AS is_nullable,
       c.column_default,
       col_description(
           (quote_ident(c.table_schema)||'.'||quote_ident(c.table_name))::regclass,
           c.ordinal_position
       ) AS column_comment
FROM information_schema.columns c
WHERE c.table_schema = ANY($1)
ORDER BY c.table_schema, c.table_name, c.ordinal_position;

-- 查询索引
SELECT pi.schemaname, pi.tablename, pi.indexname,
       ix.indisunique AS is_unique,
       array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) AS columns
FROM pg_indexes pi
JOIN pg_class ic ON ic.relname = pi.indexname
JOIN pg_index ix ON ix.indexrelid = ic.oid
JOIN pg_class tc ON tc.relname = pi.tablename
JOIN pg_attribute a ON a.attrelid = tc.oid AND a.attnum = ANY(ix.indkey)
WHERE pi.schemaname = ANY($1)
GROUP BY pi.schemaname, pi.tablename, pi.indexname, ix.indisunique;

-- 查询外键
SELECT tc.table_schema, tc.table_name, tc.constraint_name,
       array_agg(kcu.column_name ORDER BY kcu.ordinal_position) AS local_columns,
       ccu.table_schema AS foreign_schema, ccu.table_name AS foreign_table,
       array_agg(ccu.column_name ORDER BY kcu.ordinal_position) AS foreign_columns
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = ANY($1)
GROUP BY tc.table_schema, tc.table_name, tc.constraint_name,
         ccu.table_schema, ccu.table_name;

-- 查询自定义 Enum 类型
SELECT n.nspname AS schema_name, t.typname AS type_name,
       array_agg(e.enumlabel ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
JOIN pg_enum e ON e.enumtypid = t.oid
WHERE n.nspname = ANY($1)
GROUP BY n.nspname, t.typname;
```

---

## 7. asyncpg 连接池与只读执行（db_executor.py）

### 连接池初始化

```python
import asyncio
import asyncpg
from asyncpg import Pool


async def create_pool(db: DatabaseConfig) -> Pool:
    """创建 asyncpg 连接池，session 层面强制只读"""
    return await asyncpg.create_pool(
        dsn=db.dsn,
        min_size=db.min_pool_size,
        max_size=db.max_pool_size,
        server_settings={
            "default_transaction_read_only": "true",
        },
    )
```

### 只读查询执行

```python
async def execute_query(
    pool: Pool,
    sql: str,
    limit: int,
    timeout_seconds: int,
) -> ExecutionResult:
    import time

    start = time.monotonic()
    async with pool.acquire() as conn:
        # 每次查询设置 statement_timeout（覆盖连接级别）
        await conn.execute(f"SET statement_timeout = '{timeout_seconds * 1000}'")
        try:
            records = await conn.fetch(sql, timeout=timeout_seconds)
        except asyncpg.exceptions.QueryCanceledError:
            raise TimeoutError(f"Query timed out after {timeout_seconds}s")

    elapsed_ms = (time.monotonic() - start) * 1000

    if not records:
        # 零行结果：通过 prepare 获取列元数据
        async with pool.acquire() as conn:
            stmt = await conn.prepare(sql)
            columns = [attr.name for attr in stmt.get_attributes()]
        return ExecutionResult(columns=columns, rows=[], row_count=0, execution_time_ms=elapsed_ms)

    columns = list(records[0].keys())
    rows = [list(r.values()) for r in records[:limit]]
    return ExecutionResult(
        columns=columns,
        rows=rows,
        row_count=len(rows),
        execution_time_ms=elapsed_ms,
    )
```

> **只读安全说明**: asyncpg 连接池通过 `server_settings={"default_transaction_read_only": "true"}` 在 PostgreSQL session 级别设置只读，所有从该连接池获取的连接均无法执行写操作（PostgreSQL 报 `ERROR: cannot execute ... in a read-only transaction`）。这是 asyncpg 实现只读约束的标准方式，不依赖事务隔离级别，与 sqlglot 的 SQL 静态验证形成双重保障。

---

## 8. SQL 验证（sql_validator.py）

四层防御，按照从轻到重顺序检测：

```python
import sqlglot
from sqlglot import exp


def validate_sql(sql: str, max_rows: int = 1000) -> tuple[str, str | None]:
    """
    验证 SQL 并注入 LIMIT。
    Returns: (validated_sql, error_message)
    error_message is None on success.
    """
    raw = sql.strip()

    # Layer 1: 拒绝注释（LLM 生成的 SQL 不应含注释，防御注入）
    if "--" in raw or "/*" in raw:
        return "", "SQL comments are not allowed"

    # Layer 2: AST 解析 + 多语句检测
    try:
        statements = sqlglot.parse(raw.rstrip(";"), dialect="postgres")
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

    # Layer 4: 注入 LIMIT 上限（防止全表扫描打爆内存）
    if not stmt.find(exp.Limit):
        stmt.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return stmt.sql(dialect="postgres"), None
```

---

## 9. NL2SQL（nl2sql.py）

```python
from openai import AsyncOpenAI
from pydantic import BaseModel


NL2SQL_SYSTEM_PROMPT = """\
You are a PostgreSQL SQL expert. Generate ONLY a valid SQL SELECT statement.

Rules:
1. Output ONLY a SQL SELECT statement — no explanations, no markdown, no code blocks
2. Use only tables and columns from the schema below
3. Do NOT include SQL comments (-- or /* */)
4. Do NOT generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or TRUNCATE

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
    response = await client.beta.chat.completions.parse(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": NL2SQL_SYSTEM_PROMPT.format(schema_text=schema_text)},
            {"role": "user", "content": user_query},
        ],
        response_format=SQLOutput,
    )
    return response.choices[0].message.parsed.sql


def build_schema_text(tables: list[TableSchema]) -> str:
    return "\n\n".join(t.to_prompt_text() for t in tables)
```

---

## 10. 结果验证（result_validator.py）

```python
import asyncio
from openai import AsyncOpenAI
from pydantic import BaseModel


VALIDATION_SYSTEM_PROMPT = """\
You are a data quality validator. Given a user's natural language query, the SQL that was \
generated, and a sample of query results, determine whether the results are meaningful and \
match the user's intent.
Respond in Chinese for the explanation field.
"""


class ValidationResult(BaseModel):
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
    sample_text = f"Columns: {columns}\nRows (sample): {sample_rows}"
    user_msg = f"Query: {user_query}\nSQL: {sql}\n{sample_text}"

    try:
        response = await asyncio.wait_for(
            client.beta.chat.completions.parse(
                model=model,
                temperature=0,
                messages=[
                    {"role": "system", "content": VALIDATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                response_format=ValidationResult,
            ),
            timeout=timeout_seconds,
        )
        result = response.choices[0].message.parsed
        return ValidationInfo(
            is_meaningful=result.is_meaningful,
            explanation=result.explanation,
        )
    except (asyncio.TimeoutError, Exception):
        return ValidationInfo(
            is_meaningful=False,
            explanation="",
            validation_skipped=True,
        )
```

---

## 11. MCP Server 入口（server.py）

```python
from contextlib import asynccontextmanager
from typing import Any
import asyncio
import asyncpg
from openai import AsyncOpenAI
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pg-mcp")

# 全局状态（由 lifespan 初始化）
_caches: dict[str, DatabaseSchemaCache] = {}
_pools: dict[str, asyncpg.Pool] = {}
_openai: AsyncOpenAI | None = None
_config: AppConfig | None = None


@asynccontextmanager
async def lifespan():
    global _caches, _pools, _openai, _config

    _config = AppConfig()  # 从 config.yaml + 环境变量读取
    _openai = AsyncOpenAI(api_key=_config.openai.api_key.get_secret_value())

    # 并发初始化所有数据库
    async def init_db(db: DatabaseConfig):
        _caches[db.alias] = await load_schema(db)
        if _caches[db.alias].is_available:
            _pools[db.alias] = await create_pool(db)

    await asyncio.gather(*[init_db(db) for db in _config.databases])

    yield  # Server 开始接受请求

    # Graceful shutdown
    await asyncio.gather(*[pool.close() for pool in _pools.values()])


mcp.lifespan = lifespan


# ── Tool 1: query_to_sql ──────────────────────────────────────────────────────

@mcp.tool()
async def query_to_sql(query: str, database: str | None = None) -> dict[str, Any]:
    """将自然语言查询转换为 PostgreSQL SELECT 语句。

    Args:
        query: 用户的自然语言查询，例如"过去30天内注册的用户数量"
        database: 目标数据库别名（在配置文件中定义）。不填则使用所有可用数据库的 Schema。
    """
    cache = _resolve_cache(database)
    relevant_tables = cache.get_relevant_tables(query, max_tables=20)
    schema_text = build_schema_text(relevant_tables)

    sql = await generate_sql(_openai, _config.openai.model, query, schema_text)
    validated_sql, err = validate_sql(sql, _config.server.max_result_rows)
    if err:
        return {"errorCode": "VALIDATION_FAILED", "message": err}

    return QueryToSqlOutput(
        sql=validated_sql,
        database=cache.alias,
        schema_used=[t.full_name for t in relevant_tables],
    ).model_dump(by_alias=True)


# ── Tool 2: query_to_result ───────────────────────────────────────────────────

@mcp.tool()
async def query_to_result(
    query: str,
    database: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    """将自然语言查询转换为 SQL 并执行，返回查询结果。

    Args:
        query: 用户的自然语言查询
        database: 目标数据库别名（可选）
        limit: 最大返回行数，默认 100，最大 1000
    """
    cache = _resolve_cache(database)
    pool = _pools.get(cache.alias)
    if not pool:
        return {"errorCode": "DB_ERROR", "message": f"No connection pool for '{cache.alias}'"}

    relevant_tables = cache.get_relevant_tables(query, max_tables=20)
    schema_text = build_schema_text(relevant_tables)

    sql = await generate_sql(_openai, _config.openai.model, query, schema_text)
    validated_sql, err = validate_sql(sql, limit)
    if err:
        return {"errorCode": "VALIDATION_FAILED", "message": err}

    try:
        exec_result = await execute_query(
            pool, validated_sql, limit, _config.server.query_timeout_seconds
        )
    except TimeoutError as e:
        return {"errorCode": "DB_ERROR", "message": str(e)}
    except Exception as e:
        return {"errorCode": "DB_ERROR", "message": f"Query failed: {e}"}

    sample = exec_result.rows[: _config.server.result_validation_sample_rows]
    validation = await validate_result(
        _openai, _config.openai.model, query, validated_sql,
        sample, exec_result.columns, _config.openai.timeout_seconds,
    )

    # auto_retry_on_invalid: 验证不通过时重试一次
    if (
        not validation.is_meaningful
        and not validation.validation_skipped
        and _config.server.auto_retry_on_invalid
    ):
        sql2 = await generate_sql(_openai, _config.openai.model, query, schema_text)
        validated_sql2, err2 = validate_sql(sql2, limit)
        if not err2:
            try:
                exec_result = await execute_query(
                    pool, validated_sql2, limit, _config.server.query_timeout_seconds
                )
                sample = exec_result.rows[: _config.server.result_validation_sample_rows]
                validation = await validate_result(
                    _openai, _config.openai.model, query, validated_sql2,
                    sample, exec_result.columns, _config.openai.timeout_seconds,
                )
                validated_sql = validated_sql2
            except Exception:
                pass  # 重试失败，保留原结果

    return QueryToResultOutput(
        sql=validated_sql,
        columns=exec_result.columns,
        rows=exec_result.rows,
        row_count=exec_result.row_count,
        validation=validation,
    ).model_dump(by_alias=True)


# ── Tool 3: list_databases ────────────────────────────────────────────────────

@mcp.tool()
async def list_databases() -> dict[str, Any]:
    """列出所有已配置并完成 Schema 缓存的数据库及其状态。"""
    return {
        "databases": [
            DatabaseInfo(
                alias=c.alias,
                host=c.host,
                dbname=c.dbname,
                schema_cached_at=c.cached_at if c.is_available else None,
                table_count=c.table_count,
                is_available=c.is_available,
            ).model_dump(by_alias=True)
            for c in _caches.values()
        ]
    }


# ── Tool 4: refresh_schema ────────────────────────────────────────────────────

@mcp.tool()
async def refresh_schema(database: str | None = None) -> dict[str, Any]:
    """手动刷新一个或所有数据库的 Schema 缓存。

    Args:
        database: 要刷新的数据库别名。不填则刷新全部。
    """
    import time

    targets = (
        [_config.databases[0]]  # 简化，实际按 alias 查找
        if database
        else _config.databases
    )
    start = time.monotonic()
    refreshed, failed = [], []

    async def do_refresh(db: DatabaseConfig):
        new_cache = await load_schema(db)
        _caches[db.alias] = new_cache
        if new_cache.is_available:
            if db.alias not in _pools:
                _pools[db.alias] = await create_pool(db)
            refreshed.append(db.alias)
        else:
            failed.append(db.alias)

    await asyncio.gather(*[do_refresh(db) for db in targets])

    return RefreshSchemaOutput(
        refreshed=refreshed,
        failed=failed,
        duration_seconds=round(time.monotonic() - start, 3),
    ).model_dump(by_alias=True)


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def _resolve_cache(database: str | None) -> DatabaseSchemaCache:
    if database:
        cache = _caches.get(database)
        if not cache:
            raise ValueError(f"Database '{database}' not found")
        if not cache.is_available:
            raise RuntimeError(f"Database '{database}' is unavailable: {cache.error_message}")
        return cache
    available = [c for c in _caches.values() if c.is_available]
    if not available:
        raise RuntimeError("No available databases")
    return available[0] if len(available) == 1 else available[0]  # 多 DB 时合并 Schema（v2）


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

---

## 12. 整体请求流程

```
用户输入 (自然语言)
      │
      ▼
[_resolve_cache] ─────────────────────────────────► ERROR: no_database_available
      │ DatabaseSchemaCache
      ▼
[get_relevant_tables] ← 关键词 token 重叠匹配
      │ list[TableSchema]
      ▼
[build_schema_text] → schema_text（紧凑摘要）
      │
      ▼
[generate_sql via AsyncOpenAI] ──(LLM 失败)──────► ERROR: llm_error
      │ raw SQL string
      ▼
[validate_sql via sqlglot] ──(注释/多条/非SELECT)► ERROR: validation_failed
      │ validated SQL (with LIMIT)
      ├─ query_to_sql ──────────────────────────► 返回 { sql, database, schemaUsed }
      │
      ▼ (query_to_result only)
[execute_query via asyncpg] ──(超时/DB错误)──────► ERROR: db_error
      │ ExecutionResult
      ▼
[validate_result via AsyncOpenAI] ──(超时)──────► validationSkipped=true
      │ ValidationInfo
      ▼
[auto_retry?] ─── auto_retry_on_invalid=true & not meaningful ──► 重试步骤 3-7（最多1次）
      │
      ▼
返回 { sql, columns, rows, rowCount, validation }
```

---

## 13. 安全设计

| 层 | 机制 | 说明 |
|----|------|------|
| SQL 静态验证 | sqlglot AST 检查 | 注释检测 + 多语句检测 + 只允许 SELECT |
| DB 连接安全 | asyncpg `server_settings` | `default_transaction_read_only=true` 在 session 级别强制只读 |
| 结果行数限制 | sqlglot LIMIT 注入 | 自动补 LIMIT，防止全表扫描 |
| 敏感配置 | Pydantic `SecretStr` | 密码/API Key 不在日志中暴露 |
| 执行超时 | asyncpg timeout + `statement_timeout` | 双重超时保护，防止慢查询 |

---

## 14. Claude Code 配置示例

Claude Code 通过 `claude mcp add` 命令或直接编辑配置文件来注册 MCP Server。

### 方式一：命令行注册（推荐）

```bash
claude mcp add pg-mcp \
  -e DB_USER=readonly_user \
  -e DB_PASSWORD=secret \
  -e OPENAI_API_KEY=sk-... \
  -- uv run --directory /path/to/specs/w5/pg-mcp python -m pg_mcp
```

### 方式二：编辑配置文件

**项目级**（仅当前项目生效）：`.claude/mcp.json`

**用户级**（所有项目生效）：`~/.claude/mcp.json`

```json
{
  "mcpServers": {
    "pg-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/specs/w5/pg-mcp", "python", "-m", "pg_mcp"],
      "env": {
        "DB_USER": "readonly_user",
        "DB_PASSWORD": "secret",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

### 验证注册

```bash
# 查看已注册的 MCP Server
claude mcp list

# 查看 pg-mcp 详情
claude mcp get pg-mcp
```
