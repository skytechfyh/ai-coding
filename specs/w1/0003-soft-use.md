# Project Alpha 使用说明

## 项目简介

Project Alpha 是一个基于 Web 的 Ticket 任务管理系统，采用前后端分离架构：

- **后端**：FastAPI (Python) + PostgreSQL
- **前端**：React + TypeScript + Vite + Tailwind CSS

主要功能：

- 创建、编辑、删除任务
- 标记任务完成/未完成
- 添加和筛选标签
- 按标题搜索任务

---

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Node.js | >= 18.0.0 |
| Python | >= 3.10 |
| PostgreSQL | >= 14.0 |

---

## 项目结构

```
project-alpha/
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口
│   │   ├── config.py     # 配置文件
│   │   ├── database.py   # 数据库连接
│   │   ├── models/       # SQLAlchemy 模型
│   │   └── routers/      # API 路由
│   ├── venv/             # Python 虚拟环境
│   ├── .env              # 环境变量
│   └── requirements.txt  # Python 依赖
│
└── frontend/             # React 前端
    ├── src/
    │   ├── components/   # React 组件
    │   ├── hooks/        # 自定义 Hooks
    │   ├── lib/          # 工具函数
    │   └── types/        # TypeScript 类型
    ├── dist/             # 构建输出
    └── package.json      # Node 依赖
```

---

## 环境搭建

### 1. 数据库配置

确保 PostgreSQL 已启动并创建数据库：

```bash
# 连接 PostgreSQL
psql -U fengyuhao -h localhost

# 创建数据库
CREATE DATABASE project_alpha;

# 退出
\q
```

### 2. 后端环境

```bash
# 进入后端目录
cd w1/project-alpha/backend

# 创建虚拟环境（可选）
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 前端环境

```bash
# 进入前端目录
cd w1/project-alpha/frontend

# 安装依赖
npm install
```

---

## 启动服务

### 启动后端

```bash
cd w1/project-alpha/backend
source venv/bin/activate
python -m app.main
```

后端服务将在 `http://localhost:8000` 启动。

- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`

### 启动前端

```bash
cd w1/project-alpha/frontend
npm run dev
```

前端将在 `http://localhost:5173` 或 `http://localhost:5174` 启动（端口可能被占用）。

### 生产构建

```bash
# 前端构建
cd w1/project-alpha/frontend
npm run build

# 构建输出在 dist/ 目录
```

---

## 配置说明

### 后端配置 (.env)

位于 `w1/project-alpha/backend/.env`：

```env
# 数据库连接
DATABASE_URL=postgresql://fengyuhao@localhost:5432/project_alpha

# 调试模式
DEBUG=true

# API 服务
API_HOST=0.0.0.0
API_PORT=8000

# 允许的跨域来源（多个用逗号分隔）
CORS_ORIGINS=http://localhost:5173,http://localhost:5174
```

### 前端配置

前端 API 地址在 `w1/project-alpha/frontend/src/lib/api.ts` 中配置：

```typescript
const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  // ...
});
```

如需修改后端地址，编辑此文件。

---

## 使用指南

### 1. 创建任务

1. 点击页面右上角的「新建」按钮
2. 填写任务标题（必填）
3. 添加任务描述（可选）
4. 选择标签（可选）
5. 点击「创建任务」

### 2. 编辑任务

1. 将鼠标悬停在任务卡片上
2. 点击出现的编辑图标
3. 修改任务信息
4. 点击「保存修改」

### 3. 删除任务

1. 将鼠标悬停在任务卡片上
2. 点击出现的删除图标
3. 在确认对话框中点击「确定」

### 4. 完成/取消完成任务

1. 点击任务卡片左侧的圆形按钮
2. 已完成任务会显示绿色勾选标记
3. 再次点击可取消完成状态

### 5. 按标签筛选

1. 点击左侧边栏中的标签
2. 页面将只显示带有该标签的任务
3. 点击「全部任务」查看所有任务

### 6. 搜索任务

1. 在顶部搜索框中输入关键词
2. 系统会实时搜索任务标题
3. 支持标签筛选 + 搜索组合使用

---

## 常见问题

### 数据库连接失败

检查 `.env` 文件中的 `DATABASE_URL` 是否正确：

- 用户名、密码是否匹配
- 数据库是否存在
- PostgreSQL 服务是否启动

### 前端无法连接后端

1. 检查 CORS 配置是否包含前端端口
2. 确认后端服务是否运行在正确端口
3. 查看浏览器控制台的 CORS 错误信息

### 模块未找到错误

确保已激活 Python 虚拟环境并安装依赖：

```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端框架 | FastAPI |
| ORM | SQLAlchemy |
| 数据库 | PostgreSQL |
| 前端框架 | React 18 |
| 构建工具 | Vite |
| 样式 | Tailwind CSS |
| HTTP 客户端 | Axios |
| 状态管理 | TanStack Query |
| 表单验证 | React Hook Form + Zod |

---

## 许可证

MIT License
