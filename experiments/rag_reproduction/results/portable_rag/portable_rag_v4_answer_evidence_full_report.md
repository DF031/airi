# Portable RAG Baseline Evaluation

This report evaluates the domain-portable baseline. It intentionally avoids domain-specific Python rules.

- Top-K: 8
- Details JSONL: `C:\duan\home\BS\airi\experiments\rag_reproduction\results\portable_rag\portable_rag_v4_answer_evidence_full_details.jsonl`
- Details CSV: `C:\duan\home\BS\airi\experiments\rag_reproduction\results\portable_rag\portable_rag_v4_answer_evidence_full_details.csv`

| Metric | Value |
|---|---:|
| positive_count | 1264 |
| negative_count | 60 |
| answered_rate | 0.957278 |
| source_hit_at_k | 0.877373 |
| usable_proxy_rate | 0.892405 |
| answer_term_recall | 0.78816 |
| evidence_term_recall | 0.871571 |
| number_recall | 0.698288 |
| phone_recall | 0.5 |
| negative_rejection_accuracy | 0.266667 |
| negative_handled_accuracy | 0.4 |
| avg_latency_ms | 6857.498513 |

Note: `usable_proxy_rate` is a lightweight diagnostic proxy, not a final human strict accuracy score.
