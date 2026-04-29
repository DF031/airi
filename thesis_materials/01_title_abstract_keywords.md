# 题目、摘要与关键词

## 论文题目

融合大模型技术的数字人智能问答平台设计与研究

## 可选英文题目

Design and Research of a Digital Human Intelligent Question Answering Platform Integrating Large Language Model Technology

## 中文摘要初稿

随着大语言模型在自然语言理解与生成任务中的快速发展，智能问答系统在校园服务、知识检索和人机交互等场景中具有广泛应用价值。然而，单纯依赖大模型参数知识容易产生事实幻觉，传统检索式问答又难以提供自然、连续的交互体验。针对上述问题，本文设计并实现了一个融合大模型技术的数字人智能问答平台。系统以校园规章制度、办事流程和服务信息为知识来源，采用检索增强生成技术构建问答能力，并结合语音合成、Live2D 数字人模型、口型同步和动作控制实现多模态交互。

在系统设计方面，本文采用前后端分离架构，后端基于 FastAPI 实现大模型调用、RAG 检索、记忆管理和语音合成接口，前端基于 React、Vite、PixiJS 和 Live2D 实现问答界面与数字人展示。针对本地运行算力有限、免费 API 存在速率限制等约束，本文构建了一个无训练、轻量化、可迁移的 Portable RAG v4 系统。该系统通过文档结构化切分、多路稀疏检索、RRF 融合、证据评分、相邻证据扩展和 MMR 选择等方法提高知识召回和证据组织能力。同时，本文参考 CRAG、DeepNote、RAGEval 和 RAGChecker 等相关研究，将评估拆分为检索层、证据层、答案层和安全拒答层，避免仅以单一代理指标评价系统效果。

在数字人交互方面，本文对 AIRI 开源项目中与数字人表现相关的音频播放队列、TTS 分段、wLipSync 口型同步、Live2D motion 管理、自动眨眼、眼球注视和逐模型 profile 等模块进行了源码级迁移与 React 工程化适配。平台支持多个 Live2D 模型切换、多种中文 TTS 音色选择、语音播放中断与替换、数字人动作调试和实时音频电平显示。最终运行验收表明，系统能够完成从用户提问、RAG 检索、大模型回答、知识来源展示、TTS 播放到数字人口型动作同步的完整交互闭环。

实验结果显示，Portable RAG v4 在校园知识库上取得了较高的检索命中和证据覆盖表现，但严格答案级标注结果也暴露出负例拒答和精确事实抽取仍有不足。该结果说明，RAG 系统评价需要同时关注检索质量、证据忠实性、答案完整性和安全拒答能力。本文的研究与实现为低成本、本地化的数字人问答平台构建提供了一种可复现的工程方案。

## 英文摘要初稿

With the rapid development of large language models, intelligent question answering systems have shown broad application potential in campus services, knowledge retrieval, and human-computer interaction. However, relying solely on parametric knowledge may lead to factual hallucinations, while traditional retrieval-based systems often provide limited conversational and multimodal interaction experience. To address these issues, this thesis designs and implements a digital human intelligent question answering platform integrating large language model technology. The platform uses campus regulations, administrative procedures, and service documents as the knowledge base, builds question answering capability through retrieval-augmented generation, and combines text-to-speech, Live2D avatars, lip synchronization, and motion control for multimodal interaction.

The system adopts a separated frontend-backend architecture. The backend is implemented with FastAPI and provides interfaces for large language model invocation, RAG retrieval, memory management, and speech synthesis. The frontend is built with React, Vite, PixiJS, and Live2D to support the chat interface and digital human rendering. Considering local computation constraints and the rate limits of free API tiers, this thesis develops Portable RAG v4, a training-free, lightweight, and domain-portable RAG system. It improves knowledge retrieval and evidence organization through structured document chunking, multi-path sparse retrieval, reciprocal rank fusion, evidence scoring, source-neighbor expansion, and MMR-based selection. Inspired by CRAG, DeepNote, RAGEval, and RAGChecker, the evaluation is decomposed into retrieval, evidence, answer, and safety layers instead of relying on a single proxy metric.

For digital human interaction, this thesis performs source-level migration and React-based adaptation of key AIRI modules, including audio playback queues, TTS chunking, wLipSync-based lip synchronization, Live2D motion management, automatic blinking, eye focus, and per-model profiles. The platform supports multiple Live2D models, multiple Chinese TTS voices, interruptible and replaceable speech playback, avatar debugging, and real-time audio level visualization. Final acceptance testing demonstrates that the system can complete the full interaction loop from user questions, RAG retrieval, LLM-based answering, source display, TTS playback, to synchronized digital human lip motion and actions.

Experimental results show that Portable RAG v4 achieves strong retrieval and evidence coverage on the campus knowledge base, while strict answer-level annotation reveals remaining limitations in negative rejection and precise fact extraction. These findings indicate that RAG evaluation should jointly consider retrieval quality, evidence faithfulness, answer completeness, and safe refusal. The work provides a reproducible engineering solution for building low-cost and locally deployable digital human question answering platforms.

## 关键词

- 大语言模型
- 检索增强生成
- 数字人
- 智能问答
- Live2D
- 语音合成
- 口型同步

## Keywords

- Large Language Model
- Retrieval-Augmented Generation
- Digital Human
- Intelligent Question Answering
- Live2D
- Text-to-Speech
- Lip Synchronization

