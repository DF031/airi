# 安装与运行

## 环境要求

- Windows + PowerShell
- Python 虚拟环境：`venv`
- Node.js / npm
- 前端依赖已安装在 `frontend/node_modules`
- 后端依赖已安装在 `venv`

当前项目默认按本地开发方式运行，不需要 Docker，不需要本地 GPU。

## 环境变量

复制模板：

```powershell
Copy-Item .env.example .env
```

关键配置：

```text
CHAT_PROVIDER=zhipu
CHAT_MODEL=GLM-4-Flash-250414
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_API_KEY=你的智谱 API Key

RAG_STRATEGY=portable_v4
KNOWLEDGE_DIR=experiments/rag_reproduction/data
PORTABLE_RAG_CONFIG=experiments/rag_reproduction/configs/portable_rag.yaml

TTS_MODEL=edge-tts
TTS_VOICE=zh-CN-XiaoxiaoNeural
TTS_RATE=+8%
```

如果切换到 Gemini provider：

```text
CHAT_PROVIDER=gemini
GEMINI_API_KEY=你的 Gemini API Key
GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

注意：`.env` 包含私钥，不应提交或公开。

## 启动后端

```powershell
.\scripts\run_backend.ps1
```

正常输出应包含：

```text
Uvicorn running on http://127.0.0.1:8000
[rag] using PortableRAGV4 with campus corpus
[rag] PortableRAGV4 ready
```

第一次启动会加载 RAG 结构化证据和索引，可能比普通启动慢。

## 启动前端

```powershell
.\scripts\run_frontend.ps1
```

默认访问：

```text
http://127.0.0.1:5173
```

## 运行检查

检查后端状态：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/system/status
```

检查前端：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173
```

检查前端代码：

```powershell
Set-Location frontend
npm run lint
npm run build
```

检查后端 Python 语法：

```powershell
.\venv\Scripts\python.exe -m compileall backend experiments\rag_reproduction\raglab
```

## 常见问题

### 1. 智谱返回 429 限速

免费层级 API 有并发和速率限制。当前项目已经将 LLM 调用集中在平台回答阶段，RAG 评估尽量不调用 LLM。出现 429 时可以：

- 等待一段时间再提问。
- 降低连续提问频率。
- 保持 `ENABLE_CRAG_JUDGE=false` 和 `ENABLE_LLM_ACTIONS=false`。

### 2. 后端已启动但前端显示连接异常

检查：

- 后端是否在 `127.0.0.1:8000`
- `.env` 中 `CORS_ORIGINS=*`
- 前端是否使用默认 `VITE_API_BASE_URL=http://127.0.0.1:8000`

### 3. TTS 失败

当前 TTS 使用 `edge-tts`。如果失败，常见原因是网络连接或 edge-tts 服务临时不可用。可以重试，或切换前端音色后再试听。

### 4. Live2D 模型无法加载

检查：

- 模型目录是否位于 `frontend/public`
- 模型是否包含 `.model3.json`、`.moc3`、texture、motion 文件
- 浏览器控制台中是否有 404

### 5. PowerShell 显示中文乱码

项目文件是 UTF-8。若 PowerShell 直接 `Get-Content` 显示乱码，可在 VS Code 中查看，或先设置：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

