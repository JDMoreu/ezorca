#!/usr/bin/env python3
"""Detecta workers vivos de Orca que dejaron de avanzar, sin leer su correo."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any

TIMEOUT_SECONDS = 300
DONE_STATES = {"succeeded", "failed", "cancelled"}
TAIL_LINES = 5
STALLED_ACTION = (
    "leer salida; si está atascado, detener y relanzar una vez con el mismo agente"
)
WAITING_ACTION = "seguir esperando"
UNITS = {"m": 1, "h": 60, "d": 1440}


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando sin shell y devuelve (exit, stdout, stderr)."""
    try:
        done = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, "", str(error)
    return done.returncode, done.stdout, done.stderr


def orca_cmd(*args: str) -> list[str]:
    """Arma un comando de orca orchestration con el ejecutable configurado."""
    executable = os.environ.get("ORCA_CLI_COMMAND") or "orca"
    return [executable, "orchestration", *args]


def emit(payload: dict[str, Any]) -> None:
    """Escribe un objeto JSON en stdout."""
    json.dump(payload, sys.stdout, ensure_ascii=True, indent=2)
    sys.stdout.write("\n")


def idle_minutes(text: Any) -> int | None:
    """Convierte un lastActivity como '33m ago' a minutos, o None si no se entiende."""
    if not isinstance(text, str):
        return None
    value = text.strip().lower()
    if value == "just now":
        return 0
    match = re.fullmatch(r"(\d+)\s*([smhd])\s+ago", value)
    if not match:
        return None
    amount = int(match.group(1))
    factor = UNITS.get(match.group(2))
    return amount // 60 if factor is None else amount * factor


def parse_result(out: str) -> dict[str, Any]:
    """Extrae el objeto result de una respuesta de Orca."""
    data = json.loads(out)
    if not isinstance(data, dict):
        raise ValueError("Orca devolvió un JSON que no es objeto")
    result = data.get("result", data)
    return result if isinstance(result, dict) else {}


def list_workers(run: str) -> list[dict[str, Any]]:
    """Pide a Orca los workers del run y falla con ValueError si no puede."""
    code, out, err = run_cmd(
        orca_cmd("worker-list", "--environment", "local", "--run", run, "--json")
    )
    if code != 0:
        raise ValueError(f"worker-list falló ({code}): {err.strip()}")
    try:
        result = parse_result(out)
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"worker-list devolvió JSON inválido: {error}") from error
    workers = result.get("workers")
    if workers is None:
        workers = result.get("dispatches")
    if not isinstance(workers, list):
        raise ValueError("worker-list no devolvió workers ni dispatches")
    return [item for item in workers if isinstance(item, dict)]


def worker_idle(dispatch: str) -> int | None:
    """Lee el lastActivity de un worker y lo devuelve en minutos."""
    code, out, _ = run_cmd(
        orca_cmd("worker-show", "--environment", "local", "--dispatch", dispatch, "--json")
    )
    if code != 0:
        return None
    try:
        result = parse_result(out)
    except (json.JSONDecodeError, ValueError):
        return None
    return idle_minutes(result.get("lastActivity"))


def worker_tail(dispatch: str) -> list[str]:
    """Devuelve las últimas líneas de la salida de un worker."""
    code, out, _ = run_cmd(
        orca_cmd("worker-read", "--environment", "local", "--dispatch", dispatch, "--source", "auto")
    )
    if code != 0:
        return []
    return out.rstrip("\n").splitlines()[-TAIL_LINES:] if out.strip() else []


def check(run: str, minutes: int) -> dict[str, Any]:
    """Revisa los workers vivos y marca los que llevan demasiado tiempo quietos."""
    entries = []
    for worker in list_workers(run):
        if worker.get("state") in DONE_STATES or worker.get("liveness") != "live":
            continue
        dispatch = worker.get("dispatchId")
        if not isinstance(dispatch, str) or not dispatch:
            continue
        idle = worker_idle(dispatch)
        stalled = idle is not None and idle >= minutes
        entry: dict[str, Any] = {
            "dispatch": dispatch,
            "agent": worker.get("agent"),
            "idle_minutes": idle,
            "stalled": stalled,
            "action": STALLED_ACTION if stalled else WAITING_ACTION,
        }
        if stalled:
            entry["tail"] = worker_tail(dispatch)
        entries.append(entry)
    return {"run": run, "checked": len(entries), "workers": entries}


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: lista workers vivos y reporta los colgados."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="identificador del run de Orca")
    parser.add_argument(
        "--minutes",
        type=int,
        default=20,
        help="minutos sin avanzar para marcar un worker como colgado (20)",
    )
    parser.add_argument(
        "--wait", type=int, default=0, help="segundos a esperar antes de revisar"
    )
    args = parser.parse_args(argv)
    if args.minutes < 0 or args.wait < 0:
        emit({"error": "--minutes y --wait no pueden ser negativos"})
        return 2
    if args.wait:
        time.sleep(args.wait)
    try:
        result = check(args.run, args.minutes)
    except ValueError as error:
        emit({"error": str(error)})
        return 2
    emit(result)
    return 1 if any(entry["stalled"] for entry in result["workers"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
