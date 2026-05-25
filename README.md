# 合同要素抽取（CTRX）

从私募基金合同 **docx** 解析结构化 JSON、抽取字段并生成可导入 Excel。Phase 1–5：解析 → 抽取 → xlsx → HTTP API → Web 界面。

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

## Docker 一键部署（服务器）

```bash
cd contract_info
cp .env.example .env
# 编辑 .env：POSTGRES_PASSWORD、API_KEY（建议）、OPENAI_API_KEY（可选）

docker compose up -d --build
```

启动后访问 **`http://<服务器IP>:8080`**（端口由 `.env` 的 `HTTP_PORT` 控制，默认 8080）。

| 服务 | 说明 |
|------|------|
| `postgres` | 数据库（数据卷 `contract_info_pg_data`） |
| `api` | FastAPI，自动 `alembic upgrade head` |
| `web` | Nginx 静态前端 + 反代 `/api` → api |

上传与导出文件持久化在卷 `contract_info_uploads`、`contract_info_exports`。

查看日志：`docker compose logs -f api` / `docker compose logs -f web`

停止：`docker compose down`（加 `-v` 会删除数据卷，慎用）

### 轩辕镜像 `docker.xuanyuan.run`（已登录仍提示要 login）

原因：Docker 配置了镜像加速时，拉取 `postgres:16-alpine` 会走加速站，**登录凭证往往不会带上**。

**做法：** 在 `.env` 里用镜像站**完整路径**（并 `docker login docker.xuanyuan.run`），不要用短名 + 加速：

```bash
docker login docker.xuanyuan.run

# 编辑 .env，增加或取消注释：
POSTGRES_IMAGE=docker.xuanyuan.run/library/postgres:16
PYTHON_IMAGE=docker.xuanyuan.run/library/python:3.11-slim-bookworm
NODE_IMAGE=docker.xuanyuan.run/library/node:20-alpine
NGINX_IMAGE=docker.xuanyuan.run/library/nginx:1.27-alpine

docker compose up -d --build
```

可先单独测试：`docker pull docker.xuanyuan.run/library/postgres:16`

若仍失败，查看 `cat /etc/docker/daemon.json` 中的 `registry-mirrors`，必要时临时去掉加速后重启 Docker。

## 数据库（本地 venv 开发）

仅启动 PostgreSQL（宿主机 **5433**，避免与 bid_tool 5432 冲突）：

```powershell
docker compose -f docker-compose.dev.yml up -d
alembic upgrade head
```

`DATABASE_URL` 使用 `.env.example` 中本地开发那一行。

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

## HTTP API（Phase 4）

在 `.env` 中配置 `DATABASE_URL`；可选 `API_KEY`（留空则开发环境不校验 `X-API-Key`）。

```powershell
docker compose up -d
alembic upgrade head
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI 文档：`http://localhost:8000/docs`

```powershell
# 上传（返回 job_id）
curl -s -X POST http://localhost:8000/api/v1/upload `
  -H "X-API-Key: YOUR_KEY" `
  -F "file=@example\附件1：私募证券投资基金私募基金合同.docx"

# 触发处理（202，后台 parse → extract → export）
curl -s -X POST http://localhost:8000/api/v1/jobs/{job_id}/run `
  -H "X-API-Key: YOUR_KEY"

# 轮询状态
curl -s http://localhost:8000/api/v1/jobs/{job_id} -H "X-API-Key: YOUR_KEY"

# 下载（status=exported 后）
curl -OJ http://localhost:8000/api/v1/jobs/{job_id}/download/product-elements -H "X-API-Key: YOUR_KEY"
curl -OJ http://localhost:8000/api/v1/jobs/{job_id}/download/fee-rates -H "X-API-Key: YOUR_KEY"
```

CLI（`parse` / `extract` / `export`）仍可用。

## 前端（Phase 5）

需同时启动 **后端 API** 与 **Vite 开发服务器**：

```powershell
# 终端 1 — API
cd contract_info
.\.venv\Scripts\Activate.ps1
docker compose up -d
alembic upgrade head
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 终端 2 — 前端（proxy /api → 8000）
cd contract_info\frontend
npm install
npm run dev
```

浏览器打开 **http://localhost:5173**：上传 docx → 选中任务 →「开始处理」→ 步骤条完成后下载两个 Excel。

生产构建（可选 `VITE_API_KEY`）：

```powershell
cd frontend
copy .env.example .env
# 编辑 .env 设置 VITE_API_KEY=...（与后端 API_KEY 一致）
npm run build
# 将 dist/ 交由 Nginx 托管，/api 反代到 Uvicorn
```

## 测试

```powershell
pytest backend/tests/test_api_auth.py backend/tests/test_api_upload.py backend/tests/test_api_pipeline.py backend/tests/test_api_download.py -q
pytest backend/tests/test_export_product.py backend/tests/test_export_fee.py backend/tests/test_export_pipeline.py -q
pytest backend/tests -q
```

## 目录结构

```
contract_info/
  backend/          # 应用与 CLI
  frontend/         # Vue 3 上传/状态/下载
  example/          # 样例合同与 Excel 模板
  uploads/          # 持久化上传的 docx
  alembic/          # 数据库迁移
  .planning/        # GSD 规划文档
```
