from __future__ import annotations

import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import stalled  # noqa: E402


class StalledTests(unittest.TestCase):
    """Cubre conversión de lastActivity, filtro de estados y tail."""

    def setUp(self) -> None:
        env = mock.patch.dict(os.environ, {"ORCA_CLI_COMMAND": "orca"}, clear=False)
        env.start()
        self.addCleanup(env.stop)

    def run_main(self, argv: list[str], fake: object) -> tuple[int, str]:
        """Ejecuta main con run_cmd falso y captura stdout."""
        out = io.StringIO()
        with (
            mock.patch.object(stalled, "run_cmd", fake),
            redirect_stdout(out),
            redirect_stderr(io.StringIO()),
        ):
            code = stalled.main(argv)
        return code, out.getvalue()

    @staticmethod
    def fake_orca(
        workers: list[dict[str, object]],
        shows: dict[str, object],
        tails: dict[str, str] | None = None,
        list_key: str = "workers",
    ) -> object:
        """Devuelve un run_cmd falso que simula list, show y read."""

        def fake(args: list[str]) -> tuple[int, str, str]:
            if "worker-list" in args:
                return 0, json.dumps({"result": {list_key: workers}}), ""
            dispatch = args[args.index("--dispatch") + 1]
            if "worker-show" in args:
                if dispatch not in shows:
                    return 1, "", "no existe"
                return 0, json.dumps({"result": {"lastActivity": shows[dispatch]}}), ""
            return 0, (tails or {}).get(dispatch, ""), ""

        return fake

    def test_one_stalled_of_two_live(self) -> None:
        workers = [
            {"dispatchId": "ctx_a", "state": "ready", "liveness": "live", "agent": "opencode"},
            {"dispatchId": "ctx_b", "state": "working", "liveness": "live", "agent": "opencode"},
        ]
        shows = {"ctx_a": "just now", "ctx_b": "45m ago"}
        tails = {"ctx_b": "l1\nl2\nl3\nl4\nl5\nl6\n"}
        fake = self.fake_orca(workers, shows, tails)
        code, out = self.run_main(["--run", "run_1", "--minutes", "20"], fake)
        result = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(result["run"], "run_1")
        self.assertEqual(result["checked"], 2)
        first, second = result["workers"]
        self.assertEqual(first["dispatch"], "ctx_a")
        self.assertEqual(first["idle_minutes"], 0)
        self.assertFalse(first["stalled"])
        self.assertNotIn("tail", first)
        self.assertTrue(second["stalled"])
        self.assertEqual(second["idle_minutes"], 45)
        self.assertEqual(second["tail"], ["l2", "l3", "l4", "l5", "l6"])
        self.assertIn("detener y relanzar", second["action"])

    def test_filters_finished_and_dead_workers(self) -> None:
        workers = [
            {"dispatchId": "ctx_ok", "state": "succeeded", "liveness": "live"},
            {"dispatchId": "ctx_bad", "state": "failed", "liveness": "live"},
            {"dispatchId": "ctx_off", "state": "ready", "liveness": "stale"},
            {"dispatchId": "ctx_live", "state": "ready", "liveness": "live"},
        ]
        shows = {"ctx_live": "1m ago"}
        code, out = self.run_main(["--run", "run_2"], self.fake_orca(workers, shows))
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(result["checked"], 1)
        self.assertEqual(result["workers"][0]["dispatch"], "ctx_live")

    def test_accepts_dispatches_key(self) -> None:
        workers = [{"dispatchId": "ctx_a", "state": "ready", "liveness": "live"}]
        fake = self.fake_orca(workers, {"ctx_a": "3m ago"}, list_key="dispatches")
        code, out = self.run_main(["--run", "run_3"], fake)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["checked"], 1)

    def test_unreadable_last_activity_is_null_and_not_stalled(self) -> None:
        workers = [{"dispatchId": "ctx_a", "state": "ready", "liveness": "live"}]
        code, out = self.run_main(["--run", "run_4"], self.fake_orca(workers, {}))
        worker = json.loads(out)["workers"][0]
        self.assertEqual(code, 0)
        self.assertIsNone(worker["idle_minutes"])
        self.assertFalse(worker["stalled"])

    def test_orca_failure_exits_two(self) -> None:
        def fake(args: list[str]) -> tuple[int, str, str]:
            return 1, "", "sin conexión"

        code, out = self.run_main(["--run", "run_5"], fake)
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(out))

    def test_wait_sleeps_before_checking(self) -> None:
        workers = [{"dispatchId": "ctx_a", "state": "ready", "liveness": "live"}]
        fake = self.fake_orca(workers, {"ctx_a": "0m ago"})
        with mock.patch.object(stalled.time, "sleep") as sleep:
            self.run_main(["--run", "run_6", "--wait", "30"], fake)
        sleep.assert_called_once_with(30)

    def test_orca_command_shape(self) -> None:
        workers = [{"dispatchId": "ctx_a", "state": "ready", "liveness": "live"}]
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            if "worker-list" in args:
                return 0, json.dumps({"result": {"workers": workers}}), ""
            if "worker-show" in args:
                return 0, json.dumps({"result": {"lastActivity": "45m ago"}}), ""
            return 0, "salida\n", ""

        self.run_main(["--run", "run_7", "--minutes", "20"], fake)
        self.assertEqual(
            calls[0],
            [
                "orca",
                "orchestration",
                "worker-list",
                "--environment",
                "local",
                "--run",
                "run_7",
                "--json",
            ],
        )
        self.assertEqual(calls[1][:4], ["orca", "orchestration", "worker-show", "--environment"])
        self.assertIn("--dispatch", calls[1])
        self.assertEqual(calls[2][-2:], ["--source", "auto"])

    def test_idle_minutes_conversions(self) -> None:
        cases = {
            "just now": 0,
            "33m ago": 33,
            "2h ago": 120,
            "1d ago": 1440,
            "10s ago": 0,
            "90s ago": 1,
            "ayer": None,
            None: None,
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(stalled.idle_minutes(text), expected)


if __name__ == "__main__":
    unittest.main()
