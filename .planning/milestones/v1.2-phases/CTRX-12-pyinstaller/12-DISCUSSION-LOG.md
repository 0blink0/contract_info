# Phase 12: PyInstaller 打包 - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 12-PyInstaller 打包
**Areas discussed:** 打包规格策略, hiddenimports 粒度, 资源布局, 干净机验收

---

## 打包规格策略

| Option | Description | Selected |
|--------|-------------|----------|
| 单一 spec + 参数化平台分支 | 维护成本低，避免双 spec 漂移 | ✓ |
| Windows/Linux 各自独立 spec | 平台隔离清晰，但维护成本高 | |
| 公共 base + overlay | 折中方案 | |

**User's choice:** 单一 spec + 参数化平台分支  
**Notes:** 同时选择稳定优先、desktop_main 单入口、资源缺失 fail-fast。

---

## hiddenimports 粒度

| Option | Description | Selected |
|--------|-------------|----------|
| 最小白名单 + 日志补齐 | 起步快但可能多轮失败 | |
| 宽覆盖已知模块 | 干净机成功率更高 | ✓ |
| 自动扫描生成 | 自动化高但可控性较弱 | |

**User's choice:** 宽覆盖起步 + 手工锁定清单 + 平台分段 + CI 差异门禁  
**Notes:** 明确可审计优先，避免动态导入漏包。

---

## 资源布局

| Option | Description | Selected |
|--------|-------------|----------|
| resources 仅保留最终产物 | 交付目录最干净 | ✓ |
| 保留中间构建目录 | 便于排障 | |
| 发布/开发双通道 | 平衡交付与调试 | |

**User's choice:** 最终产物模式 + 版本化目录 + 日志外置 + 保留上一个版本  
**Notes:** 明确不污染安装目录，且保留回退能力。

---

## 干净机验收

| Option | Description | Selected |
|--------|-------------|----------|
| 最小主链路烟测 | 上传→抽取→下载 | ✓ |
| 主链路 + 校验/path-b | 覆盖更多但成本更高 | |
| 回归级验收 | 接近完整回归 | |

**User's choice:** 最小烟测 + 固定单黄金合同 + 失败阻断发布 + 结构化 checklist  
**Notes:** 先达成 PKG-03 可复现通过，再逐步扩大覆盖。

---

## Claude's Discretion

- hiddenimports 清单具体条目及排序。
- spec 内平台分段实现细节。
- checklist 结构模板与证据命名规范。

## Deferred Ideas

- 并发/扩展验收项作为后续阶段增强，不纳入本阶段阻断条件。
