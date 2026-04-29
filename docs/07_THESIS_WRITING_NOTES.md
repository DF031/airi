# 论文写作说明

## 推荐论文结构

### 第 1 章 绪论

写清楚背景和问题：

- 大模型具备自然语言生成能力，但容易幻觉。
- RAG 能用外部知识库约束回答，但检索质量和证据忠实性仍是难点。
- 数字人问答平台不仅要求答得对，还要求交互自然、语音和动作协调。
- 本项目面向本地运行和低成本部署，具有现实约束。

### 第 2 章 相关技术

建议覆盖：

- 大语言模型与 OpenAI-compatible API。
- RAG 基本流程：文档切分、索引、检索、重排、生成、验证。
- Hybrid RAG、CRAG、DeepNote、RAGEval、RAGChecker/RAGAS/ARES。
- TTS、Live2D、wLipSync、数字人动作和表情驱动。
- AIRI 开源项目及其可迁移模块。

### 第 3 章 系统需求分析

从用户和系统两侧写：

- 校园规章问答。
- 知识来源可追溯。
- 语音播报。
- 数字人展示、模型切换、动作/表情/口型同步。
- 本地运行、低算力、免费 API 限速、无需训练。

### 第 4 章 系统设计

对应 [系统架构](02_ARCHITECTURE.md)：

- 前端架构。
- 后端架构。
- RAG 流程。
- 数字人表现流程。
- 数据流和 API 设计。

### 第 5 章 关键模块实现

建议重点写：

- PortableRAGV4：parent-child chunk、多路检索、RRF、证据评分、MMR、拒答。
- ChatService：SSE 流式输出、RAG prompt、大模型调用、动作 token。
- TTS 与音频队列：播放中断、替换、避免排队延迟。
- AIRI 迁移：wLipSync、motion manager、idle eye focus、beat sync、逐模型 profile。
- 前端交互：模型切换、TTS 音色、调试面板、知识来源展示。

### 第 6 章 实验与评估

建议分层写，不要只写一个准确率：

- 检索层：source_hit_at_k、evidence_term_recall、answer_term_recall。
- 答案层：strict accuracy、usable accuracy、partial rate。
- 安全层：negative rejection。
- 工程层：接口响应、前端运行、TTS、Live2D 模型切换。

可以引用当前评估结果：

| 类别 | 代表结果 |
|---|---:|
| source_hit_at_k | 0.877373 |
| usable_proxy_rate | 0.892405 |
| evidence_term_recall | 0.871571 |
| positive_strict_accuracy | 0.560127 |
| positive_usable_accuracy | 0.731804 |
| negative_accuracy | 0.400000 |

解释重点：

- `usable_proxy_rate` 较高说明检索和证据覆盖较好。
- 严格答案准确率更低，说明生成/抽取/拒答仍是 RAG 系统的真实瓶颈。
- 这反而体现研究的严谨性，不能把代理指标包装成真实准确率。

### 第 7 章 总结与展望

总结：

- 完成了融合大模型、RAG、TTS、Live2D 数字人的一体化平台。
- 构建了可迁移轻量 RAG 主线。
- 完成了 AIRI 关键数字人表现能力迁移。
- 系统已通过最终运行验收。

展望：

- 更强的表格和编号结构解析。
- 更稳健的不可答/负例拒答。
- 更高质量中文 TTS 或离线语音。
- 更真实的中文口型和 viseme/phoneme 对齐。
- 增加更多知识库迁移实验。

## 可写成创新点的内容

1. 面向低算力本地部署的数字人问答平台架构。
2. 无训练、无固定问题规则的 Portable RAG v4。
3. 检索、证据、答案、安全四层评估体系。
4. AIRI 数字人表现能力的源码级迁移与 React 工程化。
5. RAG 问答、语音播报、Live2D 动作口型同步的一体化闭环。

## 需要诚实写出的不足

- 当前严格答案准确率还没有达到 90%。
- 负例拒答能力不足。
- TTS 质量受 edge-tts 和网络影响。
- Live2D 口型只能做到较自然的音频驱动，无法达到商业虚拟主播级别的精细表演。
- Gemini/GLM 等云端 API 免费层级存在限速。

## 推荐表述

可以写：

> 本文在本地低算力和免费 API 限速约束下，设计并实现了一个融合大模型技术的数字人智能问答平台。系统以 Portable RAG v4 作为知识增强问答核心，结合 GLM 生成、edge-tts 语音合成和 Live2D 数字人表现，实现了从用户提问、证据检索、答案生成、语音播报到动作口型同步的完整交互闭环。

不建议写：

> 本系统已经达到 90% 问答正确率。

除非后续有新的严格标注实验支撑，否则这句话风险很高。

