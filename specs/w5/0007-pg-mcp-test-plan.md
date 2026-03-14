# Test Plan: pg-mcp

**版本**: 1.0
**日期**: 2026-03-14
**基于文档**:
- `specs/w5/0002-pg-mcp-design.md`
- `specs/w5/0004-pg-mcp-impl-plan.md`
- `specs/w5/0006-pg-mcp-code-review.md`（现有代码审查结果）

---

## 1. 测试目标与范围

### 1.1 测试目标

| 目标 | 描述 |
|------|------|
| 功能正确性 | 四个 MCP Tool 按规范返回正确结果 |
| 错误处理 | 所有错误路径返回正确的 errorCode 和 message |
| 边界情况 | 空结果集、超时、中文查询、循环 FK 等极端输入 |
| 规范符合性 | 输出 camelCase、SecretStr 保护、只读连接 |
| 代码审查修复 | 验证 RED-01~RED-03、WARN-07、HINT-04 等已发现问题 |

### 1.2 当前测试覆盖评估

```
模块                  当前测试状态        覆盖缺口
─────────────────────────────────────────────────────
sql_validator.py     ✅ 18 个测试        较完整（空字符串断言不准确）
models.py            ✅ 12 个测试        缺少 relevance_score 直接测试
config.py            ❌ 零测试           全部缺失
db_executor.py       ❌ 零单元测试       _serialize_value、UUID 类型
schema_cache.py      ❌ 零单元测试       fetch 函数、组装逻辑
nl2sql.py            ✅ 8 个测试         较完整
result_validator.py  ✅ 6 个测试         较完整（含 P0 修复验证）
server.py            ❌ 零单元测试       _resolve_cache、4 个 tool
```

### 1.3 测试范围

- **包含**: `w5/pg-mcp/src/pg_mcp/` 下所有模块
- **不包含**: 第三方库（asyncpg、openai、sqlglot）内部逻辑
- **条件包含**: 需要真实 PostgreSQL 的集成测试（`TEST_PG_DSN` 环境变量控制）
- **条件包含**: 需要真实 OpenAI 的 E2E 测试（`OPENAI_API_KEY` 环境变量控制）

---

## 2. 测试策略

### 2.1 测试金字塔

```
               ┌────────────┐
               │  E2E 测试  │  3-5 个场景（需 PG + OpenAI）
              ┌┴────────────┴┐
             │  集成测试    │  10-15 个场景（需真实 PG）
           ┌─┴──────────────┴─┐
          │     单元测试      │  80+ 个测试用例（无外部依赖）
         └────────────────────┘
```

### 2.2 Mock 策略

| 被 Mock 的组件 | Mock 方式 | 适用场景 |
|---------------|----------|---------|
| OpenAI API | `unittest.mock.AsyncMock` | 单元测试中的 nl2sql、result_validator |
| asyncpg Pool | `AsyncMock` + `MagicMock` | 单元测试中的 db_executor、server |
| asyncpg Connection | `AsyncMock` + 自定义 Record | 单元测试中的 schema_cache |
| `load_schema` | `AsyncMock` | server 单元测试 |
| `create_pool` | `AsyncMock` | server 单元测试 |

### 2.3 测试标记（markers）

```toml
# pyproject.toml 中添加
[tool.pytest.ini_options]
markers = [
    "unit: 纯单元测试，无外部依赖",
    "integration: 需要真实 PostgreSQL（TEST_PG_DSN 环境变量）",
    "e2e: 端到端测试（需要 TEST_PG_DSN + OPENAI_API_KEY）",
    "slow: 执行时间 > 5s 的测试",
]
```

### 2.4 覆盖率目标

| 模块 | 目标行覆盖率 |
|------|------------|
| `sql_validator.py` | 100% |
| `models.py` | 95%+ |
| `config.py` | 90%+ |
| `db_executor.py` | 90%+ |
| `nl2sql.py` | 95%+ |
| `result_validator.py` | 95%+ |
| `schema_cache.py` | 70%（核心组装逻辑需覆盖，fetch SQL 在集成测试覆盖）|
| `server.py` | 80%+ |

---

## 3. 单元测试计划

### 3.1 新增文件：`tests/test_config.py`（全部新增）

**目标**: 覆盖 `config.py` 的全部公共 API，当前覆盖率 0%。

```python
# 测试用例清单（TC = Test Case）

# TC-CFG-01: DatabaseConfig.dsn 基本构造
def test_database_config_dsn_basic():
    """基础 DSN 格式正确"""
    # 输入: alias="main", host="localhost", port=5432, dbname="mydb",
    #       user="admin", password="secret"
    # 预期: "postgresql://admin:secret@localhost:5432/mydb"

# TC-CFG-02: DatabaseConfig.dsn 密码包含特殊字符
def test_database_config_dsn_password_special_chars():
    """密码中的 @、/、? 等特殊字符应被 URL 编码"""
    # 输入: password="p@ss/w?rd&more"
    # 预期: DSN 中密码部分是 URL 编码后的值
    # 注意: quote_plus("p@ss/w?rd&more") == "p%40ss%2Fw%3Frd%26more"

# TC-CFG-03: DatabaseConfig.dsn 用户名包含特殊字符
def test_database_config_dsn_username_special_chars():
    """用户名中的特殊字符应被 URL 编码"""
    # 输入: user="admin@corp"
    # 预期: URL 中用户名部分被编码

# TC-CFG-04: SecretStr 不在 repr 中暴露密码
def test_database_config_password_not_in_repr():
    """SecretStr 应在 repr/str 中掩码密码"""
    # 输入: password="supersecret"
    # 预期: repr(db) 中不包含 "supersecret"，包含 "**********"

# TC-CFG-05: DatabaseConfig 默认 schemas
def test_database_config_default_schemas():
    """schemas 默认为 ["public"]"""
    # 预期: db.schemas == ["public"]

# TC-CFG-06: DatabaseConfig 多个 schemas
def test_database_config_multiple_schemas():
    """可以配置多个 schema"""
    # 输入: schemas=["public", "analytics"]
    # 预期: db.schemas == ["public", "analytics"]

# TC-CFG-07: ServerConfig 默认值
def test_server_config_defaults():
    """ServerConfig 所有默认值正确"""
    # 预期:
    #   query_timeout_seconds == 30
    #   result_validation_sample_rows == 5
    #   max_result_rows == 1000
    #   auto_retry_on_invalid == False

# TC-CFG-08: OpenAIConfig 默认 model
def test_openai_config_default_model():
    """默认模型为 gpt-4o-mini"""
    # 预期: cfg.model == "gpt-4o-mini"

# TC-CFG-09: AppConfig 从 YAML 文件加载（使用 tmp_path）
def test_app_config_from_yaml(tmp_path):
    """AppConfig 能从 YAML 文件正确加载所有字段"""
    # 步骤:
    #   1. 在 tmp_path 写入 config.yaml
    #   2. AppConfig(_yaml_file=str(config_path))
    # 预期: databases[0].alias == "main", openai.model == "gpt-4o-mini"

# TC-CFG-10: 环境变量覆盖 YAML 值
def test_app_config_env_override(tmp_path, monkeypatch):
    """环境变量（OPENAI__API_KEY）覆盖 YAML 中的值"""
    # 步骤:
    #   1. 写 YAML: openai.api_key: "yaml-key"
    #   2. monkeypatch.setenv("OPENAI__API_KEY", "env-key")
    # 预期: config.openai.api_key.get_secret_value() == "env-key"

# TC-CFG-11: AppConfig 缺少必填字段时报错
def test_app_config_missing_required_fields(tmp_path):
    """缺少 databases 时 AppConfig 应抛出 ValidationError"""
    # 步骤: 写不完整的 YAML（只有 openai 节）
    # 预期: raises ValidationError

# TC-CFG-12: DatabaseConfig.min/max_pool_size 默认值
def test_database_config_pool_size_defaults():
    """连接池大小默认 min=1, max=5"""
    # 预期: db.min_pool_size == 1, db.max_pool_size == 5
```

---

### 3.2 新增文件：`tests/test_db_executor.py`（全部新增）

**目标**: 覆盖 `db_executor.py` 的核心逻辑，重点是 `_serialize_value` 和 `execute_query`。

```python
# TC-EXE-01: _serialize_value — datetime 类型
def test_serialize_value_datetime():
    """datetime 对象应转为 ISO 8601 字符串"""
    # 输入: datetime(2026, 3, 14, 10, 30, 0)
    # 预期: "2026-03-14T10:30:00"

# TC-EXE-02: _serialize_value — datetime 带时区
def test_serialize_value_datetime_with_tz():
    """带时区的 datetime 应保留时区信息"""
    # 输入: datetime(2026, 3, 14, 10, 30, 0, tzinfo=timezone.utc)
    # 预期: "2026-03-14T10:30:00+00:00"

# TC-EXE-03: _serialize_value — date 类型
def test_serialize_value_date():
    """date 对象应转为 ISO 8601 日期字符串"""
    # 输入: date(2026, 3, 14)
    # 预期: "2026-03-14"

# TC-EXE-04: _serialize_value — Decimal 类型
def test_serialize_value_decimal():
    """Decimal 应转为 float"""
    # 输入: Decimal("123.456")
    # 预期: float (约 123.456)

# TC-EXE-05: _serialize_value — bytes 类型
def test_serialize_value_bytes():
    """bytes 应转为 "<binary>" 字符串"""
    # 预期: "<binary>"

# TC-EXE-06: _serialize_value — memoryview 类型
def test_serialize_value_memoryview():
    """memoryview 应转为 "<binary>" 字符串"""
    # 预期: "<binary>"

# TC-EXE-07: _serialize_value — uuid.UUID 类型（BUG 验证）
def test_serialize_value_uuid():
    """uuid.UUID 应转为字符串（验证 HINT-04 bug）"""
    # 输入: uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    # 当前行为（bug）: 返回 UUID 对象，JSON 序列化会失败
    # 期望行为（fix后）: 返回 "550e8400-e29b-41d4-a716-446655440000"
    # 注意: 此测试当前应该 FAIL，标记为 xfail 直到修复

# TC-EXE-08: _serialize_value — None 值
def test_serialize_value_none():
    """None 应原样返回（PostgreSQL NULL）"""
    # 预期: None

# TC-EXE-09: _serialize_value — 基本类型保持不变
@pytest.mark.parametrize("v,expected", [
    (42, 42),
    ("hello", "hello"),
    (True, True),
    (3.14, 3.14),
])
def test_serialize_value_passthrough(v, expected):
    """基本 JSON 安全类型应原样返回"""

# TC-EXE-10: execute_query 正常返回
async def test_execute_query_returns_result(mock_pool):
    """正常 SQL 查询返回正确的 columns、rows、row_count"""
    # mock_pool 返回 [{"id": 1, "name": "alice"}, {"id": 2, "name": "bob"}]
    # 预期: result.columns == ["id", "name"]
    #       result.rows == [[1, "alice"], [2, "bob"]]
    #       result.row_count == 2

# TC-EXE-11: execute_query 零行结果使用 prepare 获取列名
async def test_execute_query_empty_result_uses_prepare(mock_pool):
    """零行结果时调用 prepare() 获取列名，不再是空列表"""
    # mock: conn.fetch 返回 [], conn.prepare().get_attributes() 返回列信息
    # 预期: result.rows == [], result.columns == ["id", "email"]

# TC-EXE-12: execute_query 超时抛出 TimeoutError
async def test_execute_query_timeout_raises(mock_pool):
    """asyncpg.QueryCanceledError 应被转换为 TimeoutError"""
    # mock: conn.fetch 抛出 asyncpg.exceptions.QueryCanceledError
    # 预期: raises TimeoutError with "timed out" in message

# TC-EXE-13: execute_query 设置 statement_timeout
async def test_execute_query_sets_statement_timeout(mock_pool):
    """应执行 SET statement_timeout = {ms}，无引号"""
    # 验证: conn.execute 被调用，参数为 "SET statement_timeout = 5000"（非 "'5000'"）

# TC-EXE-14: execute_query 对 datetime 列应用序列化
async def test_execute_query_serializes_datetime(mock_pool):
    """返回的 rows 中 datetime 值应被序列化为字符串"""
    # mock: 返回包含 datetime 值的 Record
    # 预期: rows 中对应位置是 ISO 字符串

# TC-EXE-15: execute_query limit 截断
async def test_execute_query_respects_limit(mock_pool):
    """返回行数不超过 limit 参数"""
    # mock: conn.fetch 返回 200 行
    # limit=10
    # 预期: result.row_count == 10
```

---

### 3.3 新增文件：`tests/test_schema_cache.py`（全部新增）

**目标**: 覆盖 `schema_cache.py` 的组装逻辑（不依赖真实 DB，Mock asyncpg）。

```python
# TC-SCHEMA-01: load_schema 连接失败返回 is_available=False
async def test_load_schema_connection_error():
    """asyncpg.connect 失败时返回 is_available=False，不抛出异常"""
    # mock: asyncpg.connect 抛出 ConnectionRefusedError
    # 预期: cache.is_available == False, cache.error_message 非空

# TC-SCHEMA-02: load_schema 正常返回 DatabaseSchemaCache
async def test_load_schema_happy_path(mock_conn):
    """正常路径下正确组装 DatabaseSchemaCache"""
    # mock_conn 返回预定义的 tables/columns/indexes/fkeys/types 数据
    # 预期: cache.is_available == True, cache.table_count > 0

# TC-SCHEMA-03: 列按 (schema, table) 正确分组（修正 D-01）
async def test_load_schema_column_grouping(mock_conn):
    """columns 按 (schema_name, table_name) 正确分组到对应 TableSchema"""
    # 有 users 表的 id/name 列和 orders 表的 id/total 列
    # 预期: users.columns == [id, name], orders.columns == [id, total]
    # 反例: 不会把 orders 的 total 列放到 users 表

# TC-SCHEMA-04: 索引按 (schema, table) 正确分组（修正 D-02）
async def test_load_schema_index_grouping(mock_conn):
    """indexes 按表正确分组，不会混入其他表的索引"""

# TC-SCHEMA-05: FK 按 (schema, table) 正确分组
async def test_load_schema_fk_grouping(mock_conn):
    """foreign_keys 按表正确分组"""

# TC-SCHEMA-06: 自定义类型使用 _RawCustomType dataclass（修正 P0）
async def test_load_schema_custom_type_dataclass(mock_conn):
    """custom_types 使用 dataclass 属性访问（.schema_name）而非 dict 访问"""
    # 验证: 不会因为 t["schema_name"] vs t.schema_name 报 TypeError

# TC-SCHEMA-07: VIEW 类型正确映射
async def test_load_schema_view_type(mock_conn):
    """TABLE_TYPE='VIEW' 的对象被标记为 object_type='view'"""

# TC-SCHEMA-08: 无表的空数据库
async def test_load_schema_empty_database(mock_conn):
    """没有表的数据库返回 is_available=True, table_count=0"""

# TC-SCHEMA-09: 多 schema 配置
async def test_load_schema_multiple_schemas(mock_conn):
    """public 和 analytics 两个 schema 中的表都被加载"""

# TC-SCHEMA-10: FK foreign_table 格式为 "schema.table"
async def test_load_schema_fk_full_name_format(mock_conn):
    """ForeignKeyInfo.foreign_table 格式为 'schema_name.table_name'"""
    # 预期: fk.foreign_table == "public.users"（非仅 "users"）

# TC-SCHEMA-11: 索引列顺序正确（WITH ORDINALITY 修正）
async def test_load_schema_index_column_order(mock_conn):
    """多列索引的列顺序与 pg_index.indkey 中的顺序一致"""

# TC-SCHEMA-12: 无索引的表不报错
async def test_load_schema_table_without_indexes(mock_conn):
    """没有非主键索引的表 indexes 字段为空列表"""
```

---

### 3.4 新增文件：`tests/test_server.py`（全部新增）

**目标**: 覆盖 `server.py` 中的 `_resolve_cache` 和四个 MCP tool，使用 Mock 隔离外部依赖。

```python
# ── _resolve_cache 测试 ─────────────────────────────────────────

# TC-SRV-01: 指定存在且可用的 database alias
def test_resolve_cache_found():
    """_resolve_cache(database='main') 返回对应 cache"""

# TC-SRV-02: 指定不存在的 alias
def test_resolve_cache_not_found():
    """_resolve_cache(database='unknown') 抛出 _DatabaseNotFoundError"""

# TC-SRV-03: 指定的 alias 存在但 is_available=False
def test_resolve_cache_unavailable():
    """_resolve_cache(database='broken') 抛出 _DatabaseUnavailableError"""

# TC-SRV-04: 不指定 database，只有一个可用 DB
def test_resolve_cache_single_available():
    """_resolve_cache(None) 单 DB 时自动返回该 DB"""

# TC-SRV-05: 不指定 database，多个可用 DB
def test_resolve_cache_ambiguous():
    """_resolve_cache(None) 多 DB 时抛出 _DatabaseAmbiguousError"""

# TC-SRV-06: 不指定 database，没有可用 DB
def test_resolve_cache_no_available():
    """_resolve_cache(None) 无可用 DB 时抛出 _DatabaseUnavailableError"""

# ── query_to_sql 测试 ──────────────────────────────────────────

# TC-SRV-07: query_to_sql 成功路径
async def test_query_to_sql_success(mock_server_deps):
    """正常查询返回 {sql, database, schemaUsed}（camelCase）"""
    # mock: generate_sql 返回 "SELECT * FROM users"
    #       validate_sql 返回验证通过
    # 预期: result["schemaUsed"] 存在（camelCase）

# TC-SRV-08: query_to_sql DATABASE_NOT_FOUND
async def test_query_to_sql_database_not_found(mock_server_deps):
    """指定不存在的 database 返回 errorCode=DATABASE_NOT_FOUND"""

# TC-SRV-09: query_to_sql DATABASE_AMBIGUOUS
async def test_query_to_sql_database_ambiguous(mock_server_deps):
    """多 DB 且不指定 database 返回 errorCode=DATABASE_AMBIGUOUS"""

# TC-SRV-10: query_to_sql LLM_ERROR
async def test_query_to_sql_llm_error(mock_server_deps):
    """generate_sql 抛出异常时返回 errorCode=LLM_ERROR"""

# TC-SRV-11: query_to_sql VALIDATION_FAILED
async def test_query_to_sql_validation_failed(mock_server_deps):
    """validate_sql 返回错误时返回 errorCode=VALIDATION_FAILED"""

# ── query_to_result 测试 ────────────────────────────────────────

# TC-SRV-12: query_to_result 成功路径
async def test_query_to_result_success(mock_server_deps):
    """正常查询返回完整结果（sql, columns, rows, rowCount, validation）"""
    # 预期: result["rowCount"] 存在（camelCase）

# TC-SRV-13: query_to_result DB_ERROR（超时）
async def test_query_to_result_db_timeout(mock_server_deps):
    """execute_query 抛出 TimeoutError 时返回 errorCode=DB_ERROR"""

# TC-SRV-14: query_to_result DB_ERROR（查询失败）
async def test_query_to_result_db_error(mock_server_deps):
    """execute_query 抛出其他异常时返回 errorCode=DB_ERROR"""

# TC-SRV-15: query_to_result limit 参数截断
async def test_query_to_result_limit_clamped(mock_server_deps):
    """limit > 1000 被截断为 1000，limit < 1 被截断为 1"""

# TC-SRV-16: query_to_result validation_skipped 正确传递
async def test_query_to_result_validation_skipped(mock_server_deps):
    """validate_result 返回 validation_skipped=True 时正确传递到输出"""

# ── list_databases 测试 ─────────────────────────────────────────

# TC-SRV-17: list_databases 返回所有数据库
async def test_list_databases_all(mock_server_deps):
    """list_databases 返回 {databases: [...]}"""

# TC-SRV-18: list_databases camelCase 字段
async def test_list_databases_camelcase(mock_server_deps):
    """输出中的字段为 camelCase（如 schemaCachedAt、tableCount、isAvailable）"""

# TC-SRV-19: list_databases 包含不可用的数据库
async def test_list_databases_includes_unavailable(mock_server_deps):
    """is_available=False 的数据库也出现在列表中，schemaCachedAt=null"""

# ── refresh_schema 测试 ─────────────────────────────────────────

# TC-SRV-20: refresh_schema 刷新全部数据库
async def test_refresh_schema_all(mock_server_deps):
    """不传 database 时刷新所有配置的数据库"""

# TC-SRV-21: refresh_schema 刷新单个数据库（修正 D-03）
async def test_refresh_schema_single_by_alias(mock_server_deps):
    """database='main' 时只刷新 alias='main' 的数据库，不刷新其他"""

# TC-SRV-22: refresh_schema 数据库不存在
async def test_refresh_schema_not_found(mock_server_deps):
    """database='unknown' 时返回 errorCode=DATABASE_NOT_FOUND"""

# TC-SRV-23: refresh_schema 返回 duration_seconds
async def test_refresh_schema_duration(mock_server_deps):
    """返回 {refreshed, failed, durationSeconds}（camelCase）"""
```

---

### 3.5 修复现有测试

#### 3.5.1 `tests/test_sql_validator.py` — 修复 WARN-07

当前第 29 行：
```python
("", "Only SELECT"),  # ❌ 实际错误是 "Empty SQL"
```
修正为：
```python
("", "Empty SQL"),  # ✅
```

#### 3.5.2 `tests/test_models.py` — 强化断言

当前 `test_relevant_tables_max_tables_limit` 断言 `len(result) <= len(tables)` 过于宽松：
```python
# 原:
assert len(result) <= len(tables)
# 修正: 50 张表无 FK，max_tables=5 时结果恰好等于 5
assert len(result) == 5
```

新增缺失测试：
```python
# TC-MODEL-ADD-01: relevance_score 直接测试
def test_relevance_score_match():
    """keywords 与表名/列名有重叠时返回正数"""
    table = make_table("users", columns=[ColumnInfo(name="id", ...), ...])
    score = table.relevance_score({"users", "id"})
    assert score == 2  # "users" + "id"

def test_relevance_score_no_match():
    """keywords 与表无任何重叠时返回 0"""
    table = make_table("orders")
    score = table.relevance_score({"users", "email"})
    assert score == 0

# TC-MODEL-ADD-02: _tokenize_query 中英文混合
def test_tokenize_query_mixed():
    """中英文混合查询同时提取英文单词和中文字符"""
    from pg_mcp.models import _tokenize_query
    tokens = _tokenize_query("查询users的email信息")
    assert "users" in tokens
    assert "email" in tokens
    assert "查" in tokens
    assert "信" in tokens
    # 停用词被过滤
    assert "的" not in tokens

# TC-MODEL-ADD-03: object_type view
def test_table_schema_view_type():
    """object_type='view' 时 to_prompt_text 包含表名"""
    table = TableSchema(..., object_type="view", ...)
    assert "Table:" in table.to_prompt_text()
```

---

## 4. 集成测试计划

集成测试需要真实的 PostgreSQL 连接，通过 `TEST_PG_DSN` 环境变量提供。

### 4.1 测试数据库 Schema（conftest.py 中创建）

```sql
-- 在 conftest.py 的 session-scoped fixture 中创建测试表
CREATE TABLE IF NOT EXISTS test_users (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    score       NUMERIC(10, 2),
    avatar      BYTEA,
    ext_id      UUID DEFAULT gen_random_uuid()
);

CREATE TABLE IF NOT EXISTS test_orders (
    id          SERIAL PRIMARY KEY,
    user_id     INT REFERENCES test_users(id),
    total       NUMERIC(12, 4),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE VIEW test_active_users AS
    SELECT id, email, name FROM test_users WHERE name IS NOT NULL;

CREATE TYPE test_status AS ENUM ('active', 'inactive', 'pending');

CREATE INDEX IF NOT EXISTS test_users_email_idx ON test_users(email);
CREATE INDEX IF NOT EXISTS test_orders_user_idx ON test_orders(user_id);
```

### 4.2 集成测试用例

```python
# IT-01: 基本连接测试（已实现）
async def test_pg_connection(pg_dsn): ...

# IT-02: SELECT 1 执行（已实现）
async def test_execute_select_one(pg_pool): ...

# IT-03: 只读强制（已实现）
async def test_execute_readonly_enforced(pg_pool): ...

# IT-04: Schema 加载（已实现，但需扩展）
async def test_schema_load(pg_dsn): ...

# 新增集成测试：

# IT-05: Schema 加载包含 VIEW
async def test_schema_load_includes_views(pg_dsn, test_schema):
    """加载的 schema 中包含 test_active_users（VIEW 类型）"""
    # 预期: "public.test_active_users" 在 cache.tables 中
    #       cache.tables["public.test_active_users"].object_type == "view"

# IT-06: Schema 加载包含 FK 关系
async def test_schema_load_includes_foreign_keys(pg_dsn, test_schema):
    """test_orders.user_id → test_users.id 的 FK 被正确加载"""
    # 预期: orders 表有 ForeignKeyInfo 指向 public.test_users

# IT-07: Schema 加载包含自定义 Enum 类型
async def test_schema_load_includes_enum_types(pg_dsn, test_schema):
    """test_status ENUM 类型被加载"""
    # 预期: cache.custom_types 中包含 type_name="test_status"
    #       enum_values == ["active", "inactive", "pending"]

# IT-08: 执行查询返回 TIMESTAMPTZ 列（序列化验证）
async def test_execute_query_with_timestamp_column(pg_pool, test_data):
    """包含 TIMESTAMPTZ 列的查询结果正确序列化为 ISO 字符串"""
    result = await execute_query(pg_pool, "SELECT created_at FROM test_users LIMIT 1", ...)
    assert isinstance(result.rows[0][0], str)  # 不是 datetime 对象

# IT-09: 执行查询返回 NUMERIC 列（Decimal 序列化）
async def test_execute_query_with_numeric_column(pg_pool, test_data):
    """NUMERIC 列在结果中为 float，不是 Decimal"""
    result = await execute_query(pg_pool, "SELECT score FROM test_users LIMIT 1", ...)
    assert isinstance(result.rows[0][0], (float, type(None)))

# IT-10: 执行查询返回 UUID 列（xfail 直到修复 HINT-04）
@pytest.mark.xfail(reason="HINT-04: uuid.UUID not handled in _serialize_value")
async def test_execute_query_with_uuid_column(pg_pool, test_data):
    """UUID 列在结果中为字符串，不是 uuid.UUID 对象"""
    result = await execute_query(pg_pool, "SELECT ext_id FROM test_users LIMIT 1", ...)
    assert isinstance(result.rows[0][0], str)

# IT-11: 零行查询返回正确列名
async def test_execute_query_empty_result_columns(pg_pool):
    """WHERE 条件过滤所有行时返回正确列名"""
    result = await execute_query(pg_pool, "SELECT id, email FROM test_users WHERE id = -9999", ...)
    assert result.rows == []
    assert "id" in result.columns
    assert "email" in result.columns

# IT-12: statement_timeout 测试
async def test_execute_query_statement_timeout(pg_pool):
    """超出 statement_timeout 的查询抛出 TimeoutError"""
    # 使用 pg_sleep 模拟超时
    with pytest.raises(TimeoutError):
        await execute_query(pg_pool, "SELECT pg_sleep(10)", limit=1, timeout_seconds=1)

# IT-13: 不可达数据库返回 is_available=False（已实现）
async def test_schema_load_unavailable_db(): ...
```

---

## 5. E2E 测试计划

E2E 测试需要真实的 PostgreSQL 和 OpenAI API Key（`OPENAI_API_KEY` 环境变量）。

```python
# E2E-01: 完整 NL → SQL → 执行 → 验证流程
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_pipeline_simple_query(running_server, test_schema, test_data):
    """自然语言查询 'show all users' 返回用户列表"""
    # 调用 query_to_result tool
    # 预期: result.columns 包含 id/email/name
    #       result.row_count > 0
    #       result.validation.isMeaningful == True

# E2E-02: 包含聚合的查询
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_pipeline_aggregate_query(running_server, test_schema, test_data):
    """'count total orders' 返回一个包含 count 的结果"""

# E2E-03: 跨表 JOIN 查询
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_pipeline_join_query(running_server, test_schema, test_data):
    """'show orders with user email' 触发 JOIN"""

# E2E-04: 中文自然语言查询
@pytest.mark.e2e
@pytest.mark.slow
async def test_full_pipeline_chinese_query(running_server, test_schema, test_data):
    """'查询所有用户的邮件地址' 返回正确结果"""

# E2E-05: 恶意 SQL 注入尝试被拦截
@pytest.mark.e2e
async def test_sql_injection_attempt_blocked(running_server, test_schema):
    """即使 LLM 生成了 DELETE 语句，也应被 sql_validator 拒绝"""
```

---

## 6. 边界情况与负面测试

### 6.1 SQL 验证器边界情况

```python
# TC-EDGE-SQL-01: CTE（WITH 子句）
def test_validate_sql_cte(): ...

# TC-EDGE-SQL-02: UNION ALL
def test_validate_sql_union_all():
    sql = "SELECT id FROM users UNION ALL SELECT id FROM orders"
    # 应通过（整体是 SELECT）

# TC-EDGE-SQL-03: 窗口函数
def test_validate_sql_window_function():
    sql = "SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) FROM users"
    # 应通过

# TC-EDGE-SQL-04: SELECT INTO（PostgreSQL）
def test_validate_sql_select_into_rejected():
    sql = "SELECT * INTO backup_users FROM users"
    # 应被拒绝（sqlglot 解析为 CREATE 或 Insert）

# TC-EDGE-SQL-05: 字符串中含有 "--"（可能误判）
def test_validate_sql_string_with_double_dash():
    sql = "SELECT * FROM logs WHERE message = 'Error -- retrying'"
    # 当前行为（已知限制）: 被 layer-1 拒绝
    # 此测试记录已知限制，不要求通过
    _, err = validate_sql(sql)
    assert err is not None  # 已知误报

# TC-EDGE-SQL-06: 分号结尾
def test_validate_sql_trailing_semicolon():
    sql = "SELECT * FROM users;"
    out, err = validate_sql(sql)
    assert err is None  # rstrip(";") 处理

# TC-EDGE-SQL-07: 子查询
def test_validate_sql_subquery():
    sql = "SELECT id FROM users WHERE id IN (SELECT user_id FROM orders)"
    out, err = validate_sql(sql)
    assert err is None
```

### 6.2 模型边界情况

```python
# TC-EDGE-MODEL-01: 超大 schema（压力测试）
def test_get_relevant_tables_large_schema():
    """500 张表时 get_relevant_tables 在合理时间内（<100ms）返回"""

# TC-EDGE-MODEL-02: 所有表都有相同 relevance_score
def test_get_relevant_tables_all_same_score():
    """当所有表得分相同时，返回前 max_tables 个（不崩溃）"""

# TC-EDGE-MODEL-03: FK 指向不在 cache 中的外部表
def test_get_relevant_tables_fk_to_unknown_table():
    """FK target 不在 tables 中时，不崩溃（不添加不存在的表）"""

# TC-EDGE-MODEL-04: 查询只含停用词
def test_get_relevant_tables_only_stopwords():
    """查询 'show all the list of' 只含停用词，keywords 为空集"""
    # 预期: 返回前 max_tables 个表（相同分数下稳定排序）

# TC-EDGE-MODEL-05: 空查询字符串
def test_get_relevant_tables_empty_query():
    """空字符串查询不崩溃，返回前 max_tables 个表"""
```

### 6.3 配置边界情况

```python
# TC-EDGE-CFG-01: config.yaml 不存在（graceful fallback）
def test_app_config_missing_yaml(tmp_path):
    """当 yaml_file 不存在时，pydantic-settings 应 graceful fallback，
    不能直接连 DB 但也不应在 import 时崩溃"""

# TC-EDGE-CFG-02: 非常长的密码（512 chars）
def test_database_config_long_password():
    """长密码被 URL 编码后 DSN 格式仍然正确"""

# TC-EDGE-CFG-03: schemas 为空列表
def test_database_config_empty_schemas():
    """schemas=[] 时不报 ValidationError（下游会查询空列表）"""
```

---

## 7. 性能基准测试

```python
# PF-01: sql_validator 性能
def test_sql_validator_performance(benchmark):
    """validate_sql 单次调用 < 10ms"""
    benchmark(validate_sql, "SELECT * FROM users JOIN orders ON users.id = orders.user_id")

# PF-02: get_relevant_tables 性能
def test_get_relevant_tables_performance(benchmark, large_cache):
    """500 张表时 get_relevant_tables < 50ms"""
    benchmark(large_cache.get_relevant_tables, "find user orders", max_tables=20)

# PF-03: to_prompt_text 性能（宽表）
def test_to_prompt_text_wide_table_performance(benchmark):
    """100 列的宽表 to_prompt_text < 5ms"""
    table = make_table_with_many_columns(100)
    benchmark(table.to_prompt_text)
```

---

## 8. CI/CD 配置

### 8.1 pytest.ini_options 更新

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "unit: pure unit tests, no external dependencies",
    "integration: requires real PostgreSQL (TEST_PG_DSN)",
    "e2e: end-to-end tests (TEST_PG_DSN + OPENAI_API_KEY)",
    "slow: execution time > 5s",
]
# CI 默认只运行 unit 和 integration（不含 e2e）
addopts = "-m 'not e2e'"
```

### 8.2 运行命令

```bash
# 只运行单元测试（最快，无外部依赖）
uv run pytest tests/ -m "not integration and not e2e" -v

# 运行单元 + 集成测试
TEST_PG_DSN="postgresql://user:pass@localhost/testdb" \
uv run pytest tests/ -m "not e2e" -v

# 运行全部测试（包含 E2E）
TEST_PG_DSN="postgresql://user:pass@localhost/testdb" \
OPENAI_API_KEY="sk-..." \
uv run pytest tests/ -v

# 生成覆盖率报告
uv run pytest tests/ -m "not e2e" --cov=pg_mcp --cov-report=term-missing --cov-report=html
```

### 8.3 GitHub Actions 建议（`.github/workflows/test.yml`）

```yaml
name: Tests
on: [push, pull_request]
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: cd w5/pg-mcp && uv sync
      - run: cd w5/pg-mcp && uv run pytest tests/ -m "not integration and not e2e" -v

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: testdb
        ports: ["5432:5432"]
        options: --health-cmd pg_isready
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: cd w5/pg-mcp && uv sync
      - run: cd w5/pg-mcp && uv run pytest tests/ -m "integration and not e2e" -v
        env:
          TEST_PG_DSN: postgresql://postgres:test@localhost/testdb
```

---

## 9. 测试数据管理

### 9.1 Fixture 层次

```
conftest.py (session scope)
├── pg_dsn            # 从 TEST_PG_DSN 环境变量获取
├── pg_pool           # asyncpg.Pool
├── test_schema       # 创建/清理测试表（DDL）
└── test_data         # 插入测试数据（DML）

conftest.py (function scope)
├── mock_openai_client   # 返回成功 SQL 的 mock
├── mock_pool            # 模拟 asyncpg Pool
├── mock_conn            # 模拟 asyncpg Connection
└── mock_server_deps     # 注入所有 server.py 全局变量
```

### 9.2 mock_server_deps fixture 设计

```python
@pytest.fixture
def mock_server_deps(monkeypatch):
    """注入 server.py 全局变量，隔离 MCP tool 单元测试"""
    import pg_mcp.server as server_module
    from datetime import datetime, UTC

    cache = DatabaseSchemaCache(
        alias="main", host="localhost", dbname="testdb",
        tables={"public.users": make_test_table()},
        custom_types=[], cached_at=datetime.now(UTC), is_available=True
    )
    mock_openai = AsyncMock()
    mock_pool = AsyncMock()

    monkeypatch.setattr(server_module, "_caches", {"main": cache})
    monkeypatch.setattr(server_module, "_pools", {"main": mock_pool})
    monkeypatch.setattr(server_module, "_openai", mock_openai)
    monkeypatch.setattr(server_module, "_config", make_test_config())

    return {
        "cache": cache,
        "openai": mock_openai,
        "pool": mock_pool,
    }
```

---

## 10. 测试优先级与实施顺序

| 优先级 | 任务 | 影响 | 预计工作量 |
|--------|------|------|----------|
| P0 | 修复 `test_sql_validator.py` 空字符串断言（WARN-07） | 当前测试通过率 | 极小 |
| P0 | `test_db_executor.py` — `_serialize_value` UUID xfail | 已知 bug 文档化 | 小 |
| P1 | `test_config.py` 全部 12 个测试 | 配置加载零覆盖 | 中 |
| P1 | `test_db_executor.py` 全部 15 个测试 | 序列化逻辑无覆盖 | 中 |
| P1 | `test_server.py` — `_resolve_cache` 6 个测试 | 核心路由逻辑 | 小 |
| P1 | `test_server.py` — 四个 tool 的 error case | 错误处理 | 中 |
| P2 | `test_schema_cache.py` 全部 12 个测试（mock asyncpg） | 组装逻辑 | 大 |
| P2 | 集成测试扩展（IT-05 to IT-13） | 真实 DB 场景 | 中 |
| P3 | E2E 测试（E2E-01 to E2E-05） | 完整流程 | 大 |
| P3 | 性能基准测试 | 非功能需求 | 中 |

---

## 11. 测试文档与报告

### 11.1 测试报告格式

每次 CI 运行生成：
- `pytest-junit.xml`（兼容 GitHub Actions / Jenkins）
- `htmlcov/`（HTML 覆盖率报告）

### 11.2 Definition of Done（测试完成标准）

- [ ] 所有 P0、P1 测试用例已实现并通过
- [ ] `uv run pytest tests/ -m "not integration and not e2e"` 全绿
- [ ] 单元测试总体行覆盖率 ≥ 85%
- [ ] `sql_validator.py` 覆盖率 = 100%
- [ ] `db_executor._serialize_value` UUID bug 已通过 xfail 记录
- [ ] `test_sql_validator.py` 空字符串断言已修复
- [ ] 集成测试在有 PG 的环境下全绿（允许 IT-10 xfail）
- [ ] CI pipeline 通过

---

## 附录 A：测试用例完整索引

| ID | 文件 | 测试名 | 类型 | 优先级 |
|----|------|--------|------|--------|
| TC-CFG-01~12 | test_config.py | DatabaseConfig, AppConfig | 单元 | P1 |
| TC-EXE-01~15 | test_db_executor.py | _serialize_value, execute_query | 单元 | P1 |
| TC-SCHEMA-01~12 | test_schema_cache.py | load_schema, grouping | 单元 | P2 |
| TC-SRV-01~23 | test_server.py | _resolve_cache, 4 tools | 单元 | P1 |
| TC-EDGE-SQL-01~07 | test_sql_validator.py | 边界情况 | 单元 | P1 |
| TC-EDGE-MODEL-01~05 | test_models.py | 边界情况 | 单元 | P2 |
| TC-EDGE-CFG-01~03 | test_config.py | 边界情况 | 单元 | P2 |
| IT-01~13 | test_integration.py | 集成场景 | 集成 | P1~P2 |
| E2E-01~05 | test_e2e.py | 完整流程 | E2E | P3 |
| PF-01~03 | test_performance.py | 性能基准 | 性能 | P3 |

**总计**: 约 98 个测试用例（含现有 55 个，新增约 43 个）
