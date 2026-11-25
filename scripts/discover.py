#!/usr/bin/env python3
"""Descubre los agentes instalados y clasifica sus modelos por escalón de costo."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TIERS_PATH = Path(__file__).with_name("tiers.json")
TIMEOUT_SECONDS = 120
IS_WINDOWS = os.name == "nt"


def cache_path(raw: str) -> Path:
    """Traduce una ruta estilo Git Bash (/c/...) a una ruta nativa de Windows."""
    match = re.match(r"^/([A-Za-z])(/.*)?$", raw) if IS_WINDOWS else None
    if match:
        return Path(f"{match.group(1).upper()}:{match.group(2) or '/'}")
    return Path(raw)


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando externo sin shell y devuelve (código, stdout, stderr)."""
    executable = shutil.which(args[0]) or args[0]
    try:
        done = subprocess.run(
            [executable, *args[1:]],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except OSError as exc:
        return 127, "", str(exc)
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout: {' '.join(args)}"
    return done.returncode, done.stdout, done.stderr


def orca_command() -> str:
    """Devuelve el ejecutable de Orca configurado por el entorno."""
    return os.environ.get("ORCA_CLI_COMMAND") or "orca"


def use_utf8_stdout() -> None:
    """Fuerza UTF-8 en stdout para que el JSON sea válido fuera de la consola."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")


def load_tiers(path: Path = TIERS_PATH) -> dict[str, Any]:
    """Carga las reglas de escalones desde tiers.json."""
    tiers = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(tiers.get("rules"), list) or "default" not in tiers:
        raise ValueError(f"{path.name} no tiene reglas válidas")
    return tiers


def classify(model: str, tiers: dict[str, Any]) -> str:
    """Devuelve el escalón del modelo; gana la primera regla que coincide."""
    for rule in tiers["rules"]:
        if re.search(rule["pattern"], model, re.IGNORECASE):
            return str(rule["tier"])
    return str(tiers["default"])


def installed_agents() -> list[str]:
    """Devuelve los IDs de agentes instalados o lanza RuntimeError si Orca falla."""
    code, out, err = run_cmd([orca_command(), "agent", "installed", "--json"])
    if code != 0:
        raise RuntimeError(f"orca agent installed falló: {err.strip() or code}")
    try:
        payload = json.loads(out)
        agents = payload["result"]["agents"]
        return [str(agent["id"]) for agent in agents]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"respuesta inválida de orca: {exc}") from exc


def collect(tiers: dict[str, Any]) -> dict[str, Any]:
    """Construye el informe de agentes y modelos consultando Orca y OpenCode."""
    agents = installed_agents()
    opencode_agents = [agent for agent in agents if agent.startswith("opencode")]
    models: list[dict[str, str]] = []
    warnings: list[str] = []

    if opencode_agents:
        code, out, err = run_cmd(["opencode", "models"])
        if code != 0:
            warnings.append(f"opencode models falló: {err.strip() or code}")
        else:
            for line in out.splitlines():
                model = line.strip()
                if model:
                    models.append(
                        {
                            "agent": opencode_agents[0],
                            "model": model,
                            "tier": classify(model, tiers),
                        }
                    )

    configured = tiers.get("agents") or {}
    listed = opencode_agents[0] if opencode_agents else None
    for agent in agents:
        if agent == listed:
            continue
        models.append(
            {
                "agent": agent,
                "model": "configurado",
                "tier": str(configured.get(agent, tiers["default"])),
            }
        )

    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agents": agents,
        "models": models,
    }
    if warnings:
        result["warnings"] = warnings
    return result


def is_fresh(cache: Path, max_age_hours: float) -> bool:
    """Indica si el archivo de caché existe y no supera la antigüedad máxima."""
    try:
        info = cache.stat()
    except (FileNotFoundError, NotADirectoryError):
        return False
    return stat.S_ISREG(info.st_mode) and time.time() - info.st_mtime < max_age_hours * 3600


def reject_json_constant(value: str) -> None:
    raise ValueError(f"Constante JSON no válida: {value}")


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: imprime el informe JSON y gestiona la caché."""
    use_utf8_stdout()
    parser = argparse.ArgumentParser(
        description="Lista agentes y clasifica los modelos de OpenCode por costo usando tiers.json."
    )
    parser.add_argument(
        "--cache", type=cache_path, metavar="RUTA",
        help="archivo JSON de caché; si está fresco no se ejecutan comandos",
    )
    parser.add_argument(
        "--max-age-hours", type=float, default=12.0, metavar="HORAS",
        help="antigüedad máxima de la caché en horas (por omisión 12)",
    )
    args = parser.parse_args(argv)

    try:
        fresh = args.cache and is_fresh(args.cache, args.max_age_hours)
        cached = args.cache.read_text(encoding="utf-8") if fresh else None
        if cached is not None:
            json.loads(cached, parse_constant=reject_json_constant)
    except (ValueError, RecursionError):  # Incluye JSONDecodeError y UnicodeDecodeError.
        cached = None
    except OSError as exc:
        print(f"error: no se pudo leer la caché en {args.cache}: {exc}", file=sys.stderr)
        return 2
    if cached is not None:
        sys.stdout.write(cached)
        return 0

    try:
        text = json.dumps(collect(load_tiers()), ensure_ascii=False, indent=2) + "\n"
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.cache:
        try:
            args.cache.parent.mkdir(parents=True, exist_ok=True)
            args.cache.write_text(text, encoding="utf-8")
            if not args.cache.is_file():
                raise OSError("no se creó el archivo")
        except OSError as exc:
            print(f"error: no se pudo escribir la caché en {args.cache}: {exc}", file=sys.stderr)
            return 2

    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
