---
phase: 20
slug: pathb-kb-entry-ui
status: draft
shadcn_initialized: false
preset: none
created: "2026-06-02"
---

# Phase 20 — UI 设计合同：PathB 知识库录入区

> 本阶段视觉与交互契约。由 gsd-ui-researcher 生成，gsd-ui-checker 验证。
> 范围：在 PathBDetail.vue 底部追加 KB 录入区块（KB-ENTRY-01~05）。
> 后端 UI（503 响应驱动的 el-alert 状态）包含在内。

---

## 设计系统

| 属性 | 值 |
|------|----|
| 工具 | none（无 shadcn；项目直接使用 Element Plus） |
| 预设字符串 | 不适用 |
| 组件库 | Element Plus ^2.9.0 |
| 图标库 | Element Plus 内置图标（@element-plus/icons-vue），本阶段不新增图标 |
| 字体栈 | 'Helvetica Neue', Helvetica, 'PingFang SC', 'Microsoft YaHei', sans-serif |

来源：`frontend/src/assets/styles/app.css`（已有 CSS 变量，直接复用）

---

## 间距比例

所有间距均为 4 的倍数：

| 标记 | 值 | 用途 |
|------|----|------|
| xs | 4px | 标签徽章内边距、行内图标间隔 |
| sm | 8px | 操作按钮之间间距（`.actions gap`）、小标题下边距 |
| md | 12px | `.section-table margin-bottom`、`.top-alert margin-bottom`（沿用现有值） |
| lg | 16px | KB 录入区与上方最后一个 `section-table` 之间的分隔 |
| xl | 24px | 暂无（本阶段不涉及大段落级分隔） |

**KB 录入区具体间距（必须严格遵守）：**

| 位置 | 值 | 说明 |
|------|----|------|
| `.kb-entry-section` 顶部 margin-top | 16px | 与上方 `section-table` 或 `raw-sections` 形成视觉分割 |
| `.kb-entry-section` 内 `.sub-title` margin-bottom | 8px | 与下方 `el-alert` 或 `el-table` 之间距离 |
| `.kb-alert` margin-bottom | 8px | `el-alert` 与 `el-table` 之间距离 |
| `el-table` margin-bottom | 12px | 与「存入知识库」按钮之间距离（沿用 `.section-table` 既有值） |
| 「存入知识库」`el-button` margin-top | 0（依赖 el-table margin-bottom） | 无额外 margin |
| `el-table-column type="selection"` width | 46px | 复选框列宽（含左右各 8px 内边距） |
| `el-table-column prop="field_name"` width | 150px | 字段名列固定宽度 |
| `el-table-column` 字段值 min-width | 160px | 最小宽度，允许拉伸 |
| `el-table-column` 原文摘录 min-width | 240px | 最小宽度，允许拉伸 |

**例外：**
- `el-input` 嵌入单元格时，`el-table` 内部行高由 `size="small"` 决定（约 32px 行高），不手动覆盖。
- `textarea` 模式的 `el-input`（原文摘录列）使用 `:autosize="{ minRows: 1, maxRows: 3 }"`，行高动态扩展，最多约 72px。

---

## 排版

| 角色 | 尺寸 | 字重 | 行高 | 颜色 |
|------|------|------|------|------|
| body（表格单元格文本、说明段） | 13px | 400（regular） | 1.5 | #1e293b（body 默认） |
| label（小标题 `.sub-title`） | 13px | 600（semibold） | 1.2 | #1e293b |
| caption（`.summary-line`、辅助提示） | 13px | 400 | 1.5 | #606266 |
| placeholder（el-input 占位文字） | 12px | 400 | 1.5 | #a8abb2（Element Plus 默认） |

来源：PathBDetail.vue `<style scoped>` 已有 `.field-line font-size: 13px`、`.summary-line font-size: 13px color: #606266`、`.sub-title font-size: 13px font-weight: 600`，KB 录入区沿用相同值，不引入新尺寸。

**声明：本阶段仅使用 2 个字号（13px / 12px）、2 个字重（400 / 600）。**

---

## 颜色

| 角色 | 值 | 用途 |
|------|----|------|
| 主要表面（60%） | #ffffff（`--app-surface`） | 页面主体背景、表格单元格背景 |
| 次要表面（30%） | #f4f6fb（`--app-bg`）+ #f5f7fa（代码/JSON 块背景） | KB 录入区所在内容区背景（沿用父容器） |
| 强调色（10%） | #409eff（Element Plus `primary`，即 el-button type="primary"） | 仅「存入知识库」按钮 |
| 警告色（KB 不可用状态） | #e6a23c（Element Plus `warning` / `type="warning"` el-alert 边框与图标色）+ 浅橙背景 #fdf6ec | 仅 D-07 场景：KB 模型未加载时的 `el-alert` |
| 破坏性操作色 | 不适用（本阶段无删除操作） | — |
| 禁用状态 | #a8abb2（Element Plus disabled 文字色）+ #f5f7fa（disabled 输入框背景） | KB 不可用时 el-input `disabled`、el-button `disabled` |
| 表格 stripe 奇数行背景 | #fafafa（Element Plus stripe 默认） | el-table stripe 属性自动应用 |
| 表格边框 | #ebeef5（Element Plus border-color-light） | el-table border 属性自动应用 |

来源：
- `--app-surface`、`--app-bg`：`frontend/src/assets/styles/app.css`
- `type="warning"` el-alert 橙色：Element Plus 组件默认，决策 D-07 明确使用
- `#606266`：PathBDetail.vue `.summary-line color`

**强调色（#409eff）专用列表：**
1. 「存入知识库」`el-button type="primary"`（正常状态）
2. 「存入知识库」`el-button :loading="true"` 时按钮背景（Element Plus 自动处理）

强调色不用于：表格行、标题、说明文字、分隔线。

---

## 组件规格

### 1. KB 录入区容器 `.kb-entry-section`

```
div.kb-entry-section
  v-if="available"   ← D-08：PathB 不可用时完全隐藏整个区块
  margin-top: 16px
  width: 100%
```

### 2. 区块标题 `.sub-title`

沿用 PathBDetail.vue 现有 `.sub-title` 样式（font-size: 13px; font-weight: 600; margin-bottom: 6px → 本区块改为 8px）。

文案：**「存入知识库」**（不加冒号）

### 3. el-alert（KB 不可用警告）

```
el-alert
  v-if="kbUnavailable"   ← 503 响应后设为 true
  type="warning"
  :closable="false"
  title="知识库功能不可用（模型未加载）"
  class="kb-alert"        ← margin-bottom: 8px
```

- 不设 `description` 属性（标题已足够）
- 不设 `show-icon`（节省横向空间，与 top-alert 的 info 区分）
- 决策 D-07：即使此 alert 显示，表格依然渲染（不隐藏），仅禁用输入

### 4. el-table（KB 录入表格）

```
el-table
  :data="kbRows"
  size="small"
  stripe
  border
  class="section-table"   ← 沿用现有类名，margin-bottom: 12px
  @selection-change="(sel) => kbRows.value.forEach(r => r.selected = sel.includes(r))"
```

**列定义（严格顺序）：**

| 序号 | 列类型 | label | width / min-width | 可编辑 | disabled 条件 |
|------|--------|-------|-------------------|--------|---------------|
| 1 | `type="selection"` | — | width="46" | — | — |
| 2 | `prop="field_name"` | 字段名 | width="150" | 否（纯展示 span） | — |
| 3 | 自定义 slot | 字段值 | min-width="160" | 是（el-input） | kbUnavailable |
| 4 | 自定义 slot | 原文摘录 | min-width="240" | 是（el-input textarea） | kbUnavailable |

**字段名列（列 2）**：用 `prop="field_name"` 直接绑定，不包裹 el-input，不可编辑，不受 kbUnavailable 影响。

**字段值列（列 3）**：
```
el-input
  v-model="row.field_value"
  size="small"
  :disabled="kbUnavailable"
  placeholder="（可修改）"
```

**原文摘录列（列 4）**：
```
el-input
  v-model="row.snippet"
  size="small"
  type="textarea"
  :autosize="{ minRows: 1, maxRows: 3 }"
  :disabled="kbUnavailable"
  placeholder="（可选）"
```
决策 D-10：不设 required，不设客户端非空校验，允许空字符串提交。

**表格数据行（固定 4 行，顺序不变）：**

| 行序 | field_name | 预填来源（crm_field 精确值） |
|------|------------|-----------------------------|
| 1 | 业绩报酬提取方式 | crmRows.find(r => r.crm_field === '业绩报酬提取方式') |
| 2 | 业绩基准类型 | crmRows.find(r => r.crm_field === '业绩基准类型') |
| 3 | 门槛净值类型 | crmRows.find(r => r.crm_field === '门槛净值类型') |
| 4 | 提取时点 | crmRows.find(r => r.crm_field === '提取时点') |

预填逻辑：`field_value` 取 `row?.suggested_value ?? ''`，`snippet` 取 `row?.snippet ?? ''`。

### 5. el-button（「存入知识库」）

```
el-button
  type="primary"
  size="small"
  :loading="submitting"
  :disabled="kbUnavailable || !kbRows.some(r => r.selected)"
  @click="submit"
```

- `type="primary"`：蓝色（`#409eff`），与上方 action 区的 `default` 按钮形成主次区分
- 无需 icon
- 位置：紧跟 `el-table` 之后，左对齐（不用 flex justify-end）
- loading 态：Element Plus 自动显示旋转圆圈 + 禁用交互，不需要额外 loading overlay

---

## 文案合同

| 元素 | 文案 | 来源 |
|------|------|------|
| 区块标题（`.sub-title`） | 存入知识库 | CONTEXT.md D-07 场景描述 |
| KB 不可用 el-alert title | 知识库功能不可用（模型未加载） | 决策 D-07 原文 |
| 「存入知识库」按钮 | 存入知识库 | REQUIREMENTS.md KB-ENTRY-05 |
| 表格「字段名」列 header | 字段名 | REQUIREMENTS.md KB-ENTRY-01 |
| 表格「字段值」列 header | 字段值 | REQUIREMENTS.md KB-ENTRY-01 |
| 表格「原文摘录」列 header | 原文摘录 | REQUIREMENTS.md KB-ENTRY-01 |
| 字段值 el-input placeholder | （可修改） | 提示用户可覆盖预填值 |
| 原文摘录 el-input placeholder | （可选） | 决策 D-10：允许为空 |
| 入库成功 ElMessage | 已存入 {N} 条 | RESEARCH.md Pattern 5 / CONTEXT.md KB-ENTRY-05 |
| 入库失败 ElMessage | 存入失败：{错误说明} | 格式：`ElMessage.error(e.message)` |
| KB 不可用时失败 ElMessage | 知识库不可用，请检查模型是否已加载 | 503 场景专用（同时设 kbUnavailable=true） |
| 无选中行时 | 按钮 disabled（不显示额外提示） | 决策：静默禁用，不 toast 提示 |
| PathB 不可用时 | KB 录入区整体不渲染（v-if="available"） | 决策 D-08 |

**不需要的文案（不实现）：**
- 空状态设计（决策 D-08 明确：PathB 不可用时整体隐藏，不展示空状态）
- 入库前二次确认弹窗（本阶段无删除操作，无需确认；存入是可逆的追加操作）

---

## 交互合同

### 交互 1：页面加载时预填表格

```
触发：PathBDetail.vue onMounted → load() 完成（data.value 非 null）
动作：useKbEntry.buildRows() 被调用（在 watch(data, buildRows) 中触发）
结果：
  - kbRows.value 被赋值为 4 条记录
  - 每条记录 selected = false（默认不勾选）
  - field_value / snippet 来自 crmRows 的 suggested_value / snippet（可能为空字符串）
  - 表格立即显示，无额外 loading 状态
```

### 交互 2：复选框勾选

```
触发：用户点击 el-table 行的复选框（或表头全选框）
事件：@selection-change(sel: KbRow[])
动作：kbRows.value.forEach(r => r.selected = sel.includes(r))
结果：
  - 「存入知识库」按钮 disabled 状态根据 kbRows.some(r => r.selected) 实时更新
  - kbUnavailable 为 true 时，按钮始终 disabled（不受选中状态影响）
  - 全选/取消全选由 el-table 内置表头复选框处理
```

### 交互 3：编辑单元格

```
触发：用户点击字段值列或原文摘录列的 el-input
条件：kbUnavailable === false
动作：直接 v-model 双向绑定，实时更新 kbRows.value[i].field_value / .snippet
结果：
  - 无 "编辑/查看" 模式切换（始终显示 el-input，无只读 span）
  - 不触发 dirty 守卫（KB 录入区是独立的写操作，不影响现有 PathB 数据）
  - 用户修改后若未提交直接离开页面，修改丢失（不保存草稿，不提示）
```

### 交互 4：「存入知识库」提交流程

```
前置条件：
  - kbUnavailable === false
  - kbRows.some(r => r.selected) === true

触发：用户点击「存入知识库」按钮
步骤：
  1. submitting.value = true → 按钮进入 :loading 态（显示旋转图标，禁用点击）
  2. 调用 POST /api/v1/kb/entries，body = { entries: selectedRows.map(...) }
  3a. [成功] ElMessage.success(`已存入 ${res.count} 条`)
       submitting.value = false
       勾选状态不重置（用户可再次修改后重复提交，或手动取消勾选）
  3b. [失败 503] kbUnavailable.value = true
                  ElMessage.error('知识库不可用，请检查模型是否已加载')
                  submitting.value = false
                  → el-alert 自动显示；表格 el-input 自动 disabled
  3c. [失败其他] ElMessage.error(e.message || '存入失败')
                  submitting.value = false
                  kbUnavailable 保持 false
```

**loading 状态视觉：**
- 按钮旋转图标（Element Plus `:loading` 自动处理）
- 表格数据不 skeleton/遮罩，保持正常显示
- 不显示全页 loading overlay

### 交互 5：KB 不可用状态（D-07）

```
触发条件：kbUnavailable === true（首次提交收到 503 后设置）
前端状态变化：
  - el-alert[type="warning"] 显示，title="知识库功能不可用（模型未加载）"
  - el-table 所有 el-input :disabled="true"（视觉变灰，不可输入）
  - 「存入知识库」按钮 :disabled="true"（即使有行被勾选）
  - 复选框仍可点击（el-table type="selection" 不受 kbUnavailable 控制）
  - el-alert 不可关闭（:closable="false"）
注意：
  - kbUnavailable 在页面初始化时为 false（不主动探测 KB 状态）
  - 若用户刷新页面，kbUnavailable 重置为 false（内存状态，不持久化）
  - 本阶段不新增 GET /kb/status 端点（属于 Claude's Discretion 的开放问题，推迟到 Phase 21 决定）
```

### 交互 6：行勾选与提交按钮联动

| kbUnavailable | 是否有行被勾选 | 按钮状态 |
|---------------|---------------|---------|
| true | 任意 | disabled（灰色） |
| false | false | disabled（灰色） |
| false | true | enabled（蓝色 primary） |

---

## CSS 类名合同

执行者必须使用以下类名（与现有 PathBDetail.vue scoped 样式保持一致）：

| 类名 | 作用 |
|------|------|
| `.kb-entry-section` | KB 录入区最外层容器（新增） |
| `.section-table` | el-table 统一类名（沿用现有，margin-bottom: 12px） |
| `.sub-title` | 区块标题（沿用现有 `.sub-title` 样式） |
| `.kb-alert` | el-alert 的额外类，仅控制 margin-bottom: 8px（新增） |

新增 CSS（追加到 PathBDetail.vue `<style scoped>`）：

```css
.kb-entry-section {
  margin-top: 16px;
}

.kb-alert {
  margin-bottom: 8px;
}
```

不需要额外样式：`.sub-title`、`.section-table` 已有完整样式定义，直接复用。

---

## 注册表安全

| 注册表 | 使用的块 | 安全门控 |
|--------|---------|---------|
| Element Plus（官方，已在项目中） | el-table, el-table-column, el-input, el-button, el-alert, el-skeleton | 不需要（已安装的官方库） |
| shadcn 官方 | 不使用 | 不适用（项目不使用 shadcn） |
| 第三方注册表 | 无 | 不适用 |

---

## 不在本阶段范围（不实现）

| 项目 | 原因 |
|------|------|
| GET /kb/status 探测端点 | RESEARCH.md Open Question #3，Phase 20 推迟 |
| 知识库配置页（左侧菜单入口、列表页） | Phase 21 |
| RAG 检索注入 | Phase 22 |
| 入库成功后重置勾选状态 | 用户可能需要重复提交不同记录，不强制重置 |
| textarea 字符计数 | 不在需求范围内 |
| 移动端响应式适配 | 桌面 Electron 应用，最小宽度无限制 |

---

## 检查员签字

- [ ] 维度 1 文案：通过
- [ ] 维度 2 视觉：通过
- [ ] 维度 3 颜色：通过
- [ ] 维度 4 排版：通过
- [ ] 维度 5 间距：通过
- [ ] 维度 6 注册表安全：通过

**审批：** 待审批
