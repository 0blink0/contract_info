# 启动 MCP HTTP/SSE server (本地模式)
# 运行后保持窗口开着，Trae 通过 http://127.0.0.1:8765/sse 连接

$env:PYTHONPATH = "d:\bid_management\contract_info"
$env:LANCE_TELEMETRY_ENABLED = "false"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:HTTP_PROXY = "http://127.0.0.1:7990"
$env:HTTPS_PROXY = "http://127.0.0.1:7990"

# API 密钥从 .env 文件读取，也可以在这里直接设置
# $env:OPENAI_API_KEY = "sk-..."
# $env:OPENAI_BASE_URL = "https://api.deepseek.com"
# $env:LLM_MODEL = "deepseek-v4-flash"

Write-Host "Starting MCP HTTP server at http://127.0.0.1:8765/sse" -ForegroundColor Green
python "d:\bid_management\contract_info\mcp_server\server.py" --http --host 127.0.0.1 --port 8765
