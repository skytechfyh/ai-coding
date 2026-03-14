---
description: "Task list for MySQL Support - 添加 MySQL 数据库支持"
---

# Tasks: MySQL Support

**Input**: User requirement to add MySQL support to db_query project
**Prerequisites**: Existing PostgreSQL implementation in w2/db_query/backend/src/
**Reference**: w2/db_query/backend/src/services/database.py, w2/db_query/backend/src/services/metadata.py

**Tests**: 本项目不包含测试任务，用户未明确要求测试。

**Organization**: 按用户故事分组，便于独立实现和测试

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `frontend/src/`

---

## Phase 1: Setup (MySQL 依赖和配置)

**Purpose**: 添加 MySQL 支持所需的依赖和基础配置

- [X] T001 Add mysql-connector-python or pymysql to backend dependencies in w2/db_query/backend/pyproject.toml
- [X] T002 Update .env.example with MySQL connection example in w2/db_query/.env.example
- [X] T003 Update README.md with MySQL support documentation in w2/db_query/README.md

**Checkpoint**: MySQL dependencies installed - can start implementation

---

## Phase 2: User Story 1 - MySQL 连接和元数据获取 (Priority: P1) 🎯 MVP

**Goal**: 实现 MySQL 数据库连接、元数据获取功能，支持与 PostgreSQL 相同的操作

**Independent Test**: 使用 MySQL 连接字符串连接数据库，验证能否成功获取表和视图的元数据信息

### Implementation for User Story 1

- [X] T004 [US1] Extend get_db_connection() to support MySQL URLs in w2/db_query/backend/src/services/database.py
- [X] T005 [US1] Extend test_connection() to support MySQL in w2/db_query/backend/src/services/database.py
- [X] T006 [US1] Extend execute_query() to support MySQL in w2/db_query/backend/src/services/database.py
- [X] T007 [US1] Implement get_tables_and_views() for MySQL in w2/db_query/backend/src/services/metadata.py
- [X] T008 [US1] Implement get_columns() for MySQL in w2/db_query/backend/src/services/metadata.py
- [X] T009 [US1] Add MySQL-specific error handling in w2/db_query/backend/src/services/database.py

**Checkpoint**: MySQL 连接和元数据获取功能完成 - 可以连接 MySQL 数据库并获取表结构

---

## Phase 3: User Story 2 - MySQL SQL 查询执行 (Priority: P1)

**Goal**: 确保 SQL 查询功能在 MySQL 中正确执行，处理 MySQL 和 PostgreSQL 的 SQL 语法差异

**Independent Test**: 执行简单的 MySQL SELECT 查询，验证结果正确返回

### Implementation for User Story 2

- [X] T010 [US2] Update SQL validator to handle MySQL-specific syntax in w2/db_query/backend/src/services/sql_validator.py
- [X] T011 [US2] Add MySQL dialect support for sqlglot parsing in w2/db_query/backend/src/services/sql_validator.py
- [X] T012 [US2] Test LIMIT injection works correctly for MySQL in w2/db_query/backend/src/services/sql_validator.py
- [X] T013 [US2] Handle MySQL-specific data types in query results in w2/db_query/backend/src/services/database.py

**Checkpoint**: MySQL SQL 查询执行功能完成 - 可以正确执行 MySQL SELECT 查询

---

## Phase 4: User Story 3 - MySQL 自然语言生成 SQL (Priority: P1)

**Goal**: 确保 LLM 能够根据 MySQL 表结构生成正确的 MySQL SQL 语句

**Independent Test**: 使用自然语言描述查询需求，验证生成的 SQL 在 MySQL 中能够正确执行

### Implementation for User Story 3

- [X] T014 [US3] Update LLM prompt to include database type context in w2/db_query/backend/src/services/llm.py
- [X] T015 [US3] Add MySQL-specific SQL generation hints in LLM prompt in w2/db_query/backend/src/services/llm.py
- [X] T016 [US3] Test natural language SQL generation with MySQL schema in w2/db_query/backend/src/services/llm.py

**Checkpoint**: MySQL 自然语言生成 SQL 功能完成 - LLM 可以生成正确的 MySQL SQL 语句

---

## Phase 5: Polish & Testing (优化和测试)

**Purpose**: 完善 MySQL 支持，处理边界情况和错误场景

- [X] T017 [P] Add database type detection from connection URL in w2/db_query/backend/src/services/database.py
- [X] T018 [P] Update error messages to be MySQL-specific where needed in w2/db_query/backend/src/services/database.py
- [ ] T019 Test MySQL connection with various URL formats (mysql://, mysql+pymysql://)
- [ ] T020 Test MySQL metadata extraction with different schema structures
- [ ] T021 Test MySQL query execution with complex queries
- [ ] T022 Test natural language SQL generation for MySQL-specific scenarios
- [X] T023 [P] Update CLAUDE.md with MySQL support information

**Checkpoint**: MySQL 支持完整实现并测试通过

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **User Story 1 (Phase 2)**: Depends on Setup completion - Core MySQL connection and metadata
- **User Story 2 (Phase 3)**: Depends on User Story 1 - SQL query execution
- **User Story 3 (Phase 4)**: Depends on User Story 1 and 2 - Natural language SQL generation
- **Polish (Phase 5)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Setup (Phase 1) - No dependencies on other stories
- **User Story 2 (P1)**: Depends on User Story 1 - Needs connection and metadata functionality
- **User Story 3 (P1)**: Depends on User Story 1 and 2 - Needs both connection and query execution

### Within Each User Story

- User Story 1: T004-T006 can run in parallel (different functions), then T007-T009
- User Story 2: T010-T012 sequential (same file), T013 can be parallel
- User Story 3: T014-T016 sequential (same file, building on each other)

### Parallel Opportunities

- T001, T002, T003: Setup tasks can run in parallel
- T004, T005, T006: Database connection functions can be modified in parallel
- T017, T018, T023: Polish tasks can run in parallel

---

## Implementation Strategy

### MVP First (Phase 1 + Phase 2)

1. Complete Phase 1: Setup - Add MySQL dependencies
2. Complete Phase 2: User Story 1 - MySQL connection and metadata
3. **STOP and VALIDATE**: Test MySQL connection with real database
4. Verify metadata extraction works correctly

### Incremental Delivery

1. Add Setup → Foundation ready
2. Add User Story 1 → Test independently → MySQL connection works
3. Add User Story 2 → Test independently → MySQL queries work
4. Add User Story 3 → Test independently → Natural language SQL works
5. Polish and finalize

---

## MySQL vs PostgreSQL SQL Syntax Differences to Handle

### Key Differences

1. **String Quoting**:
   - PostgreSQL: Single quotes for strings, double quotes for identifiers
   - MySQL: Both single and double quotes for strings, backticks for identifiers

2. **LIMIT Syntax**:
   - PostgreSQL: `LIMIT n OFFSET m`
   - MySQL: `LIMIT m, n` or `LIMIT n OFFSET m` (both supported)

3. **Boolean Type**:
   - PostgreSQL: `BOOLEAN` type with `TRUE`/`FALSE`
   - MySQL: `TINYINT(1)` with `1`/`0`

4. **String Concatenation**:
   - PostgreSQL: `||` operator or `CONCAT()`
   - MySQL: `CONCAT()` function

5. **Date/Time Functions**:
   - PostgreSQL: `NOW()`, `CURRENT_TIMESTAMP`
   - MySQL: `NOW()`, `CURRENT_TIMESTAMP()`, `CURDATE()`, `CURTIME()`

6. **Auto Increment**:
   - PostgreSQL: `SERIAL` or `IDENTITY`
   - MySQL: `AUTO_INCREMENT`

7. **Information Schema**:
   - PostgreSQL: `information_schema.tables` with `table_schema`
   - MySQL: `information_schema.tables` with `table_schema` (similar but different column names)

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- Each user story should be independently testable
- MySQL support should mirror PostgreSQL functionality
- Use sqlglot with MySQL dialect for SQL parsing
- Consider using pymysql or mysql-connector-python for MySQL connections
- Total: 23 tasks across 5 phases
