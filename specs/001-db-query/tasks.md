---
description: "Task list for 数据库查询工具 - UI优化版"
---

# Tasks: 数据库查询工具

**Input**: Design documents from `/specs/001-db-query/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: 本项目不包含测试任务，用户未明确要求测试。

**Organization**: 用户故事分组，便于独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup & Foundation (项目初始化和基础设施)

**Purpose**: 项目初始化、依赖安装、基础架构搭建

- [X] T001 Create backend project structure in w2/db_query/backend/
- [X] T002 Create frontend project structure in w2/db_query/frontend/
- [X] T003 [P] Initialize Python backend with uv, FastAPI, sqlglot, openai, pydantic
- [X] T004 [P] Initialize React frontend with Refine 5, Ant Design, Monaco Editor
- [X] T005 Configure TypeScript strict mode in frontend/tsconfig.json
- [X] T006 Configure mypy/pyright for backend type checking
- [X] T007 Setup CORS to allow all origins in backend
- [X] T008 Create environment configuration (.env.example)
- [X] T009 Create README.md with project setup instructions

**Checkpoint**: Project structure ready - can start backend/frontend development

---

## Phase 2: Core Features (核心功能)

**Goal**: 实现数据库连接、SQL查询、自然语言生成 SQL - MVP 功能

### 2.1 Backend - Core API

- [X] T010 [P] [US1] Create Pydantic schemas in backend/src/models/schemas.py
- [X] T011 [P] [US1] Implement SQLite storage for connections in backend/src/db/store.py
- [X] T012 [US1] Implement database connection service in backend/src/services/database.py
- [X] T013 [US1] Implement metadata extraction service in backend/src/services/metadata.py
- [X] T014 [P] [US1] Implement GET /dbs endpoint in backend/src/api/routes.py
- [X] T015 [US1] Implement PUT /dbs/{name} endpoint in backend/src/api/routes.py
- [X] T016 [US1] Implement GET /dbs/{name} endpoint in backend/src/api/routes.py
- [X] T017 [US2] Implement SQL validation and LIMIT injection in backend/src/services/sql_validator.py
- [X] T018 [US2] Implement POST /dbs/{name}/query endpoint in backend/src/api/routes.py
- [X] T019 [US3] Implement LLM SQL generation service in backend/src/services/llm.py
- [X] T020 [US3] Implement POST /dbs/{name}/query/natural endpoint in backend/src/api/routes.py
- [X] T021 [US1-3] Add DELETE /dbs/{name} endpoint in backend/src/api/routes.py
- [X] T022 [US1-3] Configure Pydantic to use camelCase in API responses

### 2.2 Frontend - Core UI

- [X] T023 [P] [US1] Create TypeScript types in frontend/src/types/index.ts
- [X] T024 [P] [US1] Create API service in frontend/src/services/api.ts
- [X] T025 [US1] Implement DatabaseList component in frontend/src/components/DatabaseList.tsx
- [X] T026 [US1] Implement DatabaseForm modal in frontend/src/components/DatabaseForm.tsx
- [X] T027 [US1] Implement TableList component in frontend/src/components/TableList.tsx
- [X] T028 [US2] Implement SqlEditor component with Monaco in frontend/src/components/SqlEditor.tsx
- [X] T029 [US2] Implement ResultTable component in frontend/src/components/ResultTable.tsx
- [X] T030 [US3] Implement NaturalLanguageInput component in frontend/src/components/NaturalLanguageInput.tsx
- [X] T031 [US1-3] Create main page layout in frontend/src/pages/index.tsx

**Checkpoint**: MVP ready - can connect to DB, execute SQL queries, generate SQL from natural language

---

## Phase 3: Enhancement & Polish (增强功能和优化)

**Goal**: 连接管理、查询历史、结果导出、错误处理优化

### 3.1 Backend - Enhanced Features

- [ ] T032 [P] [US4] Add connection update endpoint in backend/src/api/routes.py
- [X] T033 [P] [US4] Add lastUsedAt tracking in backend/src/db/store.py
- [X] T034 [US5] Implement query history storage in backend/src/db/store.py
- [X] T035 [US5] Add query history endpoint in backend/src/api/routes.py
- [X] T036 [US5] Implement CSV export in backend/src/services/exporter.py
- [X] T037 [US5] Implement JSON export in backend/src/services/exporter.py

### 3.2 Frontend - Enhanced UI

- [X] T038 [P] [US4] Add connection edit/delete functionality in frontend/src/components/DatabaseList.tsx
- [X] T039 [US5] Implement QueryHistory panel in frontend/src/components/QueryHistory.tsx
- [X] T040 [US5] Add export buttons (CSV/JSON) in frontend/src/components/ResultTable.tsx
- [X] T041 [US1-3] Add loading states and error handling UI
- [X] T042 [US1-3] Add connection status indicator

### 3.3 Polish

- [X] T043 [P] Run type checking (mypy + tsc) and fix errors
- [X] T044 [P] Verify all API responses use camelCase
- [X] T045 Test end-to-end flow with real database
- [ ] T046 Update quickstart.md with verified setup steps

---

## Phase 4: UI/UX Optimization (UI/UX 优化)

**Goal**: 按照 Apple 和 DataGrip 设计风格优化前端界面

**Design Principles**:
- Apple 风格: 简洁、极简、大量留白、清晰的视觉层次、高对比度
- DataGrip 风格: 左侧边栏显示数据库/表结构、右侧主区域查询和结果、效率优先
- 使用 Refine 5 组件库保持一致性

### 4.1 Layout Restructure (DataGrip-style three-panel layout)

- [X] T047 [P] [US1] Create three-panel layout in frontend/src/layouts/MainLayout.tsx (sidebar, query area, results)
- [X] T048 [P] [US1] Implement collapsible database sidebar in frontend/src/components/DatabaseSidebar.tsx
- [X] T049 [US1] Move TableList to sidebar with tree view in frontend/src/components/DatabaseSidebar.tsx
- [X] T050 [P] [US2] Create query tab container in frontend/src/components/SqlEditorPanel.tsx
- [X] T051 [US2] Move Monaco SQL editor to main area with toolbar in frontend/src/components/SqlEditorPanel.tsx

### 4.2 Apple-style Visual Design

- [X] T052 [P] Apply Apple design tokens in frontend/src/styles/theme.ts (colors, spacing, typography)
- [X] T053 [P] Configure Ant Design theme with Apple-inspired design in frontend/src/styles/antd.config.ts
- [X] T054 Update global styles with Apple typography in frontend/src/styles/globals.css
- [X] T055 [US1-3] Redesign DatabaseList with Apple card style in frontend/src/components/DatabaseSidebar.tsx
- [X] T056 [US3] Redesign NaturalLanguageInput with Apple input style in frontend/src/components/NaturalLanguageInput.tsx

### 4.3 Monaco Editor Enhancement

- [X] T057 [P] [US2] Configure Monaco with DataGrip-inspired theme in frontend/src/styles/monaco-theme.ts
- [X] T058 [US2] Add SQL IntelliSense/autocomplete in frontend/src/styles/sql-completion.ts
- [X] T059 [US2] Add keyboard shortcuts for query execution in frontend/src/components/SqlEditorPanel.tsx
- [X] T060 [US2] Add multiple query tabs support in frontend/src/components/SqlEditorPanel.tsx

### 4.4 Results Table Enhancement (DataGrip-style)

- [X] T061 [P] [US2] Implement sortable columns in frontend/src/components/ResultTable.tsx
- [X] T062 [US2] Add column resize in frontend/src/components/ResultTable.tsx
- [X] T063 [US2] Add cell value copy on click in frontend/src/components/ResultTable.tsx
- [ ] T064 [US2] Add data type indicators per column in frontend/src/components/ResultTable.tsx

### 4.5 Polish & Animation

- [X] T065 [P] [US1-3] Add smooth transitions for panel collapse/expand
- [ ] T066 [P] [US1-3] Add loading skeleton states instead of spinners
- [ ] T067 [US1-3] Add toast notifications with Apple-style design
- [ ] T068 [US1-3] Final visual polish and responsive design

**Checkpoint**: UI/UX optimized - Apple + DataGrip style applied

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: No dependencies - can start immediately
- **Phase 2**: Depends on Phase 1 - All core features built here
- **Phase 3**: Depends on Phase 2 - Enhancement and polish
- **Phase 4**: Depends on Phase 3 - UI/UX optimization

### Within Phase 4

- T047, T048, T052, T053: Can run in parallel (layout and theme setup)
- T054-T056: Depends on theme configuration
- T057-T060: Can run in parallel (Monaco enhancements)
- T061-T064: Can run in parallel (results table)
- T065-T068: Polish tasks, can run in parallel

### Parallel Opportunities

- T047, T048, T052, T053: Layout and theme setup can run in parallel
- T057, T058, T059, T060: Monaco enhancements can run in parallel
- T061, T062, T063, T064: Results table enhancements can run in parallel
- T065, T066, T067, T068: Polish tasks can run in parallel

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Core Features
3. **STOP and VALIDATE**: Test the full flow
4. Deploy/demo if ready

### Enhancement Phase (Phase 3)

1. Complete Phase 3: Enhanced features
2. Test and validate all enhancements

### UI/UX Optimization (Phase 4)

1. Restructure to DataGrip-style three-panel layout
2. Apply Apple design tokens and theme
3. Enhance Monaco Editor
4. Enhance Results Table
5. Polish and finalize

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each phase should be independently testable
- US1, US2, US3 are all P1 priority - done together in Phase 2
- US4 (P2), US5 (P3) done in Phase 3
- Phase 4 is UI/UX optimization based on Apple + DataGrip design
- Total: 68 tasks across 4 phases
