# RAG 系统与评估

## 研究目标

本项目 RAG 主线不是继续针对固定校园问答集写规则，而是构建一个可迁移、高泛化、轻量、无训练的 RAG 系统。校园知识库只是当前 domain profile，理论上替换语料和配置后可以迁移到其他文档库。

主线实现位于：

```text
experiments/rag_reproduction/raglab/portable/
```

平台接入适配器位于：

```text
backend/rag/retrievers/portable_v4.py
```

## 数据目录

| 路径 | 说明 |
|---|---|
| `experiments/rag_reproduction/data` | 知识库语料，平台实际使用 |
| `experiments/rag_reproduction/datasets/dataset.json` | 正例问答评测集 |
| `experiments/rag_reproduction/datasets/negative_questions.json` | 负例/不可答问题集 |
| `experiments/rag_reproduction/configs/portable_rag.yaml` | Portable RAG v4 主配置 |
| `experiments/rag_reproduction/configs/domain_profile.campus.yaml` | 校园领域 profile |
| `experiments/rag_reproduction/results/portable_rag` | 实验结果 |
| `experiments/rag_reproduction/annotations` | CSV 答案级标注评估 |

## PortableRAGV4 算法组成

PortableRAGV4 采用训练-free、规则-free 的本地算法路线：

- 文档结构化：保留 source、heading、page/table 等元信息。
- Parent-child chunk：父块保留上下文，子证据单元用于精确召回。
- 多路稀疏检索：BM25、TF-IDF、字符 n-gram TF-IDF。
- RRF 融合：融合多路召回结果，减少单一检索器偏差。
- Source-level retrieval：先定位高相关文档源，再在源内扩展证据。
- Source neighbor expansion：保留相邻证据窗口，缓解答案跨段落问题。
- Evidence scoring：基于查询覆盖、IDF、信息密度和来源得分进行证据评分。
- MMR evidence selection：控制重复证据，提高多样性。
- Statistical confidence：用统计支持度决定回答或拒答。
- Extractive grounded answer：优先从证据中抽取答案片段，保证可引用。

配置中保留了 CRAG-lite、DeepNote-lite、LLM rewrite 等概念接口，但当前主评估强调无训练、少 API、可本地复现，因此完整实验主要使用离线统计和证据评估。

## 与论文/开源思想的对应

| 参考方向 | 本项目落地方式 |
|---|---|
| Naive RAG | 作为早期 baseline 和对照 |
| Hybrid RAG | BM25 + TF-IDF + RRF 多路召回 |
| CRAG | 以 retrieval confidence / evidence confidence 控制拒答和扩展 |
| DeepNote | 以 note memory 思想保留复杂问题多步证据组织的扩展接口 |
| RAGEval | 强调场景化数据和分层评估，而不是只看单一准确率 |
| RAGChecker / RAGAS / ARES | 将评估拆成检索、证据、答案忠实性和安全拒答 |

## 运行单问题

回答模式：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4 --question "学籍证明在哪里办理？" --mode answer
```

仅检索证据：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4 --question "学籍证明在哪里办理？" --mode retrieve
```

## 重新评估

小样本 smoke test：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4-eval --limit 20 --negative-size 10 --output-name portable_rag_v4_smoke
```

全量评估：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4-eval --output-name portable_rag_v4_answer_evidence_full
```

对 CSV 做无 LLM 答案级标注：

```powershell
.\scripts\run_rag_reproduction.ps1 annotate-csv `
  --input experiments/rag_reproduction/results/portable_rag/portable_rag_v4_answer_evidence_full_details.csv `
  --output-prefix experiments/rag_reproduction/annotations/portable_rag_v4_full_annotation
```

## 当前评估结果

### 检索与证据代理指标

来源：

```text
experiments/rag_reproduction/results/portable_rag/portable_rag_v4_answer_evidence_full_report.md
```

| 指标 | 数值 |
|---|---:|
| positive_count | 1264 |
| negative_count | 60 |
| answered_rate | 0.957278 |
| source_hit_at_k | 0.877373 |
| usable_proxy_rate | 0.892405 |
| answer_term_recall | 0.788160 |
| evidence_term_recall | 0.871571 |
| number_recall | 0.698288 |
| phone_recall | 0.500000 |
| negative_rejection_accuracy | 0.266667 |
| negative_handled_accuracy | 0.400000 |
| avg_latency_ms | 6857.498513 |

`usable_proxy_rate` 是诊断指标，不等同于真实答案正确率。

### 答案级严格标注指标

来源：

```text
experiments/rag_reproduction/annotations/portable_rag_v4_full_annotation_report.md
```

| 指标 | 数值 |
|---|---:|
| total_count | 1324 |
| positive_count | 1264 |
| negative_count | 60 |
| positive_strict_accuracy | 0.560127 |
| positive_usable_accuracy | 0.731804 |
| positive_partial_rate | 0.133703 |
| negative_accuracy | 0.400000 |
| overall_strict_accuracy | 0.552870 |
| overall_usable_accuracy | 0.716767 |
| overall_weighted_score | 0.739610 |

这个结果更适合写入论文，因为它承认了代理指标和真实答案可用性之间的差距。最终平台使用时会再经过 GLM 生成润色，因此用户体验可能好于纯 extractive 离线评估，但论文中应区分“RAG 检索能力”“离线抽取答案能力”和“平台端生成回答能力”。

## 当前不足

- 负例拒答能力仍弱，后续可以从通用不可答检测、实时信息边界、隐私边界入手，而不是写具体问题规则。
- 电话、数字、日期类事实仍容易缺失，需要更强的表格和编号结构解析。
- 离线答案抽取偏保守或偏长，需要在不训练、不规则化的前提下继续改进 span selection。
- LLM 生成评估受免费 API 限速影响，没有作为全量主评估。

## 论文建议表述

建议写法：

> 本文构建了一个无训练、轻量化、可迁移的 Portable RAG v4 系统。系统在校园知识库上实现了较高的检索命中和证据覆盖，但在严格答案级标注下仍暴露出负例拒答和精确事实抽取不足的问题。该结果说明，仅以检索命中或词项覆盖衡量 RAG 质量是不充分的，因此本文进一步采用分层评估方法分析系统瓶颈。

避免写法：

> 系统准确率达到 90%。

除非后续有人工严格标注或 LLM judge 多模型复核支撑，否则不要把 `usable_proxy_rate` 当作真实准确率。

