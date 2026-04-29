# RAG 实验素材

本文件用于写第 6 章“实验与评估”。

## 实验目标

实验目标不是证明系统已经达到 90% 真实准确率，而是回答三个问题：

1. PortableRAGV4 能否在校园知识库上找到相关证据？
2. 找到的证据能否支持可用答案？
3. 系统在哪些环节仍然失败，后续应如何改进？

## 实验对象

| 项 | 内容 |
|---|---|
| RAG 系统 | PortableRAGV4 |
| 知识库 | `experiments/rag_reproduction/data` |
| 正例评测集 | `experiments/rag_reproduction/datasets/dataset.json` |
| 负例评测集 | `experiments/rag_reproduction/datasets/negative_questions.json` |
| 主配置 | `experiments/rag_reproduction/configs/portable_rag.yaml` |
| 训练 | 不训练 |
| LLM judge | 全量评估不使用 |

## 数据规模

平台最终验收状态：

| 指标 | 数值 |
|---|---:|
| 知识库文件数 | 74 |
| 知识库大小 | 35.01 MB |
| RAG documents | 74 |
| evidence units | 32635 |
| 正例问题 | 1264 |
| 负例问题 | 60 |
| 总评估问题 | 1324 |

## 实验方法

PortableRAGV4 采用无训练、无固定问题规则的本地算法：

- 文档结构化和 parent-child evidence unit。
- BM25、TF-IDF、字符 n-gram 多路检索。
- RRF 融合多路召回。
- source-level retrieval 和 source-neighbor expansion。
- 基于 IDF、查询覆盖和信息密度的 evidence scoring。
- MMR 控制冗余。
- 统计置信度和证据支持度判断回答或拒答。

## 运行命令

全量评估：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4-eval --output-name portable_rag_v4_answer_evidence_full
```

答案级 CSV 标注：

```powershell
.\scripts\run_rag_reproduction.ps1 annotate-csv `
  --input experiments/rag_reproduction/results/portable_rag/portable_rag_v4_answer_evidence_full_details.csv `
  --output-prefix experiments/rag_reproduction/annotations/portable_rag_v4_full_annotation
```

## 检索与证据代理指标

来源：

```text
experiments/rag_reproduction/results/portable_rag/portable_rag_v4_answer_evidence_full_report.md
```

| 指标 | 数值 | 解释 |
|---|---:|---|
| answered_rate | 0.957278 | 系统给出答案的比例 |
| source_hit_at_k | 0.877373 | Top-K 来源命中率 |
| usable_proxy_rate | 0.892405 | 轻量代理可用率，不等于真实准确率 |
| answer_term_recall | 0.788160 | 回答词项覆盖 |
| evidence_term_recall | 0.871571 | 证据词项覆盖 |
| number_recall | 0.698288 | 数字信息召回 |
| phone_recall | 0.500000 | 电话信息召回 |
| negative_rejection_accuracy | 0.266667 | 负例直接拒答率 |
| negative_handled_accuracy | 0.400000 | 负例安全处理率 |
| avg_latency_ms | 6857.498513 | 平均延迟 |

可写结论：

- `source_hit_at_k` 和 `evidence_term_recall` 较高，说明系统多数情况下能找到相关来源和证据。
- `number_recall` 和 `phone_recall` 明显低于整体证据召回，说明数字/电话等精确事实仍是薄弱点。
- 负例拒答能力不足，是后续改进重点。
- `usable_proxy_rate` 接近 0.89，但它只是代理指标，不能写成真实准确率。

## 答案级严格标注指标

来源：

```text
experiments/rag_reproduction/annotations/portable_rag_v4_full_annotation_report.md
```

| 指标 | 数值 | 解释 |
|---|---:|---|
| total_count | 1324 | 总问题数 |
| positive_count | 1264 | 正例问题数 |
| negative_count | 60 | 负例问题数 |
| positive_strict_accuracy | 0.560127 | 正例严格正确率 |
| positive_usable_accuracy | 0.731804 | 正例可用答案率 |
| positive_partial_rate | 0.133703 | 正例部分正确率 |
| negative_accuracy | 0.400000 | 负例处理准确率 |
| overall_strict_accuracy | 0.552870 | 整体严格准确率 |
| overall_usable_accuracy | 0.716767 | 整体可用率 |
| overall_weighted_score | 0.739610 | 加权得分 |

标签分布：

| 标签 | 数量 | 说明 |
|---|---:|---|
| complete_correct | 708 | 完整正确 |
| usable_but_noisy | 143 | 基本可用但噪声较多 |
| unsupported_correct_content | 74 | 内容接近正确但来源未充分命中 |
| partial_correct | 169 | 部分正确 |
| incorrect | 104 | 错误 |
| incorrect_refusal | 66 | 正例误拒答 |
| correct_rejection | 16 | 负例正确拒答 |
| safe_rejection | 8 | 负例安全拒答 |
| false_answer | 36 | 负例错误回答 |

可写结论：

- 严格正确率低于代理指标，证明只看检索命中或词项覆盖会高估系统。
- 可用答案率约为 0.73，说明系统在许多问题上能提供有帮助的内容，但还未达到“上线级稳定准确”。
- 负例中 `false_answer` 数量较高，说明不可答检测和拒答策略需要改进。
- `incorrect_refusal` 表明系统有时过于保守，拒答阈值仍需平衡。

## 结果分析段落

可直接写入论文：

> 从检索与证据代理指标看，PortableRAGV4 在校园知识库上能够取得较高的来源命中率和证据词项覆盖率，说明多路稀疏检索、RRF 融合、相邻证据扩展和 MMR 选择对证据召回具有积极作用。然而，答案级严格标注结果明显低于代理指标，表明检索到相关文档并不等价于生成完整正确答案。特别是在负例拒答、电话和数字等精确事实抽取方面，系统仍存在明显不足。因此，本文没有将代理指标等同于真实准确率，而是采用分层评估方式分析 RAG 系统的真实能力边界。

## 失败原因归纳

| 失败类型 | 可能原因 | 后续改进方向 |
|---|---|---|
| 正例误拒答 | confidence 阈值偏保守，证据分散 | 改进多证据聚合和段落级支持度 |
| 部分正确 | 答案跨多个段落或表格，span selection 不完整 | 加强结构化解析和多 span 合成 |
| 数字/电话漏召回 | 数字 token 化和表格抽取不足 | 针对通用数字模式做结构解析，不写具体问题规则 |
| 负例错误回答 | 不可答检测弱，缺少边界判断 | 增强通用拒答、实时信息边界、隐私边界 |
| 来源未命中但内容接近 | 标注来源与实际证据来源不完全一致 | 增加多来源证据对齐和人工复核 |

## 论文中应避免的写法

不要写：

```text
本系统问答准确率达到 90%。
```

可以写：

```text
系统在检索与证据代理指标上表现较好，其中 usable_proxy_rate 为 0.892405，但严格答案级标注显示 positive_usable_accuracy 为 0.731804，说明系统仍需在答案完整性和负例拒答方面继续优化。
```

