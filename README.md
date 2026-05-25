# 合同要素抽取（CTRX）

从私募基金合同 **docx** 解析结构化 JSON，并按文件写入 PostgreSQL。Phase 1：解析与入库；后续阶段做字段抽取与 Excel 导出。

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

## 测试

```powershell
# 单元测试（无需数据库）
pytest backend/tests/test_outline.py backend/tests/test_docx_parser.py -q

# 集成测试（需 DATABASE_URL 与 docker compose）
$env:DATABASE_URL = "postgresql+psycopg2://postgres:contract_info_dev@localhost:5433/contract_info"
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
