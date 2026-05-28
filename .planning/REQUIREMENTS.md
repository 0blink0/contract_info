# Requirements: CTRX v1.2 桌面化交付

**Defined:** 2026-05-28
**Core Value:** 上传 docx → 可导入 Excel + 路径 B 手录辅助 + 可解释校验（本地桌面，无服务器依赖）

## v1.2 Requirements

### DB — SQLite 迁移

- [ ] **DB-01**: 系统以方言无关类型运行 SQLite，7 个 Alembic 迁移和 ORM 模型中 `postgresql.JSONB` 替换为 `JSON`、`postgresql.UUID` 替换为 `Uuid`，所有 JSON 列可正常序列化/反序列化
- [ ] **DB-02**: 数据目录（uploads/、exports/）解析为 `CTRX_DATA_DIR` 环境变量所指路径，不依赖 `__file__` 相对路径，在 PyInstaller `_MEIPASS` 和开发模式下均正确
- [ ] **DB-03**: SQLite 会话开启 WAL 模式，Uvicorn 线程池并发读写不产生数据库锁超时
- [ ] **DB-04**: `desktop_main.py` 在 uvicorn 启动前以程序化方式执行 `alembic upgrade head`，首次运行自动建表，升级运行自动迁移

### PKG — PyInstaller 打包

- [ ] **PKG-01**: 新增 `desktop_main.py` 作为 Python 打包入口：读取 `CTRX_DATA_DIR` / `CTRX_PORT` 环境变量 → 初始化路径 → 清除 `get_settings` lru_cache → 程序化执行 Alembic → 启动 uvicorn；支持 `sys.frozen` 路径分支
- [ ] **PKG-02**: 完整 PyInstaller spec（`--onedir`），hiddenimports 覆盖 uvicorn 内部模块、`sqlalchemy.dialects.sqlite`、`pydantic_settings`；datas 包含 `dicts/`、`alembic/`；excludes `psycopg2`；二进制产物放入 `electron/resources/`
- [ ] **PKG-03**: 在无 Python 环境的干净 Windows VM 烟雾测试通过：上传合同 → 跑通抽取 → 下载 xlsx 全部可用

### ELEC — Electron 壳与 IPC

- [ ] **ELEC-01**: Electron 主进程管理 Python 子进程完整生命周期：spawn PyInstaller 二进制 → 健康轮询 `GET /health`（300 ms 间隔、30 s 超时）→ 健康通过后显示主窗口（启动期显示加载隔屏）→ 崩溃自动重试最多 3 次 → 应用退出时先 SIGTERM 再 SIGKILL（5 s 后）
- [ ] **ELEC-02**: Electron `contextBridge` 通过 `ipcMain.handle` 暴露三个通道：`save-settings`（写 userData/config.json）、`load-settings`（读）、`get-port`（返回子进程监听端口）；使用 electron-store v10；配置项：`llmBaseUrl`、`llmApiKey`、`llmModel`
- [ ] **ELEC-03**: 首次启动（或 `llmBaseUrl`/`llmApiKey` 为空时）显示 3 步引导向导（Welcome → LLM 凭证 → 连接测试），向导未完成时封闭主界面入口；完成后路由跳转到主界面
- [ ] **ELEC-04**: 应用内 Settings 页面可随时修改 LLM 配置；保存后重启 Python 子进程使新 Key/BaseURL 生效；Settings 与向导共用 `LlmConfigForm.vue` 组件

### BUILD — 构建流水线

- [ ] **BUILD-01**: electron-builder 配置产出 Windows NSIS 安装包（`.exe`）和 Linux AppImage，`extraResources` 引用 PyInstaller `--onedir` 产物目录，`asarUnpack` 排除大型二进制
- [ ] **BUILD-02**: 提供 4 步构建脚本（PowerShell `.ps1` 和 Bash `.sh` 各一份）：① PyInstaller 打包 Python → ② Vite 构建 Vue SPA → ③ TypeScript 编译 Electron 主进程 → ④ electron-builder 生成安装包
- [ ] **BUILD-03**: 构建流水线同时产出 Linux `.deb` 安装包，可通过 `dpkg -i` 安装

## Future Requirements (v1.3+)

### 路径 B 增强

- **PATHB-EX-01**: 业绩报酬提取方式自动映射到 CRM 枚举值（减少人工判断，v1.3 主线）
- **PATHB-EX-02**: 业绩基准类型与门槛净值枚举精度提升

### 批量处理（v2 预研）

- **BATCH-01**: 多文件并发上传与队列管理
- **BATCH-02**: ZIP 包批量导入，自动逐合同处理
- **BATCH-03**: 批量导出合并 Excel

## Out of Scope

| Feature | Reason |
|---------|--------|
| 自动更新（auto-update） | 需要代码签名基础设施，内部 2 人团队无此需求，产生 IT 政策摩擦 |
| 系统托盘图标 | 过度工程化，对内部工具无价值 |
| Keychain / OS 凭证存储 | config.json 已足够；keychain 需要额外签名证书 |
| Windows 代码签名 | 内部分发暂不需要；将来可独立处理 |
| CRM 自动录入、PDF 支持 | 与 v1 决策一致，排除在外 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 | Phase 11 | Pending |
| DB-02 | Phase 11 | Pending |
| DB-03 | Phase 11 | Pending |
| DB-04 | Phase 11 | Pending |
| PKG-01 | Phase 12 | Pending |
| PKG-02 | Phase 12 | Pending |
| PKG-03 | Phase 12 | Pending |
| ELEC-01 | Phase 13 | Pending |
| ELEC-02 | Phase 13 | Pending |
| ELEC-03 | Phase 13 | Pending |
| ELEC-04 | Phase 13 | Pending |
| BUILD-01 | Phase 14 | Pending |
| BUILD-02 | Phase 14 | Pending |
| BUILD-03 | Phase 14 | Pending |

**Coverage:**
- v1.2 requirements: 14 total
- Mapped to phases: 14 (100%)
- Unmapped: 0

---
*Requirements defined: 2026-05-28*
*Last updated: 2026-05-28 — traceability mapped (phases 11–14)*
