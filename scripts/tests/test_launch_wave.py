from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import launch_wave  # noqa: E402


def worker(name: str, **extra: object) -> dict[str, object]:
    """Arma un worker de prueba con los valores por omisión de la tanda."""
    data: dict[str, object] = {
        "name": name,
        "spec_file": f"ab/{name}.md",
        "agent": "opencode",
        "title": f"AB {name}",
        "worktree": "current",
        "model": None,
        "effort": None,
        "base_branch": None,
        "worktree_name": None,
        "repo": None,
    }
    data.update(extra)
    return data


class LaunchWaveTests(unittest.TestCase):
    """Cubre cupo, active, dry-run, argv exacto, fallos y JSON inválido."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        env = mock.patch.dict(os.environ, {"ORCA_CLI_COMMAND": "orca"}, clear=False)
        env.start()
        self.addCleanup(env.stop)

    def write(self, data: object, name: str) -> Path:
        """Escribe un JSON de prueba y devuelve su ruta."""
        path = self.dir / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def run_main(self, argv: list[str], fake: object) -> tuple[int, str, str]:
        """Ejecuta main con run_cmd falso y captura las salidas."""
        out, err = io.StringIO(), io.StringIO()
        with (
            mock.patch.object(launch_wave, "run_cmd", fake),
            redirect_stdout(out),
            redirect_stderr(err),
        ):
            code = launch_wave.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cap_and_active_defer_extras(self) -> None:
        wave = self.write(
            {
                "run": "run_1",
                "cap_per_model": 4,
                "workers": [worker(f"t{i}") for i in range(1, 7)],
            },
            "wave.json",
        )
        active = self.write({"opencode/configurado": 1}, "active.json")
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, json.dumps({"dispatchId": f"ctx_{len(calls)}"}), ""

        code, out, _ = self.run_main([str(wave), "--active", str(active)], fake)
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual([w["name"] for w in result["launched"]], ["t1", "t2", "t3"])
        self.assertEqual(result["deferred"], ["t4", "t5", "t6"])
        self.assertEqual(result["failed"], [])
        self.assertEqual(len(calls), 3)

    def test_argv_with_model_and_effort(self) -> None:
        wave = self.write(
            {
                "run": "run_9",
                "cap_per_model": 2,
                "workers": [worker("t1", model="gpt-x", effort="high")],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "recibo en texto", ""

        code, out, _ = self.run_main([str(wave)], fake)
        self.assertEqual(code, 0)
        self.assertEqual(
            calls[0],
            [
                "orca",
                "orchestration",
                "worker-start",
                "--environment",
                "local",
                "--run",
                "run_9",
                "--spec-file",
                "ab/t1.md",
                "--task-title",
                "AB t1",
                "--worktree",
                "current",
                "--agent",
                "opencode",
                "--json",
                "--model",
                "gpt-x",
                "--effort",
                "high",
            ],
        )
        self.assertEqual(json.loads(out)["launched"][0]["receipt"], "recibo en texto")

    def test_argv_without_model_omits_effort(self) -> None:
        wave = self.write(
            {
                "run": "run_3",
                "cap_per_model": 1,
                "workers": [worker("t1", effort="high")],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "{}", ""

        self.run_main([str(wave)], fake)
        self.assertNotIn("--model", calls[0])
        self.assertNotIn("--effort", calls[0])

    def test_argv_new_child(self) -> None:
        wave = self.write(
            {
                "run": "run_2",
                "cap_per_model": 1,
                "workers": [
                    worker(
                        "t1",
                        worktree="new-child",
                        worktree_name="ab-t1",
                        base_branch="main",
                    )
                ],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "{}", ""

        self.run_main([str(wave)], fake)
        self.assertEqual(
            calls[0][-6:],
            ["--name", "ab-t1", "--setup", "skip", "--base-branch", "main"],
        )

    def test_failure_is_recorded_without_retry(self) -> None:
        wave = self.write(
            {"run": "run_4", "cap_per_model": 1, "workers": [worker("t1")]},
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 1, "", "boom"

        code, out, _ = self.run_main([str(wave)], fake)
        result = json.loads(out)
        self.assertEqual(code, 1)
        self.assertEqual(
            result["failed"], [{"name": "t1", "exit": 1, "stderr": "boom"}]
        )
        self.assertEqual(result["launched"], [])
        self.assertEqual(len(calls), 1)

    def test_dry_run_prints_commands_and_skips_execution(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 4,
                "workers": [worker(f"t{i}") for i in range(1, 7)],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "{}", ""

        code, out, err = self.run_main([str(wave), "--dry-run"], fake)
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertEqual(len(result["commands"]), 4)
        self.assertIsInstance(result["commands"][0], list)
        self.assertEqual(len(result["launched"]), 4)
        self.assertEqual(result["deferred"], ["t5", "t6"])
        self.assertIsNone(result["launched"][0]["exit"])
        self.assertIn("worker-start", result["launched"][0]["command"])
        lines = [line for line in err.splitlines() if line.strip()]
        self.assertEqual(len(lines), 4)

    def test_receipt_write_error_is_reported(self) -> None:
        wave = self.write({"run": "r", "cap_per_model": 1, "workers": [worker("t1")]}, "wave.json")
        handle = mock.Mock()
        handle.write.side_effect = OSError("disk full")
        with mock.patch.object(Path, "open", return_value=handle):
            # read_wave uses read_text, which also opens: patch it independently.
            with mock.patch.object(launch_wave, "read_wave", return_value={"run": "r", "cap": 1, "workers": [worker("t1")]}):
                code, out, err = self.run_main([str(wave), "--receipts", "receipts"], lambda args: (0, "{}", ""))
        self.assertEqual(code, 1)
        self.assertIn("disk full", err)
        self.assertIn("disk full", json.loads(out)["receipt_errors"][0])
        self.assertEqual(len(json.loads(out)["launched"]), 1)

    def test_unopenable_receipts_prevents_launch(self) -> None:
        wave = self.write({"run": "r", "cap_per_model": 1, "workers": [worker("t1")]}, "wave.json")
        fake = mock.Mock(return_value=(0, "{}", ""))
        code, out, err = self.run_main([str(wave), "--receipts", str(self.dir / "missing" / "r")], fake)
        self.assertEqual(code, 2)
        fake.assert_not_called()
        self.assertIn("error", json.loads(out))

    def test_receipts_file_gets_one_line_per_launch(self) -> None:
        wave = self.write(
            {
                "run": "run_6",
                "cap_per_model": 2,
                "workers": [worker("t1"), worker("t2")],
            },
            "wave.json",
        )
        receipts = self.dir / "receipts.jsonl"

        def fake(args: list[str]) -> tuple[int, str, str]:
            name = args[args.index("--spec-file") + 1]
            return 0, json.dumps({"spec": name}), ""

        code, _, _ = self.run_main([str(wave), "--receipts", str(receipts)], fake)
        self.assertEqual(code, 0)
        lines = receipts.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            sorted(json.loads(line)["spec"] for line in lines),
            ["ab/t1.md", "ab/t2.md"],
        )

    def test_nombre_repetido_sale_con_2_sin_lanzar(self) -> None:
        wave = self.write(
            {
                "run": "run_dup",
                "cap_per_model": 4,
                "workers": [worker("g1"), worker("g1")],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "{}", ""

        code, out, err = self.run_main([str(wave)], fake)
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertIn("nombre repetido: g1", err)
        self.assertIn("nombre repetido: g1", json.loads(out)["error"])

    def test_invalid_json_exits_two(self) -> None:
        path = self.dir / "broken.json"
        path.write_text("{no es json", encoding="utf-8")
        code, out, _ = self.run_main([str(path)], lambda args: (0, "{}", ""))
        self.assertEqual(code, 2)
        self.assertIn("error", json.loads(out))

    def test_missing_spec_file_exits_two(self) -> None:
        data = {"run": "run_7", "cap_per_model": 1, "workers": [worker("t1")]}
        del data["workers"][0]["spec_file"]  # type: ignore[index]
        wave = self.write(data, "wave.json")
        code, out, _ = self.run_main([str(wave)], lambda args: (0, "{}", ""))
        self.assertEqual(code, 2)
        self.assertIn("spec_file", json.loads(out)["error"])

    def test_new_child_requires_worktree_name(self) -> None:
        wave = self.write(
            {
                "run": "run_8",
                "cap_per_model": 1,
                "workers": [worker("t1", worktree="new-child")],
            },
            "wave.json",
        )
        code, _, _ = self.run_main([str(wave)], lambda args: (0, "{}", ""))
        self.assertEqual(code, 2)

    def test_argv_new_top_level(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 1,
                "workers": [
                    worker(
                        "t1",
                        worktree="new-top-level",
                        repo="id:06de043a",
                        worktree_name="ab-t1",
                        base_branch="main",
                    )
                ],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "{}", ""

        self.run_main([str(wave)], fake)
        self.assertEqual(
            calls[0],
            [
                "orca",
                "orchestration",
                "worker-start",
                "--environment",
                "local",
                "--run",
                "run_5",
                "--spec-file",
                "ab/t1.md",
                "--task-title",
                "AB t1",
                "--worktree",
                "new-top-level",
                "--agent",
                "opencode",
                "--json",
                "--repo",
                "id:06de043a",
                "--name",
                "ab-t1",
                "--setup",
                "skip",
                "--base-branch",
                "main",
            ],
        )

    def test_new_top_level_without_base_branch(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 1,
                "workers": [
                    worker(
                        "t1",
                        worktree="new-top-level",
                        repo="id:06de043a",
                        worktree_name="ab-t1",
                    )
                ],
            },
            "wave.json",
        )
        calls: list[list[str]] = []

        def fake(args: list[str]) -> tuple[int, str, str]:
            calls.append(args)
            return 0, "{}", ""

        self.run_main([str(wave)], fake)
        self.assertEqual(
            calls[0][-6:],
            ["--repo", "id:06de043a", "--name", "ab-t1", "--setup", "skip"],
        )
        self.assertNotIn("--base-branch", calls[0])

    def test_new_top_level_requires_repo(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 2,
                "workers": [
                    worker("ok"),
                    worker("t1", worktree="new-top-level", worktree_name="ab-t1"),
                ],
            },
            "wave.json",
        )
        fake = mock.Mock(return_value=(0, "{}", ""))
        code, out, _ = self.run_main([str(wave)], fake)
        self.assertEqual(code, 2)
        self.assertIn("repo", json.loads(out)["error"])
        fake.assert_not_called()

    def test_new_top_level_requires_worktree_name(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 1,
                "workers": [worker("t1", worktree="new-top-level", repo="id:06de043a")],
            },
            "wave.json",
        )
        fake = mock.Mock(return_value=(0, "{}", ""))
        code, out, _ = self.run_main([str(wave)], fake)
        self.assertEqual(code, 2)
        self.assertIn("worktree_name", json.loads(out)["error"])
        fake.assert_not_called()

    def test_repo_rejected_with_current(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 1,
                "workers": [worker("t1", repo="id:06de043a")],
            },
            "wave.json",
        )
        fake = mock.Mock(return_value=(0, "{}", ""))
        code, out, _ = self.run_main([str(wave)], fake)
        self.assertEqual(code, 2)
        self.assertIn("repo", json.loads(out)["error"])
        fake.assert_not_called()

    def test_new_top_level_rejects_whitespace_only_required_fields(self) -> None:
        for field in ("repo", "worktree_name"):
            with self.subTest(field=field):
                fields = {"repo": "id:06de043a", "worktree_name": "ab-t1"}
                fields[field] = " \t "
                wave = self.write(
                    {
                        "run": "run_5",
                        "cap_per_model": 2,
                        "workers": [
                            worker("ok"),
                            worker("t1", worktree="new-top-level", **fields),
                        ],
                    },
                    "wave.json",
                )
                fake = mock.Mock(return_value=(0, "{}", ""))
                code, out, _ = self.run_main([str(wave)], fake)
                self.assertEqual(code, 2)
                self.assertIn(field, json.loads(out)["error"])
                fake.assert_not_called()

    def test_dry_run_new_top_level_includes_repo(self) -> None:
        wave = self.write(
            {
                "run": "run_5",
                "cap_per_model": 1,
                "workers": [
                    worker(
                        "t1",
                        worktree="new-top-level",
                        repo="id:06de043a",
                        worktree_name="ab-t1",
                    )
                ],
            },
            "wave.json",
        )
        fake = mock.Mock(return_value=(0, "{}", ""))
        code, out, _ = self.run_main([str(wave), "--dry-run"], fake)
        commands = json.loads(out)["commands"]
        self.assertEqual(code, 0)
        fake.assert_not_called()
        index = commands[0].index("--repo")
        self.assertEqual(commands[0][index + 1], "id:06de043a")


if __name__ == "__main__":
    unittest.main()
