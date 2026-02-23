# Implementation Plan: 数据库查询工具

**Branch**: `001-db-query` | **Date**: 2026-02-23 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-db-query/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

这是一个数据库查询 Web 应用程序，用户可以添加数据库连接，系统连接到数据库获取 metadata 并展示表和视图信息，用户可以手动输入 SQL 查询或使用自然语言生成 SQL 查询。后端使用 Python + FastAPI，前端使用 React + Refine + Ant Design。

## Technical Context

**Language/Version**: Python 3.11+, TypeScript 5+
**Primary Dependencies**: FastAPI, sqlglot, openai (SDK), React, Refine 5, Ant Design, Monaco Editor
**Storage**: SQLite (本地存储：~/.db_query/db_query.db) + 目标数据库（PostgreSQL）
**Testing**: pytest (后端), Jest/Vitest (前端)
**Target Platform**: Web 浏览器（桌面端优先）
**Project Type**: Web Service + Frontend Application
**Performance Goals**: 简单查询响应时间 < 5s, 界面加载 < 2s
**Constraints**: 无认证要求，CORS 开放所有 origin
**Scale/Scope**: 单用户内部工具，预计 10 个以内并发用户

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 状态 | 说明 |
|------|------|------|
| I. Ergonomic Python & TypeScript Stack | ✅ PASS | Python 3.11+ 和 TypeScript 5+ |
| II. Strict Type Annotations | ✅ PASS | 启用 mypy/pyright 和 TypeScript strict 模式 |
| III. Pydantic Data Models | ✅ PASS | 后端所有数据模型使用 Pydantic V2 |
| IV. CamelCase JSON Convention | ✅ PASS | API 响应使用 camelCase (通过 Pydantic alias_generator) |
| V. No Authentication Required | ✅ PASS | 无需认证，所有端点公开 |

## Project Structure

### Documentation (this feature)

```text
specs/001-db-query/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code

```text
w2/db_query/
├── backend/
│   ├── src/
│   │   ├── models/          # Pydantic 数据模型
│   │   ├── services/        # 业务逻辑服务
│   │   ├── api/             # FastAPI 路由
│   │   ├── db/              # 数据库连接和存储
│   │   └── main.py          # 应用入口
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   ├── pyproject.toml
│   └── uv.lock
│
├── frontend/
│   ├── src/
│   │   ├── components/     # React 组件
│   │   ├── pages/          # 页面组件
│   │   ├── services/        # API 调用服务
│   │   ├── types/           # TypeScript 类型定义
│   │   └── App.tsx
│   ├── tests/
│   ├── package.json
│   └── vite.config.ts
│
└── README.md
```

**Structure Decision**: Web 应用结构，分离 backend/ 和 frontend/ 目录。后端使用 FastAPI + Pydantic V2，前端使用 React + Refine 5 + Ant Design + Monaco Editor。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 无 | N/A | N/A |

## Phase 0: Research & Outline

### Research Tasks

1. **FastAPI 最佳实践**: 研究 FastAPI 与 Pydantic V2 集成、CORS 配置
2. **SQLGlot SQL 解析**: 研究如何使用 sqlglot 验证 SQL 语法并添加 LIMIT
3. **OpenAI Function Calling**: 研究如何构建 prompt 让 LLM 生成 SQL
4. **Refine 5 + Ant Design**: 研究 Refine 框架与 Ant Design 集成
5. **Monaco Editor React 集成**: 研究如何在 React 中集成 Monaco Editor

### Research Findings

#### FastAPI + Pydantic V2

- 使用 `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)`
- C 实现 camelCase 输出ORS 配置使用 `from fastapi.middleware.cors import CORSMiddleware`，允许所有 origin

#### SQLGlot

- 使用 `sqlglot.parse()` 解析 SQL
- 检查 AST 确保是 SELECT 语句
- 使用 `exp.Limit` 添加 LIMIT 1000

#### OpenAI API

- 使用 `openai` Python SDK
- 将表结构作为 system prompt 的一部分
- 使用 user prompt 传递自然语言查询

#### Refine + Ant Design

- Refine 5 内置支持 Ant Design
- 使用 `<Table>` 组件展示查询结果
- 使用 `<Modal>` 处理数据库连接表单

#### Monaco Editor

- 使用 `@monaco-editor/react` 包
- 配置 SQL 语言高亮
- 支持基本编辑功能

## Phase 1: Design & Contracts

### Data Model

详见 [data-model.md](data-model.md)

### API Contracts

详见 [contracts/](contracts/)

### Quick Start

详见 [quickstart.md](quickstart.md)

## Next Steps

- 执行 `/speckit.tasks` 生成任务列表
- 开始 Phase 1 实现
