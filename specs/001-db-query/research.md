# Research: 数据库查询工具

**Date**: 2026-02-23
**Feature**: 001-db-query

## Research Tasks

### 1. FastAPI + Pydantic V2 集成

**Decision**: 使用 FastAPI + Pydantic V2

**Rationale**:
- FastAPI 自动生成 OpenAPI 文档，与 Pydantic V2 深度集成
- Pydantic V2 性能更好，支持 `model_config` 配置 alias_generator 实现 camelCase

**Implementation**:
```python
from pydantic import ConfigDict, BaseModel, Field
from pydantic.alias_generators import to_camel

class DatabaseConfig(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )

    url: str
    name: str
```

### 2. CORS 配置

**Decision**: 允许所有 origin

**Rationale**: 简化开发，前端运行在不同的端口

**Implementation**:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. SQLGlot SQL 验证

**Decision**: 使用 sqlglot 解析和验证 SQL

**Rationale**:
- 支持多种数据库方言
- 能够检测 SQL 类型（SELECT vs 非 SELECT）
- 方便添加 LIMIT 子句

**Implementation**:
```python
import sqlglot
from sqlglot import exp

def validate_and_fix_sql(sql: str) -> tuple[bool, str, str]:
    """验证 SQL 并添加 LIMIT"""
    try:
        statements = sqlglot.parse(sql)
        if not statements:
            return False, "", "Empty SQL"

        stmt = statements[0]
        if not isinstance(stmt, exp.Select):
            return False, "", "Only SELECT statements are allowed"

        # 检查是否已有 LIMIT
        if not stmt.find(exp.Limit):
            stmt.set("limit", exp.Limit(this=exp.Literal.number(1000)))

        return True, stmt.sql(), ""
    except sqlglot.errors.ParseError as e:
        return False, "", f"SQL syntax error: {str(e)}"
```

### 4. OpenAI API 集成

**Decision**: 使用 openai Python SDK

**Rationale**:
- 官方 SDK，稳定性好
- 支持 function calling（虽然本项目不需要）
- 易于集成

**Implementation**:
```python
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_sql(prompt: str, table_info: str) -> str:
    system_prompt = f"""You are a SQL expert. Given a natural language query,
generate a PostgreSQL SELECT statement. Use the following table schema:

{table_info}

Rules:
- Only generate SELECT statements
- If no LIMIT specified, add LIMIT 1000
- Use proper table and column names from the schema
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content
```

### 5. PostgreSQL Metadata 获取

**Decision**: 使用 SQL 查询 information_schema

**Rationale**: 标准方法，适用于 PostgreSQL

**Implementation**:
```python
# 获取所有表
def get_tables(connection):
    query = """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
    """
    # 执行查询返回表列表

# 获取表列信息
def get_columns(connection, table_name: str):
    query = """
        SELECT
            column_name, data_type, is_nullable,
            column_default, is_primary_key
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """
    # 执行查询返回列列表
```

### 6. Refine 5 + Ant Design 集成

**Decision**: 使用 Refine 5 的 Ant Design 集成

**Rationale**:
- Refine 5 内置支持 Ant Design
- 提供现成的 CRUD 组件和数据 hooks
- 与 Ant Design 组件完全兼容

**Implementation**:
```typescript
import { Refine } from "@refinedev/core";
import { dataProvider } from "@refinedev/simple-rest";
import { MantineProvider } from "@refinedev/antd";

<Refine
  dataProvider={dataProvider("http://localhost:8000")}
>
```

### 7. Monaco Editor React 集成

**Decision**: 使用 @monaco-editor/react

**Rationale**:
- 官方 React 包装器
- 支持 SQL 语法高亮
- 易于配置

**Implementation**:
```typescript
import Editor from "@monaco-editor/react";

<Editor
  height="200px"
  defaultLanguage="sql"
  options={{
    minimap: { enabled: false },
    fontSize: 14,
  }}
/>
```

## Alternatives Considered

| 选项 | 考虑原因 | 拒绝原因 |
|------|----------|----------|
| Flask vs FastAPI | 简单项目 | FastAPI 自动生成文档，Pydantic 集成更好 |
| psycopg2 vs sqlglot | 直接执行 SQL | sqlglot 可做语法验证和转换 |
| raw SQL vs Pydantic | 快速开发 | Pydantic 提供验证和类型安全 |
| 自己实现 SQL 解析 | 灵活性 | sqlglot 成熟稳定 |
