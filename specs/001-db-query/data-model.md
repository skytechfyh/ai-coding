# Data Model: 数据库查询工具

**Feature**: 001-db-query
**Date**: 2026-02-23

## Entities

### DatabaseConnection

表示一个数据库连接配置

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | 唯一标识符 |
| name | string | Yes | 连接名称（用户自定义） |
| url | string | Yes | 数据库连接字符串 |
| databaseType | string | Yes | 数据库类型 (postgres/mysql/sqlite) |
| createdAt | datetime | Yes | 创建时间 |
| lastUsedAt | datetime | No | 最后使用时间 |

### TableMetadata

表示数据库表的元数据

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | 唯一标识符 |
| databaseId | string (UUID) | Yes | 关联的数据库连接ID |
| name | string | Yes | 表/视图名称 |
| type | string | Yes | 类型 (table/view) |
| columns | Column[] | Yes | 列信息列表 |

### Column

表示表或视图的列

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | 列名 |
| dataType | string | Yes | 数据类型 |
| isNullable | boolean | Yes | 是否可空 |
| isPrimaryKey | boolean | Yes | 是否主键 |
| defaultValue | string | No | 默认值 |

### QueryRecord

表示一次查询记录

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | string (UUID) | Yes | 唯一标识符 |
| databaseId | string (UUID) | Yes | 关联的数据库连接ID |
| sql | string | Yes | 执行的 SQL 语句 |
| executedAt | datetime | Yes | 执行时间 |
| rowCount | integer | Yes | 返回行数 |
| duration | float | Yes | 执行耗时（秒） |
| status | string | Yes | success/error |

### QueryResult

表示查询结果

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| columns | string[] | Yes | 列名列表 |
| rows | object[] | Yes | 行数据 |
| totalRows | integer | Yes | 总行数 |
| queryTime | float | Yes | 查询耗时（秒） |

## Validation Rules

### DatabaseConnection

- `name`: 1-50 字符，不能包含特殊字符
- `url`: 必须是有效的数据库连接字符串
- `databaseType`: 必须是支持的值之一 (postgres, mysql, sqlite)

### QueryRequest

- `sql`: 不能为空，最大 10000 字符

### NaturalLanguageRequest

- `prompt`: 不能为空，最大 2000 字符

## State Transitions

```
[New Connection] --> [Connecting] --> [Connected]
                                     |
                                     v
                               [Disconnected]

[Query Ready] --> [Executing] --> [Success]
                                   |
                                   v
                                [Error]
```

## API Models (Pydantic)

### Request Models

```python
# PUT /api/v1/dbs/{name}
class CreateDatabaseRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    url: str = Field(..., description="Database connection URL")

# POST /api/v1/dbs/{name}/query
class QueryRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    sql: str = Field(..., description="SQL query to execute")

# POST /api/v1/dbs/{name}/query/natural
class NaturalLanguageRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    prompt: str = Field(..., description="Natural language query")
```

### Response Models

```python
class DatabaseResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    databaseType: str
    createdAt: datetime
    lastUsedAt: datetime | None

class TableMetadataResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    type: str  # table/view
    columns: list[ColumnResponse]

class ColumnResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str
    dataType: str
    isNullable: bool
    isPrimaryKey: bool

class QueryResultResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    columns: list[str]
    rows: list[dict]
    totalRows: int
    queryTime: float

class NaturalLanguageResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    sql: str
    needsConfirmation: bool = False

class ApiResponse(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool
    data: Any = None
    errorMessage: str | None = None
```
