# Quickstart: pg-mcp

## 前提条件

- Python 3.11+
- uv (`pip install uv` 或 `brew install uv`)
- PostgreSQL 数据库（可访问）
- OpenAI API Key

---

## 1. 安装依赖

```bash
cd specs/w5/pg-mcp
uv sync
```

---

## 2. 配置

复制示例配置文件：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`：

```yaml
databases:
  - alias: "main"
    host: "localhost"
    port: 5432
    dbname: "mydb"
    user: "${DB_USER}"        # 引用环境变量
    password: "${DB_PASSWORD}"
    schemas:
      - "public"

openai:
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-4o-mini"

server:
  query_timeout_seconds: 30
  result_validation_sample_rows: 5
  max_result_rows: 1000
  auto_retry_on_invalid: false
```

设置环境变量：

```bash
export DB_USER=myuser
export DB_PASSWORD=mypassword
export OPENAI_API_KEY=sk-...
```

---

## 3. 运行 MCP Server

```bash
uv run python -m pg_mcp --config config.yaml
```

Server 将在 stdio 上监听，输出日志到 stderr。

---

## 4. 配置 Claude Desktop

在 Claude Desktop 配置文件中添加（macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "pg-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/specs/w5/pg-mcp", "python", "-m", "pg_mcp"],
      "env": {
        "DB_USER": "myuser",
        "DB_PASSWORD": "mypassword",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

---

## 5. 测试工具调用

使用 MCP CLI 测试：

```bash
# 列出数据库
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"list_databases","arguments":{}}}' | uv run python -m pg_mcp

# 生成 SQL
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"query_to_sql","arguments":{"query":"查询过去30天注册的用户数量"}}}' | uv run python -m pg_mcp
```

---

## 6. 运行测试

```bash
cd specs/w5/pg-mcp
uv run pytest tests/ -v
```

---

## 项目依赖（pyproject.toml）

```toml
[project]
name = "pg-mcp"
version = "0.1.0"
description = "PostgreSQL MCP Server — Natural language to SQL"
requires-python = ">=3.11"
dependencies = [
    "mcp[cli]>=1.8.0",
    "psycopg[binary]>=3.2",
    "psycopg-pool>=3.2",
    "openai>=1.30.0",
    "sqlglot>=23.0",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "pyyaml>=6.0",
]

[project.scripts]
pg-mcp = "pg_mcp.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.3",
]
```
