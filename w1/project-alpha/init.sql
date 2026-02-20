-- Project Alpha 数据库初始化脚本
-- 数据库: project_alpha

-- 创建 tickets 表
DROP TABLE IF EXISTS ticket_tags;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS tags;

CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);

-- 创建 tags 表
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_tags_name ON tags(name);

-- 创建 ticket_tags 关联表
CREATE TABLE ticket_tags (
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (ticket_id, tag_id)
);

CREATE INDEX idx_ticket_tags_ticket_id ON ticket_tags(ticket_id);
CREATE INDEX idx_ticket_tags_tag_id ON ticket_tags(tag_id);

-- 插入初始标签
INSERT INTO tags (name, color) VALUES
    ('Bug', '#EF4444'),
    ('功能', '#3B82F6'),
    ('文档', '#10B981'),
    ('优化', '#F59E0B'),
    ('紧急', '#DC2626');

-- 插入示例 Ticket
INSERT INTO tickets (title, description, status) VALUES
    ('欢迎使用 Project Alpha', '这是您的第一个 Ticket，您可以使用它来管理任务和待办事项', 'pending'),
    ('创建一个新标签', '点击侧边栏可以创建新的标签来分类管理 Ticket', 'pending'),
    ('搜索 Ticket', '使用顶部的搜索框可以按标题搜索 Ticket', 'pending');

-- 关联标签
INSERT INTO ticket_tags (ticket_id, tag_id) VALUES
    (1, 2),
    (2, 3),
    (3, 3);
