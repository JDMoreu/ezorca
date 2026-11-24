from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "cost_report.py"
SECRET = "SECRETO"


def claude_line(mid: str, model: str, inp: int, out: int, stamp: str) -> dict:
    usage = {"input_tokens": inp, "output_tokens": out,
             "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": mid, "model": model, "content": SECRET, "usage": usage}}


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def codex_token(usage: dict) -> dict:
    payload = {"type": "token_count", "info": {"total_token_usage": usage}}
    return {"type": "event_msg", "timestamp": "2026-11-24T10:00:05Z", "payload": payload}


def make_opencode_db(path: Path, table: str = "session", model: object = "deepseek",
                     tokens_in: int = 100, cache_write: bool = True) -> None:
    """Base mínima con una fila; elige tabla, modelo y si existe tokens_cache_write."""
    columns = "id, model, tokens_input, tokens_output, tokens_reasoning, tokens_cache_read"
    values: list[object] = ["oc1", model, tokens_in, 50, 10, 20]
    if cache_write:
        columns, values = columns + ", tokens_cache_write", values + [0]
    columns, values = columns + ", time_created, time_updated", values + [1795435200000, 1795435260000]
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE " + table + " (" + columns + ")")
    conn.execute("INSERT INTO " + table + " VALUES (" + ", ".join("?" * len(values)) + ")", values)
    conn.commit()
    conn.close()


class CostReportTests(unittest.TestCase):
    """Cubre las tres fuentes, los filtros, la robustez y los errores de uso."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.claude = self.root / "claude"
        self.codex = self.root / "codex"
        self.claude.mkdir()
        self.codex.mkdir()
        self.db = self.root / "opencode.db"
        write_jsonl(self.claude / "s1.jsonl", [
            claude_line("m1", "claude-x", 10, 5, "2026-11-24T10:00:00Z"),
            claude_line("m1", "claude-x", 10, 7, "2026-11-24T10:00:05Z"),
            claude_line("m2", "claude-x", 3, 1, "2026-11-24T10:00:10Z")])
        write_jsonl(self.codex / "rollout-a.jsonl", [
            {"type": "session_meta", "timestamp": "2026-11-24T09:00:00Z", "payload": {"id": "cx1"}},
            {"type": "turn_context", "timestamp": "2026-11-24T09:00:01Z", "payload": {"model": "gpt-x"}},
            codex_token({"input_tokens": 100, "cached_input_tokens": 40, "output_tokens": 20,
                         "reasoning_output_tokens": 5}),
            codex_token({"input_tokens": 150, "cached_input_tokens": 60, "output_tokens": 30,
                         "reasoning_output_tokens": 8})])
        make_opencode_db(self.db)

    def run_script(self, *extra: str, claude: Path | None = None, codex: Path | None = None,
                   db: Path | None = None) -> tuple[int, dict | None, str]:
        """Ejecuta el script con fuentes temporales y devuelve (código, JSON, stderr)."""
        args = [sys.executable, str(SCRIPT), "--claude-dir", str(claude or self.claude),
                "--codex-dir", str(codex or self.codex), "--opencode-db", str(db or self.db), *extra]
        done = subprocess.run(args, capture_output=True, text=True)
        payload = json.loads(done.stdout) if done.stdout.strip().startswith("{") else None
        return done.returncode, payload, done.stderr

    def folder(self, name: str, filename: str, records: list[dict]) -> Path:
        path = self.root / name
        path.mkdir()
        write_jsonl(path / filename, records)
        return path

    def test_claude_counts_each_message_once(self) -> None:
        code, data, _ = self.run_script("--no-codex", "--no-opencode")
        self.assertEqual(code, 0)
        session = data["sessions"][0]
        self.assertEqual((session["session"], session["input_tokens"], session["output_tokens"]), ("s1", 13, 8))
        self.assertEqual(session["model"], "claude-x")
        self.assertNotIn(SECRET, json.dumps(data))

    def test_claude_without_usage_keeps_tokens_and_timestamps(self) -> None:
        records = [claude_line("m1", "claude-x", 10, 5, "2026-11-24T10:00:00Z"),
                   {"type": "assistant", "timestamp": "2026-11-24T10:05:00Z",
                    "message": {"id": "m1", "model": "claude-x"}}]
        code, data, _ = self.run_script("--no-codex", "--no-opencode", claude=self.folder("noun", "s3.jsonl", records))
        self.assertEqual(code, 0)
        session = data["sessions"][0]
        self.assertEqual(session["total_tokens"], 15)
        self.assertEqual(session["ended_at"], "2026-11-24T10:05:00Z")

    def test_codex_uses_last_cumulative_token_count(self) -> None:
        code, data, _ = self.run_script("--no-claude", "--no-opencode")
        self.assertEqual(code, 0)
        session = data["sessions"][0]
        self.assertEqual(session["session"], "cx1")
        self.assertEqual((session["input_tokens"], session["cache_read_tokens"]), (90, 60))
        self.assertEqual((session["output_tokens"], session["reasoning_tokens"]), (30, 8))
        self.assertEqual((session["model"], session["total_tokens"]), ("gpt-x", 180))

    def test_codex_last_turn_context_without_model_is_null(self) -> None:
        records = [{"type": "turn_context", "payload": {"model": "old"}},
                   {"type": "turn_context", "payload": {}}]
        code, data, _ = self.run_script("--no-claude", "--no-opencode", codex=self.folder("ctx", "r.jsonl", records))
        self.assertEqual(code, 0)
        self.assertIsNone(data["sessions"][0]["model"])

    def test_opencode_reads_session_table_read_only(self) -> None:
        code, data, _ = self.run_script("--no-claude", "--no-codex")
        self.assertEqual(code, 0)
        session = data["sessions"][0]
        self.assertEqual(session["session"], "oc1")
        self.assertEqual((session["total_tokens"], session["reasoning_tokens"]), (170, 10))
        self.assertEqual((session["started_at"], session["ended_at"]),
                         ("2026-11-23T12:00:00Z", "2026-11-23T12:01:00Z"))

    def test_opencode_prefers_session_v2_and_normalizes_model(self) -> None:
        v2 = self.root / "v2.db"
        make_opencode_db(v2, "session_v2", '{"id": "kimi-k3.1-pro", "providerID": "x"}', 200)
        code, data, _ = self.run_script("--no-claude", "--no-codex", db=v2)
        self.assertEqual(code, 0)
        session = data["sessions"][0]
        self.assertEqual((session["model"], session["total_tokens"]), ("kimi-k3.1-pro", 270))
        both = self.root / "both.db"
        make_opencode_db(both, "session", tokens_in=1)
        make_opencode_db(both, "session_v2", tokens_in=2)
        code, data, _ = self.run_script("--no-claude", "--no-codex", db=both)
        self.assertEqual(data["sessions"][0]["input_tokens"], 2)
        legacy = self.root / "legacy.db"
        make_opencode_db(legacy, "session", cache_write=False)
        code, data, _ = self.run_script("--no-claude", "--no-codex", db=legacy)
        self.assertEqual((code, data["sessions"][0]["cache_write_tokens"]), (0, 0))

    def test_totals_sum_by_agent(self) -> None:
        code, data, _ = self.run_script()
        self.assertEqual(code, 0)
        self.assertEqual(data["totals"]["claude"]["sessions"], 1)
        self.assertEqual(data["totals"]["claude"]["total_tokens"], 21)
        self.assertEqual(data["totals"]["codex"]["total_tokens"], 180)
        self.assertEqual(data["totals"]["opencode"]["total_tokens"], 170)
        starts = [s["started_at"] for s in data["sessions"]]
        self.assertEqual(starts, sorted(starts))

    def test_filters_since_and_session(self) -> None:
        code, data, _ = self.run_script("--since", "2026-11-24T00:00:00Z")
        self.assertEqual(code, 0)
        self.assertEqual([s["session"] for s in data["sessions"]], ["cx1", "s1"])
        code, data, _ = self.run_script("--session", "cx1")
        self.assertEqual([s["session"] for s in data["sessions"]], ["cx1"])
        self.assertEqual(data["totals"]["claude"]["sessions"], 0)
        code, data, _ = self.run_script("--no-codex")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(s["agent"] for s in data["sessions"]), ["claude", "opencode"])

    def test_malformed_records_warn_without_traceback(self) -> None:
        records = [{"type": "assistant", "message": "texto"},
                   {"type": "assistant",
                    "message": {"id": "m9", "model": "x", "usage": {"input_tokens": "diez", "output_tokens": 1}}}]
        folder = self.folder("bad", "s9.jsonl", records)
        code, data, err = self.run_script("--no-codex", "--no-opencode", claude=folder)
        self.assertEqual(code, 0)
        self.assertTrue(data["warnings"])
        text = json.dumps(data) + err
        self.assertNotIn("Traceback", text)
        self.assertNotIn(str(self.root), text)

    def test_microsecond_bounds_are_compared_exactly(self) -> None:
        folder = self.folder("micro", "s2.jsonl", [claude_line("m1", "claude-x", 1, 1, "2026-11-24T00:00:00.900Z")])
        code, data, _ = self.run_script("--since", "2026-11-24T00:00:00.500Z", "--no-codex",
                                        "--no-opencode", claude=folder)
        self.assertEqual(code, 0)
        self.assertEqual([s["session"] for s in data["sessions"]], ["s2"])
        self.assertTrue(data["sessions"][0]["ended_at"].endswith(".9Z"))

    def test_usage_errors_exit_2(self) -> None:
        code, _, err = self.run_script("--since", "ayer")
        self.assertEqual(code, 2)
        self.assertIn("--since", err)
        args = [sys.executable, str(SCRIPT), "--claude-dir", str(self.root / "no-existe"),
                "--no-codex", "--no-opencode"]
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)
        help_done = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True)
        self.assertEqual(help_done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
