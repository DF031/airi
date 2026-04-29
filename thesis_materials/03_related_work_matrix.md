# 相关工作矩阵

本表用于写第 2 章“相关技术与研究现状”。每篇文献都按“研究问题、核心方法、本文借鉴点、本文差异”整理。

## RAG 基础与高级方法

| 文献 | 核心问题 | 核心方法 | 本文借鉴点 | 本文差异 |
|---|---|---|---|---|
| Lewis et al., 2020, RAG | 大模型参数知识不足，开放域问答需要外部知识 | 将检索器与生成模型结合，用非参数化知识增强生成 | 本文采用“检索证据 + 大模型生成”的基本框架 | 本文不训练端到端 RAG 模型，而是工程化接入校园知识库 |
| Yan et al., 2024, CRAG | RAG 对检索质量敏感，错误检索会导致错误生成 | 用轻量检索评价器评估文档质量，并触发纠错检索和信息过滤 | 本文使用 confidence 和 evidence evaluator 思想决定回答、扩展或拒答 | 本文不训练 CRAG evaluator，也不依赖外部 web search |
| Wang et al., 2025, DeepNote | 自适应 RAG 难以充分累积和利用多轮检索知识 | 用 note 作为知识积累载体，驱动迭代检索和最终回答 | 本文保留 note memory / 多步证据组织的设计思想 | 本文为轻量本地系统，没有训练 DPO 或复杂 note policy |
| Guo et al., 2024/2025, LightRAG | 扁平文本索引难以捕捉复杂关系 | 图结构索引、低层/高层双级检索、增量更新 | 本文借鉴“结构化检索比扁平切块更可靠”的观点 | 本文没有构建完整知识图谱，而是采用结构化 evidence unit |
| Chen et al., 2025, UltraRAG | RAG 工具链缺少面向场景的知识适配和模块化编排 | 模块化 RAG toolkit，覆盖数据构建、训练、评估、WebUI | 本文借鉴 YAML 配置、模块化 pipeline、端到端实验思路 | 本文规模更小，强调毕业设计可运行和本地轻量实现 |

## RAG 评估方法

| 文献 | 核心问题 | 核心方法 | 本文借鉴点 | 本文差异 |
|---|---|---|---|---|
| Es et al., 2023/2024, RAGAS | RAG 评价维度复杂，不应只看最终答案 | context relevance、faithfulness、answer relevancy 等指标 | 本文将评价拆分为检索、证据、答案和安全层 | 本文为了节省 API，主要采用无 LLM 的离线指标和 CSV 标注 |
| Saad-Falcon et al., 2023/2024, ARES | RAG 评价依赖人工标注，跨领域成本高 | 自动生成训练数据，训练轻量 judge，评估上下文相关性、答案忠实性和答案相关性 | 本文借鉴分维度评价思想 | 本文不训练 judge，只保留人工/规则可核验的严格标注 |
| Ru et al., 2024, RAGChecker | RAG 错误来源复杂，检索与生成需要细粒度诊断 | 同时诊断 retrieval 和 generation 模块 | 本文采用“代理指标不能替代真实答案准确率”的结论思路 | 本文没有完整复现 RAGChecker，而是设计 RAGChecker-lite 风格指标 |
| Zhu et al., 2025, RAGEval | 专门场景 RAG 评估集构建成本高、指标不足 | 基于 schema 生成文档、问题、答案和 references，并提出 Completeness、Hallucination、Irrelevance | 本文借鉴场景化评估和答案层指标 | 本文使用已有校园数据集和人工/离线标注，没有大规模生成评估集 |

## 数字人与交互表现

| 项目/技术 | 核心能力 | 本文借鉴点 | 本文差异 |
|---|---|---|---|
| AIRI | 自托管 AI 虚拟伴侣，支持实时语音、多平台、Web 技术栈、Live2D/VRM 等能力 | 源码级迁移音频 pipeline、wLipSync、motion manager、idle eye focus、beat sync、逐模型 profile | 本文没有迁移完整 AIRI 应用生态，而是将数字人表现模块接入校园问答平台 |
| wLipSync | 基于 MFCC、WASM 和 WebAudio 的口型同步库 | 用真实音频驱动 Live2D 嘴型参数，改善仅按文本猜口型的问题 | 本文结合 TTS mouth cues 和每模型 profile，适配多个模型参数族 |
| Live2D Cubism | 2D 数字人模型、参数、motion、expression 和 physics | 用于数字人展示、动作、表情和口型参数控制 | 本文重点在平台集成和问答交互，不涉及模型建模和绑定制作 |

## 可直接写入论文的相关工作段落

### RAG 技术段落

检索增强生成通过引入外部知识库缓解大语言模型参数知识不足和事实幻觉问题。Lewis 等提出的 RAG 方法将检索器与生成模型结合，为知识密集型 NLP 任务提供了代表性框架。后续研究进一步关注检索质量、纠错机制和复杂知识组织。例如 CRAG 针对错误检索会影响生成的问题，引入检索质量评价和纠错检索机制；DeepNote 则将 note 作为知识积累载体，在多步检索中持续更新信息状态；LightRAG 和 UltraRAG 分别从图结构检索和模块化工具链角度提升 RAG 系统的适应能力。本文在本地低算力约束下，不进行训练或微调，而是借鉴上述研究思想，构建无训练、轻量化的 Portable RAG v4。

### RAG 评估段落

RAG 系统的评估不能仅依赖最终答案的表面准确率，因为错误可能来自检索、证据组织、生成忠实性或拒答策略等不同环节。RAGAS、ARES 和 RAGChecker 等工作分别从上下文相关性、答案忠实性、答案相关性和检索/生成诊断等维度提出评价框架。RAGEval 进一步面向特定场景构建 schema-based 评估集，并强调完整性、幻觉和无关性等事实性指标。受这些研究启发，本文将校园 RAG 评估划分为检索层、证据层、答案层和安全层，并对代理指标与严格答案级标注结果进行区分。

### 数字人段落

数字人问答系统不仅需要生成正确答案，还需要具备语音、表情、动作和口型等多模态表现能力。AIRI 开源项目展示了以 WebGPU、WebAudio、WebAssembly 和 WebSocket 等 Web 技术构建 AI 虚拟伴侣的可能性。wLipSync 等音频驱动口型库则为浏览器端实时口型同步提供了轻量实现基础。本文参考 AIRI 的音频 pipeline、Live2D 舞台管理和口型同步设计，对相关模块进行源码级迁移与 React 工程化适配，实现了校园问答场景下的数字人语音播报和动作口型同步。

## 核对过的主要来源

- RAG 原始论文：<https://arxiv.org/abs/2005.11401>
- CRAG 论文：<https://arxiv.org/abs/2401.15884>
- CRAG 官方代码：<https://github.com/HuskyInSalt/CRAG>
- RAGEval ACL 2025：<https://aclanthology.org/2025.acl-long.418/>
- DeepNote EMNLP Findings 2025：<https://aclanthology.org/2025.findings-emnlp.1073.pdf>
- RAGChecker：<https://arxiv.org/abs/2408.08067>
- RAGAS：<https://arxiv.org/abs/2309.15217>
- ARES：<https://arxiv.org/abs/2311.09476>
- UltraRAG：<https://arxiv.org/abs/2504.08761>
- LightRAG：<https://arxiv.org/abs/2410.05779>
- AIRI：<https://github.com/moeru-ai/airi>
- wLipSync：<https://github.com/mrxz/wLipSync>

