# 代码深度审查报告

**审查目标**: `specs/w5/0004-pg-mcp-impl-plan.md`（含所有嵌入 Python 代码片段）
**审查日期**: 2026-03-14
**代码语言**: Python 3.11+

---

## 概览

| 指标 | 数值 |
|------|------|
| 审查文件数 | 1（含 8 个模块代码片段）|
| 审查代码量 | ~350 行 Python |
| 严重问题（🔴） | 6 |
| 警告（🟡） | 9 |
| 建议（💡） | 7 |

---

## 问题汇总

### 🔴 严重问题（必须修复）

#### [config.py / T-03] CLI `--config` 参数覆盖逻辑无效

**问题**: `os.environ.setdefault("PG_MCP__YAML_FILE", args.config)` 不会生效。`pydantic-settings` 的 `yaml_file` 在 `SettingsConfigDict` 中是**类定义时**固定的路径，不会在运行时从环境变量读取。

**影响**: `--config path/to/config.yaml` 参数被完全忽略，始终从默认的 `config.yaml` 加载，无法支持多环境部署。

**建议修复**:
```python
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args()
    # 在运行时动态构建 AppConfig，而非依赖 env var
    config = AppConfig(_yaml_file=args.config)  # pydantic-settings v2 支持构造时覆盖
    # 或者: 手动加载 YAML 再 merge
    mcp.run(transport="stdio")
```

---

#### [schema_cache.py / T-05] `raw_types` 类型不一致：dataclass vs dict 访问混用

**问题**: `_fetch_custom_types` 按照与其他 fetch 函数一致的风格应返回 `list[_RawCustomType]`，但组装时使用的是 `t["schema_name"]`（dict 访问），而非 `t.schema_name`（dataclass 属性访问）。asyncpg `Record` 支持 dict-style 访问，但其他 fetch 函数返回的是手工构建的 `@dataclass`。

**影响**: 若 `_fetch_custom_types` 返回 asyncpg `Record`，则 dict 访问正确但与其他 fetch 函数的模式不一致，易引起混淆和维护错误；若返回 `@dataclass`，则 `t["schema_name"]` 会在运行时 `TypeError`。

**建议修复**: 为 custom types 也定义 `@dataclass _RawCustomType`，保持所有 `_fetch_*` 函数返回同类结构，组装时统一用 `t.schema_name`。

---

#### [db_executor.py / T-06] `_serialize_value` 未集成进 `execute_query`

**问题**: 计划正文描述了 `_serialize_value` 函数用于处理 datetime/Decimal/bytes 等 asyncpg 不可序列化类型，但实际的 `execute_query` 代码片段中 `rows` 的构建直接使用 `[list(r.values()) for r in records[:limit]]`，未调用 `_serialize_value`。

**影响**: 当查询包含 `TIMESTAMP`、`NUMERIC`、`UUID`、`BYTEA` 类型列时，返回的 `rows` 将包含 Python 原生对象（`datetime`、`Decimal`），导致 MCP JSON 序列化失败，tool 调用报错。

**建议修复**: 在 `execute_query` 的最终代码中显式集成：
```python
rows = [[_serialize_value(v) for v in r.values()] for r in records[:limit]]
```

---

#### [result_validator.py / T-08] `except (asyncio.TimeoutError, Exception)` 静默吞掉所有错误

**问题**: `asyncio.TimeoutError` 是 `Exception` 的子类，两者同时列在 `except` 中是冗余的。更严重的是，这个宽泛的 `except Exception` 会将网络错误、`KeyError`、`AttributeError` 等编程错误全部静默为 `validation_skipped=True`，使调试极为困难。

**影响**: 真实的 bug（如 OpenAI API 破坏性变更、模型名拼写错误）在生产环境中完全不可见，只表现为静默跳过验证。

**建议修复**:
```python
except asyncio.TimeoutError:
    # 超时是预期情况，正常跳过
    return ValidationInfo(is_meaningful=False, explanation="", validation_skipped=True)
except openai.APIError as e:
    # OpenAI 服务端错误，记录日志后跳过
    logger.warning("OpenAI validation call failed: %s", e)
    return ValidationInfo(is_meaningful=False, explanation="", validation_skipped=True)
# 其他未预期异常应继续向上抛出
```

---

#### [models.py / T-02] 中文查询的 `get_relevant_tables` 关键词提取无效

**问题**: `query.split()` 按空格分词。中文查询（如"查询过去30天注册的用户数量"）没有空格，整个字符串作为单个 token，与表名/列名的 token 重叠为 0，导致所有表的 `relevance_score` 相同。

**影响**: 中文用户的查询（这是 PRD 明确支持的场景）无法从 Schema 裁剪中获益，始终返回前 20 个表（按字典顺序），SQL 生成质量下降。

**建议修复**:
```python
import re

def _tokenize(query: str) -> set[str]:
    # 英文单词 + 中文字符拆分（逐字）
    en_words = re.findall(r'[a-zA-Z_]\w*', query.lower())
    zh_chars = re.findall(r'[\u4e00-\u9fff]+', query)
    zh_tokens = set(''.join(zh_chars))  # 逐字作为 token
    return set(en_words) | zh_tokens
```

---

#### [test_models.py / T-11] 测试函数为空存根，无任何断言

**问题**: `test_models.py` 中的 4 个测试函数只有注释，没有实现体。Python 的空函数体（只有注释）会通过 pytest 收集并**静默通过**，给出虚假的绿色信号。

**影响**: 测试覆盖率报告将显示这些测试通过，但实际上没有任何验证发生。`get_relevant_tables` 的 FK 循环引用、CamelCase 序列化等关键逻辑完全未被测试。

**建议修复**: 每个测试函数必须有完整实现，包含至少一个 `assert`。

---

### 🟡 警告（建议修复）

#### [result_validator.py / T-08] 空结果集语义判断过于武断

**问题**: 空结果集直接返回 `is_meaningful=False` 并给出固定解释。但某些查询的正确答案就是空集：例如"查询所有被删除的订单"在没有删除订单时返回空，是完全有意义的结果。

**影响**: 会向用户呈现错误的"查询无意义"提示，降低用户信任度。

**建议**: 空结果集时返回 `is_meaningful=True`，`explanation="查询成功，但当前无匹配数据。"`。语义验证的目的是发现 SQL 生成错误，而非对结果集大小做判断。

---

#### [models.py / T-02] `stop_words` 常量在方法内部定义

**问题**: `stop_words` 集合在 `get_relevant_tables()` 方法内部定义，每次调用都会重新创建这个 set 对象。

**影响**: 轻微性能损耗（每次调用约 40 次 hash 操作），但更重要的是代码意图不清晰——stop_words 是静态数据，应为模块级常量。

**建议**: 移到模块顶层：`_STOP_WORDS: frozenset[str] = frozenset({...})`

---

#### [server.py / T-09] `ValueError` 映射到错误的 `errorCode`

**问题**: `_resolve_cache` 中"多个数据库可用，请指定 database 参数"抛出 `ValueError`，但调用处将所有 `ValueError` 和 `RuntimeError` 统一映射为 `NO_DATABASE_AVAILABLE`。"多个可用数据库"不等于"无可用数据库"。

**影响**: 用户看到误导性错误码，无法理解真正原因。

**建议**: 定义自定义异常：
```python
class DatabaseNotFoundError(Exception): ...
class DatabaseAmbiguousError(Exception): ...
class DatabaseUnavailableError(Exception): ...
```
分别映射到不同 `errorCode`。

---

#### [server.py / T-09] 全局可变状态难以单元测试

**问题**: `_caches`、`_pools`、`_openai`、`_config` 作为模块级全局变量，在 lifespan 中赋值。这使得单元测试必须 mock 模块级变量，且测试间可能互相污染。

**建议**: 将这些状态封装进 `AppContext` dataclass，通过 `mcp.state`（FastMCP 提供的 lifespan 状态机制）在 tool 函数中访问：
```python
@mcp.tool()
async def query_to_sql(query: str, ctx: Context) -> dict:
    config: AppConfig = ctx.request_context.lifespan_context["config"]
```

---

#### [db_executor.py / T-06] `elapsed_ms` 变量在非空路径中未被使用

**问题**: `elapsed_ms` 在 `acquire` 块内计算并用于零行结果，但在非空路径中返回时重新计算 `(time.monotonic() - start) * 1000`。`elapsed_ms` 在非空路径中是一个"死变量"。

**建议**: 统一在 `async with` 块退出后计算一次：
```python
elapsed_ms = (time.monotonic() - start) * 1000
return ExecutionResult(columns=columns, rows=rows, row_count=len(rows), execution_time_ms=elapsed_ms)
```

---

#### [lifespan / T-09] lifespan 签名不确定，计划给出"尝试" 性建议

**问题**: 计划中注释 `# 若报错改为 async def lifespan():` 表明实现者不确定正确的 API 签名。这是一个"试错"驱动的计划，不应出现在实施文档中。

**建议**: 在编写计划时应先查阅 `mcp` 包源码或文档确认签名。当前 `mcp>=1.8` 的 FastMCP lifespan 为：
```python
@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    ...
    yield {}  # lifespan context dict，可通过 ctx.request_context.lifespan_context 访问
```

---

#### [sql_validator.py / T-04] 注释检测对字符串字面量的误报

**问题**: `if "--" in raw or "/*" in raw:` 会拒绝合法的 SQL，如：
```sql
SELECT * FROM logs WHERE message = 'Error -- not a comment'
```
字符串字面量中的 `--` 会导致误判。

**影响**: 对包含 `--` 的字符串过滤条件的查询，LLM 将无法生成正确 SQL（被 layer-1 拒绝后触发 `VALIDATION_FAILED`）。

**建议**: 在 Prompt 中强化禁止，同时将 layer-1 的注释检测改为"检测 SQL 解析后的 AST 中的 Comment 节点"而非简单字符串匹配：
```python
# 更精确的检测：AST 级别
if any(isinstance(node, exp.Comment) for node in stmt.walk()):
    return "", "SQL comments are not allowed"
```

---

#### [nl2sql.py / T-07] Prompt 模板使用 `str.format()` 有注入风险

**问题**: `NL2SQL_SYSTEM_PROMPT.format(schema_text=schema_text)` — 若 `schema_text` 中包含 `{column_name}` 这样的格式化占位符（数据库列名完全可能是 `{id}` 等），会导致 `KeyError`。

**影响**: 低概率但一旦触发会导致整个 tool 调用异常。

**建议**: 改用不受列名影响的替换方式：
```python
prompt = NL2SQL_SYSTEM_PROMPT.replace("{schema_text}", schema_text)
```

---

### 💡 建议（可选优化）

#### [T-05] `load_schema` 函数职责过重，建议拆分

`load_schema` 目前承担：连接 DB、5 次 fetch、3 次分组、组装 TableSchema、错误处理——共 80+ 行。建议拆出 `_assemble_table_map()` 纯函数，将 IO 与组装分离，便于独立测试组装逻辑。

---

#### [T-05] 并发 fetch 可提升 Schema 加载速度

5 个 `_fetch_*` 调用是顺序执行的。改为 `asyncio.gather()` 并发执行可将加载时间从 5×单次延迟降为 1×最慢查询延迟：

```python
raw_tables, raw_columns, raw_indexes, raw_fkeys, raw_types = await asyncio.gather(
    _fetch_tables(conn, db.schemas),
    _fetch_columns(conn, db.schemas),
    _fetch_indexes(conn, db.schemas),
    _fetch_foreign_keys(conn, db.schemas),
    _fetch_custom_types(conn, db.schemas),
)
```

---

#### [T-05, T-06] 缺少日志模块规划

PRD §4.4 要求结构化 JSON 日志，但整个实现计划中没有任何 logging 配置或日志调用。建议增加 `T-00: 日志初始化` 任务，在 `server.py` 的 `main()` 中配置 `structlog` 或 `logging.basicConfig`，并在每个关键操作点（schema 加载完成、SQL 生成、查询执行完成）记录日志。

---

#### [T-03] `DatabaseConfig.dsn` 中密码 URL 编码缺失

```python
return f"postgresql://{self.user}:{pwd}@{self.host}:{self.port}/{self.dbname}"
```

若密码包含 `@`、`/`、`?` 等特殊字符，DSN 解析会失败。建议：
```python
from urllib.parse import quote_plus
return f"postgresql://{quote_plus(self.user)}:{quote_plus(pwd)}@{self.host}:{self.port}/{self.dbname}"
```

---

#### [T-11] 测试夹具未处理 `asyncio_mode = "auto"` 与 `scope="session"` 的兼容性

`pg_pool` fixture 使用 `scope="session"` 且是 `async` fixture。`pytest-asyncio` 在 `asyncio_mode="auto"` 下对 session-scoped async fixture 有特殊要求（需在 `conftest.py` 中设置 `event_loop` scope）。若不处理，会收到 `ScopeMismatch` 警告或错误。

---

#### [T-09] `import time` 在 `refresh_schema` 函数内部

```python
@mcp.tool()
async def refresh_schema(...):
    import time
    ...
```

`time` 是标准库，应在模块顶部导入。函数内 import 会在每次调用时触发模块查找（虽然有缓存，但不符合 Python 习惯）。

---

#### [T-12] `test_schema_load` 集成测试硬编码占位符

```python
db = DatabaseConfig(alias="test", host="...", dbname="...", user="...", ...)
```

`"..."` 是真实字符串，不是 `None` 或跳过标记。这个测试会尝试连接主机名为字面量 `"..."` 的 PostgreSQL，必然失败但报错信息难以理解。应改为从 `pg_dsn` fixture 解析：
```python
from urllib.parse import urlparse
parsed = urlparse(pg_dsn)
db = DatabaseConfig(alias="test", host=parsed.hostname, ...)
```

---

## 详细审查结果

### 架构和设计

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Pydantic 数据建模 | ✅ | 全面使用 Pydantic V2，dataclass 用于内部临时结构，层次清晰 |
| 模块划分合理性 | ✅ | 7 个模块职责边界清晰（config/models/validator/cache/executor/nl2sql/validator）|
| 循环依赖风险 | ✅ | 依赖图为 DAG，`models.py` 无上游依赖 |
| 类型注解完整性 | ✅ | 所有公共函数均有完整类型注解 |
| 全局可变状态 | ⚠️ | `server.py` 使用模块级全局变量，测试难度高（见警告 #4）|
| 自定义异常 | ⚠️ | 使用原生 `ValueError`/`RuntimeError`，导致错误码语义混乱（见警告 #3）|
| 依赖注入 | ⚠️ | `AsyncOpenAI` 和 `Pool` 通过参数传递（良好），但全局 config 通过 globals 访问 |
| 配置与代码分离 | ✅ | YAML + 环境变量 + Pydantic Settings，设计合理 |
| CLI 参数支持 | ❌ | `--config` 参数覆盖逻辑有根本性错误（见严重问题 #1）|

### KISS 原则

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 函数长度 | ⚠️ | `load_schema` ~80 行，`query_to_result` ~50 行，略超建议值 |
| 嵌套深度 | ✅ | 最深 3 层（`load_schema` 中的 list comprehension），未超限 |
| 参数数量 | ✅ | 最多 7 参数（`validate_result`），略多但均有意义 |
| 过度抽象 | ✅ | 未发现不必要的抽象层 |
| `_RawXxx` dataclass 设计 | ✅ | 临时中间结构的引入是必要的，解决了 D-01/D-02 |

### 代码质量（DRY, YAGNI, SOLID）

| 检查项 | 状态 | 说明 |
|--------|------|------|
| DRY | ⚠️ | 3 处重复的 `setdefault` 分组模式（cols/idx/fk），可提取为 `_group_by_table()` helper |
| YAGNI | ✅ | 未发现明显的超前设计 |
| SRP | ⚠️ | `load_schema` 同时负责 IO + 数据组装，建议拆分 |
| 魔法数字 | ✅ | `max_tables=20`, `timeout=10000` 均通过参数或配置传入 |
| 命名清晰性 | ✅ | 命名语义明确，`_RawXxx` 前缀清楚标识内部临时结构 |
| 注释与文档 | ✅ | 关键逻辑有注释，函数有 docstring |
| 未使用代码 | ⚠️ | `elapsed_ms` 在非空路径中是死变量（见警告 #5）|
| 异常处理一致性 | ❌ | `except (asyncio.TimeoutError, Exception)` 过于宽泛（见严重问题 #4）|

### 性能

| 检查项 | 状态 | 说明 |
|--------|------|------|
| Schema 加载并发 | ⚠️ | 5 个 fetch 为顺序执行，可改为 `asyncio.gather()` 并发（见建议 #2）|
| 关键词匹配 O(n) | ✅ | `relevance_score` 是 O(表数) 的线性扫描，对 <500 表规模可接受 |
| `stop_words` 每次重建 | ⚠️ | 应为模块级常量（见警告 #2）|
| 连接池配置 | ✅ | `min_size=1, max_size=5` 合理，`server_settings` 在池层面设置只读 |
| 零行结果二次 prepare | ✅ | D-06 已修正，prepare 在同一 acquire 块内执行 |
| asyncpg Record 序列化 | ❌ | `_serialize_value` 未集成（见严重问题 #3），运行时会对非 JSON-safe 类型失败 |

### Builder 模式

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 复杂对象构建识别 | ✅ | `DatabaseSchemaCache` 的构建通过 `load_schema` 封装，非裸露的逐步构建 |
| Pydantic 替代 Builder | ✅ | 合理地用 Pydantic 模型替代传统 Builder，符合 Python 惯用法 |
| Builder 必要性 | ✅ | 未发现不必要的 Builder 模式 |
| dataclass + 分组构建 | ✅ | `_Raw*` dataclass + 分组 dict + `TableSchema` 组装是合理的 builder 变体 |

---

## 代码评分

| 维度 | 评分 (1-10) | 说明 |
|------|-------------|------|
| 架构设计 | 8 | 模块边界清晰，全局状态是主要扣分点 |
| 代码简洁 | 7 | `load_schema` 略长，但整体控制较好 |
| 代码质量 | 6 | 存在多处运行时 bug（序列化缺失、异常吞咽）|
| 性能 | 7 | 顺序 fetch 和 stop_words 重建是小问题 |
| 可维护性 | 7 | 测试 stub 和全局状态是隐患 |
| **总体** | **7** | 架构设计扎实，关键实现细节需修正后可投入开发 |

---

## 修复优先级

### [P0] 必须修复（阻断实现）

1. **`--config` 参数覆盖逻辑**（严重问题 #1）— 动态构建 `AppConfig`
2. **`_serialize_value` 集成**（严重问题 #3）— 集成进 `execute_query` 的 `rows` 构建
3. **`except Exception` 静默吞咽**（严重问题 #4）— 分离超时与编程错误的处理
4. **`raw_types` 类型不一致**（严重问题 #2）— 统一为 `_RawCustomType` dataclass

### [P1] 强烈建议（影响正确性）

5. **中文查询分词**（严重问题 #5）— 支持中文字符级 tokenization
6. **测试 stub 实现**（严重问题 #6）— 填充所有 `test_models.py` 测试体
7. **错误码语义修正**（警告 #3）— 区分 `NO_DATABASE`、`DATABASE_AMBIGUOUS` 等
8. **Prompt `str.format()` 注入**（警告 #7）— 改用 `str.replace()`
9. **`test_schema_load` 占位符修正**（建议 #5）— 用 `urlparse` 解析 `pg_dsn`

### [P2] 可选优化

10. **并发 Schema fetch**（建议 #2）— `asyncio.gather()` 优化启动时间
11. **`stop_words` 提取为常量**（警告 #2）— 模块级 `frozenset`
12. **添加日志模块**（建议 #3）— 补充 PRD 要求的结构化 JSON 日志
13. **密码 URL 编码**（建议 #4）— `quote_plus` 处理特殊字符
14. **全局状态改为 lifespan context**（警告 #4）— 提升可测试性

---

## 总结

**实现计划的整体质量良好**，架构分层清晰，前期对设计文档的 10 处问题进行了系统性修正（D-01 ~ D-10），依赖图和实施顺序规划合理。

**主要风险集中在 3 个区域**：

1. **配置加载**：`--config` 覆盖方案有根本性错误，且 `dsn` 中缺少 URL 编码，这两个问题在部署阶段才会显现。

2. **运行时序列化**：`_serialize_value` 描述完整但未集成到实际代码路径，会导致含有 datetime/Decimal 列的查询在生产环境中静默失败。

3. **错误处理质量**：`result_validator.py` 的宽泛 `except` 会把代码 bug 伪装成"验证跳过"，测试中难以察觉，生产中难以排查。

建议在开始编码前先完成 **P0 的 4 项修复**，然后按 T-01 → T-02 → T-03 → T-04 → T-07 → T-08 → T-05 → T-06 → T-09 顺序实施，每个模块完成后立即补全对应单元测试（不要等到 T-11 才统一补测试）。
