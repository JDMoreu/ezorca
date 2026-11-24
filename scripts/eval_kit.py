#!/usr/bin/env python3
"""Evaluación ciega de variantes: ensayos, pares de jueces y unión de juicios."""

from __future__ import annotations

import argparse
import json
import random
import secrets
import sys
from pathlib import Path
from typing import Any

Record = dict[str, Any]


def dump(value: Any) -> None:
    """Imprime un JSON de una línea por stdout."""
    json.dump(value, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")


def fail(message: str) -> int:
    """Informa el error como JSON y por stderr y devuelve el código de uso inválido."""
    dump({"error": message})
    sys.stderr.write(message + "\n")
    return 2


def read_cases(directory: Path) -> tuple[int, list[Record]]:
    """Lee y valida cases.json; devuelve repeticiones y casos."""
    record = json.loads((directory / "cases.json").read_text(encoding="utf-8-sig"))
    repeats = record.get("repeats") if isinstance(record, dict) else None
    cases = record.get("cases") if isinstance(record, dict) else None
    if type(repeats) is not int or repeats < 1 or not isinstance(cases, list) or not cases:
        raise ValueError("cases.json necesita repeats entero positivo y cases no vacío")
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get("id"), str):
            raise ValueError("cada caso necesita un id de texto")
        if not isinstance(case.get("prompt"), str):
            raise ValueError(f"el caso {case['id']} necesita un prompt de texto")
    return repeats, cases


def read_map(directory: Path) -> dict[str, Record]:
    """Lee el mapa de ensayos; si no existe, devuelve un mapa vacío."""
    path = directory / "trials" / "map.json"
    value = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError("map.json debe contener un objeto")
    return value


def render(template: str, values: dict[str, str]) -> str:
    """Sustituye las marcas {{CLAVE}} de la plantilla."""
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def cmd_exec(args: argparse.Namespace) -> int:
    """Crea un ensayo por caso y repetición, con nombres opacos."""
    try:
        if len(args.label) < 2 or args.label in "t":
            raise ValueError("etiqueta demasiado corta")
        repeats, cases = read_cases(args.dir)
        template = args.template.read_text(encoding="utf-8")
        mapping = read_map(args.dir)
        unknown = set(args.cases) - {case["id"] for case in cases}
        if unknown:
            raise ValueError(f"casos desconocidos: {', '.join(sorted(unknown))}")
        selected = [case for case in cases if not args.cases or case["id"] in args.cases]
        tids = []
        for case in selected:
            for repeat in range(1, repeats + 1):
                tid = "t" + secrets.token_hex(4)
                out = args.dir / "trials" / f"{tid}.md"
                spec = args.dir / "specs" / f"exec-{tid}.md"
                spec.parent.mkdir(parents=True, exist_ok=True)
                values = {"VARIANT": str(args.variant_dir), "OUT": str(out)}
                spec.write_text(render(template, values | {"PROMPT": case["prompt"]}), "utf-8")
                mapping[tid] = {"variant": args.label, "case": case["id"], "repeat": repeat}
                tids.append(tid)
        path = args.dir / "trials" / "map.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    except (OSError, ValueError) as error:
        return fail(str(error))
    dump({"tids": tids})
    return 0


def cmd_pair(args: argparse.Namespace) -> int:
    """Escribe una spec de juez ciega con dos planes del mismo caso en orden aleatorio."""
    try:
        mapping = read_map(args.dir)
        for tid in (args.a, args.b):
            if tid not in mapping:
                raise ValueError(f"tid desconocido: {tid}")
        if mapping[args.a].get("case") != mapping[args.b].get("case"):
            raise ValueError("los tids pertenecen a casos distintos")
        _, cases = read_cases(args.dir)
        case = {item["id"]: item for item in cases}.get(mapping[args.a]["case"])
        if case is None:
            raise ValueError(f"el caso {mapping[args.a]['case']} no está en cases.json")
        template = args.template.read_text(encoding="utf-8")
        ordered = [args.a, args.b]
        random.shuffle(ordered)
        first, second = ordered
        trials = args.dir / "trials"
        criteria = [
            f"- {item.get('id')}: {item.get('description')}"
            for item in case.get("criteria") or []
        ]
        text = render(template, {
            "PROMPT": case["prompt"],
            "CASE": case["id"],
            "CRITERIA": "\n".join(criteria),
            "T1": str(trials / f"{first}.md"),
            "T2": str(trials / f"{second}.md"),
            "O1": str(args.out_dir / f"{first}.json"),
            "O2": str(args.out_dir / f"{second}.json"),
        })
        args.out_dir.mkdir(parents=True, exist_ok=True)
        spec = args.dir / "specs" / f"pjudge-{secrets.token_hex(4)}.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(text, encoding="utf-8")
    except (OSError, ValueError) as error:
        return fail(str(error))
    dump({"spec": str(spec)})
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    """Junta los juicios ciegos de los ensayos de una etiqueta."""
    try:
        mapping = read_map(args.dir)
        tids = [tid for tid, item in mapping.items() if item.get("variant") == args.label]
        if not tids:
            raise ValueError(f"no hay ensayos con la etiqueta {args.label}")
        judgments: list[Record] = []
        missing = []
        for tid in sorted(tids):
            path = args.judgments / f"{tid}.json"
            if not path.exists():
                missing.append(tid)
                continue
            record = json.loads(path.read_text(encoding="utf-8-sig"))
            items = record.get("judgments") if isinstance(record, dict) else None
            if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                raise ValueError(f"{path.name} no contiene una lista judgments de objetos")
            judgments += [{**item, "repeat": mapping[tid]["repeat"]} for item in items]
        if missing:
            sys.stderr.write("Faltan juicios: " + ", ".join(missing) + "\n")
            dump({"missing": missing})
            return 1
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"judgments": judgments}, indent=2), encoding="utf-8")
    except (OSError, ValueError) as error:
        return fail(str(error))
    dump({"out": str(args.out), "judgments": len(judgments)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Arma el CLI con sus tres subcomandos."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True, help="carpeta de evaluación con cases.json")
    sub = parser.add_subparsers(dest="command", required=True, help="subcomando")

    run = sub.add_parser("exec", help="crea un ensayo por caso")
    run.add_argument("--variant-dir", type=Path, required=True, help="carpeta de la skill")
    run.add_argument("--label", required=True, help="etiqueta interna de la variante")
    run.add_argument("--template", type=Path, required=True, help="plantilla markdown del ensayo")
    run.add_argument("--case", action="append", default=[], dest="cases", help="caso a incluir")
    run.set_defaults(func=cmd_exec)

    pair = sub.add_parser("pair", help="empareja dos ensayos del mismo caso para un juez")
    pair.add_argument("--a", required=True, help="primer tid")
    pair.add_argument("--b", required=True, help="segundo tid")
    pair.add_argument("--template", type=Path, required=True, help="plantilla markdown del juez")
    pair.add_argument("--out-dir", type=Path, required=True, help="carpeta de juicios del juez")
    pair.set_defaults(func=cmd_pair)

    merge = sub.add_parser("merge", help="junta los juicios de una etiqueta")
    merge.add_argument("--label", required=True, help="etiqueta de la variante")
    merge.add_argument("--judgments", type=Path, required=True, help="carpeta con los <tid>.json")
    merge.add_argument("--out", type=Path, required=True, help="JSON de salida")
    merge.set_defaults(func=cmd_merge)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Despacha al subcomando elegido."""
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
