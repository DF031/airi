# 论文详细大纲

## 第 1 章 绪论

### 1.1 研究背景

可写内容：

- 大语言模型提升了自然语言理解与生成能力。
- 校园服务问答场景有大量规章制度、办事流程和服务信息，适合用智能问答系统提升查询效率。
- 大模型参数知识不适合直接回答强事实性、强时效性、本地化知识问题。
- RAG 通过外部知识库补充大模型，可以降低幻觉并提高可追溯性。
- 数字人界面让问答系统从文本工具变成交互型助手，提升可用性和展示效果。

### 1.2 研究意义

理论意义：

- 探索 RAG 在校园垂直知识库中的构建与评估方法。
- 将 RAG 评价从单一准确率扩展为检索、证据、答案、安全多层指标。

工程意义：

- 在低算力和免费 API 限速条件下实现可运行平台。
- 将数字人语音、口型、动作与问答系统结合。
- 为校园智能服务平台提供可复现原型。

### 1.3 国内外研究现状

建议分三段：

1. 大模型与 RAG 技术：RAG 原始方法、Hybrid RAG、CRAG、LightRAG、UltraRAG。
2. RAG 评估技术：RAGAS、ARES、RAGChecker、RAGEval。
3. 数字人与虚拟助手：Live2D、AIRI、wLipSync、TTS 与音频驱动口型。

### 1.4 研究内容

本文主要研究内容：

- 设计数字人智能问答平台总体架构。
- 构建校园知识库 RAG 系统。
- 实现大模型增强回答与来源展示。
- 实现 TTS 语音播报和 Live2D 数字人表现。
- 对 RAG 系统和平台运行效果进行评估。

### 1.5 论文组织结构

按第 2 章到第 7 章简述。

## 第 2 章 相关技术

### 2.1 大语言模型

说明大模型能力、API 调用方式、上下文提示、幻觉问题和本项目使用 GLM 的原因。

### 2.2 检索增强生成

描述 RAG 基本流程：

```text
文档采集 -> 文档切分 -> 索引构建 -> 查询检索 -> 证据组织 -> 大模型生成 -> 答案验证
```

### 2.3 高级 RAG 方法

可写：

- Hybrid RAG：结合稀疏检索和语义检索。
- CRAG：通过检索评价器判断证据质量并触发纠错。
- DeepNote：用 note 作为知识累积和多步检索载体。
- LightRAG：通过图结构改善复杂关系检索。
- UltraRAG：强调模块化、自动化和知识适配。

### 2.4 RAG 评估方法

可写：

- RAGAS：参考无关的自动评估思路。
- ARES：上下文相关性、答案忠实性、答案相关性。
- RAGChecker：细粒度诊断检索与生成模块。
- RAGEval：面向场景的 schema-based 评估数据构建。

### 2.5 数字人相关技术

可写：

- Live2D 模型和 motion/expression 参数。
- TTS 语音合成。
- 音频驱动口型和 wLipSync。
- AIRI 的开源虚拟助手架构。

## 第 3 章 需求分析

### 3.1 功能需求

- 校园知识问答。
- 知识来源展示。
- 流式回答。
- 语音播报。
- 数字人动作、表情、口型同步。
- 模型和音色切换。
- 系统状态展示和调试。

### 3.2 非功能需求

- 本地运行。
- 低算力。
- 免费 API 限速适配。
- 可迁移。
- 可评估。
- 可解释。

### 3.3 数据需求

- 校园知识库文档。
- 正例问答集。
- 负例问题集。
- Live2D 模型文件。
- TTS 缓存与长期记忆数据。

## 第 4 章 系统设计

### 4.1 总体架构设计

引用 `docs/02_ARCHITECTURE.md` 中的架构图。

### 4.2 后端设计

写 FastAPI、配置管理、RAG 适配器、ChatService、TTSService、Memory。

### 4.3 前端设计

写 React 主界面、SSE 流式接收、状态栏、来源展示、数字人控制面板。

### 4.4 RAG 设计

写 PortableRAGV4 pipeline。

### 4.5 数字人表现设计

写 TTS、音频队列、wLipSync、motion manager、每模型 profile。

### 4.6 数据库和文件组织

写知识库、索引、TTS cache、长期记忆 SQLite。

## 第 5 章 系统实现

### 5.1 后端接口实现

重点接口：

- `/api/system/status`
- `/api/avatar/models`
- `/api/tts/voices`
- `/api/chat/stream`
- `/api/tts`

### 5.2 PortableRAGV4 实现

写实现点：

- 文档结构化。
- parent-child chunk。
- BM25/TF-IDF/字符 n-gram。
- RRF 融合。
- source-constrained hits。
- evidence scoring。
- MMR。
- confidence 和拒答。

### 5.3 大模型问答实现

写 GLM-4-Flash-250414、速率限制、流式输出、RAG prompt、fallback。

### 5.4 语音和口型实现

写 edge-tts、音频播放队列、speech pipeline、mouth cues、wLipSync。

### 5.5 Live2D 数字人实现

写模型加载、模型切换、自适应缩放、idle motion、interaction motion、自动眨眼、眼球注视、调试面板。

## 第 6 章 实验与评估

### 6.1 实验环境

写 Windows、本地 CPU、FastAPI、React、GLM API、edge-tts。

### 6.2 数据集

写校园知识库 74 文件、35.01 MB；正例 1264 条、负例 60 条。

### 6.3 评价指标

分层：

- 检索层：source_hit_at_k、answer_term_recall、evidence_term_recall。
- 答案层：strict accuracy、usable accuracy、partial rate。
- 安全层：negative accuracy。
- 工程层：服务启动、接口返回、前端真实交互、TTS、模型切换。

### 6.4 RAG 实验结果

引用 `05_rag_experiment_materials.md`。

### 6.5 平台运行验收

引用 `docs/06_FINAL_ACCEPTANCE.md`。

### 6.6 结果分析

重点写：

- 检索证据表现较好。
- 严格答案准确率和负例拒答仍是瓶颈。
- 平台端结合 GLM 后可提供更自然回答，但论文中要区分离线抽取评估和平台生成效果。

## 第 7 章 总结与展望

### 7.1 工作总结

概括平台、RAG、数字人、评估。

### 7.2 不足

- 严格答案正确率未达到 90%。
- 负例拒答不足。
- 表格/数字/电话精确抽取仍需加强。
- TTS 和口型仍难达到商业虚拟主播级别。

### 7.3 展望

- 更强文档结构解析。
- 更稳健不可答检测。
- 引入轻量 reranker 或本地 embedding。
- 更高质量 TTS。
- 多知识库迁移实验。

