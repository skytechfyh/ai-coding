# MCP Tool Contracts: pg-mcp

**日期**: 2026-03-14
**传输协议**: stdio (MCP JSON-RPC over stdin/stdout)

---

## 总览

| Tool Name | 描述 | 副作用 |
|-----------|------|--------|
| `query_to_sql` | 自然语言 → SQL | 只读（不写数据库） |
| `query_to_result` | 自然语言 → SQL + 执行结果 | 只读 |
| `list_databases` | 列出已缓存的数据库 | 只读 |
| `refresh_schema` | 刷新 Schema 缓存 | 写内存缓存 |

---

## Tool 1: `query_to_sql`

### 描述

将用户的自然语言查询转换为可执行的 PostgreSQL SELECT 语句。

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "自然语言查询描述，例如：'查询过去30天内注册的用户数量'"
    },
    "database": {
      "type": "string",
      "description": "目标数据库别名（在配置文件中定义）。不填则使用所有可用数据库的 Schema。"
    }
  },
  "required": ["query"]
}
```

### Output Schema（成功）

```json
{
  "sql": "SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '30 days'",
  "database": "main",
  "schemaUsed": ["public.users"]
}
```

### Output Schema（失败）

```json
{
  "errorCode": "VALIDATION_FAILED",
  "message": "Generated SQL is not a SELECT statement",
  "details": "Got: Insert"
}
```

### 可能的 errorCode 值

| errorCode | 触发条件 |
|-----------|---------|
| `NO_DATABASE_AVAILABLE` | 没有可用的数据库（所有 DB 加载失败） |
| `DATABASE_NOT_FOUND` | 指定的 database alias 不存在 |
| `LLM_ERROR` | OpenAI API 调用失败（网络/超时/token 超限） |
| `VALIDATION_FAILED` | 生成的 SQL 不是合法的只读 SELECT |

### 流程

```
1. 查找目标 DB 的 schema cache
2. 用关键词匹配选取相关表（top 20）
3. 构建 Prompt（schema 摘要 + 用户查询）
4. 调用 OpenAI gpt-4o-mini（structured output: SQLOutput）
5. 用 sqlglot 验证 SQL（四层检查）
6. 返回 { sql, database, schemaUsed }
```

---

## Tool 2: `query_to_result`

### 描述

将用户的自然语言查询转换为 SQL，执行查询，并返回结果及语义验证。

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "自然语言查询描述"
    },
    "database": {
      "type": "string",
      "description": "目标数据库别名（可选）"
    },
    "limit": {
      "type": "integer",
      "description": "最大返回行数，默认 100，最大 1000",
      "default": 100,
      "minimum": 1,
      "maximum": 1000
    }
  },
  "required": ["query"]
}
```

### Output Schema（成功）

```json
{
  "sql": "SELECT id, email, created_at FROM users WHERE created_at >= NOW() - INTERVAL '30 days' LIMIT 100",
  "columns": ["id", "email", "created_at"],
  "rows": [
    [42, "alice@example.com", "2026-02-20T10:00:00Z"],
    [43, "bob@example.com", "2026-02-21T11:30:00Z"]
  ],
  "rowCount": 2,
  "validation": {
    "isMeaningful": true,
    "explanation": "结果返回了过去30天内注册的用户，与查询意图吻合",
    "validationSkipped": false
  }
}
```

### Output Schema（验证跳过，OpenAI 超时）

```json
{
  "sql": "...",
  "columns": [...],
  "rows": [...],
  "rowCount": 5,
  "validation": {
    "isMeaningful": false,
    "explanation": "",
    "validationSkipped": true
  }
}
```

### Output Schema（失败）

```json
{
  "errorCode": "DB_ERROR",
  "message": "Query execution timed out after 30 seconds",
  "details": null
}
```

### 可能的 errorCode 值

| errorCode | 触发条件 |
|-----------|---------|
| `NO_DATABASE_AVAILABLE` | 无可用数据库 |
| `DATABASE_NOT_FOUND` | 指定 alias 不存在 |
| `LLM_ERROR` | OpenAI NL2SQL 调用失败 |
| `VALIDATION_FAILED` | SQL 非只读 SELECT |
| `DB_ERROR` | 执行超时或 PostgreSQL 报错 |

### 流程

```
1-5. 同 query_to_sql（生成并验证 SQL）
6.  用 psycopg3 只读事务执行 SQL（30s 超时）
7.  取前 N 行 sample 调用 OpenAI 验证（10s 超时，超时则 skip）
8.  返回完整结果 + 验证信息
    （若 auto_retry_on_invalid=true 且验证不通过，重试步骤 1-7 一次）
```

---

## Tool 3: `list_databases`

### 描述

列出所有已配置并完成 Schema 缓存的数据库及其元信息。

### Input Schema

```json
{
  "type": "object",
  "properties": {}
}
```

（无必填参数）

### Output Schema

```json
{
  "databases": [
    {
      "alias": "main",
      "host": "localhost",
      "dbname": "production",
      "schemaCachedAt": "2026-03-14T10:00:00Z",
      "tableCount": 42,
      "isAvailable": true
    },
    {
      "alias": "analytics",
      "host": "analytics-db.internal",
      "dbname": "warehouse",
      "schemaCachedAt": null,
      "tableCount": 0,
      "isAvailable": false
    }
  ]
}
```

### 流程

```
1. 遍历所有 DatabaseSchemaCache
2. 返回摘要信息（不暴露密码/连接串）
```

---

## Tool 4: `refresh_schema`

### 描述

手动触发一个或所有数据库的 Schema 重新发现与缓存更新。

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "database": {
      "type": "string",
      "description": "要刷新的数据库别名。不填则刷新全部。"
    }
  }
}
```

### Output Schema（成功）

```json
{
  "refreshed": ["main", "analytics"],
  "failed": [],
  "durationSeconds": 2.4
}
```

### Output Schema（部分失败）

```json
{
  "refreshed": ["main"],
  "failed": ["analytics"],
  "durationSeconds": 5.1
}
```

### 流程

```
1. 确定要刷新的数据库列表
2. 对每个 DB 并发执行 Schema 发现（information_schema 查询）
3. 成功则更新内存 cache，失败则标记 is_available=false
4. 返回刷新摘要
```

---

## MCP Schema 查询 SQL（启动时使用）

### 查询所有表和视图

```sql
SELECT
    t.table_schema,
    t.table_name,
    t.table_type,
    obj_description(
        (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
        'pg_class'
    ) AS table_comment
FROM information_schema.tables t
WHERE t.table_schema NOT IN ('pg_catalog', 'information_schema')
  AND t.table_schema = ANY($1)  -- 配置的 schema 白名单
ORDER BY t.table_schema, t.table_name;
```

### 查询列信息

```sql
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.data_type,
    c.udt_name,
    c.is_nullable = 'YES' AS is_nullable,
    c.column_default,
    col_description(
        (quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass,
        c.ordinal_position
    ) AS column_comment
FROM information_schema.columns c
WHERE c.table_schema = ANY($1)
ORDER BY c.table_schema, c.table_name, c.ordinal_position;
```

### 查询索引

```sql
SELECT
    schemaname AS schema_name,
    tablename AS table_name,
    indexname AS index_name,
    indexdef AS index_definition,
    ix.indisunique AS is_unique
FROM pg_indexes pi
JOIN pg_class ic ON ic.relname = pi.indexname
JOIN pg_index ix ON ix.indexrelid = ic.oid
WHERE schemaname = ANY($1);
```

### 查询外键关系

```sql
SELECT
    tc.table_schema,
    tc.table_name,
    kcu.column_name,
    ccu.table_schema AS foreign_table_schema,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    tc.constraint_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = ANY($1);
```

### 查询自定义 Enum 类型

```sql
SELECT
    n.nspname AS schema_name,
    t.typname AS type_name,
    'enum' AS type_category,
    array_agg(e.enumlabel ORDER BY e.enumsortorder) AS enum_values
FROM pg_type t
JOIN pg_namespace n ON n.oid = t.typnamespace
JOIN pg_enum e ON e.enumtypid = t.oid
WHERE n.nspname = ANY($1)
GROUP BY n.nspname, t.typname;
```

---

## Prompt 模板

### NL2SQL System Prompt

```
You are a PostgreSQL SQL expert. Your ONLY job is to generate a valid SQL SELECT statement based on the user's natural language query and the provided database schema.

Rules:
1. Output ONLY a SQL SELECT statement — no explanations, no markdown, no code blocks
2. The SQL must be valid PostgreSQL syntax
3. Only use tables and columns that exist in the schema below
4. Do not include SQL comments (-- or /* */)
5. Do not generate INSERT, UPDATE, DELETE, DROP, CREATE, ALTER, or TRUNCATE statements

Database Schema:
{schema_text}
```

### 结果验证 System Prompt

```
You are a data quality validator. Given a user's natural language query, the SQL that was generated, and a sample of the query results, determine whether the results are meaningful and match the user's intent.

Respond with:
- is_meaningful: true if the results answer the user's question, false otherwise
- explanation: a brief explanation in Chinese (1-2 sentences)
```
