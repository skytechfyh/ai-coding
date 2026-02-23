# API Contracts: 数据库查询工具

**Feature**: 001-db-query
**Date**: 2026-02-23

## Overview

本项目暴露以下 HTTP API 端点供前端调用。

Base URL: `http://localhost:8000/api/v1`

## Common Response Format

所有 API 响应遵循统一格式：

```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  errorMessage: string | null;
}
```

成功响应：
```json
{
  "success": true,
  "data": { ... },
  "errorMessage": null
}
```

错误响应：
```json
{
  "success": false,
  "data": null,
  "errorMessage": "Error description"
}
```

---

## Endpoints

### 1. 获取所有数据库列表

**Endpoint**: `GET /dbs`

**Description**: 获取所有已保存的数据库连接列表

**Response**:
```typescript
interface DatabaseListResponse {
  databases: Array<{
    name: string;
    databaseType: string;
    createdAt: string; // ISO datetime
    lastUsedAt: string | null; // ISO datetime
  }>;
}
```

**Example**:
```json
{
  "success": true,
  "data": {
    "databases": [
      {
        "name": "my-postgres",
        "databaseType": "postgres",
        "createdAt": "2026-02-23T10:00:00Z",
        "lastUsedAt": "2026-02-23T12:00:00Z"
      }
    ]
  },
  "errorMessage": null
}
```

---

### 2. 添加数据库

**Endpoint**: `PUT /dbs/{name}`

**Description**: 添加一个新的数据库连接

**Path Parameters**:
- `name` (string): 数据库连接名称

**Request Body**:
```typescript
interface CreateDatabaseRequest {
  url: string; // Database connection URL, e.g., "postgres://user:pass@host:5432/db"
}
```

**Response**: 返回 `DatabaseListResponse`

**Errors**:
- 400: 无效的连接字符串
- 409: 名称已存在

---

### 3. 获取数据库元数据

**Endpoint**: `GET /dbs/{name}`

**Description**: 获取指定数据库的表和视图元数据

**Path Parameters**:
- `name` (string): 数据库连接名称

**Response**:
```typescript
interface MetadataResponse {
  name: string;
  databaseType: string;
  tables: Array<{
    name: string;
    type: "table" | "view";
    columns: Array<{
      name: string;
      dataType: string;
      isNullable: boolean;
      isPrimaryKey: boolean;
    }>;
  }>;
}
```

**Example**:
```json
{
  "success": true,
  "data": {
    "name": "my-postgres",
    "databaseType": "postgres",
    "tables": [
      {
        "name": "users",
        "type": "table",
        "columns": [
          { "name": "id", "dataType": "integer", "isNullable": false, "isPrimaryKey": true },
          { "name": "email", "dataType": "varchar", "isNullable": false, "isPrimaryKey": false }
        ]
      }
    ]
  },
  "errorMessage": null
}
```

---

### 4. 执行 SQL 查询

**Endpoint**: `POST /dbs/{name}/query`

**Description**: 执行 SQL SELECT 查询

**Path Parameters**:
- `name` (string): 数据库连接名称

**Request Body**:
```typescript
interface QueryRequest {
  sql: string; // SQL SELECT statement
}
```

**Response**:
```typescript
interface QueryResultResponse {
  columns: string[];
  rows: Record<string, any>[];
  totalRows: number;
  queryTime: number; // seconds
}
```

**Errors**:
- 400: SQL 语法错误
- 400: 非 SELECT 语句
- 500: 数据库执行错误

---

### 5. 自然语言生成 SQL

**Endpoint**: `POST /dbs/{name}/query/natural`

**Description**: 使用自然语言生成 SQL 查询

**Path Parameters**:
- `name` (string): 数据库连接名称

**Request Body**:
```typescript
interface NaturalLanguageRequest {
  prompt: string; // Natural language query description
}
```

**Response**:
```typescript
interface NaturalLanguageResponse {
  sql: string; // Generated SQL
  needsConfirmation: boolean; // Whether user needs to confirm before execution
}
```

**Example**:
```json
{
  "success": true,
  "data": {
    "sql": "SELECT * FROM users LIMIT 1000",
    "needsConfirmation": false
  },
  "errorMessage": null
}
```

---

### 6. 删除数据库

**Endpoint**: `DELETE /dbs/{name}`

**Description**: 删除已保存的数据库连接

**Path Parameters**:
- `name` (string): 数据库连接名称

**Response**: 返回 `ApiResponse` with null data

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - 请求参数错误 |
| 404 | Not Found - 数据库不存在 |
| 409 | Conflict - 资源冲突 |
| 500 | Internal Server Error - 服务器内部错误 |
| 503 | Service Unavailable - LLM 服务不可用 |
