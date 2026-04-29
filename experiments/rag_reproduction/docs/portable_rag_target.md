# Portable RAG 目标定义

项目目标：构建一个可迁移、高泛化、高准确率、轻量化的 RAG 系统，用于支撑数字人智能问答平台。

## 四个硬约束

1. 可迁移

   更换知识库时，不修改 Python 业务规则。只允许替换：

   - `data_dir`
   - `domain_profile.yaml`
   - `schema.yaml`
   - `golden_set / negative_set`

2. 高泛化

   系统不能依赖固定问题模板。查询理解、召回、证据评估、拒答、生成必须通过通用模块完成。领域术语可配置，但不能写死在代码中。

3. 高准确率

   准确率目标拆成多个可解释指标：

   - 检索层：`Recall@8 >= 0.90`
   - 证据层：`Evidence Support >= 0.85`
   - 生成层：高置信可回答问题 `usable accuracy >= 0.90`
   - 安全层：负例拒答 `negative rejection >= 0.95`

   严格答案完全正确率可以作为保守指标，但不应单独作为系统是否可用的唯一判断。

4. 轻量化

   默认系统必须能在本地 CPU 环境运行：

   - 第一阶段只用 BM25 + TF-IDF + RRF，不依赖 GPU。
   - dense embedding、reranker、LLM judge 都是可选模块。
   - GLM-4.7-flash 只用于低频生成、改写或小样本评测，并必须带缓存。

## 不再采用的路线

- 不继续给 `final_rag.py` 添加具体问题规则。
- 不以固定校园问答集的分数作为唯一目标。
- 不把“命中文档”或“词项覆盖率”伪装成答案正确率。

## 主线实现

新主线位于：

```text
experiments/rag_reproduction/raglab/portable/
```

第一版提供轻量 baseline：

- `BM25Retriever`
- `TfidfRetriever`
- `RRF Fusion`
- `retrieval_confidence`
- `extractive grounded answer`
- `insufficient evidence abstention`

后续在这个骨架上加入：

- CRAG-style corrective retrieval
- DeepNote-style note memory
- configurable domain profile
- RAGEval-lite schema evaluation
- optional GLM-4.7-flash generation and verification

