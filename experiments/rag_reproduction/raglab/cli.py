from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="AIRI RAG v4 reproduction utilities.")
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("portable-v4", help="Run Portable RAG v4 on one question.")
    ask.add_argument("--question", required=True)
    ask.add_argument("--top-k", type=int, default=None)
    ask.add_argument("--portable-config", default=None, help="Path to portable_rag.yaml")
    ask.add_argument("--mode", choices=["answer", "retrieve"], default="answer")

    evaluate = sub.add_parser("portable-v4-eval", help="Evaluate Portable RAG v4.")
    evaluate.add_argument("--portable-config", default=None, help="Path to portable_rag.yaml")
    evaluate.add_argument("--top-k", type=int, default=None)
    evaluate.add_argument("--limit", type=int, default=None)
    evaluate.add_argument("--offset", type=int, default=0)
    evaluate.add_argument("--negative-size", type=int, default=None)
    evaluate.add_argument("--output-name", default="portable_rag_v4")

    annotate = sub.add_parser("annotate-csv", help="Annotate an existing v4 evaluation CSV without LLM calls.")
    annotate.add_argument("--input", required=True)
    annotate.add_argument("--output-prefix", required=True)

    args = parser.parse_args()

    if args.command == "portable-v4":
        from .portable import PortableRAGV4

        system = PortableRAGV4.from_config(args.portable_config)
        if args.mode == "retrieve":
            hits, trace = system.retrieve(args.question, top_k=args.top_k)
            payload = {
                "question": args.question,
                "trace": trace,
                "hits": [hit.to_dict() for hit in hits],
            }
        else:
            payload = system.answer(args.question, top_k=args.top_k).to_dict()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if args.command == "portable-v4-eval":
        from .portable.config import load_portable_config
        from .portable.eval_v4 import evaluate_portable_rag_v4

        config = load_portable_config(args.portable_config)
        evaluate_portable_rag_v4(
            config,
            top_k=args.top_k,
            limit=args.limit,
            offset=args.offset,
            negative_size=args.negative_size,
            output_name=args.output_name,
        )
        return

    if args.command == "annotate-csv":
        from .eval.annotate_csv import main as annotate_main

        # Reuse the standalone script implementation without duplicating its logic.
        import sys

        sys.argv = [
            "annotate_csv",
            "--input",
            str(Path(args.input)),
            "--output-prefix",
            str(Path(args.output_prefix)),
        ]
        annotate_main()


if __name__ == "__main__":
    main()
