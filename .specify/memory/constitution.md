<!--
## Sync Impact Report

**Version change**: N/A → 1.0.0 (Initial creation)
**Modified principles**: N/A (New file)
**Added sections**:
  - Core Principles (5 principles)
  - Technology Stack
  - Data Conventions
  - Governance
**Removed sections**: N/A
**Templates requiring updates**:
  - .specify/templates/plan-template.md ✅ No changes needed (generic template)
  - .specify/templates/spec-template.md ✅ No changes needed (generic template)
  - .specify/templates/tasks-template.md ✅ No changes needed (generic template)
**Follow-up TODOs**: None
-->

# DB Query Project Constitution

## Core Principles

### I. Ergonomic Python & TypeScript Stack

后端代码 MUST 使用 Ergonomic Python 风格编写，强调代码的可读性、简洁性和 Pythonic 实践。
前端代码 MUST 使用 TypeScript 编写。

**具体要求**:

- 后端使用现代 Python 特性（类型提示、dataclasses、context managers 等）
- 遵循 PEP 8 和 Python 之禅的原则
- 前端使用 TypeScript，启用严格模式
- 代码清晰优先于过度工程化

**Rationale**: 确保代码库的可维护性和一致性，降低团队成员的学习成本，提高开发效率。

### II. Strict Type Annotations (NON-NEGOTIABLE)

所有后端和前端代码 MUST 具有完整的类型标注。不允许存在 `Any` 类型的滥用或类型标注缺失。

**具体要求**:

- 后端：所有函数参数、返回值、类属性必须有类型标注
- 前端：所有 TypeScript 代码启用 `strict` 模式
- 禁止使用 `# type: ignore` 注释，除非有明确的文档说明原因
- 使用类型检查工具（mypy/pyright for Python, tsc for TypeScript）进行静态类型检查

**Rationale**: 类型安全是代码质量的基石，能够在编译/静态检查阶段发现大量潜在错误，提升代码可靠性和 IDE 支持。

### III. Pydantic Data Models

所有数据模型 MUST 使用 Pydantic 定义。禁止使用裸字典、namedtuple 或无验证的数据类。

**具体要求**:

- 使用 Pydantic V2 或更高版本
- 所有 API 输入/输出必须通过 Pydantic 模型验证
- 模型必须包含字段验证逻辑
- 复杂数据结构使用嵌套 Pydantic 模型

**Rationale**: Pydantic 提供运行时数据验证、序列化/反序列化、以及与类型系统的完美集成，确保数据完整性。

### IV. CamelCase JSON Convention

后端生成的所有 JSON 数据 MUST 使用 camelCase 格式命名键名。

**具体要求**:

- Pydantic 模型配置：`model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)`
- API 响应统一使用 camelCase 键名
- 前端接收到的数据已经是 camelCase 格式，无需额外转换
- 数据库字段和 Python 代码内部使用 snake_case

**Rationale**: 前后端命名约定统一，减少手动转换代码，降低出错风险，提升开发体验。

### V. No Authentication Required

系统 MUST NOT 实现任何形式的身份验证或授权机制。所有功能对所有用户开放。

**具体要求**:

- 无需登录/注册功能
- 无需 API 密钥或 Token
- 无需用户角色或权限管理
- 所有 API 端点公开可访问

**Rationale**: 简化系统架构，专注于核心业务功能，适合内部工具或演示场景。

## Technology Stack

**Backend**:
- Language: Python 3.11+
- Web Framework: FastAPI (recommended) or Flask
- Data Validation: Pydantic V2+
- Type Checker: mypy or pyright
- Package Manager: uv or poetry

**Frontend**:
- Language: TypeScript 5+
- Framework: React/Vue/Svelte (project-specific)
- Type Checker: TypeScript strict mode
- Package Manager: npm/pnpm/yarn

**Database**:
- Any SQL or NoSQL database (project-specific)
- ORM: SQLAlchemy (if SQL) or project-appropriate

## Data Conventions

### Naming Conventions

| Context | Convention | Example |
|---------|------------|---------|
| Python variables/functions | snake_case | `get_user_by_id` |
| Python classes | PascalCase | `UserProfile` |
| JSON keys (API response) | camelCase | `{ "userId": 123 }` |
| Database columns | snake_case | `user_id` |
| TypeScript variables | camelCase | `userId` |
| TypeScript interfaces/types | PascalCase | `UserProfile` |

### API Response Format

```json
{
  "success": true,
  "data": { ... },
  "errorMessage": null
}
```

Error response:
```json
{
  "success": false,
  "data": null,
  "errorMessage": "Error description"
}
```

## Governance

### Amendment Procedure

1. 宪法修改必须通过代码评审批准
2. 重大变更（原则增删）需要递增 MAJOR 版本号
3. 新增指导性内容递增 MINOR 版本号
4. 文档修正递增 PATCH 版本号
5. 所有修改必须在 Sync Impact Report 中记录

### Compliance Review

- 所有 PR 必须通过类型检查
- 所有 Pydantic 模型必须经过验证
- API 响应格式必须符合 camelCase 约定
- 代码审查时检查宪法合规性

### Versioning Policy

遵循语义化版本规范 (SemVer):
- **MAJOR**: 不兼容的原则变更或原则删除
- **MINOR**: 新增原则或显著扩展指导内容
- **PATCH**: 澄清、措辞修正、非语义性改进

**Version**: 1.0.0 | **Ratified**: 2026-02-23 | **Last Amended**: 2026-02-23
