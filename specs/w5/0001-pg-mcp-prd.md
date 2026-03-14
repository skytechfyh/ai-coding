# PRD: PostgreSQL MCP Server (pg-mcp)

**版本**: 1.0
**日期**: 2026-03-14
**状态**: 待审阅

---

## 1. 背景与目标

### 1.1 背景

随着 LLM 的普及，越来越多的用户希望通过自然语言与数据库交互，而无需掌握 SQL 语法。MCP（Model Context Protocol）是 Anthropic 推出的一套标准化的工具调用协议，允许 AI 助手通过结构化的工具接口访问外部服务。

本项目旨在构建一个基于 Python 的 PostgreSQL MCP Server，让 AI 助手（如 Claude）能够：

- 理解用户的自然语言查询意图
- 自动生成并验证对应的 SQL 查询语句
- 返回 SQL 本身或查询结果

### 1.2 目标

- 提供一个符合 MCP 规范的 PostgreSQL 查询服务
- 通过缓存数据库 Schema 来提升查询生成的准确性
- 通过 OpenAI 大模型（gpt-4o-mini）将自然语言转化为 SQL
- 确保生成的 SQL 安全（只允许查询语句）且有意义（结果验证）
- 支持用户按需选择：只返回 SQL，或返回 SQL + 查询结果

---

## 2. 用户故事

| # | 角色 | 需求描述 | 验收标准 |
|---|------|----------|----------|
| US-01 | AI 助手用户 | 我想通过自然语言描述数据查询需求，获取对应的 SQL | 输入自然语言后返回可执行的 SQL |
| US-02 | AI 助手用户 | 我想直接获取查询结果，而不仅仅是 SQL | 输入自然语言后返回格式化的查询结果 |
| US-03 | 系统管理员 | 我希望 MCP Server 启动时自动探索可访问的数据库，不需要手动配置每张表 | 启动后自动发现并缓存所有可访问的 Schema |
| US-04 | AI 助手用户 | 我希望系统能告诉我生成的 SQL 是否合理、结果是否有意义 | 不合理的 SQL 或无意义结果应有明确的错误或警告提示 |

---

## 3. 功能需求

### 3.1 启动时的 Schema 发现与缓存

**FR-01: 数据库连接配置**

- Server 启动时，通过配置文件或环境变量读取一个或多个 PostgreSQL 连接信息（DSN 或 host/port/user/password/dbname 组合）
- 每个连接对应一个逻辑"数据库"，可以有别名

**FR-02: Schema 自动发现**

Server 启动后，针对每个配置的数据库连接，自动查询并缓存以下元数据：

| 元数据类型 | 内容 |
|-----------|------|
| Tables | schema、表名、列名、列类型、是否可为空、默认值、注释 |
| Views | schema、视图名、列信息、视图定义（可选） |
| Custom Types | schema、类型名、类型类别（enum/composite 等）、枚举值（如适用） |
| Indexes | 所属表、索引名、索引列、是否唯一 |
| Foreign Keys | 源表、源列、目标表、目标列（用于辅助 JOIN 推断） |

**FR-03: Schema 缓存管理**

- Schema 在进程内存中缓存，进程重启时重新加载
- 提供一个 MCP 工具（`refresh_schema`）允许手动触发 Schema 刷新
- 缓存应包含加载时间戳

### 3.2 自然语言转 SQL（NL2SQL）

**FR-04: 调用 OpenAI 生成 SQL**

- 使用 OpenAI API（模型：`gpt-4o-mini`）将用户的自然语言输入转化为 SQL
- Prompt 构建需包含：
  - 目标数据库的 Schema 摘要（表结构、列类型、外键关系等）
  - 用户的自然语言查询描述
  - 明确的指令：只生成 SELECT 语句，不生成 DML/DDL
- 如果用户指定了目标数据库（通过数据库别名），则只注入该数据库的 Schema；否则注入所有已缓存的 Schema

**FR-05: SQL 生成的上下文控制**

- 当 Schema 内容过大（token 超限），应按相关性裁剪注入的 Schema：
  - 优先注入与用户查询相关的表（可通过关键词匹配或简单向量相似度过滤）
  - 次要注入可能相关的表（外键关联表等）

### 3.3 SQL 安全验证

**FR-06: SQL 类型校验**

- 使用 SQL 解析器（如 `sqlglot`）对生成的 SQL 进行静态分析
- 只允许以下语句类型：`SELECT`
- 遇到以下类型应拒绝执行并返回错误：
  - `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `ALTER`, `TRUNCATE`
  - 存储过程调用、任何 DDL/DML

**FR-07: SQL 注入防护**

- 不允许 SQL 中包含多条语句（`;` 分隔多条语句）
- 不允许注释中携带可执行内容（基础防护）

### 3.4 SQL 执行与结果验证

**FR-08: SQL 执行**

- 使用只读数据库账号（或开启只读事务）执行生成的 SQL
- 设置执行超时（默认 30 秒，可配置）
- 捕获执行异常并返回结构化错误信息

**FR-09: 结果有意义性验证**

- 执行 SQL 后，将以下内容发送给 OpenAI（`gpt-4o-mini`）进行语义验证：
  - 原始用户自然语言查询
  - 生成的 SQL
  - 查询结果的前 N 行（N 默认为 5，可配置）
- OpenAI 返回：
  - `is_meaningful: bool` — 结果是否与用户意图匹配
  - `explanation: str` — 简要说明结果是否符合预期，如不符合给出原因
- 如果验证不通过，MCP Server 可以：
  - 选项 A（默认）：将结果连同警告一起返回，提示用户结果可能不准确
  - 选项 B（可配置）：自动重试一次 NL2SQL 过程，最多重试 1 次

### 3.5 MCP 工具接口

Server 暴露以下 MCP Tools：

#### Tool 1: `query_to_sql`

**描述**: 将自然语言查询转换为 SQL 语句

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `query` | string | 是 | 用户的自然语言查询描述 |
| `database` | string | 否 | 目标数据库别名，不填则使用所有可用数据库 |

**返回**:

```json
{
  "sql": "SELECT ...",
  "database": "mydb",
  "schema_used": ["public.users", "public.orders"]
}
```

#### Tool 2: `query_to_result`

**描述**: 将自然语言查询转换为 SQL 并执行，返回查询结果

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `query` | string | 是 | 用户的自然语言查询描述 |
| `database` | string | 否 | 目标数据库别名 |
| `limit` | integer | 否 | 最大返回行数，默认 100，最大 1000 |

**返回**:

```json
{
  "sql": "SELECT ...",
  "columns": ["id", "name", "email"],
  "rows": [[1, "Alice", "alice@example.com"]],
  "row_count": 1,
  "validation": {
    "is_meaningful": true,
    "explanation": "结果与查询意图吻合，返回了用户表中的数据"
  }
}
```

#### Tool 3: `list_databases`

**描述**: 列出所有已配置并缓存 Schema 的数据库

**返回**:

```json
{
  "databases": [
    {
      "alias": "mydb",
      "host": "localhost",
      "dbname": "production",
      "schema_cached_at": "2026-03-14T10:00:00Z",
      "table_count": 42
    }
  ]
}
```

#### Tool 4: `refresh_schema`

**描述**: 手动触发某个或所有数据库的 Schema 刷新

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `database` | string | 否 | 要刷新的数据库别名，不填则刷新全部 |

**返回**:

```json
{
  "refreshed": ["mydb"],
  "duration_seconds": 1.2
}
```

---

## 4. 非功能需求

### 4.1 性能

| 指标 | 要求 |
|------|------|
| Schema 加载时间 | 单库 Schema 加载 < 10 秒（针对 < 500 张表的数据库） |
| NL2SQL 响应时间 | 端到端（含 OpenAI 调用）< 10 秒（P90） |
| SQL 执行超时 | 默认 30 秒，可配置 |
| 结果验证超时 | OpenAI 调用超时 10 秒，超时后跳过验证并标注 `validation_skipped: true` |

### 4.2 安全性

- 数据库连接信息通过环境变量或加密配置文件传入，不得硬编码
- 只允许只读操作（SELECT），通过双重保障：SQL 静态解析 + 只读数据库账号/只读事务
- OpenAI API Key 通过环境变量传入

### 4.3 可靠性

- Schema 缓存加载失败时，Server 应正常启动但标记该数据库为不可用，并在工具调用时返回明确错误
- OpenAI 调用失败时，`query_to_sql` 和 `query_to_result` 应返回结构化错误，不应崩溃

### 4.4 可观测性

- 结构化日志（JSON 格式），记录每次工具调用的：
  - 输入参数
  - 生成的 SQL
  - 执行耗时
  - OpenAI 调用耗时
  - 验证结果
- 日志级别可通过环境变量配置

---

## 5. 配置与部署

### 5.1 配置方式

Server 通过 YAML 配置文件（`config.yaml`）和环境变量进行配置：

```yaml
# config.yaml 示例
databases:
  - alias: "main"
    host: "localhost"
    port: 5432
    dbname: "production"
    user: "${DB_USER}"          # 支持环境变量引用
    password: "${DB_PASSWORD}"

openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o-mini"

server:
  query_timeout_seconds: 30
  result_validation_sample_rows: 5
  max_result_rows: 1000
  auto_retry_on_invalid: false  # 验证失败是否自动重试
```

### 5.2 部署方式

- 以 Python 包形式分发，通过 `uvx` 或 `python -m pg_mcp` 启动
- 支持 stdio 传输（标准 MCP stdio 模式）
- 配置文件路径可通过命令行参数 `--config` 指定

---

## 6. 约束与边界

| 约束 | 说明 |
|------|------|
| 只支持 PostgreSQL | 不支持 MySQL、SQLite 等其他数据库 |
| 只允许 SELECT 查询 | 任何写操作均被拒绝 |
| Schema 缓存为进程内存 | 重启后需重新加载，不持久化到磁盘 |
| OpenAI 模型固定为 gpt-4o-mini | 不支持其他模型（v1.0） |
| 结果行数上限 1000 | 防止大结果集占用过多内存 |

---

## 7. 成功指标

| 指标 | 目标值 |
|------|--------|
| NL2SQL 准确率（人工评估） | ≥ 80%（在测试查询集上） |
| 结果有意义性验证通过率 | ≥ 90%（验证为 meaningful 的查询） |
| Server 崩溃率 | 0%（对于常见错误场景） |

---

## 8. 开放问题（待讨论）

| # | 问题 | 影响 |
|---|------|------|
| Q-01 | Schema 过大时如何裁剪注入给 OpenAI？是否需要向量化相关性搜索？ | 影响 NL2SQL 准确率和 token 成本 |
| Q-02 | 结果验证失败时，是否自动重试？重试次数上限？ | 影响用户体验和 OpenAI 调用成本 |
| Q-03 | 是否需要支持多 schema（PostgreSQL search_path）？ | 影响 Schema 发现的完整性 |
| Q-04 | 是否需要支持连接池？单连接 vs 多连接？ | 影响并发性能 |
| Q-05 | 配置文件中的密码是否需要支持外部密钥管理（如 AWS Secrets Manager）？ | 影响安全合规性 |

