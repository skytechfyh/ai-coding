# Quickstart: 数据库查询工具

**Feature**: 001-db-query
**Date**: 2026-02-23

## Prerequisites

### Backend

- Python 3.11+
- uv (package manager)

### Frontend

- Node.js 18+
- npm or pnpm

### Environment Variables

创建 `.env` 文件：

```bash
# Backend
OPENAI_API_KEY=your-openai-api-key

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Backend Setup

```bash
cd w2/db_query/backend

# 创建虚拟环境
uv venv

# 安装依赖
uv sync

# 运行开发服务器
uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

后端将在 `http://localhost:8000` 启动。

API 文档可在 `http://localhost:8000/docs` 查看。

---

## Frontend Setup

```bash
cd w2/db_query/frontend

# 安装依赖
npm install

# 运行开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动。

---

## Project Structure

```
w2/db_query/
├── backend/
│   ├── src/
│   │   ├── api/
│   │   │   └── routes.py       # API 路由
│   │   ├── models/
│   │   │   └── schemas.py       # Pydantic 模型
│   │   ├── services/
│   │   │   ├── database.py     # 数据库连接
│   │   │   ├── metadata.py     # 元数据获取
│   │   │   └── llm.py         # LLM SQL 生成
│   │   ├── db/
│   │   │   └── store.py        # SQLite 存储
│   │   └── main.py             # 应用入口
│   ├── pyproject.toml
│   └── uv.lock
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── DatabaseList.tsx
    │   │   ├── DatabaseForm.tsx
    │   │   ├── TableList.tsx
    │   │   ├── SqlEditor.tsx
    │   │   └── ResultTable.tsx
    │   ├── pages/
    │   │   └── index.tsx
    │   ├── services/
    │   │   └── api.ts
    │   ├── types/
    │   │   └── index.ts
    │   └── App.tsx
    ├── package.json
    └── vite.config.ts
```

---

## Key Technologies

| Layer | Technology |
|-------|------------|
| Backend Framework | FastAPI |
| Data Validation | Pydantic V2 |
| SQL Parsing | sqlglot |
| LLM | OpenAI API |
| Local Storage | SQLite |
| Frontend Framework | React + Refine 5 |
| UI Library | Ant Design |
| Code Editor | Monaco Editor |

---

## First Run

1. 启动后端：`uv run python -m uvicorn src.main:app --reload`
2. 启动前端：`npm run dev`
3. 打开浏览器访问 `http://localhost:5173`
4. 点击 "Add Database" 添加一个 PostgreSQL 数据库
5. 连接成功后，点击表名查看元数据
6. 在 SQL 编辑器中输入查询并执行，或使用自然语言生成 SQL
