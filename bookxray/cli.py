"""BookXray CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit import export, validate, write_report
from .core import prepare

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
        elif args.action == "export":
            print(export(args.project))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"BookXray error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
