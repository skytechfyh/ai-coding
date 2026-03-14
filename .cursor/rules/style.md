# Motherduck 风格前端设计规则

本规则定义与 Motherduck 产品一致的前端设计语言：现代、干净、高信息密度、技术感与易用性兼顾。

---

## 1. 整体布局

- **三区/笔记本式布局**：左侧导航/对象树，中间主编辑/工作区，右侧结果/详情。可折叠侧栏，用快捷键切换（如 `Cmd+B` 左栏、`Cmd+I` 右栏）。
- **主窗口聚焦**：主操作区（编辑器/画布）占据视觉中心，侧栏不抢戏。
- **全屏模式**：关键视图（如结果、编辑器）提供「展开/全屏」入口，减少干扰。

---

## 2. 信息密度与层级

- **高密度但可扫读**：在有限空间内呈现更多有效信息，通过颜色、字重、间距区分层级，避免堆砌感。
- **预注意处理**：用颜色、宽度、形状（如迷你图、条形）让用户快速发现异常或重点，无需逐行读。
- **渐进披露**：默认展示摘要/概览，点击或悬停再展开详情（「按需详情」），避免首屏过载。

---

## 3. 实时反馈与交互

- **即时反馈**：关键操作（如输入、筛选）应尽量实时更新预览或结果，减少「点击运行」的等待感。
- **缓存与状态提示**：当结果来自缓存或后台仍在加载时，在单元格/面板头部用轻量指示器标明（如「来自缓存」「加载中」）。
- **交互式数据**：列表/表格支持排序、筛选、透视等，无需额外写查询或提交表单；可配合列级统计、迷你图、分布图增强可探索性。

---

## 4. 色彩与主题

- **主色与品牌**：采用克制的品牌色（如 Motherduck 的黄色/橙色点缀），主要用于 CTA、高亮、状态，不铺满整屏。
- **语义色**：成功/错误/警告/信息使用一致语义色，并兼顾对比度与可访问性。
- **深浅主题**：支持明暗主题切换；数据/代码区可默认深色以减轻长时间使用疲劳。

---

## 5. 排版与字体

- **层级清晰**：标题、副标题、正文、辅助说明有明确字重与字号阶梯，保持视觉层级稳定。
- **等宽与比例**：代码、SQL、数据、路径使用等宽字体；正文使用比例字体，保证可读性。
- **行高与间距**：高密度表格/列表适当收紧行高，但保证可点击区域与可读性；段落与区块留白充足。

---

## 6. 数据与结果展示

- **交互式网格**：结果以表格/网格展示，支持排序、筛选、列宽调整；关键列可配置迷你图、分布或时间序列预览。
- **列/字段探索**：提供「列浏览器」或类似视图，展示每列统计（频次、空值比例、直方图、时间分布等），支持点击列深入。
- **单元格详情**：点击单元格可在侧边或浮层展示完整内容；复杂类型（如 JSON）支持展开/折叠、复制值或路径。

---

## 7. 命令与效率

- **命令面板**：全局快捷键（如 `Cmd+K`）打开命令菜单，可搜索并执行常用操作、打开设置、切换视图。
- **键盘优先**：核心操作提供快捷键（运行、格式化、注释、切换面板、上下移动单元等），并在 UI 或文档中暴露。
- **自动完成与内联文档**：输入时提供自动完成（语法、表名、列名、函数）；悬停显示简要说明与文档链接，可关闭以适配偏好。

---

## 8. AI 与辅助功能

- **内联纠错**：出错时在编辑区内或附近提供修复建议，一键接受并重跑，可配置是否自动建议。
- **自然语言编辑**：支持选中内容后通过自然语言描述修改意图，在弹窗中预览并应用变更。
- **上下文帮助**：错误信息、空状态、复杂功能配有简短说明或「了解更多」链接，不阻塞主流程。

---

## 9. 组件与模式

- **可组合视图**：将可视化或面板设计为可组合单元（如「Dives」），便于复用与编排。
- **统一的状态与加载**：加载中、空数据、错误状态使用统一组件与文案风格，避免各页面各做一套。
- **设置与偏好集中**：通过头像/设置入口进入统一设置页，分组清晰（账户、偏好、集成、监控等），关键开关可搜索。

---

## 10. 禁止与避免

- 避免首屏一次性展示过多未分组的控件或表格列。
- 避免仅能通过多次点击或提交才能看到结果的核心流程；优先「边输入边预览」。
- 避免无层级的大色块或过度装饰；保持界面「工具感」而非营销页感。
- 避免忽略键盘用户与可访问性（焦点顺序、ARIA、对比度）。

---

在实现新页面或改版时，优先对齐上述布局、信息密度、实时反馈与数据展示原则，以保持 Motherduck 风格的一致性与体验质量。

---

## 11. 对应 CSS 样式（设计令牌与示例）

以下 CSS 变量与类与上述规则一一对应，可在全局样式或 Tailwind 主题中引用。

### 11.1 设计令牌（CSS 变量）

```css
:root {
  /* 布局 - 对应 §1 */
  --layout-sidebar-width: 260px;
  --layout-sidebar-collapsed: 48px;
  --layout-detail-width: 320px;
  --layout-main-min-width: 480px;
  --layout-gap: 1rem;
  --layout-radius: 6px;

  /* 色彩 - 对应 §4 */
  --color-brand: #f5a623;           /* 品牌黄/橙，CTA、高亮 */
  --color-brand-muted: #fef3d9;
  --color-success: #22c55e;
  --color-error: #ef4444;
  --color-warning: #f59e0b;
  --color-info: #3b82f6;
  --color-bg-base: #ffffff;
  --color-bg-muted: #f8fafc;
  --color-bg-code: #1e293b;        /* 代码/数据区深色 */
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-border: #e2e8f0;

  /* 排版 - 对应 §5 */
  --font-sans: ui-sans-serif, system-ui, sans-serif;
  --font-mono: ui-monospace, "Cascadia Code", "Fira Code", monospace;
  --text-title: 1.25rem;
  --text-subtitle: 1rem;
  --text-body: 0.875rem;
  --text-caption: 0.75rem;
  --font-weight-title: 600;
  --font-weight-body: 400;
  --font-weight-muted: 500;
  --leading-dense: 1.35;
  --leading-relaxed: 1.6;

  /* 信息密度 - 对应 §2 */
  --space-cell-y: 0.375rem;
  --space-cell-x: 0.75rem;
  --space-block: 1rem;
  --space-section: 1.5rem;
}

[data-theme="dark"] {
  --color-bg-base: #0f172a;
  --color-bg-muted: #1e293b;
  --color-bg-code: #0f172a;
  --color-text: #f1f5f9;
  --color-text-muted: #94a3b8;
  --color-border: #334155;
}
```

### 11.2 布局类示例

```css
/* 三区布局 - §1 */
.layout-notebook {
  display: grid;
  grid-template-columns: var(--layout-sidebar-width) 1fr var(--layout-detail-width);
  grid-template-rows: 1fr;
  gap: var(--layout-gap);
  min-height: 100vh;
}
.layout-notebook.sidebar-collapsed {
  grid-template-columns: var(--layout-sidebar-collapsed) 1fr var(--layout-detail-width);
}
.layout-notebook.detail-collapsed {
  grid-template-columns: var(--layout-sidebar-width) 1fr 0;
}
.layout-main {
  min-width: var(--layout-main-min-width);
  overflow: auto;
}

/* 全屏模式 */
.layout-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: var(--color-bg-base);
}
```

### 11.3 排版与密度

```css
/* 标题层级 - §5 */
.text-title {
  font-size: var(--text-title);
  font-weight: var(--font-weight-title);
  line-height: var(--leading-dense);
  color: var(--color-text);
}
.text-subtitle {
  font-size: var(--text-subtitle);
  font-weight: var(--font-weight-muted);
  color: var(--color-text);
}
.text-caption {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
}
.font-mono {
  font-family: var(--font-mono);
  font-size: var(--text-body);
}

/* 高密度表格 - §2、§6 */
.table-dense th,
.table-dense td {
  padding: var(--space-cell-y) var(--space-cell-x);
  font-size: var(--text-body);
  line-height: var(--leading-dense);
}
.table-dense th {
  font-weight: var(--font-weight-muted);
  color: var(--color-text-muted);
  background: var(--color-bg-muted);
}
```

### 11.4 状态与反馈

```css
/* 缓存/加载指示 - §3 */
.badge-cache {
  font-size: var(--text-caption);
  color: var(--color-text-muted);
  background: var(--color-bg-muted);
  padding: 0.125rem 0.5rem;
  border-radius: var(--layout-radius);
}
.badge-loading {
  color: var(--color-info);
}

/* 语义色 - §4 */
.text-success { color: var(--color-success); }
.text-error { color: var(--color-error); }
.text-warning { color: var(--color-warning); }
.bg-brand-subtle { background: var(--color-brand-muted); }
```

### 11.5 代码/数据区

```css
/* 代码与数据区深色 - §4、§5 */
.region-code,
.region-data {
  background: var(--color-bg-code);
  color: var(--color-text);
  font-family: var(--font-mono);
  border-radius: var(--layout-radius);
  padding: var(--space-block);
}
```

### 11.6 在 Tailwind 中引用（tailwind.config）

若使用 Tailwind，可在 `tailwind.config.js` 的 `theme.extend` 中映射上述变量：

```js
// theme.extend 示例
theme: {
  extend: {
    colors: {
      brand: 'var(--color-brand)',
      'brand-muted': 'var(--color-brand-muted)',
    },
    fontFamily: {
      sans: 'var(--font-sans)',
      mono: 'var(--font-mono)',
    },
    spacing: {
      'cell-y': 'var(--space-cell-y)',
      'cell-x': 'var(--space-cell-x)',
    },
  },
}
```

使用示例：`className="font-mono text-caption text-muted"`、`className="bg-brand-muted text-brand"`。
