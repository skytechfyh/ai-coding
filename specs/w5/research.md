# Research: pg-mcp Design Decisions

**日期**: 2026-03-14
**Feature**: PostgreSQL MCP Server

---

## Decision 1: MCP Python SDK — FastMCP vs Low-level Server

**Decision**: 使用 `FastMCP`（`mcp[cli]` 包提供的高级 API）

**Rationale**:
- `@mcp.tool()` 装饰器自动从函数签名生成 JSON Schema，无需手写 inputSchema
- `asynccontextmanager` lifespan 支持在 server loop 启动前执行异步初始化（Schema 加载、DB 连接池建立）
- 函数 docstring 自动成为 tool description，符合 Pythonic 风格
- 相比低级 `Server` API 减少 60% 样板代码，且功能同等完整

**Async Init Pattern**:
```python
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pg-mcp")

@asynccontextmanager
async def lifespan():
    schema_cache = await load_all_schemas()   # 在 server loop 前执行
    pool = await create_connection_pools()
    yield {"schema_cache": schema_cache, "pool": pool}
    await pool.close()                        # Graceful shutdown

mcp.lifespan = lifespan

@mcp.tool()
async def query_to_sql(query: str, database: str | None = None) -> dict:
    """将自然语言查询转换为 SQL 语句"""
    ...

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**Alternatives considered**:
- Low-level `mcp.server.Server` API：灵活性更高但样板代码过多，不推荐

**Dependencies**: `mcp[cli]>=1.8.0`, Python 3.11+

---

## Decision 2: PostgreSQL Driver — asyncpg vs psycopg3

**Decision**: 使用 `psycopg3`（`psycopg[binary]>=3.2`）

**Rationale**:

| 维度 | asyncpg | psycopg3 | 胜出 |
|------|---------|----------|------|
| 只读事务 | 只支持 serializable 隔离级别 | `conn.read_only = True` 支持任意隔离级别 | **psycopg3** |
| 连接池 | `asyncpg.create_pool()` 内置 | `psycopg_pool`（单独安装） | asyncpg |
| 异步支持 | 原生 async-first | `AsyncConnection` / `AsyncCursor` | 平手 |
| 列名获取 | `record.keys()` | `cursor.description` → `.name` | 平手 |
| Statement timeout | execute() timeout + server param | SET statement_timeout | 平手 |

**关键因素**: 本项目强依赖只读事务（安全保障层），psycopg3 支持任意隔离级别的只读模式，asyncpg 限制只能用 serializable，性能开销更高。

**只读事务 Pattern**:
```python
import psycopg
from psycopg import AsyncConnection

async with await AsyncConnection.connect(dsn) as conn:
    conn.read_only = True                          # 设置只读
    async with conn.cursor() as cur:
        await cur.execute("SET statement_timeout = '30s'")
        await cur.execute(sql)
        cols = [desc.name for desc in cur.description]
        rows = await cur.fetchmany(size=limit)
```

**Connection Pool Pattern**:
```python
from psycopg_pool import AsyncConnectionPool

pool = AsyncConnectionPool(conninfo=dsn, min_size=1, max_size=5)
async with pool.connection() as conn:
    conn.read_only = True
    ...
```

**Dependencies**: `psycopg[binary]>=3.2`, `psycopg-pool>=3.2`

---

## Decision 3: SQL Validation — sqlglot (已有依赖)

**Decision**: 使用 `sqlglot`，复用项目现有依赖，添加注释检测

**Rationale**:
- sqlglot 已在项目中使用（`w2/db_query/backend`），零增量依赖
- 提供真正的 AST 解析，比 regex 安全可靠
- 支持 `dialect="postgres"` 正确处理 PostgreSQL 语法
- 可自动注入 `LIMIT` 安全上限

**验证函数 Pattern（四层防御）**:
```python
import sqlglot
from sqlglot import exp

def validate_sql(sql: str, max_rows: int = 1000) -> tuple[str, str | None]:
    """
    Returns: (validated_sql, error_message)
    error_message is None on success
    """
    raw = sql.strip()

    # Layer 1: 拒绝 SQL 注释（LLM 生成的 SQL 不应有注释）
    if "--" in raw or "/*" in raw:
        return "", "SQL comments are not allowed"

    # Layer 2: 解析并检测多条语句
    statements = sqlglot.parse(raw.rstrip(";"), dialect="postgres")
    if not statements:
        return "", "Empty SQL"
    if len(statements) > 1:
        return "", f"Multiple statements not allowed ({len(statements)} found)"

    # Layer 3: 只允许 SELECT
    stmt = statements[0]
    if not isinstance(stmt, exp.Select):
        return "", f"Only SELECT is allowed (got {type(stmt).__name__})"

    # Layer 4: 注入 LIMIT 上限
    if not stmt.find(exp.Limit):
        stmt.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    return stmt.sql(dialect="postgres"), None
```

**Alternatives considered**:
- `sqlparse`：轻量但缺乏 dialect 支持和 AST 修改能力
- 纯 regex：易绕过，不推荐

---

## Decision 4: OpenAI 集成 — NL2SQL 和结果验证

**Decision**: 使用 `AsyncOpenAI` + Pydantic Structured Outputs

**NL2SQL（返回 SQL 字符串）**:

使用 `response_format` Pydantic 模型确保输出格式：

```python
from openai import AsyncOpenAI
from pydantic import BaseModel

class SQLOutput(BaseModel):
    sql: str  # 只包含 SQL SELECT 语句，不含 markdown

client = AsyncOpenAI(api_key=settings.openai_api_key)

response = await client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    temperature=0,
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ],
    response_format=SQLOutput,
)
sql = response.choices[0].message.parsed.sql
```

**结果验证**:

```python
class ValidationResult(BaseModel):
    is_meaningful: bool
    explanation: str

response = await client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    temperature=0,
    messages=[
        {"role": "system", "content": "You validate if a SQL query result matches the user's intent."},
        {"role": "user", "content": f"Query: {user_query}\nSQL: {sql}\nSample rows: {sample_rows}"},
    ],
    response_format=ValidationResult,
)
validation = response.choices[0].message.parsed
```

**Dependencies**: `openai>=1.30.0`

---

## Decision 5: Schema 上下文裁剪策略

**Decision**: v1 使用关键词匹配（TF-IDF 风格的简单 token 重叠），不引入向量数据库

**Rationale**:
- 向量相似度（如 pgvector / faiss）引入大量依赖和运维复杂度
- gpt-4o-mini 的 128K context window 可以容纳约 300 张表的 Schema 摘要
- 简单关键词匹配（用户查询词 vs 表名/列名的 token 重叠）对于大多数业务场景已经足够
- v2 可按需升级为向量检索

**Schema 摘要格式**（注入给 LLM 的格式）:
```
Table: public.users
  Columns: id (int4, NOT NULL), email (text), created_at (timestamptz)
  Indexes: idx_users_email (UNIQUE on email)
  FK: orders.user_id → users.id

Table: public.orders
  Columns: id (int4), user_id (int4), total (numeric), status (text)
  FK: order_items.order_id → orders.id
```

**裁剪逻辑**:
1. 提取用户查询中的关键词（小写、去停用词）
2. 计算每张表的相关性分数（表名/列名/注释与关键词的 token 重叠数）
3. 按分数降序排列，取 top-N 张表（N 根据 token 预算动态计算）
4. 总是包含与 top 表有直接外键关系的表（JOIN 辅助）

---

## Decision 6: 配置管理

**Decision**: 使用 Pydantic Settings（`pydantic-settings`）+ YAML 文件 + 环境变量覆盖

**Rationale**:
- 符合 Constitution 的 Pydantic-first 原则
- `pydantic-settings` 支持 `.env` 文件和环境变量自动映射
- 敏感字段（密码、API key）通过环境变量覆盖，不暴露在配置文件中

**Dependencies**: `pydantic-settings>=2.0`, `pyyaml>=6.0`

---

## Decision 7: 项目结构

```
specs/w5/pg-mcp/
├── pyproject.toml
├── config.yaml.example
├── src/
│   └── pg_mcp/
│       ├── __init__.py
│       ├── server.py          # FastMCP 入口，lifespan，tool 注册
│       ├── config.py          # Pydantic Settings 配置模型
│       ├── schema_cache.py    # Schema 发现与缓存
│       ├── nl2sql.py          # OpenAI NL2SQL + Prompt 构建
│       ├── sql_validator.py   # sqlglot 验证层
│       ├── db_executor.py     # psycopg3 只读执行
│       ├── result_validator.py # OpenAI 结果语义验证
│       └── models.py          # Pydantic 数据模型（camelCase JSON）
└── tests/
    ├── test_schema_cache.py
    ├── test_sql_validator.py
    ├── test_nl2sql.py
    └── test_result_validator.py
```

---

## Open Questions Resolution

| Q | 决策 |
|---|------|
| Q-01 Schema 裁剪 | 关键词 token 重叠，v1 不用向量 |
| Q-02 验证失败重试 | 默认不重试（只返回警告），可配置开启最多 1 次重试 |
| Q-03 多 schema (search_path) | 支持，发现所有 non-system schemas（`public`, etc.），可通过配置白名单过滤 |
| Q-04 连接池 | 使用 `psycopg_pool.AsyncConnectionPool`，per-database min=1 max=5 |
| Q-05 外部密钥管理 | v1 不支持，通过环境变量传入，v2 可扩展 |
