#!/usr/bin/env python3
"""Lectores de los registros locales de Claude Code, Codex y OpenCode: solo números."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

COUNT_KEYS = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens", "reasoning_tokens")
CLAUDE_USAGE = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
CODEX_USAGE = ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens", "reasoning_output_tokens")


def _moment(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.strftime("%Y-%m-%dT%H:%M:%S.%f").rstrip("0").rstrip(".") + "Z"


def _counts(usage: dict, keys: tuple[str, ...]) -> list[int] | None:
    values = [usage.get(key) for key in keys]
    valid = all(value is None or type(value) is int for value in values)
    return [value or 0 for value in values] if valid else None


def _lines(path: Path) -> Iterator[dict | None]:
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                yield None
                continue
            yield record if isinstance(record, dict) else None


def _session(agent: str, sid: str, model: str | None, stamps: list[datetime], counts: dict[str, int]) -> dict:
    return {"agent": agent, "session": sid, "model": model,
            "started_at": _iso(min(stamps) if stamps else None),
            "ended_at": _iso(max(stamps) if stamps else None),
            **{key: counts.get(key, 0) for key in COUNT_KEYS},
            "total_tokens": sum(counts.get(key, 0) for key in COUNT_KEYS[:4])}


def _read(root: str, agent: str, handler: Callable, state: Callable, build: Callable) -> tuple[list[dict], list[str]]:
    """Recorre los *.jsonl: handler acumula, build arma la sesión y los fallos van a warnings."""
    sessions, warnings = [], []
    for path in sorted(Path(root).rglob("*.jsonl")):
        current = state(path)
        ignored = 0
        try:
            for record in _lines(path):
                if record is None or not handler(record, current):
                    ignored += 1
                    continue
                moment = _moment(record.get("timestamp"))
                if moment is not None:
                    current["stamps"].append(moment)
        except (OSError, UnicodeDecodeError):
            warnings.append(f"{agent}: una sesión no se pudo leer")
            continue
        if ignored:
            warnings.append(f"{agent}: {ignored} líneas ignoradas en una sesión")
        sessions.append(build(path, current))
    return sessions, warnings


def _claude_record(record: dict, state: dict) -> bool:
    message = record.get("message")
    usage = message.get("usage") if isinstance(message, dict) else None
    if record.get("type") == "assistant":
        if not isinstance(message, dict):
            return False
        if isinstance(usage, dict):
            values = _counts(usage, CLAUDE_USAGE)
            if values is None:
                return False
            mid = message.get("id")
            if isinstance(mid, str) and mid:
                state["usage"][mid] = values
            else:
                state["loose"].append(values)
            model = message.get("model")
            if isinstance(model, str) and model:
                state["models"][model] += 1
    return True


def read_claude(root: str) -> tuple[list[dict], list[str]]:
    """Lee cada *.jsonl como sesión, contando cada message.id una sola vez."""
    def state(_path: Path) -> dict:
        return {"usage": {}, "loose": [], "models": Counter(), "stamps": []}
    def build(path: Path, data: dict) -> dict:
        counts = dict.fromkeys(COUNT_KEYS, 0)
        for values in [*data["usage"].values(), *data["loose"]]:
            for key, value in zip(COUNT_KEYS[:4], values):
                counts[key] += value
        model = data["models"].most_common(1)[0][0] if data["models"] else None
        return _session("claude", path.stem, model, data["stamps"], counts)

    return _read(root, "claude", _claude_record, state, build)


def _codex_record(record: dict, state: dict) -> bool:
    payload = record.get("payload")
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return False
    kind = record.get("type")
    if kind == "session_meta":
        sid = payload.get("id")
        if isinstance(sid, str) and sid:
            state["sid"] = sid
    elif kind == "turn_context":
        model = payload.get("model")
        state["model"] = model if isinstance(model, str) and model else None
    elif kind == "event_msg" and payload.get("type") == "token_count":
        info = payload.get("info")
        usage = info.get("total_token_usage") if isinstance(info, dict) else None
        if not isinstance(usage, dict) or _counts(usage, CODEX_USAGE) is None:
            return False
        state["usage"] = usage
    return True


def read_codex(root: str) -> tuple[list[dict], list[str]]:
    """Lee cada *.jsonl y usa el último token_count acumulado de la sesión."""
    def state(path: Path) -> dict:
        return {"sid": path.stem, "model": None, "usage": {}, "stamps": []}
    def build(_path: Path, data: dict) -> dict:
        values = _counts(data["usage"], CODEX_USAGE) or [0] * len(CODEX_USAGE)
        counts = dict(zip(COUNT_KEYS, [values[0] - values[1], values[3], values[1], values[2], values[4]]))
        return _session("codex", data["sid"], data["model"], data["stamps"], counts)

    return _read(root, "codex", _codex_record, state, build)


def _from_ms(value: object) -> datetime | None:
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc) if type(value) in (int, float) else None
    except (OverflowError, OSError, ValueError):
        return None


def _model(value: object) -> str | None:
    """Modelo de OpenCode: id si viene como JSON con id, texto tal cual, null si no es texto."""
    if not isinstance(value, str):
        return value.get("id") if isinstance(value, dict) and isinstance(value.get("id"), str) else None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return value
    mid = parsed.get("id") if isinstance(parsed, dict) else None
    return mid if isinstance(mid, str) else value


def read_opencode(db_path: str) -> tuple[list[dict], list[str]]:
    """Lee session_v2 (o session) de la base OpenCode en modo solo lectura."""
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
        try:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
            table = "session_v2" if "session_v2" in tables else "session"
            columns = [row[1] for row in conn.execute("PRAGMA table_info(" + table + ")")]
            written = "tokens_cache_write" if "tokens_cache_write" in columns else "0"
            query = ("SELECT id, model, tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, " + written
                     + ", time_created, time_updated FROM " + table)
            rows = conn.execute(query).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as error:
        return [], [f"opencode: no se pudo leer la base ({type(error).__name__})"]
    sessions, ignored = [], 0
    for row in rows:
        values = row[2:7]
        if any(not (value is None or type(value) is int) for value in values):
            ignored += 1
            continue
        counts = dict(zip(COUNT_KEYS, [values[0] or 0, values[1] or 0, values[3] or 0, values[4] or 0, values[2] or 0]))
        stamps = [moment for moment in (_from_ms(row[7]), _from_ms(row[8])) if moment]
        sessions.append(_session("opencode", str(row[0]), _model(row[1]), stamps, counts))
    return sessions, [f"opencode: {ignored} filas ignoradas"] if ignored else []
