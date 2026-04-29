# 融合大模型技术的数字人智能问答平台

本项目是毕业设计《融合大模型技术的数字人智能问答平台设计与研究》的工程实现。系统面向本地运行场景，集成校园知识库 RAG 问答、GLM 大模型生成、短期/长期记忆、TTS 语音合成、Live2D 数字人展示、AIRI 源码级迁移后的动作/口型/音频播放能力。

当前主线目标不是堆叠云端高算力模型，而是在低成本、本地 CPU 可运行、免费层级 API 限速约束下，构建一个可迁移、可评估、可解释、能实际交互的数字人问答平台。

## 当前状态

- 后端：FastAPI，默认运行在 `http://127.0.0.1:8000`
- 前端：React + Vite + PixiJS + Live2D，默认运行在 `http://127.0.0.1:5173`
- 大模型：智谱 GLM，默认 `GLM-4-Flash-250414`
- RAG：`PortableRAGV4`，默认使用校园知识库 `experiments/rag_reproduction/data`
- TTS：`edge-tts` 本地库封装，支持多中文音色和语速配置
- 数字人：支持多 Live2D 模型切换、逐模型 profile、AIRI 风格 idle/motion/口型同步

## 快速运行

先复制并填写环境变量：

```powershell
Copy-Item .env.example .env
```

在第一个终端启动后端：

```powershell
.\scripts\run_backend.ps1
```

在第二个终端启动前端：

```powershell
.\scripts\run_frontend.ps1
```

浏览器打开：

```text
http://127.0.0.1:5173
```

快速检查后端：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/system/status
```

## 文档入口

- [项目概述](docs/01_PROJECT_OVERVIEW.md)
- [系统架构](docs/02_ARCHITECTURE.md)
- [安装与运行](docs/03_SETUP_AND_RUN.md)
- [RAG 系统与评估](docs/04_RAG_SYSTEM_AND_EVALUATION.md)
- [数字人与 AIRI 迁移](docs/05_DIGITAL_HUMAN_AND_AIRI_MIGRATION.md)
- [最终验收记录](docs/06_FINAL_ACCEPTANCE.md)
- [论文写作说明](docs/07_THESIS_WRITING_NOTES.md)
- [论文材料目录](thesis_materials/README.md)

## 主要目录

```text
backend/                         FastAPI 后端、RAG 接入、记忆、TTS、大模型服务
frontend/                        React 前端、Live2D 舞台、AIRI 迁移模块
experiments/rag_reproduction/    RAG 复现、可迁移 RAG v4、评估数据和结果
scripts/                         本地启动和实验运行脚本
data/                            运行时索引、TTS 缓存、长期记忆数据库
archive/                         已废弃或被替代的历史实验材料
docs/                            项目交付文档
```

## 关键接口

- `GET /api/health`: 基础健康检查
- `GET /api/system/status`: 平台状态、RAG 状态、TTS 配置、模型信息摘要
- `GET /api/avatar/models`: 前端 Live2D 模型列表
- `GET /api/tts/voices`: 可选 TTS 音色列表
- `POST /api/chat/stream`: 流式问答
- `POST /api/tts`: TTS 音频生成，并返回口型 cue header

## 验收结论

2026-04-23 的最终运行验收显示：前端、后端、RAG、TTS、Live2D 模型切换、TTS 试听、口型/Level 驱动和浏览器真实问答链路均可运行。详细记录见 [最终验收记录](docs/06_FINAL_ACCEPTANCE.md)。
