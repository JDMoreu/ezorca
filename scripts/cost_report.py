#!/usr/bin/env python3
"""Resume los tokens de cada sesión de Claude Code, Codex y OpenCode sin leer contenidos."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

import cost_sources

AGENTS = ("claude", "codex", "opencode")
FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "reasoning_tokens",
    "total_tokens",
)


def bound(value: str) -> datetime:
    """Convierte una fecha ISO (sin zona = UTC); falla si no es ISO."""
    moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def moment(value: str | None) -> datetime | None:
    """Convierte un ISO de salida en datetime UTC."""
    return bound(value) if value else None


def overlaps(session: dict, since: datetime | None, until: datetime | None) -> bool:
    """Dice si [started_at, ended_at] cruza [since, until]."""
    start, end = moment(session["started_at"]), moment(session["ended_at"])
    if start is None or end is None:
        return since is None and until is None
    return (since is None or end >= since) and (until is None or start <= until)


def totals(sessions: list[dict]) -> dict[str, dict]:
    """Suma por agente, con las tres claves siempre presentes."""
    result = {agent: {"sessions": 0, **dict.fromkeys(FIELDS, 0)} for agent in AGENTS}
    for session in sessions:
        bucket = result[session["agent"]]
        bucket["sessions"] += 1
        for field in FIELDS:
            bucket[field] += session[field]
    return result


def fail(message: str) -> int:
    """Informa el uso inválido por stdout (JSON) y stderr, con exit 2."""
    json.dump({"error": message}, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    sys.stderr.write(message + "\n")
    return 2


def collect(args: argparse.Namespace, paths: dict[str, str]) -> tuple[list[dict], list[str]]:
    """Lee las fuentes habilitadas y junta sesiones y warnings."""
    sessions: list[dict] = []
    warnings: list[str] = []
    readers = (("claude", cost_sources.read_claude), ("codex", cost_sources.read_codex))
    for agent, reader in readers:
        if getattr(args, "no_" + agent):
            continue
        if not os.path.isdir(paths[agent]):
            warnings.append(f"{agent}: sin registros locales")
            continue
        found, notes = reader(paths[agent])
        sessions += found
        warnings += notes
    if not args.no_opencode:
        if not os.path.isfile(paths["opencode"]):
            warnings.append("opencode: sin base de datos local")
        else:
            found, notes = cost_sources.read_opencode(paths["opencode"])
            sessions += found
            warnings += notes
    return sessions, warnings


def main(argv: list[str] | None = None) -> int:
    """Calcula el informe y, ante cualquier fallo no previsto, informa solo el tipo."""
    try:
        return run(argv)
    except Exception as error:  # último cinturón: nunca traceback con rutas ni valores
        return fail(f"error interno ({type(error).__name__})")


def run(argv: list[str] | None = None) -> int:
    """Filtra, ordena e imprime el informe de tokens."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude-dir", help="por omisión ~/.claude/projects")
    parser.add_argument("--codex-dir", help="por omisión ~/.codex/sessions")
    parser.add_argument("--opencode-db", help="por omisión ~/.local/share/opencode/opencode.db")
    parser.add_argument("--since", type=bound, help="inicio ISO 8601 (sin zona = UTC)")
    parser.add_argument("--until", type=bound, help="fin ISO 8601 (sin zona = UTC)")
    parser.add_argument("--session", action="append", default=[], help="ID de sesión (repetible)")
    parser.add_argument("--no-claude", action="store_true")
    parser.add_argument("--no-codex", action="store_true")
    parser.add_argument("--no-opencode", action="store_true")
    args = parser.parse_args(argv)

    paths = {
        "claude": args.claude_dir or os.path.expanduser("~/.claude/projects"),
        "codex": args.codex_dir or os.path.expanduser("~/.codex/sessions"),
        "opencode": args.opencode_db or os.path.expanduser("~/.local/share/opencode/opencode.db"),
    }
    given = (
        ("--claude-dir", args.claude_dir, os.path.isdir),
        ("--codex-dir", args.codex_dir, os.path.isdir),
        ("--opencode-db", args.opencode_db, os.path.isfile),
    )
    for flag, value, check in given:
        if value is not None and not check(value):
            return fail(f"{flag} no existe")

    sessions, warnings = collect(args, paths)
    if args.session:
        wanted = set(args.session)
        sessions = [s for s in sessions if s["session"] in wanted]
    sessions = [s for s in sessions if overlaps(s, args.since, args.until)]
    sessions.sort(key=lambda s: moment(s["started_at"]) or datetime.min.replace(tzinfo=timezone.utc))

    result = {"sessions": sessions, "totals": totals(sessions), "warnings": warnings}
    json.dump(result, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
