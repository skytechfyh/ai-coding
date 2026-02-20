# Project Alpha 实现计划

## 项目基础路径

**项目根目录**: `./w1/project-alpha/`

完整的项目结构如下：
```
./w1/project-alpha/
├── backend/          # 后端项目
│   ├── app/
│   ├── requirements.txt
│   └── ...
└── frontend/        # 前端项目
    ├── src/
    ├── package.json
    └── ...
```

> **注意**: 本文档中所有文件路径均基于项目根目录 `./w1/project-alpha/`。
> 例如 `backend/app/main.py` 表示 `./w1/project-alpha/backend/app/main.py`

---

## 概述

本文档基于 `0001-spec.md` 需求和设计文档，详细描述 Project Alpha 项目的具体实现步骤、文件创建顺序和技术要点。

---

## 阶段一：项目初始化与环境搭建

### 1.1 创建项目目录结构

```bash
# 进入项目目录
cd ./w1/project-alpha

# 创建后端目录结构
mkdir -p backend/app/{models,schemas,routers,services,utils}
mkdir -p ./w1/project-alpha/backend/alembic/versions
mkdir -p ./w1/project-alpha/backend/tests

# 创建前端目录结构
mkdir -p frontend/src/{components/ui,hooks,lib,types}
mkdir -p frontend/public
```

### 1.2 后端初始化

#### 步骤 1.2.1：创建 Python 虚拟环境

```bash
cd ./w1/project-alpha/backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Linux/Mac)
source venv/bin/activate

# Windows
# venv\Scripts\activate
```

#### 步骤 1.2.2：创建 requirements.txt

```bash
# 文件路径: ./w1/project-alpha/backend/requirements.txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0
alembic==1.13.1
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

#### 步骤 1.2.3：安装后端依赖

```bash
cd ./w1/project-alpha/backend
pip install -r requirements.txt
```

#### 步骤 1.2.4：创建环境变量文件

```bash
# 文件路径: ./w1/project-alpha/backend/.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/project_alpha
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### 1.3 前端初始化

#### 步骤 1.3.1：创建 Vite React 项目

```bash
cd ./w1/project-alpha/frontend

# 使用 Vite 创建 React TypeScript 项目
npm create vite@latest . -- --template react-ts
```

#### 步骤 1.3.2：安装项目依赖

```bash
cd ./w1/project-alpha/frontend

# 安装核心依赖
npm install

# 安装额外依赖
npm install axios @tanstack/react-query react-hook-form zod @hookform/resolvers
npm install react-router-dom

# 安装 Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# 安装 Shadcn UI 相关依赖
npm install -D @types/node
```

#### 步骤 1.3.3：配置 Tailwind CSS

```javascript
// 文件路径: ./w1/project-alpha/frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

```css
/* 文件路径: ./w1/project-alpha/frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### 步骤 1.3.4：创建 .env 文件

```bash
# 文件路径: ./w1/project-alpha/frontend/.env
VITE_API_URL=http://localhost:8000/api/v1
```

---

## 阶段二：后端核心功能实现

### 2.1 数据库配置

#### 文件：./w1/project-alpha/backend/app/__init__.py
```python
# 空文件，用于将 app 目录标记为 Python 包
```

#### 文件：./w1/project-alpha/backend/app/config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()
```

#### 文件：./w1/project-alpha/backend/app/database.py
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
```

### 2.2 数据模型

#### 文件：./w1/project-alpha/backend/app/models/__init__.py
```python
from app.models.ticket import Ticket
from app.models.tag import Tag

__all__ = ["Ticket", "Tag"]
```

#### 文件：./w1/project-alpha/backend/app/models/ticket.py
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

ticket_tags = Table(
    'ticket_tags',
    Base.metadata,
    Column('ticket_id', Integer, ForeignKey('tickets.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default='pending', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    tags = relationship('Tag', secondary=ticket_tags, back_populates='tickets')
```

#### 文件：./w1/project-alpha/backend/app/models/tag.py
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default='#6B7280', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tickets = relationship('Ticket', secondary='ticket_tags', back_populates='tags')
```

### 2.3 Pydantic Schema

#### 文件：./w1/project-alpha/backend/app/schemas/__init__.py
```python
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.schemas.tag import TagCreate, TagUpdate, TagResponse

__all__ = ["TicketCreate", "TicketUpdate", "TicketResponse", "TagCreate", "TagUpdate", "TagResponse"]
```

#### 文件：./w1/project-alpha/backend/app/schemas/ticket.py
```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class TagInResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime

    class Config:
        from_attributes = True

class TicketBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)

class TicketCreate(TicketBase):
    tag_ids: Optional[List[int]] = None

class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None
    tag_ids: Optional[List[int]] = None

class TicketResponse(TicketBase):
    id: int
    status: str
    tags: List[TagInResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

#### 文件：./w1/project-alpha/backend/app/schemas/tag.py
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = Field('#6B7280', max_length=7)

class TagCreate(TagBase):
    pass

class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, max_length=7)

class TagResponse(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
```

### 2.4 自定义异常

#### 文件：./w1/project-alpha/backend/app/utils/__init__.py
```python
# 空文件
```

#### 文件：./w1/project-alpha/backend/app/utils/exceptions.py
```python
from fastapi import HTTPException, status

class TicketNotFoundException(HTTPException):
    def __init__(self, ticket_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} 不存在"
        )

class TagNotFoundException(HTTPException):
    def __init__(self, tag_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"标签 #{tag_id} 不存在"
        )

class DuplicateNameException(HTTPException):
    def __init__(self, name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"名称 '{name}' 已存在"
        )

class InvalidInputException(HTTPException):
    def __init__(self, message: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
```

### 2.5 服务层

#### 文件：./w1/project-alpha/backend/app/services/__init__.py
```python
# 空文件
```

#### 文件：./w1/project-alpha/backend/app/services/ticket_service.py
```python
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from app.models.ticket import Ticket
from app.models.tag import Tag
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.utils.exceptions import TicketNotFoundException, TagNotFoundException

class TicketService:
    @staticmethod
    def get_tickets(
        db: Session,
        tag_id: Optional[int] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Ticket], int]:
        query = db.query(Ticket)

        # 按标签筛选
        if tag_id:
            query = query.join(Ticket.tags).filter(Tag.id == tag_id)

        # 按状态筛选
        if status:
            query = query.filter(Ticket.status == status)

        # 按标题搜索
        if search:
            query = query.filter(Ticket.title.ilike(f"%{search}%"))

        # 获取总数
        total = query.count()

        # 分页
        tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()

        return tickets, total

    @staticmethod
    def get_ticket_by_id(db: Session, ticket_id: int) -> Ticket:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise TicketNotFoundException(ticket_id)
        return ticket

    @staticmethod
    def create_ticket(db: Session, ticket_data: TicketCreate) -> Ticket:
        # 处理标签
        tags = []
        if ticket_data.tag_ids:
            tags = db.query(Tag).filter(Tag.id.in_(ticket_data.tag_ids)).all()

        ticket = Ticket(
            title=ticket_data.title,
            description=ticket_data.description,
            tags=tags
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def update_ticket(db: Session, ticket_id: int, ticket_data: TicketUpdate) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)

        # 更新字段
        if ticket_data.title is not None:
            ticket.title = ticket_data.title
        if ticket_data.description is not None:
            ticket.description = ticket_data.description
        if ticket_data.status is not None:
            ticket.status = ticket_data.status

        # 更新标签
        if ticket_data.tag_ids is not None:
            tags = db.query(Tag).filter(Tag.id.in_(ticket_data.tag_ids)).all()
            ticket.tags = tags

        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def delete_ticket(db: Session, ticket_id: int) -> None:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        db.delete(ticket)
        db.commit()

    @staticmethod
    def complete_ticket(db: Session, ticket_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        ticket.status = 'completed'
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def uncomplete_ticket(db: Session, ticket_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        ticket.status = 'pending'
        db.commit()
        db.refresh(ticket)
        return ticket

    @staticmethod
    def add_tag_to_ticket(db: Session, ticket_id: int, tag_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise TagNotFoundException(tag_id)

        if tag not in ticket.tags:
            ticket.tags.append(tag)
            db.commit()
            db.refresh(ticket)
        return ticket

    @staticmethod
    def remove_tag_from_ticket(db: Session, ticket_id: int, tag_id: int) -> Ticket:
        ticket = TicketService.get_ticket_by_id(db, ticket_id)
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise TagNotFoundException(tag_id)

        if tag in ticket.tags:
            ticket.tags.remove(tag)
            db.commit()
            db.refresh(ticket)
        return ticket
```

#### 文件：./w1/project-alpha/backend/app/services/tag_service.py
```python
from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.tag import Tag
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.exceptions import TagNotFoundException, DuplicateNameException

class TagService:
    @staticmethod
    def get_tags(db: Session) -> List[Tag]:
        return db.query(Tag).order_by(Tag.created_at.desc()).all()

    @staticmethod
    def get_tag_by_id(db: Session, tag_id: int) -> Tag:
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise TagNotFoundException(tag_id)
        return tag

    @staticmethod
    def create_tag(db: Session, tag_data: TagCreate) -> Tag:
        # 检查名称是否重复
        existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
        if existing:
            raise DuplicateNameException(tag_data.name)

        tag = Tag(
            name=tag_data.name,
            color=tag_data.color or '#6B7280'
        )
        db.add(tag)
        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def update_tag(db: Session, tag_id: int, tag_data: TagUpdate) -> Tag:
        tag = TagService.get_tag_by_id(db, tag_id)

        # 检查名称是否重复
        if tag_data.name and tag_data.name != tag.name:
            existing = db.query(Tag).filter(Tag.name == tag_data.name).first()
            if existing:
                raise DuplicateNameException(tag_data.name)
            tag.name = tag_data.name

        if tag_data.color:
            tag.color = tag_data.color

        db.commit()
        db.refresh(tag)
        return tag

    @staticmethod
    def delete_tag(db: Session, tag_id: int) -> None:
        tag = TagService.get_tag_by_id(db, tag_id)
        db.delete(tag)
        db.commit()
```

### 2.6 API 路由

#### 文件：./w1/project-alpha/backend/app/routers/__init__.py
```python
# 空文件
```

#### 文件：./w1/project-alpha/backend/app/routers/ticket.py
```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketResponse
from app.services import ticket_service

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("")
def get_tickets(
    tag_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    tickets, total = ticket_service.TicketService.get_tickets(
        db, tag_id=tag_id, status=status, search=search, skip=skip, limit=page_size
    )

    return {
        "success": True,
        "data": {
            "items": [TicketResponse.model_validate(t) for t in tickets],
            "total": total,
            "page": page,
            "page_size": page_size
        }
    }

@router.get("/{ticket_id}")
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.get_ticket_by_id(db, ticket_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}

@router.post("")
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    new_ticket = ticket_service.TicketService.create_ticket(db, ticket)
    return {"success": True, "data": TicketResponse.model_validate(new_ticket)}

@router.put("/{ticket_id}")
def update_ticket(ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_db)):
    updated_ticket = ticket_service.TicketService.update_ticket(db, ticket_id, ticket)
    return {"success": True, "data": TicketResponse.model_validate(updated_ticket)}

@router.patch("/{ticket_id}")
def patch_ticket(ticket_id: int, ticket: TicketUpdate, db: Session = Depends(get_db)):
    updated_ticket = ticket_service.TicketService.update_ticket(db, ticket_id, ticket)
    return {"success": True, "data": TicketResponse.model_validate(updated_ticket)}

@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket_service.TicketService.delete_ticket(db, ticket_id)
    return {"success": True, "message": "Ticket 删除成功"}

@router.patch("/{ticket_id}/complete")
def complete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.complete_ticket(db, ticket_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}

@router.patch("/{ticket_id}/uncomplete")
def uncomplete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.uncomplete_ticket(db, ticket_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}

@router.post("/{ticket_id}/tags")
def add_tag_to_ticket(ticket_id: int, data: dict, db: Session = Depends(get_db)):
    tag_id = data.get("tag_id")
    if not tag_id:
        return {"success": False, "error": {"code": "INVALID_INPUT", "message": "tag_id 不能为空"}}

    ticket = ticket_service.TicketService.add_tag_to_ticket(db, ticket_id, tag_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}

@router.delete("/{ticket_id}/tags/{tag_id}")
def remove_tag_from_ticket(ticket_id: int, tag_id: int, db: Session = Depends(get_db)):
    ticket = ticket_service.TicketService.remove_tag_from_ticket(db, ticket_id, tag_id)
    return {"success": True, "data": TicketResponse.model_validate(ticket)}
```

#### 文件：./w1/project-alpha/backend/app/routers/tag.py
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.tag import TagCreate, TagUpdate, TagResponse
from app.services import tag_service

router = APIRouter(prefix="/tags", tags=["tags"])

@router.get("")
def get_tags(db: Session = Depends(get_db)):
    tags = tag_service.TagService.get_tags(db)
    return {"success": True, "data": [TagResponse.model_validate(t) for t in tags]}

@router.get("/{tag_id}")
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = tag_service.TagService.get_tag_by_id(db, tag_id)
    return {"success": True, "data": TagResponse.model_validate(tag)}

@router.post("")
def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    new_tag = tag_service.TagService.create_tag(db, tag)
    return {"success": True, "data": TagResponse.model_validate(new_tag)}

@router.put("/{tag_id}")
def update_tag(tag_id: int, tag: TagUpdate, db: Session = Depends(get_db)):
    updated_tag = tag_service.TagService.update_tag(db, tag_id, tag)
    return {"success": True, "data": TagResponse.model_validate(updated_tag)}

@router.delete("/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag_service.TagService.delete_tag(db, tag_id)
    return {"success": True, "message": "标签删除成功"}
```

### 2.7 主应用入口

#### 文件：./w1/project-alpha/backend/app/main.py
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import ticket, tag

app = FastAPI(
    title="Project Alpha API",
    description="Ticket 管理系统 API",
    version="1.0.0"
)

# CORS 配置
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(ticket.router, prefix="/api/v1")
app.include_router(tag.router, prefix="/api/v1")

# 初始化数据库
@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
```

### 2.8 创建数据库并运行后端

```bash
# 初始化数据库（确保 PostgreSQL 运行中）
# 方法一：直接运行 SQL 脚本
psql -U postgres -f init.sql

# 方法二：运行 Alembic 迁移
alembic upgrade head

# 启动后端
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 阶段三：前端核心功能实现

### 3.1 类型定义

#### 文件：./w1/project-alpha/frontend/src/types/index.ts
```typescript
export type TicketStatus = 'pending' | 'completed';

export interface Ticket {
  id: number;
  title: string;
  description: string | null;
  status: TicketStatus;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
  created_at: string;
}

export interface CreateTicketRequest {
  title: string;
  description?: string;
  tag_ids?: number[];
}

export interface UpdateTicketRequest {
  title?: string;
  description?: string;
  status?: TicketStatus;
  tag_ids?: number[];
}

export interface CreateTagRequest {
  name: string;
  color?: string;
}

export interface UpdateTagRequest {
  name?: string;
  color?: string;
}

export interface AddTagToTicketRequest {
  tag_id: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: {
    code: string;
    message: string;
  };
}

export interface TicketQueryParams {
  tag_id?: number;
  status?: TicketStatus;
  search?: string;
  page?: number;
  page_size?: number;
}

export const TAG_COLORS = [
  '#EF4444', '#F97316', '#F59E0B', '#84CC16', '#22C55E',
  '#10B981', '#14B8A6', '#06B6D4', '#0EA5E9', '#3B82F6',
  '#6366F1', '#8B5CF6', '#A855F7', '#D946EF', '#EC4899', '#6B7280',
] as const;
```

### 3.2 API 封装

#### 文件：./w1/project-alpha/frontend/src/lib/api.ts
```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.error?.message || error.message || '请求失败';
    return Promise.reject(new Error(message));
  }
);

export default api;
```

### 3.3 工具函数

#### 文件：./w1/project-alpha/frontend/src/lib/utils.ts
```typescript
import { type ClassValue, clsx } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}
```

### 3.4 React Query Hooks

#### 文件：./w1/project-alpha/frontend/src/hooks/useTickets.ts
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { Ticket, CreateTicketRequest, UpdateTicketRequest, TicketQueryParams, PaginatedResponse } from '../types';

export function useTickets(params: TicketQueryParams = {}) {
  return useQuery({
    queryKey: ['tickets', params],
    queryFn: async () => {
      const response = await api.get<{ success: boolean; data: PaginatedResponse<Ticket> }>('/tickets', { params });
      return response.data;
    },
  });
}

export function useTicket(id: number) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: async () => {
      const response = await api.get<{ success: boolean; data: Ticket }>(`/tickets/${id}`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateTicketRequest) => {
      const response = await api.post<{ success: boolean; data: Ticket }>('/tickets', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useUpdateTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UpdateTicketRequest }) => {
      const response = await api.put<{ success: boolean; data: Ticket }>(`/tickets/${id}`, data);
      return response.data;
    },
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
      queryClient.invalidateQueries({ queryKey: ['ticket', id] });
    },
  });
}

export function useDeleteTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/tickets/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useCompleteTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.patch<{ success: boolean; data: Ticket }>(`/tickets/${id}/complete`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}

export function useUncompleteTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await api.patch<{ success: boolean; data: Ticket }>(`/tickets/${id}/uncomplete`);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] });
    },
  });
}
```

#### 文件：./w1/project-alpha/frontend/src/hooks/useTags.ts
```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../lib/api';
import { Tag, CreateTagRequest, UpdateTagRequest } from '../types';

export function useTags() {
  return useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      const response = await api.get<{ success: boolean; data: Tag[] }>('/tags');
      return response.data;
    },
  });
}

export function useCreateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateTagRequest) => {
      const response = await api.post<{ success: boolean; data: Tag }>('/tags', data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
    },
  });
}

export function useUpdateTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UpdateTagRequest }) => {
      const response = await api.put<{ success: boolean; data: Tag }>(`/tags/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
    },
  });
}

export function useDeleteTag() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/tags/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags'] });
    },
  });
}
```

### 3.5 UI 组件

#### 文件：./w1/project-alpha/frontend/src/components/ui/button.tsx
```typescript
import * as React from "react"

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost' | 'destructive';
  size?: 'default' | 'sm' | 'lg';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 disabled:pointer-events-none disabled:opacity-50"

    const variants = {
      default: "bg-slate-900 text-white hover:bg-slate-900/90",
      outline: "border border-slate-200 bg-white hover:bg-slate-100",
      ghost: "hover:bg-slate-100",
      destructive: "bg-red-500 text-white hover:bg-red-500/90",
    }

    const sizes = {
      default: "h-10 px-4 py-2",
      sm: "h-9 rounded-md px-3",
      lg: "h-11 rounded-md px-8",
    }

    return (
      <button
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className || ''}`}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button }
```

（其他 UI 组件如 Dialog, Input, Badge 等按需创建，建议直接使用 Shadcn UI 组件）

### 3.6 业务组件

#### 文件：./w1/project-alpha/frontend/src/components/TicketCard.tsx
```typescript
import { Ticket } from '../types';
import { Button } from './ui/button';
import { formatDate } from '../lib/utils';

interface TicketCardProps {
  ticket: Ticket;
  onComplete: (id: number) => void;
  onUncomplete: (id: number) => void;
  onEdit: (ticket: Ticket) => void;
  onDelete: (id: number) => void;
}

export function TicketCard({ ticket, onComplete, onUncomplete, onEdit, onDelete }: TicketCardProps) {
  const isCompleted = ticket.status === 'completed';

  return (
    <div className={`border rounded-lg p-4 ${isCompleted ? 'bg-slate-50' : 'bg-white'}`}>
      <div className="flex gap-1 mb-2 flex-wrap">
        {ticket.tags.map((tag) => (
          <span
            key={tag.id}
            className="px-2 py-0.5 rounded text-xs text-white"
            style={{ backgroundColor: tag.color }}
          >
            {tag.name}
          </span>
        ))}
      </div>

      <h3 className={`font-medium ${isCompleted ? 'line-through text-slate-500' : ''}`}>
        {ticket.title}
      </h3>

      {ticket.description && (
        <p className={`text-sm mt-1 ${isCompleted ? 'text-slate-400' : 'text-slate-600'}`}>
          {ticket.description}
        </p>
      )}

      <div className="flex items-center justify-between mt-4 pt-3 border-t">
        <span className="text-xs text-slate-500">创建于 {formatDate(ticket.created_at)}</span>

        <div className="flex gap-2">
          {isCompleted ? (
            <Button size="sm" variant="ghost" onClick={() => onUncomplete(ticket.id)}>
              取消
            </Button>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => onComplete(ticket.id)}>
              完成
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => onEdit(ticket)}>
            编辑
          </Button>
          <Button size="sm" variant="destructive" onClick={() => onDelete(ticket.id)}>
            删除
          </Button>
        </div>
      </div>
    </div>
  );
}
```

#### 文件：./w1/project-alpha/frontend/src/components/TicketForm.tsx
```typescript
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Ticket, Tag, CreateTicketRequest, UpdateTicketRequest } from '../types';
import { Button } from './ui/button';

const ticketSchema = z.object({
  title: z.string().min(1, '标题不能为空').max(255),
  description: z.string().max(5000).optional(),
  tag_ids: z.array(z.number()).optional(),
});

interface TicketFormProps {
  ticket?: Ticket | null;
  tags: Tag[];
  onSubmit: (data: CreateTicketRequest | UpdateTicketRequest) => void;
  onCancel: () => void;
}

export function TicketForm({ ticket, tags, onSubmit, onCancel }: TicketFormProps) {
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<CreateTicketRequest>({
    resolver: zodResolver(ticketSchema),
    defaultValues: {
      title: ticket?.title || '',
      description: ticket?.description || '',
      tag_ids: ticket?.tags.map(t => t.id) || [],
    },
  });

  const selectedTagIds = watch('tag_ids') || [];

  const toggleTag = (tagId: number) => {
    const current = selectedTagIds;
    if (current.includes(tagId)) {
      setValue('tag_ids', current.filter(id => id !== tagId));
    } else {
      setValue('tag_ids', [...current, tagId]);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium mb-1">标题 *</label>
        <input
          {...register('title')}
          className="w-full border rounded-md px-3 py-2"
          placeholder="输入标题"
        />
        {errors.title && <p className="text-red-500 text-sm mt-1">{errors.title.message}</p>}
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">描述</label>
        <textarea
          {...register('description')}
          className="w-full border rounded-md px-3 py-2 min-h-[100px]"
          placeholder="输入描述"
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-1">标签</label>
        <div className="flex gap-2 flex-wrap">
          {tags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() => toggleTag(tag.id)}
              className={`px-3 py-1 rounded-full text-sm text-white transition-opacity ${
                selectedTagIds.includes(tag.id) ? 'opacity-100' : 'opacity-60'
              }`}
              style={{ backgroundColor: tag.color }}
            >
              {tag.name} {selectedTagIds.includes(tag.id) && '×'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <Button type="button" variant="outline" onClick={onCancel}>
          取消
        </Button>
        <Button type="submit">
          {ticket ? '保存' : '创建'}
        </Button>
      </div>
    </form>
  );
}
```

#### 文件：./w1/project-alpha/frontend/src/components/SearchBar.tsx
```typescript
import { useState, useEffect } from 'react';
import { useDebounce } from '../hooks/useDebounce';

interface SearchBarProps {
  onSearch: (value: string) => void;
  placeholder?: string;
}

export function SearchBar({ onSearch, placeholder = '搜索...' }: SearchBarProps) {
  const [value, setValue] = useState('');
  const debouncedValue = useDebounce(value, 300);

  useEffect(() => {
    onSearch(debouncedValue);
  }, [debouncedValue, onSearch]);

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => setValue(e.target.value)}
      placeholder={placeholder}
      className="border rounded-md px-3 py-2 w-full max-w-xs"
    />
  );
}
```

#### 文件：./w1/project-alpha/frontend/src/hooks/useDebounce.ts
```typescript
import { useState, useEffect } from 'react';

export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
```

#### 文件：./w1/project-alpha/frontend/src/components/TagFilter.tsx
```typescript
import { Tag } from '../types';

interface TagFilterProps {
  tags: Tag[];
  selectedTagId: number | null;
  onSelectTag: (tagId: number | null) => void;
}

export function TagFilter({ tags, selectedTagId, onSelectTag }: TagFilterProps) {
  return (
    <div className="space-y-1">
      <button
        onClick={() => onSelectTag(null)}
        className={`w-full text-left px-3 py-2 rounded-md transition-colors ${
          selectedTagId === null ? 'bg-slate-900 text-white' : 'hover:bg-slate-100'
        }`}
      >
        全部
      </button>
      {tags.map((tag) => (
        <button
          key={tag.id}
          onClick={() => onSelectTag(tag.id)}
          className={`w-full text-left px-3 py-2 rounded-md transition-colors flex items-center gap-2 ${
            selectedTagId === tag.id ? 'bg-slate-900 text-white' : 'hover:bg-slate-100'
          }`}
        >
          <span
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: tag.color }}
          />
          {tag.name}
        </button>
      ))}
    </div>
  );
}
```

### 3.7 主页面组件

#### 文件：./w1/project-alpha/frontend/src/App.tsx
```typescript
import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { TicketList } from './components/TicketList';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TicketList />
    </QueryClientProvider>
  );
}

export default App;
```

#### 文件：./w1/project-alpha/frontend/src/components/TicketList.tsx
```typescript
import { useState } from 'react';
import { useTickets, useCreateTicket, useUpdateTicket, useDeleteTicket, useCompleteTicket, useUncompleteTicket } from '../hooks/useTickets';
import { useTags, useCreateTag, useDeleteTag } from '../hooks/useTags';
import { TicketCard } from './TicketCard';
import { TicketForm } from './TicketForm';
import { TagFilter } from './TagFilter';
import { SearchBar } from './SearchBar';
import { Button } from './ui/button';
import { Ticket, CreateTicketRequest, UpdateTicketRequest } from '../types';

export function TicketList() {
  const [search, setSearch] = useState('');
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTicket, setEditingTicket] = useState<Ticket | null>(null);

  const { data: ticketsData, isLoading } = useTickets({
    search: search || undefined,
    tag_id: selectedTagId || undefined,
  });

  const { data: tagsData } = useTags();
  const createTicket = useCreateTicket();
  const updateTicket = useUpdateTicket();
  const deleteTicket = useDeleteTicket();
  const completeTicket = useCompleteTicket();
  const uncompleteTicket = useUncompleteTicket();
  const createTag = useCreateTag();
  const deleteTag = useDeleteTag();

  const handleCreateTicket = async (data: CreateTicketRequest) => {
    await createTicket.mutateAsync(data);
    setShowCreateForm(false);
  };

  const handleUpdateTicket = async (data: CreateTicketRequest | UpdateTicketRequest) => {
    if (editingTicket) {
      await updateTicket.mutateAsync({ id: editingTicket.id, data });
      setEditingTicket(null);
    }
  };

  const handleDeleteTicket = async (id: number) => {
    if (confirm('确定要删除这个 Ticket 吗？')) {
      await deleteTicket.mutateAsync(id);
    }
  };

  const tags = tagsData?.data || [];
  const tickets = ticketsData?.data?.items || [];
  const total = ticketsData?.data?.total || 0;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4">
        <div className="flex items-center justify-between max-w-7xl mx-auto">
          <h1 className="text-xl font-bold">Project Alpha</h1>
          <div className="flex items-center gap-4">
            <SearchBar onSearch={setSearch} placeholder="搜索 Ticket..." />
            <Button onClick={() => setShowCreateForm(true)}>新建 Ticket</Button>
          </div>
        </div>
      </header>

      <div className="flex max-w-7xl mx-auto">
        {/* Sidebar */}
        <aside className="w-64 p-4 border-r bg-white min-h-[calc(100vh-65px)]">
          <h2 className="font-medium mb-3 px-3">标签</h2>
          <TagFilter
            tags={tags}
            selectedTagId={selectedTagId}
            onSelectTag={setSelectedTagId}
          />
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {/* Status Bar */}
          <div className="flex items-center justify-between mb-4">
            <span className="text-slate-600">共 {total} 个 Ticket</span>
            {(search || selectedTagId) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSearch('');
                  setSelectedTagId(null);
                }}
              >
                清除筛选
              </Button>
            )}
          </div>

          {/* Ticket List */}
          {isLoading ? (
            <div className="text-center py-10">加载中...</div>
          ) : tickets.length === 0 ? (
            <div className="text-center py-10 text-slate-500">
              暂无 Ticket，点击"新建 Ticket"创建第一个
            </div>
          ) : (
            <div className="grid gap-4">
              {tickets.map((ticket) => (
                <TicketCard
                  key={ticket.id}
                  ticket={ticket}
                  onComplete={(id) => completeTicket.mutate(id)}
                  onUncomplete={(id) => uncompleteTicket.mutate(id)}
                  onEdit={setEditingTicket}
                  onDelete={handleDeleteTicket}
                />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Create Dialog */}
      {showCreateForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-lg font-medium mb-4">新建 Ticket</h2>
            <TicketForm
              tags={tags}
              onSubmit={handleCreateTicket}
              onCancel={() => setShowCreateForm(false)}
            />
          </div>
        </div>
      )}

      {/* Edit Dialog */}
      {editingTicket && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-lg font-medium mb-4">编辑 Ticket</h2>
            <TicketForm
              ticket={editingTicket}
              tags={tags}
              onSubmit={handleUpdateTicket}
              onCancel={() => setEditingTicket(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
```

### 3.8 入口文件

#### 文件：./w1/project-alpha/frontend/src/main.tsx
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

---

## 阶段四：测试与验证

### 4.1 后端单元测试

#### 文件：./w1/project-alpha/backend/tests/test_tickets.py
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.ticket import Ticket

client = TestClient(app)

@pytest.fixture(scope="module")
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_create_ticket(setup_database):
    response = client.post("/api/v1/tickets", json={
        "title": "Test Ticket",
        "description": "Test Description"
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["title"] == "Test Ticket"

def test_get_tickets(setup_database):
    response = client.get("/api/v1/tickets")
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "items" in response.json()["data"]

def test_complete_ticket(setup_database):
    # 先创建 ticket
    create_response = client.post("/api/v1/tickets", json={"title": "Complete Test"})
    ticket_id = create_response.json()["data"]["id"]

    # 完成 ticket
    response = client.patch(f"/api/v1/tickets/{ticket_id}/complete")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "completed"
```

### 4.2 手动测试清单

| 序号 | 测试项 | 预期结果 | 实际结果 |
|------|--------|----------|----------|
| 1 | 访问 http://localhost:5173 | 页面正常加载，显示空状态或示例数据 |  |
| 2 | 点击"新建 Ticket"按钮 | 弹出创建表单对话框 |  |
| 3 | 填写标题后点击创建 | Ticket 创建成功，列表刷新 |  |
| 4 | 不填写标题点击创建 | 显示错误提示"标题不能为空" |  |
| 5 | 点击 Ticket 的"编辑"按钮 | 弹出编辑表单，预填数据 |  |
| 6 | 修改标题后点击保存 | Ticket 更新成功 |  |
| 7 | 点击 Ticket 的"删除"按钮 | 弹出确认对话框 |  |
| 8 | 确认删除后 | Ticket 删除成功，列表刷新 |  |
| 9 | 点击"完成"按钮 | Ticket 状态变为已完成，样式变化 |  |
| 10 | 点击"取消"按钮 | Ticket 状态恢复为未完成 |  |
| 11 | 在侧边栏点击标签 | 列表只显示该标签的 Ticket |  |
| 12 | 在搜索框输入关键字 | 列表显示匹配的 Ticket |  |
| 13 | 创建重复名称的标签 | 显示错误提示"名称已存在" |  |

---

## 阶段五：优化与部署

### 5.1 性能优化

1. **添加数据库索引**：已包含在 SQL 脚本中
2. **API 响应缓存**：使用 React Query 自动缓存
3. **分页优化**：限制每页最大数量

### 5.2 用户体验优化

1. 添加加载状态骨架屏
2. 添加 Toast 通知
3. 添加键盘快捷键支持
4. 优化移动端响应式布局

### 5.3 部署检查清单

- [ ] 数据库连接正常
- [ ] 后端 API 可访问
- [ ] 前端构建成功
- [ ] 环境变量配置正确
- [ ] CORS 配置正确

---

## 文件清单汇总

### 后端文件

| 文件路径 | 描述 |
|----------|------|
| ./w1/project-alpha/backend/requirements.txt | Python 依赖 |
| ./w1/project-alpha/backend/.env | 环境变量 |
| ./w1/project-alpha/backend/app/__init__.py | 应用初始化 |
| ./w1/project-alpha/backend/app/config.py | 配置管理 |
| ./w1/project-alpha/backend/app/database.py | 数据库连接 |
| ./w1/project-alpha/backend/app/main.py | Fast API 入口 |
| ./w1/project-alpha/backend/app/models/__init__.py | 模型初始化 |
| ./w1/project-alpha/backend/app/models/ticket.py | Ticket 模型 |
| ./w1/project-alpha/backend/app/models/tag.py | Tag 模型 |
| ./w1/project-alpha/backend/app/schemas/__init__.py | Schema 初始化 |
| ./w1/project-alpha/backend/app/schemas/ticket.py | Ticket Schema |
| ./w1/project-alpha/backend/app/schemas/tag.py | Tag Schema |
| ./w1/project-alpha/backend/app/routers/__init__.py | 路由初始化 |
| ./w1/project-alpha/backend/app/routers/ticket.py | Ticket 路由 |
| ./w1/project-alpha/backend/app/routers/tag.py | Tag 路由 |
| ./w1/project-alpha/backend/app/services/__init__.py | 服务初始化 |
| ./w1/project-alpha/backend/app/services/ticket_service.py | Ticket 服务 |
| ./w1/project-alpha/backend/app/services/tag_service.py | Tag 服务 |
| ./w1/project-alpha/backend/app/utils/__init__.py | 工具初始化 |
| ./w1/project-alpha/backend/app/utils/exceptions.py | 自定义异常 |

### 前端文件

| 文件路径 | 描述 |
|----------|------|
| ./w1/project-alpha/frontend/package.json | NPM 依赖 |
| ./w1/project-alpha/frontend/.env | 环境变量 |
| ./w1/project-alpha/frontend/vite.config.ts | Vite 配置 |
| ./w1/project-alpha/frontend/tailwind.config.js | Tailwind 配置 |
| ./w1/project-alpha/frontend/src/main.tsx | 入口文件 |
| ./w1/project-alpha/frontend/src/App.tsx | 主组件 |
| ./w1/project-alpha/frontend/src/index.css | 全局样式 |
| ./w1/project-alpha/frontend/src/types/index.ts | 类型定义 |
| ./w1/project-alpha/frontend/src/lib/api.ts | API 封装 |
| ./w1/project-alpha/frontend/src/lib/utils.ts | 工具函数 |
| ./w1/project-alpha/frontend/src/hooks/useTickets.ts | Ticket Hooks |
| ./w1/project-alpha/frontend/src/hooks/useTags.ts | Tag Hooks |
| ./w1/project-alpha/frontend/src/hooks/useDebounce.ts | 防抖 Hook |
| ./w1/project-alpha/frontend/src/components/ui/button.tsx | 按钮组件 |
| ./w1/project-alpha/frontend/src/components/TicketList.tsx | Ticket 列表页面 |
| ./w1/project-alpha/frontend/src/components/TicketCard.tsx | Ticket 卡片 |
| ./w1/project-alpha/frontend/src/components/TicketForm.tsx | Ticket 表单 |
| ./w1/project-alpha/frontend/src/components/TagFilter.tsx | 标签筛选 |
| ./w1/project-alpha/frontend/src/components/SearchBar.tsx | 搜索栏 |

---

## 里程碑与时间线

| 里程碑 | 完成标准 | 预计时间 |
|--------|----------|----------|
| M1: 项目初始化 | 目录结构创建完成，依赖安装完成 | 第 1 天 |
| M2: 后端基础 | 数据库连接正常，CRUD API 可用 | 第 2 天 |
| M3: 前端基础 | 页面框架搭建完成，UI 组件就绪 | 第 3 天 |
| M4: Ticket 功能 | Ticket 增删改查功能完整 | 第 4 天 |
| M5: 标签功能 | 标签管理功能完整 | 第 5 天 |
| M6: 筛选搜索 | 筛选和搜索功能正常 | 第 6 天 |
| M7: 测试优化 | 所有验收标准通过 | 第 7 天 |
