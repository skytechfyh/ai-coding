# Data Model: pg-mcp

**日期**: 2026-03-14

所有模型使用 Pydantic V2，JSON 输出使用 camelCase（Constitution §III & §IV）。

---

## 1. 配置模型

### `DatabaseConfig`

```python
class DatabaseConfig(BaseModel):
    alias: str                    # 数据库逻辑别名，如 "main"
    host: str = "localhost"
    port: int = 5432
    dbname: str
    user: str
    password: SecretStr           # 敏感字段
    schemas: list[str] = ["public"]  # 要发现的 PG schema 列表
```

### `OpenAIConfig`

```python
class OpenAIConfig(BaseModel):
    api_key: SecretStr
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 10.0
```

### `ServerConfig`

```python
class ServerConfig(BaseModel):
    query_timeout_seconds: int = 30
    result_validation_sample_rows: int = 5
    max_result_rows: int = 1000
    auto_retry_on_invalid: bool = False
```

### `AppConfig`（顶层配置，via pydantic-settings）

```python
class AppConfig(BaseSettings):
    databases: list[DatabaseConfig]
    openai: OpenAIConfig
    server: ServerConfig = ServerConfig()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",  # OPENAI__API_KEY=xxx
        yaml_file="config.yaml",
    )
```

---

## 2. Schema 缓存模型

### `ColumnInfo`

```python
class ColumnInfo(BaseModel):
    name: str
    data_type: str           # e.g. "int4", "text", "timestamptz"
    is_nullable: bool
    default: str | None
    comment: str | None
```

### `IndexInfo`

```python
class IndexInfo(BaseModel):
    name: str
    columns: list[str]
    is_unique: bool
```

### `ForeignKeyInfo`

```python
class ForeignKeyInfo(BaseModel):
    constraint_name: str
    local_columns: list[str]
    foreign_table: str       # "schema.table" 格式
    foreign_columns: list[str]
```

### `TableSchema`

```python
class TableSchema(BaseModel):
    schema_name: str         # PostgreSQL schema，如 "public"
    table_name: str
    full_name: str           # "public.users"
    object_type: Literal["table", "view"]
    columns: list[ColumnInfo]
    indexes: list[IndexInfo]
    foreign_keys: list[ForeignKeyInfo]
    comment: str | None

    def to_prompt_text(self) -> str:
        """生成注入 LLM Prompt 的紧凑文本格式"""
        ...
```

### `CustomTypeInfo`

```python
class CustomTypeInfo(BaseModel):
    schema_name: str
    type_name: str
    type_category: Literal["enum", "composite", "domain", "other"]
    enum_values: list[str] | None    # enum 类型的可选值
```

### `DatabaseSchemaCache`

```python
class DatabaseSchemaCache(BaseModel):
    alias: str
    host: str
    dbname: str
    tables: dict[str, TableSchema]   # key: "schema.table_name"
    custom_types: list[CustomTypeInfo]
    cached_at: datetime
    is_available: bool = True
    error_message: str | None = None  # 加载失败时记录错误

    @property
    def table_count(self) -> int:
        return len(self.tables)

    def get_relevant_tables(self, query: str, max_tables: int = 20) -> list[TableSchema]:
        """关键词匹配，返回最相关的表"""
        ...
```

---

## 3. MCP Tool 输入/输出模型

### `QueryToSqlInput`

```python
class QueryToSqlInput(BaseModel):
    query: str                       # 用户自然语言查询
    database: str | None = None      # 目标 DB 别名（可选）
```

### `QueryToSqlOutput`

```python
class QueryToSqlOutput(BaseModel):
    sql: str
    database: str
    schema_used: list[str]           # 参与生成的表名列表

    model_config = ConfigDict(
        alias_generator=to_camel,    # camelCase JSON
        populate_by_name=True,
    )
```

### `QueryToResultInput`

```python
class QueryToResultInput(BaseModel):
    query: str
    database: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
```

### `ValidationInfo`

```python
class ValidationInfo(BaseModel):
    is_meaningful: bool
    explanation: str
    validation_skipped: bool = False  # OpenAI 超时时为 True

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

### `QueryToResultOutput`

```python
class QueryToResultOutput(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    validation: ValidationInfo

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

### `DatabaseInfo`

```python
class DatabaseInfo(BaseModel):
    alias: str
    host: str
    dbname: str
    schema_cached_at: datetime | None
    table_count: int
    is_available: bool

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

### `ListDatabasesOutput`

```python
class ListDatabasesOutput(BaseModel):
    databases: list[DatabaseInfo]
```

### `RefreshSchemaInput`

```python
class RefreshSchemaInput(BaseModel):
    database: str | None = None      # None = 刷新全部
```

### `RefreshSchemaOutput`

```python
class RefreshSchemaOutput(BaseModel):
    refreshed: list[str]             # 成功刷新的 alias 列表
    failed: list[str]                # 失败的 alias 列表
    duration_seconds: float

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

---

## 4. 内部服务模型

### `SQLOutput`（OpenAI NL2SQL 结构化输出）

```python
class SQLOutput(BaseModel):
    """OpenAI structured output for NL2SQL"""
    sql: str
```

### `ValidationResult`（OpenAI 结果验证结构化输出）

```python
class ValidationResult(BaseModel):
    """OpenAI structured output for result validation"""
    is_meaningful: bool
    explanation: str
```

### `ExecutionResult`

```python
class ExecutionResult(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    execution_time_ms: float
```

---

## 5. 错误模型

### `PgMcpError`（MCP Tool 返回的错误结构）

```python
class PgMcpError(BaseModel):
    error_code: str       # "VALIDATION_FAILED" | "DB_ERROR" | "LLM_ERROR" | "TIMEOUT"
    message: str
    details: str | None = None

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```

---

## 6. 状态转换图

```
用户输入 (自然语言)
      │
      ▼
[Schema 选择] ──(无可用DB)──► ERROR: no_database_available
      │
      ▼
[NL2SQL via OpenAI] ──(调用失败)──► ERROR: llm_error
      │
      ▼
[SQL 验证 via sqlglot] ──(非SELECT/多条语句/注释)──► ERROR: validation_failed
      │
      ▼
[SQL 执行 via psycopg3] ──(超时/DB错误)──► ERROR: db_error
      │
      ▼
[结果验证 via OpenAI] ──(超时)──► validation_skipped=true (不阻断)
      │
      ▼
[返回结果]
      │
      ├─ query_to_sql: { sql, database, schema_used }
      └─ query_to_result: { sql, columns, rows, row_count, validation }
```
