#!/usr/bin/env python3
"""Lanza una tanda de workers de Orca en paralelo, con tope por modelo."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, TextIO

TIMEOUT_SECONDS = 300
MAX_PARALLEL = 4
def run_cmd(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando sin shell y devuelve (exit, stdout, stderr)."""
    try:
        done = subprocess.run(
            args, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, "", str(error)
    return done.returncode, done.stdout, done.stderr
def emit(payload: dict[str, Any]) -> None:
    """Escribe un objeto JSON en stdout."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=True, indent=2) + "\n")
def read_json(path: Path) -> Any:
    """Lee un archivo JSON y devuelve su contenido."""
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        raise ValueError(f"No se pudo leer {path.name}: {error}") from error
def normalize_worker(item: Any) -> dict[str, Any]:
    """Valida un worker de la tanda y rellena sus campos opcionales."""
    if not isinstance(item, dict):
        raise ValueError("Cada worker debe ser un objeto JSON")
    for field in ("name", "agent", "title"):
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field} debe ser texto no vacío")
    spec_file = item.get("spec_file")
    if not isinstance(spec_file, str) or not spec_file.strip():
        raise ValueError(f"Falta spec_file en el worker {item['name']}")
    worktree = item.get("worktree") or "current"
    if worktree not in ("current", "new-child", "new-top-level"):
        raise ValueError(f"worktree debe ser current, new-child o new-top-level en {item['name']}")
    optional = {}
    for field in ("model", "effort", "base_branch", "worktree_name", "repo"):
        value = item.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError(f"{field} debe ser texto o null en {item['name']}")
        optional[field] = value or None
    if worktree != "current" and not (optional["worktree_name"] or "").strip():
        raise ValueError(f"{worktree} exige worktree_name en {item['name']}")
    if worktree == "new-top-level" and not (optional["repo"] or "").strip():
        raise ValueError(f"new-top-level exige repo en {item['name']}")
    if worktree != "new-top-level" and optional["repo"]:
        raise ValueError(f"repo solo se admite con new-top-level en {item['name']}")
    return {
        "name": item["name"], "spec_file": spec_file, "agent": item["agent"],
        "title": item["title"], "worktree": worktree, **optional,
    }
def read_wave(path: Path) -> dict[str, Any]:
    """Lee y valida el JSON de la tanda."""
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("La tanda debe ser un objeto JSON")
    run = data.get("run")
    if not isinstance(run, str) or not run.strip():
        raise ValueError("run debe ser texto no vacío")
    cap = data.get("cap_per_model")
    if type(cap) is not int or cap < 1:
        raise ValueError("cap_per_model debe ser un entero positivo")
    raw = data.get("workers")
    if not isinstance(raw, list) or not raw:
        raise ValueError("workers debe ser una lista no vacía")
    workers = [normalize_worker(item) for item in raw]
    names = [worker["name"] for worker in workers]
    repeated = next((name for name in names if names.count(name) > 1), None)
    if repeated is not None:
        raise ValueError(f"nombre repetido: {repeated}")
    return {"run": run, "cap": cap, "workers": workers}
def build_command(run: str, worker: dict[str, Any]) -> list[str]:
    """Arma el argv exacto de worker-start para un worker."""
    executable = os.environ.get("ORCA_CLI_COMMAND") or "orca"
    args = [
        executable, "orchestration", "worker-start", "--environment", "local",
        "--run", run, "--spec-file", worker["spec_file"],
        "--task-title", worker["title"], "--worktree", worker["worktree"],
        "--agent", worker["agent"], "--json",
    ]
    if worker["model"]:
        args += ["--model", worker["model"]]
        if worker["effort"]:
            args += ["--effort", worker["effort"]]
    if worker["worktree"] != "current":
        if worker["worktree"] == "new-top-level":
            args += ["--repo", worker["repo"]]
        args += ["--name", worker["worktree_name"], "--setup", "skip"]
        if worker["base_branch"]:
            args += ["--base-branch", worker["base_branch"]]
    return args
def plan(wave: dict[str, Any], active: dict[str, int]) -> tuple[list[dict[str, Any]], list[str]]:
    """Reparte los workers entre los que caben en el cupo y los diferidos."""
    used = dict(active)
    ready, deferred = [], []
    for worker in wave["workers"]:
        key = f"{worker['agent']}/{worker['model'] or 'configurado'}"
        if used.get(key, 0) < wave["cap"]:
            used[key] = used.get(key, 0) + 1
            ready.append(worker)
        else:
            deferred.append(worker["name"])
    return ready, deferred
def parse_receipt(text: str) -> Any:
    """Convierte la salida de worker-start en JSON o en texto recortado."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
def launch(run: str, ready: list[dict[str, Any]], handle: TextIO | None) -> tuple:
    """Lanza workers y guarda los recibos al completar cada uno."""
    results: dict[int, tuple[int, str, str]] = {}
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as pool:
        futures = {pool.submit(run_cmd, build_command(run, w)): i for i, w in enumerate(ready)}
        for future in concurrent.futures.as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            code, out, _ = results[i]
            if code == 0 and handle:
                try:
                    handle.write(json.dumps(parse_receipt(out), ensure_ascii=True) + "\n")
                    handle.flush()
                except OSError as error:
                    message = f"recibo {ready[i]['name']}: {error}"
                    errors.append(message)
                    print(message, file=sys.stderr)
    launched, failed = [], []
    for i, worker in enumerate(ready):
        code, out, err = results[i]
        if code == 0:
            launched.append({"name": worker["name"], "exit": code, "receipt": parse_receipt(out)})
        else:
            failed.append({"name": worker["name"], "exit": code, "stderr": err.strip()})
    return launched, failed, errors
def main(argv: list[str] | None = None) -> int:
    """Punto de entrada: valida la tanda, reparte cupo y lanza o simula."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wave", type=Path, help="archivo JSON con la tanda")
    parser.add_argument("--active", type=Path, help="JSON con workers vivos por clave de cupo")
    parser.add_argument("--dry-run", action="store_true", help="imprime los comandos sin ejecutarlos")
    parser.add_argument("--receipts", type=Path, help="archivo .jsonl donde añadir cada recibo")
    args = parser.parse_args(argv)
    try:
        wave = read_wave(args.wave)
        active = read_json(args.active) if args.active else {}
        if not isinstance(active, dict) or any(
            type(count) is not int or count < 0 for count in active.values()
        ):
            raise ValueError("--active debe ser un objeto de enteros >= 0")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        emit({"error": str(error)})
        return 2
    ready, deferred = plan(wave, active)
    if args.dry_run:
        argvs = [build_command(wave["run"], w) for w in ready]
        commands = [(subprocess.list2cmdline(a) if os.name == "nt" else shlex.join(a)) for a in argvs]
        for command in commands:
            print(command, file=sys.stderr)
        emit({"launched": [
            {"name": w["name"], "exit": None, "receipt": None, "command": c}
            for w, c in zip(ready, commands)
        ], "deferred": deferred, "failed": [], "commands": argvs})
        return 0
    try:
        handle = args.receipts.open("a", encoding="utf-8") if args.receipts else None
    except OSError as error:
        print(f"error: {error}", file=sys.stderr)
        emit({"error": str(error)})
        return 2
    try:
        launched, failed, errors = launch(wave["run"], ready, handle)
    finally:
        if handle:
            try:
                handle.close()
            except OSError as error:
                errors.append(str(error))
                print(str(error), file=sys.stderr)
    emit({"launched": launched, "deferred": deferred, "failed": failed, "receipt_errors": errors})
    return 1 if failed or errors else 0
if __name__ == "__main__":
    raise SystemExit(main())
