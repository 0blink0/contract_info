# 合同要素抽取（CTRX）

从私募基金合同 **docx** 解析结构化 JSON、抽取字段并生成可导入 Excel。Phase 1–3：解析 → 抽取 → xlsx 导出。

**Git 仓库：** [github.com/0blink0/contract_info](https://github.com/0blink0/contract_info.git)

```powershell
git clone https://github.com/0blink0/contract_info.git
cd contract_info
```

## 环境准备

依赖安装默认走 **清华 PyPI 镜像**（见根目录 `pip.conf`）。

```powershell
cd contract_info
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 推荐：脚本安装
.\scripts\install-deps.ps1

# 或手动指定镜像
pip install -c pip.conf -r requirements.txt

copy .env.example .env
```

## 数据库

```powershell
docker compose up -d
alembic upgrade head
```

PostgreSQL 监听 **5433**（避免与 bid_tool 的 5432 冲突）。口令与 `.env` 中 `DATABASE_URL` 一致。

若 Docker 卷已存在导致口令不一致，参见：
[troubleshooting-postgres-docker-password.md](../ai_bid_management/bid_tool_agents/docs/troubleshooting-postgres-docker-password.md)

## 解析（CLI）

```powershell
# 仅解析，打印摘要
python -m backend.cli parse example\附件1：私募证券投资基金私募基金合同.docx

# 解析并入库
python -m backend.cli parse example\附件1：私募证券投资基金私募基金合同.docx --persist

# 输出完整 JSON
python -m backend.cli parse example\*.docx --out out.json
```

## 母版与导出目录

- **`templates/`** — 官方导入母版（与 `example/` 同步，运行时使用）
- **`exports/{file_id}/`** — 生成的 `product_elements.xlsx`、`fee_rates.xlsx`

## 字段抽取（CLI）

在 `.env` 中配置 `OPENAI_API_KEY`（及可选 `OPENAI_BASE_URL`、`LLM_MODEL`）。无 Key 时仅运行规则层。

```powershell
# 从 docx 解析并抽取（不写库）
python -m backend.cli extract example\*.docx

# 输出完整 JSON
python -m backend.cli extract example\*.docx --out extract.json

# 先 parse 再 extract 入库
python -m backend.cli parse example\*.docx --persist
python -m backend.cli extract --file-id <uuid> --persist
```

字典表（校验用）首次导出：

```powershell
python scripts/export_dicts.py
```

## Excel 导出（CLI）

```powershell
# 完整链路（需 Docker + alembic upgrade head）
python -m backend.cli parse example\*.docx --persist
python -m backend.cli extract --file-id <uuid> --persist
python -m backend.cli export --file-id <uuid> --persist

# 仅从 JSON 调试导出
python -m backend.cli export --from-json backend/tests/fixtures/sample_extraction.json
```

## 测试

```powershell
pytest backend/tests/test_export_product.py backend/tests/test_export_fee.py backend/tests/test_export_pipeline.py -q
pytest backend/tests -q
```

## 目录结构

```
contract_info/
  backend/          # 应用与 CLI
  example/          # 样例合同与 Excel 模板
  uploads/          # 持久化上传的 docx
  alembic/          # 数据库迁移
  .planning/        # GSD 规划文档
```
