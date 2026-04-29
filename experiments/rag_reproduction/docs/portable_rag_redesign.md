# 可迁移 RAG 系统重构方案

本方案用于替代当前依赖题面关键词、固定校园知识库和人工补规则的 `final_rag` 路线。新的目标不是把某一份评测集刷到 90%，而是构建一个可迁移到不同知识库、可解释、可评测、可复现实验的 RAG 系统。

## 方向判断

当前做法的问题：

- 规则写在代码里，例如针对具体文件、具体问法、具体实体加权，短期能修复样例，但迁移到新知识库会失效。
- 评估集与优化过程耦合，容易变成“测评集适配器”，无法支撑毕业设计中的研究性结论。
- 检索、重排、纠错、生成、评估没有清晰边界，后续难以消融实验，也难以解释失败原因。

新的主线：

- 保留 BM25 / TF-IDF / Hybrid / CRAG / DeepNote 作为可复现 baseline 和消融模块。
- 废弃面向具体校园问法的硬编码规则，把领域差异放入外部配置、语料 schema 和评测数据中。
- 按 RAGEval 思路构建场景化评测集，按 RAGChecker / RAGAS / ARES 思路拆分检索、证据支撑、答案忠实性和答案完整性指标。
- 参考 UltraRAG 的模块化编排思想，用 YAML 描述 pipeline，代码只实现通用组件。

## 参考依据

- RAGEval: Scenario Specific RAG Evaluation Dataset Generation Framework, ACL 2025。核心价值是 schema-based 的场景评测数据生成，并提出 Completeness、Hallucination、Irrelevance 等事实准确性指标。
- UltraRAG: A Modular and Automated Toolkit for Adaptive Retrieval-Augmented Generation, arXiv 2025。核心价值是把 Retriever、Generation、Evaluation 等能力拆成可编排模块，支持知识适配和端到端实验。
- CRAG: Corrective Retrieval Augmented Generation, arXiv 2024。核心价值是 retrieval evaluator，根据检索置信度触发 rewrite、补充检索、decompose-recompose。
- DeepNote: Note-Centric Deep Retrieval-Augmented Generation, Findings of EMNLP 2025。核心价值是 note-centric adaptive retrieval，把多轮检索得到的知识沉淀到 note 中，再由 note 驱动下一轮检索和最终生成。
- RAGChecker / RAGAS / ARES。核心价值是把 RAG 评估拆为 context relevance、faithfulness、answer relevance、retrieval diagnostics 等维度，而不是只看词面重叠。

## 新系统边界

新系统命名为 Portable RAG，不绑定校园知识库。校园数据只是一个 domain profile。

```text
PortableRAG
├── CorpusAdapter          # 文档读取、清洗、结构化切分
├── Chunker                # 固定长度、段落、标题、表格行、父子块
├── IndexStore             # BM25 / TF-IDF / dense / hybrid，可替换
├── QueryProcessor         # 查询改写、分解、HyDE，可选 LLM
├── Retriever              # 多路召回
├── EvidenceEvaluator      # CRAG 式证据置信度、去噪、证据覆盖
├── NoteMemory             # DeepNote 式知识积累，可关闭
├── Reranker               # 交叉编码器或轻量无模型重排
├── AnswerGenerator        # 严格基于证据生成，GLM-4.7-flash 可插拔
├── Verifier               # 引用校验、幻觉检测、拒答判定
└── Evaluator              # RAGEval / TREC-BEIR / RAGChecker-lite
```

## 迁移原则

代码中只允许出现通用机制，不允许出现某个学校、某份文件、某个项目名称的硬编码。

允许的领域信息：

- `domain_profile.yaml`：领域名、文档类型、术语表、同义词、敏感边界、实时信息边界。
- `schema.yaml`：RAGEval 式评测 schema，用于生成或组织 QRA。
- `golden_set.jsonl`：少量人工确认的查询、答案、证据，用于回归测试。

不允许的领域信息：

- 在 Python 代码中写死“澳门大学”“宿舍商业活动”“预答辩”等具体问法。
- 为某个评测问题单独增加检索 boost。
- 让评估逻辑知道某个问题的标准答案形式。

## Pipeline 设计

默认离线 pipeline：

1. Ingest：读取任意 `data_dir`，保留 source、page、heading、table row 等元数据。
2. Chunk：生成 parent chunk 和 child evidence unit。父块用于上下文，子块用于精确召回。
3. Index：同时建立 sparse index 和可选 dense index。本地低算力下 dense 可关闭。
4. Retrieve：BM25 + TF-IDF + optional dense，多路 RRF 融合。
5. Evaluate Evidence：计算 query-evidence relevance、source diversity、answerability confidence。
6. Correct：低置信度时触发 query rewrite / query decomposition / parent expansion。
7. Note：复杂问题启用 note memory，累计支持回答的事实点。
8. Generate：用 GLM-4.7-flash 或 extractive 模式生成答案，必须带 citation。
9. Verify：检查答案是否被证据支持；证据不足时拒答。
10. Evaluate：输出检索指标、生成指标、负例指标和失败样例。

## 评估方案

评估不再只追求一个“正确率”数字，而是拆成四层。

| 层级 | 指标 | 作用 |
|---|---|---|
| 检索层 | Recall@K, nDCG@K, MRR@K, EIR | 判断是否找到足够、干净的证据 |
| 证据层 | context relevance, source diversity, evidence coverage | 判断证据是否支持回答 |
| 生成层 | Completeness, Hallucination, Irrelevance, faithfulness | 判断答案是否完整、忠实、无幻觉 |
| 安全层 | negative rejection, privacy refusal, realtime refusal | 判断是否能拒答不可回答问题 |

在免费 API 限速下，主评估采用：

- retrieval-only：无 LLM，可全量跑；
- strict answer：少量人工/规则复核；
- RAGEval-lite：用 schema 生成或组织测试集；
- LLM judge：只在小样本上使用 GLM-4.7-flash，并加缓存。

## 项目重构步骤

1. 冻结旧 `final_rag`：保留为 `legacy_rule_rag`，只用于对照实验，不再继续加规则。
2. 新增 `portable_rag` 模块：组件接口先行，pipeline 由 YAML 配置组装。
3. 改造语料处理：加入 parent-child chunk、表格行、标题层级、页码/来源元数据。
4. 改造检索：用统一 `Retriever` 接口实现 BM25、TF-IDF、Hybrid、CRAG-corrected、DeepNote-note。
5. 改造生成：生成器只读取证据包，不直接接触原始索引；必须输出 answer、citations、confidence、abstain_reason。
6. 改造评估：引入 domain-independent 的 RAGEval-lite schema、TREC/BEIR qrels、RAGChecker-lite 诊断表。
7. 做迁移测试：除校园知识库外，再构造一个小型公开文档集，验证无需改代码即可运行。

## 毕设写法

论文中应避免写“通过规则优化使准确率达到 90%”。更合理的研究表述是：

- 复现并比较 Naive RAG、Hybrid RAG、CRAG、DeepNote。
- 在低算力、本地运行、免费 API 约束下，提出一个模块化 Portable RAG 系统。
- 参考 RAGEval 构建场景化评估数据，参考 RAGChecker/RAGAS/ARES 拆分诊断指标。
- 通过校园知识库和迁移知识库进行实验，证明系统具备可迁移性，而不是只适配单一数据集。

## 近期可执行目标

- 第一阶段：先完成 Portable RAG 的接口和 YAML 编排，不接入前端。
- 第二阶段：把校园知识库作为一个 domain profile 跑通。
- 第三阶段：构建一个非校园小知识库迁移实验。
- 第四阶段：对两个知识库分别输出检索、生成、安全三类评估报告。

