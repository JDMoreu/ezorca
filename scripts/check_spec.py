#!/usr/bin/env python3
"""Comprueba que un encargo Markdown tiene lo mínimo para un modelo económico."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

IMPLEMENTACION = "implementacion"
REVISION = "revision"


def normalize(text: str) -> str:
    """Pasa el texto a minúsculas y sin tildes para comparar."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def use_utf8_stdout() -> None:
    """Fuerza UTF-8 en stdout para que el JSON sea válido fuera de la consola."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def has_label(text: str, labels: tuple[str, ...]) -> bool:
    """Indica si alguna etiqueta abre una línea como palabra completa."""
    wanted = tuple(normalize(label) for label in labels)
    for line in text.splitlines():
        stripped = normalize(line.lstrip(" \t#*_>-"))
        for label in wanted:
            if stripped.startswith(label):
                rest = stripped[len(label) : len(label) + 1]
                if not rest or not rest.isalnum():
                    return True
    return False


def missing_implementacion(text: str, flat: str) -> list[str]:
    """Devuelve lo que falta a un encargo de implementación."""
    missing = []
    if not has_label(
        text, ("Puede editar", "Pueden editar", "Archivos que puedes editar")
    ):
        missing.append("Puede editar")
    if not has_label(text, ("Ejemplo", "Ejemplos")):
        missing.append("Ejemplo")
    if not has_label(text, ("Comprobaciones", "Comprobación")):
        missing.append("Comprobaciones")
    if not has_label(text, ("Límites del proyecto",)):
        missing.append("Límites del proyecto")
    if "worker_done" not in flat:
        missing.append("worker_done")
    return missing


def missing_revision(text: str, flat: str) -> list[str]:
    """Devuelve lo que falta a un encargo de revisión."""
    missing = []
    if not has_label(text, ("Comprobaciones", "Comprobación", "Qué devolver")):
        missing.append("Comprobaciones")
    if "no verificable" not in flat:
        missing.append("no verificable")
    metodo = has_label(text, ("Método y límites", "Métodos y límites")) or (
        "leiste" in flat and "dedujiste" in flat
    )
    if not metodo:
        missing.append("Método y límites")
    if "worker_done" not in flat:
        missing.append("worker_done")
    return missing


def evaluate(path: Path, text: str, kind: str) -> dict[str, Any]:
    """Evalúa el texto de un archivo y devuelve su resultado como diccionario."""
    flat = normalize(text)
    if kind == REVISION:
        missing = missing_revision(text, flat)
    else:
        missing = missing_implementacion(text, flat)
    warnings = ["coletilla: No delegues"] if "no delegues" in flat else []
    return {
        "file": str(path),
        "ok": not missing,
        "missing": missing,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: imprime una lista JSON y agrega el código de salida."""
    use_utf8_stdout()
    parser = argparse.ArgumentParser(
        description=(
            "Comprueba que los encargos Markdown traen archivos permitidos, "
            "ejemplo, comprobaciones y cierre con worker_done."
        )
    )
    parser.add_argument("files", nargs="+", type=Path, metavar="SPEC", help="specs Markdown")
    parser.add_argument(
        "--kind",
        choices=(IMPLEMENTACION, REVISION),
        default=IMPLEMENTACION,
        help="tipo de encargo a comprobar (por omisión implementacion)",
    )
    args = parser.parse_args(argv)

    texts = {}
    for path in args.files:
        try:
            texts[path] = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(f"archivo no existe: {path}", file=sys.stderr)
            return 2
        except OSError as exc:
            print(f"no se pudo leer {path}: {exc}", file=sys.stderr)
            return 2

    results = [evaluate(path, text, args.kind) for path, text in texts.items()]
    print(json.dumps(results, ensure_ascii=False))
    return 0 if all(result["ok"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
