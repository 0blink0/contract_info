# CTRX v1.4 Smoke Test — Phase 23: KB 全链路打包验证

## 执行元数据

| 字段 | 值 |
|------|-----|
| 执行人 | |
| 执行日期 | |
| 机器名 / OS | |
| 安装包版本 | CTRX-Setup-1.4.0.exe |
| 安装路径 | |
| CTRX_DATA_DIR (userData) | （Windows: %APPDATA%\CTRX 或启动日志第一行）|
| 后端日志路径 | %APPDATA%\CTRX\logs\backend.log |
| bge-m3 模型目录是否存在 | 安装完成后检查: <安装路径>\resources\electron\resources\models\bge-m3\ |
| CTRX_MODELS_DIR（注入值） | 通过 Electron DevTools console 确认（可选）|

## 前提条件

全部勾选后方可继续：

- [ ] 执行机器**无 Python 运行时**（确保测试的是打包产物而非开发环境）
- [ ] 已安装 CTRX-Setup-1.4.0.exe 至测试机器
- [ ] <安装路径>\resources\electron\resources\models\bge-m3\ 目录存在且包含 config.json
- [ ] 备有一份含**业绩报酬条款**的 .docx 合同文件（用于步骤 C 和步骤 D）
- [ ] %APPDATA%\CTRX\logs\ 目录可写（首次启动后自动创建）

## 烟测链路

按顺序执行以下步骤。每步完成后勾选对应检查项。

### 步骤 A：应用启动 + 后端健康（D-14 标准 1）

1. 双击 CTRX 桌面快捷方式启动应用
2. 等待加载完成（最多 60 秒）
3. 打开后端日志文件：`%APPDATA%\CTRX\logs\backend.log`
4. 检查日志内容：

**Pass 标准 1（D-14.1）：**
- [ ] 日志中**不含** `ModuleNotFoundError` 字样
- [ ] 日志中可见 embedding 模型加载相关行（如 `Embedding model loaded`、
      `SentenceTransformer` 或 `bge-m3` 字样）
- [ ] 应用主界面正常显示（无「后端启动失败」对话框）

### 步骤 B：PathB 录入 → embedding 生成 → LanceDB 持久化（D-14 标准 2 + 3）

1. 在应用中上传步骤 A 准备的含业绩报酬条款 .docx 文件
2. 点击「开始处理」，等待处理完成
3. 进入该任务详情 → 字段 B 页
4. 在页面底部知识库录入表格中，确认 4 行均已预填字段值
5. 勾选至少 1 行复选框
6. 点击「存入知识库」按钮

**Pass 标准 2（D-14.2）：**
- [ ] 界面出现 `ElMessage.success` 提示，文字格式为「已存入 N 条」（N 为勾选行数）

7. 进入左侧菜单「知识库配置」页面
8. 刷新页面（F5 或重新点击菜单项）

**Pass 标准 3（D-14.3）：**
- [ ] 知识库列表中可见刚才录入的条目（字段名 / 字段值 / 原文摘录 / 来源合同均显示正确）

### 步骤 C：RAG 检索 + prompt 注入验证（D-14 标准 4）

> 前提：步骤 B 中已存入至少 1 条案例，否则 RAG 无数据可检索。

1. 在应用中重新上传同一份含业绩报酬条款的 .docx 文件（或上传另一份）
2. 点击「开始处理」，等待处理完成
3. 重新打开后端日志文件：`%APPDATA%\CTRX\logs\backend.log`
4. 在日志中搜索关键字（Ctrl+F 或 grep）：

**Pass 标准 4（D-14.4）：**
- [ ] 日志中包含 `RAG context` **或** `few-shot` 关键字
      （证明 kb_service 检索到结果并注入了 prompt 构造块）

### 步骤 D：数据隔离验证

- [ ] 所有写入（LanceDB 数据、日志、上传文件）均在 `%APPDATA%\CTRX\` 下
- [ ] 安装目录（Program Files）中无运行时生成文件

## 通过判定

**四项标准全部满足 = PASS，可发布 v1.4。任一项不满足 = FAIL，阻断发布（D-16）。**

| 标准 | 描述 | 结果 |
|------|------|------|
| D-14.1 | 后端启动日志无 ModuleNotFoundError，embedding 加载行可见 | PASS / FAIL |
| D-14.2 | PathB 录入后「已存入 N 条」提示出现 | PASS / FAIL |
| D-14.3 | 知识库配置页刷新后条目可见 | PASS / FAIL |
| D-14.4 | 重处理合同后日志含 RAG context 或 few-shot | PASS / FAIL |
| **总体** | | **PASS / FAIL** |

## 失败处理

如任一标准失败：

1. 截图 / 复制相关日志片段
2. 记录失败步骤编号和实际观察
3. 在本文件 `## 证据收集` 节填写
4. 阻断发布，通知开发者修复后重新执行本清单

## 证据收集

| 项目 | 内容 |
|------|------|
| 后端启动日志片段（步骤 A） | （粘贴前 50 行或模型加载行附近）|
| 「已存入 N 条」截图 / 文字（步骤 B） | |
| 知识库列表截图（步骤 B.8）| |
| RAG 日志行（步骤 C）| （粘贴包含 RAG context 或 few-shot 的日志行）|
| 最终判定 | PASS / FAIL |
| 执行人签名 | |

---
*Phase 23 Smoke Test — generated 2026-06-02*
*Pass criteria source: 23-CONTEXT.md D-14*
