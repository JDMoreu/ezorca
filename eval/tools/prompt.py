#!/usr/bin/env python3
"""Emite el reto público de un escenario, sin su fixture esperado."""
from __future__ import annotations
import json, sys
from pathlib import Path

CASES = Path(__file__).with_name("cases.json")
def main(argv: list[str] | None = None) -> int:
    if not argv or len(argv) != 1:
        print("uso: prompt.py ID", file=sys.stderr); return 2
    try:
        case = next(c for c in json.loads(CASES.read_text(encoding="utf-8")) if c["id"] == argv[0])
    except (StopIteration, OSError, ValueError, KeyError):
        print(json.dumps({"error": "escenario desconocido"}), file=sys.stdout); return 2
    result = {"id": case["id"], "title": case["title"], "prompt": case["prompt"],
              "response_schema": {"argv": "array de textos", "files": "objeto opcional solo para wave/spec"}}
    print(json.dumps(result, ensure_ascii=False)); return 0
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
