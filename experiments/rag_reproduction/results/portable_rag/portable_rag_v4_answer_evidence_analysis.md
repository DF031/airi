# Portable RAG v4 Answer Evidence Evaluation

## Scope

This run evaluates a training-free and domain-rule-free RAG variant. The system does not use LLM calls, supervised training, fixed question templates, or domain-specific answer rules.

Implemented algorithmic changes:

- Broadened reader candidate pool with semantic retrieval candidates and reranked retrieval candidates.
- Added source-local neighbor expansion so answer extraction can see adjacent evidence windows.
- Added coverage-oriented span selection to prefer marginal query-term coverage over redundant snippets.
- Added generic information-density scoring for fact-rich evidence.
- Added local BGE span reranking for the top extractive answer candidates.
- Returned the actual answer evidence pack first, so answer text, citations, and evaluation evidence are aligned.

## Evaluation Results

### Head 20 Positive + 20 Negative

Output prefix: `portable_rag_v4_answer_evidence_head20`

| Metric | Value |
|---|---:|
| positive_count | 20 |
| negative_count | 20 |
| answered_rate | 1.000000 |
| source_hit_at_k | 0.100000 |
| usable_proxy_rate | 1.000000 |
| answer_term_recall | 0.888401 |
| evidence_term_recall | 0.903974 |
| number_recall | 0.888889 |
| negative_rejection_accuracy | 0.300000 |
| negative_handled_accuracy | 0.400000 |
| avg_latency_ms | 6151.532425 |

### Offset 100, 80 Positive + 20 Negative

Output prefix: `portable_rag_v4_answer_evidence_offset100_80`

| Metric | Value |
|---|---:|
| positive_count | 80 |
| negative_count | 20 |
| answered_rate | 0.962500 |
| source_hit_at_k | 0.937500 |
| usable_proxy_rate | 0.925000 |
| answer_term_recall | 0.771952 |
| evidence_term_recall | 0.872213 |
| number_recall | 0.933333 |
| phone_recall | 0.000000 |
| negative_rejection_accuracy | 0.300000 |
| negative_handled_accuracy | 0.400000 |
| avg_latency_ms | 5446.210340 |

### Full Evaluation, 1264 Positive + 60 Negative

Output prefix: `portable_rag_v4_answer_evidence_full`

| Metric | Value |
|---|---:|
| positive_count | 1264 |
| negative_count | 60 |
| answered_rate | 0.957278 |
| source_hit_at_k | 0.877373 |
| usable_proxy_rate | 0.892405 |
| answer_term_recall | 0.788160 |
| answer_term_f1 | 0.116586 |
| evidence_term_recall | 0.871571 |
| number_recall | 0.698288 |
| phone_recall | 0.500000 |
| negative_rejection_accuracy | 0.266667 |
| negative_handled_accuracy | 0.400000 |
| avg_latency_ms | 6857.498513 |

Positive usable cases: 1128 / 1264.
Positive failed cases: 136 / 1264.
Negative handled cases: 24 / 60.
Negative failed cases: 36 / 60.

Positive failure status distribution:

| Status | Count |
|---|---:|
| answered | 82 |
| insufficient_evidence | 54 |

Positive failure source-hit distribution:

| source_hit | Count |
|---|---:|
| True | 101 |
| False | 35 |

Top positive failure categories:

| Category | Count |
|---|---:|
| 学术政策-科研与项目管理 | 20 |
| 行政管理-教学管理 | 18 |
| 学术政策-其他 | 17 |
| 行政管理-校规校纪 | 16 |
| 行政管理-学籍管理 | 8 |
| 校园生活-安全与健康 | 5 |
| 校园生活-校园活动 | 5 |
| 校内资源-学习资源管理 | 5 |
| 行政管理-职业与就业 | 4 |
| 行政管理-校外活动与校企合作 | 4 |

Top negative failure categories:

| Category | Count |
|---|---:|
| realtime_status | 4 |
| personal_private | 4 |
| future_policy | 4 |
| out_of_scope | 3 |
| personal_private_contact | 3 |
| false_premise | 2 |
| future_false_premise | 2 |
| personal_private_realtime | 2 |
| out_of_scope_service | 2 |

## CSV Annotation Evaluation

The full CSV was additionally annotated at answer level. This annotation is stricter than `usable_proxy`: document hit and evidence term coverage are not directly counted as final answer correctness. It does not call LLM/API.

Output prefix: `experiments/rag_reproduction/annotations/portable_rag_v4_full_annotation`

| Metric | Value |
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
| overall_weighted_score | 0.739615 |
| review_queue_count | 592 |
| review_queue_rate | 0.447130 |

Positive label distribution:

| Label | Count |
|---|---:|
| complete_correct | 708 |
| usable_but_noisy | 143 |
| unsupported_correct_content | 74 |
| partial_correct | 169 |
| incorrect | 104 |
| incorrect_refusal | 66 |

Negative label distribution:

| Label | Count |
|---|---:|
| correct_rejection | 16 |
| safe_rejection | 8 |
| false_answer | 36 |

The annotation result confirms that the earlier 89.24% `usable_proxy_rate` is optimistic. Once answers are judged as user-facing answers, only 56.01% of positive samples are complete and clean enough to count as strict correct. If noisy but basically usable answers and unsupported correct-content answers are included, positive usable accuracy is 73.18%.

## Interpretation

The positive usable proxy reaches the 90% target on the offset evaluation set, but the full evaluation is stricter and drops to 89.24%. The current system is therefore close to the target but does not yet satisfy the 90% target on the complete pool. It needs about 10 additional positive questions to pass the 90% line.

The retrieval and evidence side is already relatively strong: full-set source_hit_at_k is 87.74% and evidence_term_recall is 87.16%. Among the 136 positive failures, 101 still hit the reference source, which means many failures are not pure retrieval misses. The main bottleneck is answer extraction and abstention calibration: 82 failures still return an answer but miss too much reference content, while 54 failures abstain even when partial evidence is present.

The negative set remains weak under the current constraints. Questions about privacy, real-time status, future policy, prediction, false premises, and out-of-scope institutions require a boundary/OOD mechanism, an LLM verifier, or trained/calibrated intent detection. Those are intentionally not added in this run because the current requirement forbids rules and training.

## Remaining Risks

- Some positive answers are long and contain extra neighboring evidence.
- Latency increased because BGE span reranking runs locally on CPU.
- Negative rejection is not production-ready without an explicit boundary/OOD mechanism.
- Phone and exact-number answers remain fragile.
- A full human strict-accuracy evaluation is still needed before claiming real 90% answer accuracy.
