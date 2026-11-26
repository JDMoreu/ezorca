#!/usr/bin/env python3
"""Decide si la skill se cargó en corridas de `claude -p --output-format stream-json`.

Los archivos de salida se llaman `<id del caso>__<modelo>.jsonl`. Una corrida carga la
skill si hay un tool_use `Skill` con skill igual a la buscada, o un `Read` de `.../<skill>/SKILL.md`.
Criterio: nivel `favor` debe cargarla, `contra` no, `neutro` solo se informa.
Salida: un JSON por corrida y un resumen. Exit 0 si se cumple, 1 si no, 2 si la entrada es inválida.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class InvalidInput(Exception):
    """La entrada no se puede interpretar."""


def parse_events(text: str, name: str) -> list[dict[str, Any]]:
    """Lee una línea JSON por evento, ignorando líneas vacías."""
    events = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise InvalidInput(f"{name}: línea {number} no es JSON ({error.msg})") from error
        if not isinstance(event, dict):
            raise InvalidInput(f"{name}: línea {number} no es un objeto")
        events.append(event)
    if not events:
        raise InvalidInput(f"{name}: sin eventos")
    return events


def tool_uses(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Devuelve los bloques tool_use de los mensajes del asistente."""
    found = []
    for event in events:
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if event.get("type") != "assistant" or not isinstance(content, list):
            continue
        found += [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
    return found


def load_via(events: list[dict[str, Any]], skill: str) -> str | None:
    """Indica cómo se cargó la skill ('Skill' o 'Read') o None si no se cargó."""
    for block in tool_uses(events):
        data = block.get("input") if isinstance(block.get("input"), dict) else {}
        if block.get("name") == "Skill" and data.get("skill") == skill:
            return "Skill"
        path = str(data.get("file_path", "")).replace("\\", "/")
        if block.get("name") == "Read" and path.endswith(f"/{skill}/SKILL.md"):
            return "Read"
    return None


def verdict(level: str, loaded: bool) -> bool | None:
    """Cumple el criterio del nivel; None si el nivel solo se informa."""
    return {"favor": loaded, "contra": not loaded}.get(level)


def evaluate(cases: dict[str, Any], results: Path) -> dict[str, Any]:
    """Evalúa todas las corridas de la carpeta contra los casos."""
    skill = cases.get("skill")
    if not isinstance(skill, str) or not isinstance(cases.get("cases"), list):
        raise InvalidInput("cases.json necesita 'skill' y 'cases'")
    if not results.is_dir():
        raise InvalidInput(f"no existe la carpeta de resultados {results}")
    runs = []
    for case in cases["cases"]:
        if not isinstance(case, dict) or not {"id", "level"} <= case.keys():
            raise InvalidInput("cada caso necesita 'id' y 'level'")
        files = sorted(results.glob(f"{case['id']}__*.jsonl"))
        if not files:
            raise InvalidInput(f"faltan corridas del caso {case['id']}")
        for path in files:
            events = parse_events(path.read_text(encoding="utf-8"), path.name)
            via = load_via(events, skill)
            model = path.stem.split("__", 1)[1]
            runs.append({"case": case["id"], "level": case["level"], "model": model,
                         "loaded": via is not None, "via": via,
                         "ok": verdict(case["level"], via is not None)})
    summary: dict[str, Any] = {}
    for level in ("favor", "neutro", "contra"):
        subset = [r for r in runs if r["level"] == level]
        summary[level] = {"runs": len(subset), "loaded": sum(r["loaded"] for r in subset)}
    return {"runs": runs, "summary": summary, "ok": all(r["ok"] is not False for r in runs)}


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: imprime un JSON por corrida y un resumen."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("cases.json"))
    parser.add_argument("--results", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        cases = json.loads(args.cases.read_text(encoding="utf-8"))
        report = evaluate(cases, args.results)
    except (InvalidInput, OSError, ValueError) as error:
        sys.stderr.write(f"entrada inválida: {error}\n")
        return 2
    for run in report["runs"]:
        print(json.dumps(run, ensure_ascii=False))
    print(json.dumps({"summary": report["summary"], "ok": report["ok"]}, ensure_ascii=False))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
