# 代码深度审查报告：pg-mcp 实现

**审查目标**: `w5/pg-mcp/src/` 和 `w5/pg-mcp/tests/`
**审查日期**: 2026-03-14
**参考规范**: `specs/w5/0002-pg-mcp-design.md`, `specs/w5/0004-pg-mcp-impl-plan.md`
**代码语言**: Python 3.11+

---

## 概览

| 指标 | 数值 |
|------|------|
| 审查文件数 | 12（源码 8 + 测试 4） |
| 总代码行数 | 约 1,234（排除空文件和 conftest） |
| 与规范符合度 | ~92% |
| 严重问题（🔴） | 3 |
| 警告（🟡） | 7 |
| 建议（💡） | 6 |

---

## 规范符合性检查

| 规范要求 | 实现状态 | 说明 |
|---------|---------|------|
| 四个 MCP Tool 均已实现 | ✅ | `query_to_sql`, `query_to_result`, `list_databases`, `refresh_schema` 全部存在 |
| MCP Tool 输出 camelCase | ✅ | `model_dump(by_alias=True)` 配合 `alias_generator=to_camel` |
| 错误码规范返回 | ✅ | `DATABASE_NOT_FOUND`, `DATABASE_AMBIGUOUS`, `NO_DATABASE_AVAILABLE`, `LLM_ERROR`, `VALIDATION_FAILED`, `DB_ERROR` |
| Pydantic V2 全量使用 | ✅ | 所有模型均继承 `BaseModel`，使用 `ConfigDict` |
| asyncpg 只读连接池 | ✅ | `server_settings={"default_transaction_read_only": "true"}` |
| SQL 四层验证 | ✅ | 注释检测 + AST 解析 + 多语句检测 + 只允许 SELECT |
| LIMIT 自动注入 | ✅ | 使用 sqlglot 链式 API `stmt.limit(max_rows)`，修正了 D-10 |
| SecretStr 保护敏感字段 | ✅ | `password` 和 `api_key` 均为 `SecretStr` |
| DSN URL 编码 | ✅ | `quote_plus` 防止密码特殊字符破坏 DSN（规范未要求但实现超出预期） |
| D-01/D-02 修正（schema 组装）| ✅ | 使用 `_RawTable`/`_RawColumn` 等临时 dataclass 分离 fetch 与组装 |
| D-03 修正（refresh_schema alias 查找）| ✅ | `[db for db in _config.databases if db.alias == database]` |
| D-05 修正（statement_timeout 无引号）| ✅ | `f"SET statement_timeout = {int(timeout_seconds * 1000)}"` |
| D-06 修正（零行结果同连接内 prepare）| ✅ | `prepare` 在同一 `acquire` 块内执行 |
| D-07 修正（pydantic-settings[yaml]）| ✅ | `pyproject.toml` 已使用 `pydantic-settings[yaml]>=2.0` |
| D-08 修正（lifespan 签名）| ✅ | `async def lifespan(app: FastMCP)` |
| D-09 修正（去掉 beta 前缀）| ✅ | `client.chat.completions.parse(...)` |
| D-10 修正（LIMIT 链式 API）| ✅ | `stmt = stmt.limit(max_rows)` |
| `asyncio.gather` 并发初始化 | ✅ | `lifespan` 和 `schema_cache.py` 中均使用 `asyncio.gather` |
| 连接池 min/max 配置 | ✅ | `min_pool_size`, `max_pool_size` 均可配置 |
| `--config` CLI 参数 | ✅ | `argparse` 支持 `--config` 覆盖 YAML 路径 |
| `pydantic-settings` YAML 加载 | ⚠️ | `AppConfig(_yaml_file=args.config)` 使用私有参数，存在版本兼容风险 |
| 多 DB 时明确指定 | ✅ | `_DatabaseAmbiguousError` 要求明确指定 database |
| D-04 多 DB 场景说明 | ✅ | 已通过异常消息说明"请指定 database 参数" |
| `test_schema_cache.py` | ❌ | 规范要求有此测试文件，实际只有 `test_integration.py` 包含 schema 测试 |
| `_serialize_value` JSON 序列化 | ✅ | `datetime`, `Decimal`, `bytes` 均有处理 |
| `build_schema_text` 空列表处理 | ✅ | 返回 `"(no schema available)"` |

---

## 问题汇总

### 🔴 严重问题（必须修复）

**[RED-01] `server.py:39` — `mcp` 变量被双重赋值，第一次定义无效**

`server.py` 第 39 行定义了 `mcp = FastMCP("pg-mcp")`，第 90 行又以 `mcp = FastMCP("pg-mcp", lifespan=lifespan)` 重新赋值。这意味着第 39 行的对象被立即丢弃，但第 39 行之前的代码（如全局变量声明）依赖的是第 90 行的对象。实际功能上第 90 行的 `mcp` 才是真正使用的实例，第 39 行是多余的垃圾赋值，容易造成误解，且如果有代码在第 39-90 行之间调用了 `mcp`，将使用错误的对象。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 39 行和第 90 行。

**[RED-02] `server.py:251` — `query_to_result` 中 `auto_retry` 分支的 `schema_text` 变量可能未定义**

在 `query_to_result` 函数中，`schema_text` 在"生成 SQL"的 `try` 块内被赋值（第 215 行）。若该 `try` 块因异常返回错误，则不会到达 `auto_retry` 分支；但若 `generate_sql` 本身成功而后续步骤失败，流程才会进入 `auto_retry`。实际上此路径下 `schema_text` 已赋值，但由于 `try/except` 跨越赋值点，Python 静态分析工具（如 `mypy`/`ruff` 的未初始化检测）会报 `schema_text` possibly unbound，是一个潜在的可维护性隐患。在 `try` 块外声明初始值可消除此问题。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 210-253 行。

**[RED-03] `result_validator.py` — `except (asyncio.TimeoutError, Exception)` 已被改进但仍存在过度捕获残留**

实现版本已将宽泛的 `except (asyncio.TimeoutError, Exception)` 拆分为 `asyncio.TimeoutError` 和 `openai.APIError` 两个分支，并注明"其他未预期异常继续向上抛出"。这是正确的。**但** `asyncio.wait_for` 包装的 `coro` 中，若 `openai>=1.50` 的 `client.chat.completions.parse` 内部抛出 `asyncio.CancelledError`（这是 asyncio 取消任务的标准方式），当前代码中 `asyncio.TimeoutError` 的捕获不会捕获 `CancelledError`，因为 Python 3.11+ 中 `asyncio.TimeoutError` 是 `TimeoutError` 的子类，而 `CancelledError` 是 `BaseException`。在极端情况下（如外部取消），`CancelledError` 会穿透所有 `except Exception` 块向上传播，这其实是正确行为，但缺少文档注释说明。此问题评级为严重，因为无注释的行为会导致维护人员在调试时误加 `except BaseException`。

受影响文件：`w5/pg-mcp/src/pg_mcp/result_validator.py`，第 78-93 行。

---

### 🟡 警告（建议修复）

**[WARN-01] `config.py:48` — `AppConfig` 没有 `yaml_file` 字段，但 `server.py` 传入 `_yaml_file` 私有参数**

设计规范要求 `SettingsConfigDict(yaml_file="config.yaml")`，实现按规范。但 `main()` 中用 `AppConfig(_yaml_file=args.config)` 传入私有参数来覆盖 YAML 路径。`_yaml_file` 是 `pydantic-settings` 的内部参数名，在不同版本中可能变化（或不被支持）。更健壮的做法是在 `AppConfig` 中显式添加一个 `yaml_file` 字段，或通过环境变量覆盖（如 `PG_MCP__YAML_FILE`）。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 366 行；`w5/pg-mcp/src/pg_mcp/config.py`，第 45-49 行。

**[WARN-02] `server.py` — 工具函数中使用裸 `assert` 进行空值检查**

`query_to_sql`（第 163、172 行）和 `query_to_result`（第 197、211 行）使用 `assert _openai is not None` 和 `assert _config is not None`。`assert` 语句在 Python 以 `-O` 优化模式运行时会被完全移除，导致 `NoneType has no attribute ...` 的运行时错误。应改为显式的 `if ... is None: raise RuntimeError(...)` 或通过 `lifespan` 的 `assert` 确保（已存在）加上类型系统的支持。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 163、172、197、211 行。

**[WARN-03] `schema_cache.py` — `asyncio.gather` 在同一连接上并发执行，asyncpg 单连接不是线程安全的**

`load_schema` 中使用 `asyncio.gather` 并发调用 `_fetch_tables`, `_fetch_columns`, `_fetch_indexes`, `_fetch_foreign_keys`, `_fetch_custom_types`，但这五个调用共享同一个 `conn` 对象。asyncpg 的 `Connection` 对象本身是协程安全的（不是线程安全的），但同一时刻只能有一个查询在连接上运行。`asyncio.gather` 会并发调度这五个协程，asyncpg 内部会将后续请求排队等待，实际上是串行执行而非真正并发。代码的注释写"并发执行 5 个 fetch"是误导性的。更好的做法是用连接池 + 多连接并发，或保持顺序执行并去掉注释。

受影响文件：`w5/pg-mcp/src/pg_mcp/schema_cache.py`，第 244-251 行及第 244 行注释。

**[WARN-04] `db_executor.py:76` — 外部 `ExecutionResult` 的 `execution_time_ms` 重新计算时间，但包含了 `prepare` 的时间**

在正常路径（有数据行），`elapsed_ms` 在第 55 行已计算（fetch 完成后），而最终返回的 `ExecutionResult`（第 72-77 行，在 `async with` 块外部）使用了重新计算的 `(time.monotonic() - start) * 1000`，这包含了退出 `acquire` 上下文的时间（连接释放回池）。两者逻辑不一致：零行分支用的是 fetch 后的时间，有数据分支用的是 acquire 退出后的时间。应统一。

受影响文件：`w5/pg-mcp/src/pg_mcp/db_executor.py`，第 55 行对比第 76 行。

**[WARN-05] `models.py` — `PgMcpError` 模型定义但从未使用**

第 205-210 行定义了 `PgMcpError` 模型，但在 `server.py` 的所有错误返回路径中，都直接返回 `{"errorCode": ..., "message": ...}` 字典而非使用此模型。这是 YAGNI 原则的违反——定义了但不使用的代码增加维护负担。要么用 `PgMcpError` 统一错误格式，要么删除该模型。

受影响文件：`w5/pg-mcp/src/pg_mcp/models.py`，第 203-210 行；`w5/pg-mcp/src/pg_mcp/server.py`，所有 `return {"errorCode": ...}` 处。

**[WARN-06] `server.py` — `refresh_schema` 中并发刷新时 `refreshed`/`failed` 列表存在并发写入竞争**

`refresh_one` 协程（第 321-335 行）通过闭包修改外部的 `refreshed` 和 `failed` 列表，并通过 `asyncio.gather` 并发调用。Python 的 `list.append` 在 asyncio 协程中是安全的（GIL + 单线程事件循环），但这依赖于 CPython 实现细节。在其他运行时（PyPy）或真正的多线程场景下会有问题。更稳健的做法是让 `refresh_one` 返回结果元组，由调用方汇总。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 318-337 行。

**[WARN-07] `test_sql_validator.py:29` — 空字符串测试的期望错误信息不准确**

`FAIL_CASES` 中 `("", "Only SELECT")` 期望错误信息包含 "Only SELECT"。但 `validate_sql("")` 的实际执行路径：`"".strip()` 是空字符串，注释检测通过，`"".rstrip(";")` 仍为空，`sqlglot.parse("")` 返回空列表（`not statements`），因此实际返回 `"Empty SQL"` 而非包含 "Only SELECT" 的信息。该测试用例的期望错误子串是错误的，测试可能因此失败。

受影响文件：`w5/pg-mcp/tests/test_sql_validator.py`，第 29 行。

---

### 💡 建议（可选优化）

**[HINT-01] `models.py` — `get_relevant_tables` 中的中文分词仅支持单字匹配**

`_tokenize_query` 将中文逐字拆分（如"用户"→{"用","户"}），这对于多字词（如"订单号"）的匹配效果很差。即使是简单的 2-gram 分词也会显著提升中文查询的表关联精度。当前实现可以接受，但应在注释中明确说明此限制。

受影响文件：`w5/pg-mcp/src/pg_mcp/models.py`，第 99-104 行。

**[HINT-02] `nl2sql.py` — `_SCHEMA_PLACEHOLDER` 常量定义方式略显绕道**

定义 `_SCHEMA_PLACEHOLDER = "{schema_text}"` 再用 `str.replace` 的目的是防止 `schema_text` 中含有 `{...}` 导致 `str.format` 失败，这是正确的防御。但注释说明不够清晰。更 Pythonic 的方式是使用 `string.Template`（`$schema_text` 占位符），可避免 `{...}` 冲突且语义清晰。

受影响文件：`w5/pg-mcp/src/pg_mcp/nl2sql.py`，第 9-39 行。

**[HINT-03] `server.py` — `_get_pool` 帮助函数的价值有限**

`_get_pool`（第 134-138 行）仅是 `_pools.get` 加一个 `None` 检查，只在 `query_to_result` 中调用一次。`query_to_sql` 并不需要连接池，而 `list_databases` 和 `refresh_schema` 直接操作 `_caches`/`_pools`。此函数是轻微过度封装，可以直接在调用处内联。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 134-138 行。

**[HINT-04] `db_executor.py` — `_serialize_value` 未处理 `uuid.UUID` 类型**

`_serialize_value` 处理了 `datetime`, `date`, `Decimal`, `bytes`，但未处理 `uuid.UUID`。PostgreSQL 的 UUID 列在 asyncpg 中返回 `uuid.UUID` 对象，JSON 序列化时会失败。实现计划文档 T-06 提到"datetime/Decimal/UUID 类型正确序列化"，但实际实现遗漏了 UUID。

受影响文件：`w5/pg-mcp/src/pg_mcp/db_executor.py`，第 14-22 行。

**[HINT-05] `server.py` — `query_to_result` 的 `auto_retry` 分支代码重复度高**

`auto_retry_on_invalid` 分支（第 251-269 行）完整重复了"生成 SQL → 验证 → 执行 → 语义验证"的逻辑，约 20 行代码是前面流程的复制。建议提取为内部辅助函数 `_run_pipeline(query, schema_text, limit) -> tuple[ExecutionResult, ValidationInfo, str]`，供主流程和重试流程共同调用。

受影响文件：`w5/pg-mcp/src/pg_mcp/server.py`，第 210-269 行。

**[HINT-06] `tests/test_models.py:202` — `test_relevant_tables_max_tables_limit` 断言过于宽松**

`assert len(result) <= len(tables)` 只验证结果不超过总表数，但 `max_tables=5` 加 FK 扩展后的实际上限应该更具体。考虑到测试数据中 50 张表均无 FK，结果应恰好等于 5，可以加上更精确的断言 `assert len(result) == 5`。

受影响文件：`w5/pg-mcp/tests/test_models.py`，第 201-202 行。

---

## 详细审查结果

### 架构和设计

**模块划分**：整体划分合理，严格按照设计规范的分层架构实现：
- `config.py`：纯配置，无业务逻辑
- `models.py`：数据模型，包含少量业务方法（`to_prompt_text`, `relevance_score`, `get_relevant_tables`）
- `schema_cache.py`：数据库 Schema 发现，使用临时 dataclass 隔离 DB 数据
- `db_executor.py`：查询执行，JSON 序列化处理
- `nl2sql.py`、`result_validator.py`：AI 服务层，各自独立
- `server.py`：MCP 入口，组合各层

**全局状态**：`_caches`, `_pools`, `_openai`, `_config` 四个模块级全局变量通过 `lifespan` 初始化。此模式在 FastMCP 的单进程模型下是可接受的，但 `server.py:39` 存在 `mcp = FastMCP("pg-mcp")` 的重复初始化（见 RED-01）。

**Pydantic V2**：全面使用，`ConfigDict`、`Field(default_factory=...)`、`model_dump(by_alias=True)`、`model_copy(update=...)` 均已正确使用。`from __future__ import annotations` 配合 Python 3.11+ 类型注解规范。

**自定义异常**：`server.py` 中定义了 `_DatabaseNotFoundError`, `_DatabaseAmbiguousError`, `_DatabaseUnavailableError` 三个内部异常类，细粒度地区分错误类型，是对设计规范的正向扩展。

### KISS 原则

**函数长度检查**：
- `server.py::query_to_result`：约 80 行（第 184-277 行），超过 50 行警告阈值，主要是因为 `auto_retry_on_invalid` 分支重复了完整流程（见 HINT-05）
- `schema_cache.py::load_schema`：约 95 行（第 233-330 行），超过 50 行，但逻辑清晰分段，尚可接受
- 其他函数均在 50 行以内

**嵌套层级**：
- `server.py::refresh_schema` 中的 `refresh_one` 内部嵌套最深约 3 层，在边界内
- `server.py::query_to_result` 在 `auto_retry` 分支中 `if/try/if/try` 嵌套 4 层，超过警告阈值

**过度抽象**：无过度抽象，没有不必要的基类、接口或工厂。`_get_pool` 略显多余（见 HINT-03）。

### 代码质量（DRY, YAGNI, SOLID）

**DRY 违反**：
1. `query_to_sql` 和 `query_to_result` 的前半段逻辑完全重复：`_resolve_cache` → `get_relevant_tables` → `build_schema_text` → `generate_sql` → `validate_sql`，约 25 行重复代码（`server.py` 第 151-175 行 vs 第 200-222 行）
2. `auto_retry` 分支再次重复执行 + 验证逻辑（见 HINT-05）

**YAGNI 违反**：
1. `PgMcpError` 模型定义但未使用（见 WARN-05）
2. `server.py:39` 的第一次 `mcp = FastMCP("pg-mcp")` 立即被第 90 行覆盖

**命名清晰度**：整体命名清晰，`_Raw*` 系列 dataclass 前缀 `_` 明确表示内部使用，`_resolve_cache`、`_get_pool` 等辅助函数命名语义明确。

**潜在安全问题**：
- SQL 注入：双重防御（sqlglot 静态验证 + asyncpg 只读连接），无参数化注入风险（Schema 加载使用 `$1` 参数化）
- 凭证泄露：`SecretStr` 保护密码和 API Key，`dsn` 属性不通过 `__repr__` 暴露
- 潜在风险：`SET statement_timeout = {int(timeout_seconds * 1000)}` 中 `timeout_seconds` 来自配置（整型），无注入风险

**测试断言质量**：
- 测试均有具体断言（非空断言 `assert result is not None`），而是 `assert result.is_meaningful is True`，`assert "schemaUsed" in data` 等有意义的断言
- `test_sql_validator.py:29` 的期望字符串有误（见 WARN-07）
- `test_result_validator.py` 覆盖了超时、API 错误、空结果集、编程错误四种异常场景，超出规范要求

### 性能

**asyncio.gather 并发**：
- `lifespan` 中用 `asyncio.gather` 并发初始化多个数据库，正确
- `refresh_schema` 中用 `asyncio.gather` 并发刷新多个数据库，正确
- `schema_cache.py::load_schema` 中对同一连接的五个 fetch 使用 `asyncio.gather` 是伪并发（见 WARN-03）

**Schema 加载效率**：
- 5 个信息系统视图查询均使用参数化 `$1`，安全高效
- 索引查询使用了 `CROSS JOIN LATERAL unnest(ix.indkey::int[]) WITH ORDINALITY` 替代设计文档中的 `array_position(ix.indkey, ...)` 转换问题，修正正确
- 主键索引通过 `AND NOT ix.indisprimary` 排除，减少噪音

**连接池配置**：默认 `min_size=1, max_size=5`，通过配置可调，合理。执行时通过 `acquire` 上下文管理器正确使用池。

**`_serialize_value` 未处理 UUID**（见 HINT-04）：可能导致包含 UUID 列的查询结果序列化失败，影响可靠性。

### 规范符合性

所有 10 个设计文档问题（D-01 至 D-10）均已在实现层面修正，实现还超出规范做了以下改进：
1. `config.py::dsn` 中 `quote_plus` URL 编码（规范未要求）
2. `_DatabaseNotFoundError` 等细粒度自定义异常（规范只用 `ValueError`/`RuntimeError`）
3. `models.py` 中 `_STOP_WORDS` 模块级常量（规范建议了但未要求）
4. `nl2sql.py` 中 `str.replace` 防止 schema_text 中 `{...}` 破坏 prompt 格式化（规范未提及）
5. `result_validator.py` 中区分 `asyncio.TimeoutError` 和 `openai.APIError` 两种异常（规范笼统 `except (asyncio.TimeoutError, Exception)`）
6. `server.py` 中为每种错误场景返回不同的 `errorCode`（规范只有三类错误码）
7. `db_executor.py` 中 `_serialize_value` 处理多种非 JSON 序列化类型

唯一与规范不符的是：`test_schema_cache.py` 单元测试文件不存在（仅有集成测试中的 schema 测试）。

---

## 代码评分

| 维度 | 评分 (1-10) | 说明 |
|------|-------------|------|
| 规范符合度 | 9 | 全部 10 个设计问题已修正，有多处超规范改进；缺失 `test_schema_cache.py` 单元测试文件 |
| 架构设计 | 8 | 模块划分清晰，数据流向单向；`mcp` 双重初始化和全局 `assert` 是减分项 |
| 代码简洁 | 7 | 大部分函数简洁；`query_to_result` 超长，`auto_retry` 重复了完整流程；`PgMcpError` 未使用 |
| 代码质量 | 8 | 命名清晰，安全防御充分，测试断言有意义；`query_to_sql`/`query_to_result` 前半段代码重复 |
| 性能 | 7 | 连接池正确配置；schema 加载中 gather 是伪并发；UUID 序列化未处理 |
| 可维护性 | 8 | `from __future__ import annotations`，完整类型注解，有意义的日志；`assert` 优化模式下不可靠 |
| **总体** | **7.8** | 实现质量良好，规范覆盖度高；核心问题是 `mcp` 双初始化、`assert` 用于运行时检查、以及测试用例中的错误期望字符串 |

---

## 修复优先级

### [P0] 必须修复

1. **[RED-01] 删除 `server.py:39` 的冗余 `mcp = FastMCP("pg-mcp")`**
   - 位置：`w5/pg-mcp/src/pg_mcp/server.py` 第 39 行
   - 修复：删除该行，只保留第 90 行的 `mcp = FastMCP("pg-mcp", lifespan=lifespan)`

2. **[WARN-07] 修正 `test_sql_validator.py` 空字符串测试用例的期望子串**
   - 位置：`w5/pg-mcp/tests/test_sql_validator.py` 第 29 行
   - 修复：将 `("", "Only SELECT")` 改为 `("", "Empty SQL")`

3. **[HINT-04] 在 `_serialize_value` 中添加 `uuid.UUID` 处理**
   - 位置：`w5/pg-mcp/src/pg_mcp/db_executor.py` 第 14-22 行
   - 修复：添加 `import uuid`，在函数中增加 `if isinstance(v, uuid.UUID): return str(v)`

### [P1] 强烈建议

4. **[WARN-02] 将 `assert _openai is not None` 替换为显式运行时检查**
   - 位置：`w5/pg-mcp/src/pg_mcp/server.py` 第 163、172、197、211 行
   - 修复：使用 `if _openai is None: raise RuntimeError("OpenAI client not initialized")` 替代 `assert`

5. **[WARN-05] 删除未使用的 `PgMcpError` 模型，或在 server.py 中使用它统一错误格式**
   - 位置：`w5/pg-mcp/src/pg_mcp/models.py` 第 203-210 行
   - 选项 A：删除 `PgMcpError`，维持现有 `dict` 错误返回
   - 选项 B：在 `server.py` 中改用 `PgMcpError(...).model_dump(by_alias=True)` 统一错误格式

6. **[WARN-03] 修正 `schema_cache.py` 中 `asyncio.gather` 的误导性注释**
   - 位置：`w5/pg-mcp/src/pg_mcp/schema_cache.py` 第 244 行注释
   - 修复：将注释改为"顺序执行 5 个 fetch（单连接不支持真正并发）"，或改用多连接实现真并发

7. **[WARN-04] 统一 `db_executor.py` 中 `execution_time_ms` 的计算时间点**
   - 位置：`w5/pg-mcp/src/pg_mcp/db_executor.py` 第 55 行和第 76 行
   - 修复：在 `async with` 块内统一记录 `elapsed_ms`，并在 `return ExecutionResult(...)` 中使用同一变量

8. **[RED-02] 在 `query_to_result` 中将 `schema_text` 声明移到 `try` 块外**
   - 位置：`w5/pg-mcp/src/pg_mcp/server.py` 第 210-215 行
   - 修复：在函数开头初始化 `schema_text: str = ""`，消除 possibly-unbound 隐患

### [P2] 可选优化

9. **[HINT-05] 提取 `query_to_result` 中的公共流程为内部函数**
   - 将"生成 SQL → 验证 → 执行 → 语义验证"提取为 `_execute_pipeline`，减少重复代码

10. **[WARN-01] 修正 `config.py` 的 `_yaml_file` 私有参数依赖**
    - 确认当前使用的 `pydantic-settings` 版本支持 `_yaml_file` 参数，或改用官方支持的方式覆盖 YAML 路径

11. **[HINT-01] 在 `_tokenize_query` 注释中明确说明中文单字匹配的限制**
    - 避免维护人员误认为中文全词匹配可以正确工作

12. **[WARN-06] 将 `refresh_one` 闭包改为返回结果元组**
    - 消除闭包修改外部列表的隐式依赖

---

## 总结

pg-mcp 的实现整体质量良好，代码结构清晰，与设计规范高度吻合（约 92%）。设计文档中列出的所有 10 个问题（D-01 至 D-10）均在实现层面得到了正确修正，且有多处超出规范要求的质量改进，例如 URL 编码防御、细粒度自定义异常、`str.replace` 防止 prompt 注入、以及异常分类处理。

**最需要立即修复的是**：`server.py` 中的 `mcp` 双重初始化（RED-01），它虽然不影响功能，但是明确的代码错误；测试用例中空字符串的期望错误子串不正确（WARN-07），会导致测试失败；以及缺失 `uuid.UUID` 序列化支持（HINT-04），会在实际使用中导致含 UUID 列的查询失败。

测试覆盖范围合理，关键路径（SQL 验证、模型序列化、NL2SQL mock、结果验证异常处理）均有测试，且测试断言有具体语义，而非仅检查非空。唯一缺失的是 `test_schema_cache.py` 单元测试文件（规范要求），目前 Schema 测试仅存在于集成测试中，在无 PG 环境下无法运行。
