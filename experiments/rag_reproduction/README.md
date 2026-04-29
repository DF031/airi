# AIRI RAG v4 Reproduction Area

本目录保留毕业设计中最终采用的 RAG 研究材料：可迁移、无训练、轻量化的 Portable RAG v4。早期 v2/v3、Final RAG、CRAG/DeepNote 本地试验和旧索引已经清理，不再作为主线实验材料。

## 保留内容

- `data/`: 校园知识库原始语料。
- `datasets/`: 配套问答评测集与负例集。
- `configs/portable_rag.yaml`: v4 主配置。
- `configs/domain_profile.campus.yaml`: 校园领域 profile。
- `raglab/portable/v4.py`: 最终 RAG 算法实现。
- `raglab/portable/eval_v4.py`: v4 全量评估入口。
- `raglab/eval/annotate_csv.py`: 不调用 LLM 的 CSV 答案级标注评估。
- `indexes/portable_rag/`: v4 结构化证据单元与本地语义向量缓存，平台运行会直接复用。
- `results/portable_rag/`: v4 最终评估摘要、报告和分析。
- `annotations/`: v4 最终答案级标注摘要和报告。

## 运行单问题

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4 --question "学籍证明在哪里办理？" --mode answer
```

只查看检索证据：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4 --question "学籍证明在哪里办理？" --mode retrieve
```

## 重新评估

小样本快速检查：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4-eval --limit 20 --negative-size 10 --output-name portable_rag_v4_smoke
```

全量评估：

```powershell
.\scripts\run_rag_reproduction.ps1 portable-v4-eval --output-name portable_rag_v4_answer_evidence_full
```

对生成的 CSV 做无 LLM 标注评估：

```powershell
.\scripts\run_rag_reproduction.ps1 annotate-csv `
  --input experiments/rag_reproduction/results/portable_rag/portable_rag_v4_answer_evidence_full_details.csv `
  --output-prefix experiments/rag_reproduction/annotations/portable_rag_v4_full_annotation
```

## 当前最终结果

最终实验保留两类结果：

- 检索与证据指标：`results/portable_rag/portable_rag_v4_answer_evidence_full_report.md`
- 答案级标注指标：`annotations/portable_rag_v4_full_annotation_report.md`

需要注意：`usable_proxy_rate` 只是诊断性代理指标，不等价于真实答案正确率。论文中应优先引用答案级标注评估，并说明它不调用 LLM/API。

## 平台接入

平台后端已经通过 `RAG_STRATEGY=portable_v4` 接入本目录中的 v4 系统，并使用 `data/` 作为校园知识库。相关平台适配器位于：

```text
backend/rag/retrievers/portable_v4.py
```
