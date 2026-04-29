# 论文材料目录

本目录用于整理毕业设计论文写作材料，和工程运行文档 `docs/` 分开管理。

论文题目：

```text
融合大模型技术的数字人智能问答平台设计与研究
```

## 阅读顺序

1. [题目、摘要与关键词](01_title_abstract_keywords.md)
2. [论文详细大纲](02_chapter_outline.md)
3. [相关工作矩阵](03_related_work_matrix.md)
4. [系统设计素材](04_system_design_materials.md)
5. [RAG 实验素材](05_rag_experiment_materials.md)
6. [数字人实现素材](06_digital_human_materials.md)
7. [图表清单](07_figures_and_tables.md)
8. [答辩材料](08_defense_materials.md)
9. [写作规范与检查清单](09_writing_requirements_and_checklist.md)
10. [BibTeX 参考文献](references.bib)

## 使用建议

- 写论文时先从 [论文详细大纲](02_chapter_outline.md) 搭骨架。
- 写相关工作时从 [相关工作矩阵](03_related_work_matrix.md) 提炼段落。
- 写实验章时优先使用 [RAG 实验素材](05_rag_experiment_materials.md) 中的严格标注指标，不要把代理指标写成真实准确率。
- 做答辩 PPT 时优先使用 [图表清单](07_figures_and_tables.md) 和 [答辩材料](08_defense_materials.md)。

## 当前论文主张

本文不主张“系统已经达到 90% 真实问答准确率”。更稳妥、也更符合实验结果的主张是：

> 在低算力本地运行和免费 API 限速约束下，本文设计并实现了一个融合大模型、可迁移 RAG、TTS 与 Live2D 数字人的智能问答平台。系统实现了从用户提问、知识检索、证据增强生成、来源展示、语音播报到数字人口型动作同步的完整闭环，并通过分层评估揭示了 RAG 系统在检索、证据、答案和拒答环节的能力与不足。

