# 代码深度审查报告：pg-mcp 测试计划

**审查目标**: `specs/w5/0007-pg-mcp-test-plan.md`
**审查日期**: 2026-03-14
**文档类型**: 测试计划文档（含 Python 测试代码片段）

---

## 概览

| 指标 | 数值 |
|------|------|
| 审查文件数 | 1（含嵌入测试代码片段约 250 行）|
| 测试用例总数 | 98（计划声称）/ 实际新增约 97（见严重问题 #4）|
| 严重问题（🔴） | 6 |
| 警告（🟡） | 8 |
| 建议（💡） | 6 |

---

## 问题汇总

### 🔴 严重问题（必须修复）

#### [§5 / E2E] `running_server` fixture 未定义，E2E 测试无法实现

**问题**: `test_full_pipeline_simple_query` 等 5 个 E2E 测试依赖 `running_server` fixture，但整个测试计划中没有任何地方定义该 fixture。FastMCP 的运行方式是 `mcp.run(transport="stdio")`，这是一个阻塞的 stdin/stdout 协议循环，无法直接在 pytest 进程内启动并调用。

**影响**: E2E 测试整节内容无法执行，照搬代码片段会导致 `fixture 'running_server' not found` 错误。这是 P3 优先级测试，但若开发者按计划实施将浪费大量时间。

**建议修复**: 明确 E2E 测试的技术方案，三种可选路径：
1. **直接函数调用**（推荐）：绕过 MCP transport，直接 `await query_to_result(...)` 调用 tool 函数，`mock_server_deps` 注入全局状态。这实际上是高级集成测试而非真正 E2E。
2. **FastMCP 测试客户端**：若 FastMCP 提供测试工具（如 `mcp.testing.TestClient`），使用它。需验证当前版本是否支持。
3. **子进程方式**：使用 `subprocess.Popen` 启动 MCP server，通过 stdin/stdout 发送 JSON-RPC 消息。复杂但最接近真实场景。

---

#### [§9.2 / mock_server_deps] `monkeypatch.setattr` 与 server.py 内部全局变量的兼容性未验证

**问题**: `mock_server_deps` 使用 `monkeypatch.setattr(server_module, "_caches", {...})` 注入全局变量。但 `server.py` 中的 tool 函数（如 `query_to_sql`）通过**模块级全局变量名**访问这些值（`_caches.get(database)`），而 `_resolve_cache` 是定义在同一模块的内部函数，它也直接访问 `_caches` 全局变量。

此模式在 Python 中通常可行，**但有一个陷阱**：如果 tool 函数内部有 `from pg_mcp.server import _caches` 形式的局部导入（即使只是在函数调用链中），`monkeypatch.setattr` 将失效。需明确说明这个限制，并提供验证方法。

另外，`mock_server_deps` 是 `function` 作用域 fixture，但测试声明了 `async def test_query_to_sql_success(mock_server_deps):`，需要确认 `monkeypatch` fixture 在异步测试中正常工作（`asyncio_mode="auto"` 下需要验证）。

**建议修复**: 在计划中明确：
```python
# 使用 pytest.monkeypatch 在异步测试中有效的前提
# asyncio_mode="auto" 下 monkeypatch 正常工作，已由 pytest-asyncio 支持
# 但需确认 server.py 中无循环导入或局部 import 导致 setattr 失效
```

---

#### [§3.3 / TC-SCHEMA] `mock_conn` fixture 未定义，12 个测试无法实现

**问题**: `test_schema_cache.py` 中 TC-SCHEMA-02~12 全部依赖 `mock_conn` fixture，但整个测试计划中没有定义该 fixture。asyncpg 的 `Connection` 对象由 C 扩展（Cython）实现，`conn.fetch()` 返回 `asyncpg.Record` 对象（而非普通 dict）。正确 mock 需要：

1. mock `asyncpg.connect` 返回 mock connection
2. mock connection 的 `fetch()` 返回结构化 Record 数据
3. 不同调用的 `fetch()` 返回不同数据（5 次查询：tables/columns/indexes/fkeys/types）

由于 `load_schema` 用 `asyncio.gather` 并发调用 5 个 `_fetch_*` 函数，且它们共享同一个 `conn`，这使得 mock 更加复杂。

**建议修复**: 提供 `mock_conn` fixture 的具体实现，例如：
```python
@pytest.fixture
def mock_conn():
    conn = AsyncMock()
    # 为不同的 SQL 调用返回不同数据
    # 注意：asyncio.gather 时 fetch 会被并发调用，side_effect 用列表
    conn.fetch.side_effect = [
        [Mock(table_schema="public", table_name="users", ...)],  # _fetch_tables
        [Mock(table_schema="public", table_name="users", column_name="id", ...)],  # _fetch_columns
        [],  # _fetch_indexes
        [],  # _fetch_foreign_keys
        [],  # _fetch_custom_types
    ]
    return conn
```
并在测试中 `patch("pg_mcp.schema_cache.asyncpg.connect", return_value=mock_conn)`。

---

#### [§7 / PF] 性能测试依赖 `pytest-benchmark`，但未加入 dev-dependencies

**问题**: PF-01~03 使用 `benchmark` fixture，这来自 `pytest-benchmark` 第三方库，但 `pyproject.toml` 的 `dev-dependencies` 中没有列出此依赖。直接运行这些测试会报 `fixture 'benchmark' not found`。

此外，`pytest-benchmark` 的 `benchmark()` 函数只做性能测量，**不会自动断言时间上限**。"validate_sql 单次调用 < 10ms"这类断言需要额外使用 `benchmark.pedantic()` + `pytest-benchmark` 的 `--benchmark-max-time` 参数，或自定义断言，但计划中均未提及。

**建议修复**:
1. 在 `pyproject.toml` 中添加 `pytest-benchmark>=4.0`
2. 或将性能测试改为手动计时断言：
```python
import time
def test_sql_validator_performance():
    start = time.perf_counter()
    for _ in range(1000):
        validate_sql("SELECT * FROM users JOIN orders ON users.id = orders.user_id")
    elapsed_ms = (time.perf_counter() - start)
    assert elapsed_ms < 10  # 1000 次总共 < 10s → 平均 < 10ms
```

---

#### [§10 / 总计] 测试用例数量计算错误

**问题**: 附录 A 声称"总计: 约 98 个测试用例（含现有 55 个，新增约 43 个）"。但按各 section 实际数量统计：

| 新增测试 | 数量 |
|--------|------|
| TC-CFG-01~12 | 12 |
| TC-EXE-01~15 | 15 |
| TC-SCHEMA-01~12 | 12 |
| TC-SRV-01~23 | 23 |
| TC-EDGE-SQL-01~07 | 7 |
| TC-EDGE-MODEL-01~05 | 5 |
| TC-EDGE-CFG-01~03 | 3 |
| TC-MODEL-ADD-01~03 | 3 |
| IT-05~IT-13 | 9 |
| E2E-01~05 | 5 |
| PF-01~03 | 3 |
| **新增小计** | **97** |
| 现有 | 55 |
| **实际总计** | **152** |

"约 98"与"约 152"相差 54 个测试，计算错误可能导致工时估算严重偏差。

---

#### [§3.5.2 / TC-MODEL-ADD] 代码片段中存在语法错误

**问题**: `test_relevance_score_match` 的测试代码：
```python
table = make_table("users", columns=[ColumnInfo(name="id", ...), ...])
```
`ColumnInfo(name="id", ...)` 中的 `...` 是 Python 的 `Ellipsis` 对象，不是有效的 `ColumnInfo` 参数。同理 `test_table_schema_view_type` 中：
```python
table = TableSchema(..., object_type="view", ...)
```
这两处代码作为"可执行测试片段"是无效的，开发者照搬会遇到 `TypeError`。

**建议修复**: 将占位符 `...` 替换为合法的最小有效参数，或标注这些是"伪代码示例（pseudo-code）"而非可执行代码。

---

### 🟡 警告（建议修复）

#### [§3.1 / TC-CFG-09] `AppConfig(_yaml_file=...)` 使用已知不稳定的私有参数

**问题**: `TC-CFG-09` 使用 `AppConfig(_yaml_file=str(config_path))` 加载 YAML。这个 `_yaml_file` 私有参数已在代码审查报告（0006）的 WARN-01 中被标记为"版本兼容风险"。测试计划未承认此风险，且整个 `test_config.py` 的 YAML 加载测试（TC-CFG-09、TC-CFG-10、TC-CFG-11）都依赖此脆弱参数。

若 pydantic-settings 升级后 `_yaml_file` 行为变更，这些测试会静默失败或行为不符预期。

**建议**: 在测试计划中明确说明此限制，并建议在 CI 中 pin pydantic-settings 版本，或同时测试环境变量方式加载配置。

---

#### [§4.1 / `test_data` fixture] 集成测试引用了未定义的 `test_data` fixture

**问题**: IT-08、IT-09、IT-10 依赖 `test_data` fixture（用于插入测试数据），但 §4.1 只定义了建库 DDL，没有提供 `test_data` fixture 的实现。没有测试数据，`SELECT created_at FROM test_users LIMIT 1` 会返回空结果集，使 `result.rows[0][0]` 产生 `IndexError`。

**建议**: 在 §9.1 Fixture 层次或 §4.1 中补充 `test_data` fixture 的 DML，例如：
```python
@pytest.fixture(scope="session")
async def test_data(pg_pool, test_schema):
    await pg_pool.execute("""
        INSERT INTO test_users (email, name, score) VALUES
        ('alice@example.com', 'Alice', 99.50),
        ('bob@example.com', 'Bob', 85.25)
        ON CONFLICT DO NOTHING
    """)
```

---

#### [§2.3 / markers] `unit` 标记已添加但测试代码未实际使用 `@pytest.mark.unit`

**问题**: §2.3 定义了 `unit` 标记，§8.1 的运行命令也使用 `-m "not integration and not e2e"` 排除非单元测试，但整个计划中所有单元测试函数都没有 `@pytest.mark.unit` 装饰器。

这意味着"只运行单元测试"的命令 `pytest -m "not integration and not e2e"` 实际上会运行**所有**未标记的测试，包括慢速或不稳定测试。标记策略与执行策略不一致。

**建议**: 选择以下一种一致策略：
- **负向排除**（当前）：只给 integration/e2e/slow 加标记，单元测试无标记
- **正向包含**：给单元测试加 `@pytest.mark.unit`，运行命令用 `-m unit`
两者均可，但需在计划中明确说明并统一代码片段。

---

#### [§3.2 / TC-EXE-07] UUID xfail 测试缺少 `strict=True`

**问题**: `@pytest.mark.xfail(reason="HINT-04: ...")` 如果不设置 `strict=True`，当 `_serialize_value` 被修复后（uuid 正常序列化），测试会变成 `xpass`（意外通过）。`xpass` 在默认配置下不会让 CI 失败，会导致已修复的 bug 对应的 xfail 测试长期留存而不被清理。

**建议**:
```python
@pytest.mark.xfail(
    strict=True,
    reason="HINT-04: uuid.UUID not handled in _serialize_value. Fix in db_executor.py"
)
```
`strict=True` 确保一旦 xfail 测试意外通过，CI 会失败并提示开发者移除 xfail 标记。

---

#### [§8.3 / GitHub Actions] health check 配置不完整

**问题**: GitHub Actions 的 PostgreSQL service 配置：
```yaml
options: --health-cmd pg_isready
```
缺少 `--health-interval`、`--health-timeout`、`--health-retries` 参数，在 PG 启动较慢时可能导致测试在 DB 就绪前开始执行。

**建议**:
```yaml
options: >-
  --health-cmd pg_isready
  --health-interval 10s
  --health-timeout 5s
  --health-retries 5
```

---

#### [§4.2 / IT-12] `pg_sleep` 测试可能造成 CI 超时

**问题**: IT-12 使用 `"SELECT pg_sleep(10)"` 配合 `timeout_seconds=1` 触发超时。`pg_sleep(10)` 会在 PostgreSQL 服务端持续 10 秒（即使客户端已取消），在 CI 环境中多个测试并发运行时可能导致：
1. PG 连接池被长时间占用
2. 总 CI 运行时间增加

**建议**: 改用 `pg_sleep(2)` 配合 `timeout_seconds=0.5`，既能触发超时又能快速释放 PG 连接。

---

#### [§3.3 / TC-SCHEMA-02] `asyncio.gather` mock 的顺序依赖问题

**问题**: `load_schema` 使用 `asyncio.gather` 并发调用 5 个 `_fetch_*` 函数，但实现文件的代码审查（WARN-03）已指出这 5 个函数共享同一个 `conn`，asyncpg 单连接实际上是串行排队执行的。

在 mock 层面，若 `mock_conn.fetch.side_effect` 用列表传入，`asyncio.gather` 的实际调用顺序依赖 asyncio 事件循环调度，**不保证**与 `side_effect` 列表顺序严格对应。如果 `_fetch_columns` 先于 `_fetch_tables` 执行，`side_effect` 返回的数据会错位，导致测试结果混乱。

**建议**: 使用 `side_effect` 函数而非列表，通过 SQL 模式匹配返回对应数据：
```python
def fetch_side_effect(query, *args):
    if "information_schema.tables" in query:
        return [...]  # tables 数据
    elif "information_schema.columns" in query:
        return [...]  # columns 数据
    # ...
mock_conn.fetch.side_effect = fetch_side_effect
```

---

#### [§6.2 / TC-EDGE-MODEL-01] `large_cache` fixture 未定义

**问题**: `test_get_relevant_tables_large_schema` 依赖 `large_cache` fixture，该 fixture 在整个测试计划中没有定义。

**建议**: 在 §9.1 Fixture 层次中添加 `large_cache` fixture 定义：
```python
@pytest.fixture
def large_cache():
    tables = [make_table(f"table_{i}") for i in range(500)]
    return make_cache(tables)
```

---

### 💡 建议（可选优化）

#### [§2.2 / Mock 策略] 建议明确 asyncpg Record 的 mock 方法

Mock asyncpg Record 对象（由 `conn.fetch()` 返回）是整个测试计划中技术难度最高的部分。`asyncpg.Record` 是 C 扩展类，不能直接用 `MagicMock` 替换，但可以通过 `unittest.mock.MagicMock(spec=dict)` 或 `asyncpg.Record` 行为仿真来实现。建议在 §2.2 中给出一个具体示例，降低实施难度。

---

#### [§5 / E2E-05] SQL 注入测试应直接测试 `sql_validator`，不应依赖 LLM

**问题**: `test_sql_injection_attempt_blocked` 的前提是"LLM 生成了 DELETE 语句"。但 LLM 的输出是不确定的（gpt-4o-mini 通常不会生成 DELETE），无法通过 E2E 测试稳定复现注入场景。

**建议**: 将安全测试移到单元测试层（sql_validator 层），直接传入 "DELETE FROM users WHERE 1=1" 并验证被拒绝。已在 TC-EXE 部分覆盖，E2E 中可删除此测试。

---

#### [§3.5.1 / WARN-07 修复] 建议同时修复测试，而非仅描述修复

**问题**: §3.5.1 正确指出了 `test_sql_validator.py` 第 29 行的断言错误，但仅提供了"应改为"的描述。已知这是 P0 问题，建议测试计划明确指出这个修复**必须先于其他新增测试实施**，否则 CI 中已有 1 个测试用例会失败，会干扰新增测试的调试。

---

#### [§9.1 / session-scoped async fixture] 需要处理 event_loop scope 兼容性

**问题**: `pg_pool` 是 `scope="session"` 的异步 fixture。pytest-asyncio 在 `asyncio_mode="auto"` 下对 session-scoped async fixture 有特殊要求：在 pytest-asyncio 0.21+ 中需要在 `pyproject.toml` 中配置 `asyncio_default_fixture_loop_scope = "session"`，否则会收到 `PytestUnraisableExceptionWarning` 或 `ScopeMismatch` 错误。

建议在 §8.1 的 pyproject.toml 配置中添加：
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"  # pytest-asyncio >= 0.21
```

---

#### [§4.1 / test_schema fixture] DDL 清理逻辑缺失

**问题**: §4.1 提供了建表 DDL，但没有对应的清理逻辑。若多次运行集成测试，`CREATE TABLE IF NOT EXISTS` 不会失败，但测试数据可能累积导致结果不稳定。

**建议**: `test_schema` fixture 应包含 teardown：
```python
@pytest.fixture(scope="session")
async def test_schema(pg_pool):
    await pg_pool.execute("CREATE TABLE IF NOT EXISTS test_users (...)")
    yield
    await pg_pool.execute("DROP TABLE IF EXISTS test_orders")
    await pg_pool.execute("DROP TABLE IF EXISTS test_users")
    await pg_pool.execute("DROP VIEW IF EXISTS test_active_users")
    await pg_pool.execute("DROP TYPE IF EXISTS test_status")
```

---

#### [§10 / 实施顺序] `test_schema_cache.py` 的"大"工作量需要细化

§10 将 `test_schema_cache.py` 标注为"大"工作量，但没有任何说明。鉴于 `mock_conn` fixture 和 asyncpg Record mock 的复杂性，建议将该任务拆分为：
- P2a: TC-SCHEMA-01（连接失败）— fixture 最简单
- P2b: TC-SCHEMA-07、08、12（简单场景）— 少量 fetch 调用
- P2c: TC-SCHEMA-02~06（核心组装）— 需要完整 mock_conn

---

## 详细审查结果

### 架构和设计

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 测试层次结构清晰 | ✅ | 单元/集成/E2E/性能分层明确，测试金字塔比例合理 |
| Mock 策略描述 | ⚠️ | mock_conn 和 running_server 未定义，最难实现的部分缺少细节 |
| Fixture 层次设计 | ✅ | §9.1 的 fixture 层次图清晰，mock_server_deps 设计合理 |
| 测试覆盖缺口识别 | ✅ | 正确识别出 config/db_executor/schema_cache/server 的覆盖缺口 |
| E2E 技术方案 | ❌ | `running_server` fixture 无法实现，需要重新设计 E2E 策略 |
| CI/CD 配置 | ⚠️ | GitHub Actions health check 不完整，性能测试依赖未加入 |

### KISS 原则

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 测试用例粒度 | ✅ | 每个 TC 只测试一件事，职责单一 |
| 文档复杂度 | ✅ | 11 个章节合理覆盖所有方面，不过度冗余 |
| E2E 测试必要性 | ⚠️ | 5 个 E2E 场景与高级集成测试高度重叠，考虑合并 |
| Fixture 复杂度 | ⚠️ | TC-SCHEMA 中的 mock_conn 极为复杂，计划低估了实现难度 |

### 代码质量（DRY, YAGNI, SOLID）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 测试代码 DRY | ✅ | mock_server_deps fixture 正确提取了重复的 server 状态设置 |
| YAGNI | ⚠️ | E2E-05（SQL 注入）与 TC-EXE 重复，属于不必要的测试 |
| 命名一致性 | ✅ | TC/IT/E2E/PF 前缀命名规范，易于跟踪 |
| 测试代码语法 | ❌ | 多处使用 `...` 作为函数参数占位符，是无效 Python 语法 |
| 测试数量估算 | ❌ | "约 98 个"实为约 152 个，误差超过 50% |

### 性能

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 性能测试技术方案 | ❌ | `benchmark` fixture 需要 pytest-benchmark，未加入依赖 |
| 时间断言方式 | ⚠️ | `benchmark()` 不自动断言时间上限，需额外逻辑 |
| pg_sleep 测试风险 | ⚠️ | `pg_sleep(10)` 过长，建议改为 2 秒 |
| 覆盖率目标 | ✅ | 各模块目标合理（schema_cache 70% 反映了其 DB 查询特性） |

### 规范符合性（对照 impl-plan 和 design-doc）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| D-01/D-02 修正验证 | ✅ | TC-SCHEMA-03/04 专门验证列/索引分组逻辑 |
| D-03 修正验证 | ✅ | TC-SRV-21 验证 refresh_schema 按 alias 查找 |
| D-05/D-06 修正验证 | ✅ | TC-EXE-13 验证 statement_timeout 无引号，TC-EXE-11 验证 prepare |
| RED-01（双重 mcp 实例）| ⚠️ | 未规划专门测试验证此问题，但 test_smoke.py 间接覆盖 |
| RED-02（schema_text 未绑定）| ❌ | 无对应测试用例，需补充 TC-SRV-16 验证 auto_retry 路径 |
| HINT-04（UUID 序列化）| ✅ | TC-EXE-07 和 IT-10 都以 xfail 形式记录此 bug |
| camelCase 输出 | ✅ | TC-SRV-07/18、TC-SRV-23 验证 camelCase |
| WARN-07（空字符串断言）| ✅ | §3.5.1 明确列出此修复 |

---

## 代码评分

| 维度 | 评分 (1-10) | 说明 |
|------|-------------|------|
| 覆盖全面性 | 9 | 正确识别所有 4 个零覆盖模块，边界用例设计细致 |
| 技术可行性 | 5 | E2E 无法实现，mock_conn 细节缺失，依赖遗漏 |
| 优先级设计 | 8 | P0/P1/P2/P3 划分合理，实施顺序清晰 |
| 代码片段质量 | 6 | 语法错误（Ellipsis 占位符）、测试数量算错 |
| CI/CD 可操作性 | 7 | GitHub Actions 配置基本正确，health check 有小瑕疵 |
| 规范符合性 | 8 | 大部分设计 bug 修复均有对应测试，RED-02 有遗漏 |
| **总体** | **7** | 覆盖思路优秀，关键实现细节需要补全 |

---

## 修复优先级

### [P0] 必须修复（阻断实施）

1. **`running_server` fixture 重新设计**（§5）— 明确 E2E 技术方案，或降级为高级集成测试
2. **`mock_conn` fixture 详细设计**（§3.3）— 提供 asyncpg Connection mock 的具体实现，处理 `asyncio.gather` 的调用顺序问题
3. **修复代码片段中的 `...` 语法错误**（§3.5.2）— 替换为合法的最小参数，或明确标注"伪代码"
4. **修正测试数量估算**（§附录 A）— 98 → 152（实际数量）

### [P1] 强烈建议

5. **`pytest-benchmark` 加入 dev-dependencies**（§7）— 或改为手动计时断言
6. **`test_data` fixture 定义**（§4.1）— IT-08~10 依赖插入数据
7. **`large_cache` fixture 定义**（§6.2）— TC-EDGE-MODEL-01 依赖此 fixture
8. **TC-EXE-07 添加 `strict=True`**（§3.2）— 防止修复后 xpass 不被察觉
9. **`asyncio_default_fixture_loop_scope = "session"` 配置**（§8.1）

### [P2] 可选优化

10. **标记策略统一**（§2.3）— 选择负向排除或正向包含，保持一致
11. **E2E-05 SQL 注入测试移除**（§5）— 已被单元测试覆盖，E2E 中冗余
12. **GitHub Actions health check 补全**（§8.3）— 加 interval/timeout/retries
13. **test_schema fixture 添加 teardown**（§4.1）
14. **TC-SCHEMA-05 `test_schema_cache.py` 工作量细化**（§10）— 拆分为 P2a/P2b/P2c

---

## 总结

**测试计划的整体思路优秀**：正确识别了现有测试的 4 个零覆盖模块（config/db_executor/schema_cache/server），测试用例设计细致，对现有代码审查中发现的 bug 均有对应的 xfail 测试或修复验证，优先级划分合理。

**最主要的风险集中在两个区域**：

1. **E2E 测试技术方案**：`running_server` fixture 无法实现，整个 E2E 章节需要重新设计为"直接调用 tool 函数"的高级集成测试，绕过 MCP transport 层。

2. **schema_cache 单元测试的 mock 策略**：asyncpg `Connection.fetch()` 在 `asyncio.gather` 并发调用下的 mock 顺序问题是一个隐蔽的实施难点。`mock_conn` fixture 需要使用基于 SQL 内容匹配的 `side_effect` 函数，而非简单的列表。

建议按 P0 修复完成后，按 P1 优先级实施：先实现 `test_config.py` 和 `test_db_executor.py`（复杂度低），再实施 `test_server.py`（`mock_server_deps` 已设计好），最后处理 `test_schema_cache.py`（最复杂）。
