"""BookXray CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import export, validate, write_report
from .core import prepare
from .agent import ChatModel, run
from .evaluation import evaluate
import os

PROFILES = ["auto", "textbook", "technical", "academic", "literature", "history", "business"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bookxray", description="Evidence-first Agent Skill")
    sub = parser.add_subparsers(dest="action", required=True)
    command = sub.add_parser("prepare")
    command.add_argument("source", type=Path)
    command.add_argument("--output", type=Path, required=True)
    command.add_argument("--profile", choices=PROFILES, default="auto")
    command.add_argument("--max-chars", type=int, default=2800)
    command.add_argument("--pdf-backend", choices=["auto", "docling", "pymupdf"], default="auto")
    for action in ("audit", "export"):
        sub.add_parser(action).add_argument("project", type=Path)

    analyze = sub.add_parser("analyze", help="Generate units with model and independent reviewer; network opt-in")
    analyze.add_argument("project", type=Path)
    analyze.add_argument("--endpoint", default="https://api.openai.com/v1")
    analyze.add_argument("--model", required=True)
    analyze.add_argument("--review-model", required=True)
    analyze.add_argument("--max-repairs", type=int, default=2)
    analyze.add_argument("--allow-same-model", action="store_true")
    analyze.add_argument("--allow-remote", action="store_true", help="Explicit consent to send book excerpts to the configured endpoint")
    assess = sub.add_parser("evaluate", help="Score against an independently annotated gold inventory")
    assess.add_argument("project", type=Path)
    assess.add_argument("--gold", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "prepare":
            result = prepare(args.source, args.output, args.profile, args.max_chars, args.pdf_backend)
            print(json.dumps({
                "status": result["status"], "sections": len(result["sections"]),
                "packets": result["chunk_count"], "warnings": result["warnings"],
            }, ensure_ascii=False, indent=2))
        elif args.action == "audit":
            result = validate(args.project)
            write_report(args.project, result)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["status"] == "pass" else 2

        elif args.action == "analyze":
            if not args.allow_remote:
                raise ValueError("Explicit --allow-remote consent is required for model requests, including localhost")
            key = os.environ.get("BOOKXRAY_API_KEY", "")
            if not key:
                raise ValueError("Set BOOKXRAY_API_KEY (do not put secrets in CLI arguments)")
            generator = ChatModel(args.endpoint,args.model,key)
            reviewer = ChatModel(args.endpoint,args.review_model,key)
            result = run(args.project,generator,reviewer,generator_id=args.model,
                reviewer_id=args.review_model,max_repairs=args.max_repairs,
                allow_same_model=args.allow_same_model)
            print(json.dumps(result,ensure_ascii=False,indent=2))
            return 0 if result["status"] == "pass" else 2
        elif args.action == "evaluate":
            print(json.dumps(evaluate(args.project,args.gold),ensure_ascii=False,indent=2))
        elif args.action == "export":
            print(export(args.project))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"BookXray error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
