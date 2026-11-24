from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eval_kit  # noqa: E402

SCRIPT = Path(__file__).resolve().parents[1] / "eval_kit.py"
CASES = {
    "repeats": 1,
    "cases": [
        {
            "id": "caso-alfa",
            "prompt": "Encargo distintivo alfa",
            "criteria": [{"id": "c1", "description": "hace alfa", "critical": True}],
        },
        {
            "id": "caso-beta",
            "prompt": "Encargo distintivo beta",
            "criteria": [{"id": "c1", "description": "hace beta", "critical": False}],
        },
    ],
}
EXEC_TEMPLATE = "VARIANTE: {{VARIANT}}\nSALIDA: {{OUT}}\nENCARGO: {{PROMPT}}\n"
JUDGE_TEMPLATE = (
    "ENCARGO: {{PROMPT}}\nCASO: {{CASE}}\n"
    "P1: {{T1}} -> {{O1}}\nP2: {{T2}} -> {{O2}}\nCRITERIOS:\n{{CRITERIA}}\n"
)


class EvalKitTests(unittest.TestCase):
    """Cubre exec, pair ciego y merge de juicios ciegos."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.eval_dir = self.root / "eval"
        self.eval_dir.mkdir()
        (self.eval_dir / "cases.json").write_text(
            json.dumps(CASES), encoding="utf-8"
        )
        self.variant = self.root / "variante"
        self.variant.mkdir()
        (self.variant / "SKILL.md").write_text("# skill\n", encoding="utf-8")
        self.exec_tpl = self.root / "exec.md"
        self.exec_tpl.write_text(EXEC_TEMPLATE, encoding="utf-8")
        self.judge_tpl = self.root / "judge.md"
        self.judge_tpl.write_text(JUDGE_TEMPLATE, encoding="utf-8")

    def run_kit(self, *args: str) -> tuple[int, str, str]:
        """Ejecuta main y devuelve código, stdout y stderr."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = eval_kit.main(["--dir", str(self.eval_dir), *args])
        return code, out.getvalue(), err.getvalue()

    def run_exec(self, *args: str) -> list[str]:
        """Corre exec y devuelve los tids."""
        code, out, _ = self.run_kit(
            "exec",
            "--variant-dir",
            str(self.variant),
            "--label",
            "original",
            "--template",
            str(self.exec_tpl),
            *args,
        )
        self.assertEqual(code, 0)
        return json.loads(out)["tids"]

    def map(self) -> dict[str, dict[str, object]]:
        """Lee el mapa de ensayos."""
        return json.loads((self.eval_dir / "trials" / "map.json").read_text("utf-8"))

    def assert_opaque_names(self) -> None:
        """Ningún archivo generado delata etiqueta ni caso."""
        forbidden = ("original", "candidata", "caso-alfa", "caso-beta")
        for path in self.eval_dir.rglob("*"):
            for token in forbidden:
                self.assertNotIn(token, path.name.lower(), str(path))

    def test_exec_creates_opaque_specs_and_map(self) -> None:
        tids = self.run_exec()
        self.assertEqual(len(tids), 2)
        self.assertEqual(len(set(tids)), 2)
        specs = sorted((self.eval_dir / "specs").glob("exec-*.md"))
        self.assertEqual(len(specs), 2)
        for spec in specs:
            self.assertRegex(spec.name, r"^exec-t[0-9a-f]{8}\.md$")
            text = spec.read_text(encoding="utf-8")
            self.assertIn(str(self.variant), text)
            self.assertIn(str(self.eval_dir / "trials"), text)
        mapping = self.map()
        self.assertEqual(set(mapping), set(tids))
        self.assertEqual(sorted(item["case"] for item in mapping.values()), ["caso-alfa", "caso-beta"])
        self.assertTrue(all(item["variant"] == "original" for item in mapping.values()))
        self.assertTrue(all(item["repeat"] == 1 for item in mapping.values()))
        self.assert_opaque_names()

    def test_short_label_rejected(self) -> None:
        code, _, _ = self.run_kit("exec", "--variant-dir", str(self.variant), "--label", "t", "--template", str(self.exec_tpl))
        self.assertEqual(code, 2)

    def test_pair_rejects_different_cases(self) -> None:
        tids = self.run_exec()
        mapping = self.map()
        by_case = {item["case"]: tid for tid, item in mapping.items()}
        code, _, _ = self.run_kit(
            "pair",
            "--a",
            by_case["caso-alfa"],
            "--b",
            by_case["caso-beta"],
            "--template",
            str(self.judge_tpl),
            "--out-dir",
            str(self.root / "juicios"),
        )
        self.assertEqual(code, 2)

    def test_pair_writes_case_text_and_criteria(self) -> None:
        tids = self.run_exec()
        extra = self.run_exec("--case", "caso-alfa")
        alfa = [tid for tid in tids + extra if self.map()[tid]["case"] == "caso-alfa"]
        self.assertEqual(len(alfa), 2)
        out_dir = self.root / "juicios"
        code, out, _ = self.run_kit(
            "pair",
            "--a",
            alfa[0],
            "--b",
            alfa[1],
            "--template",
            str(self.judge_tpl),
            "--out-dir",
            str(out_dir),
        )
        self.assertEqual(code, 0)
        spec = Path(json.loads(out)["spec"])
        self.assertRegex(spec.name, r"^pjudge-[0-9a-f]{8}\.md$")
        text = spec.read_text(encoding="utf-8")
        self.assertIn("Encargo distintivo alfa", text)
        self.assertIn("caso-alfa", text)
        self.assertIn("- c1: hace alfa", text)
        for tid in alfa:
            self.assertIn(str(self.eval_dir / "trials" / f"{tid}.md"), text)
            self.assertIn(str(out_dir / f"{tid}.json"), text)
        self.assert_opaque_names()

    def test_merge_collects_and_reports_missing(self) -> None:
        tids = self.run_exec()
        judgments_dir = self.root / "juicios"
        judgments_dir.mkdir()
        for tid in tids:
            case = self.map()[tid]["case"]
            item = {
                "judgments": [
                    {
                        "case": case,
                        "criterion": "c1",
                        "repeat": 1,
                        "passed": True,
                        "evidence": "cita",
                    }
                ]
            }
            (judgments_dir / f"{tid}.json").write_text(json.dumps(item), encoding="utf-8")
        out_file = self.root / "merge.json"
        code, out, _ = self.run_kit(
            "merge",
            "--label",
            "original",
            "--judgments",
            str(judgments_dir),
            "--out",
            str(out_file),
        )
        self.assertEqual(code, 0)
        merged = json.loads(out_file.read_text(encoding="utf-8"))
        self.assertEqual(len(merged["judgments"]), 2)
        self.assertEqual(json.loads(out)["judgments"], 2)
        (judgments_dir / f"{tids[0]}.json").unlink()
        code, _, err = self.run_kit(
            "merge",
            "--label",
            "original",
            "--judgments",
            str(judgments_dir),
            "--out",
            str(out_file),
        )
        self.assertEqual(code, 1)
        self.assertIn(tids[0], err)

    def test_help_exits_0(self) -> None:
        for argv in ([], ["exec"], ["pair"], ["merge"]):
            done = subprocess.run(
                [sys.executable, str(SCRIPT), *argv, "--help"], capture_output=True
            )
            self.assertEqual(done.returncode, 0, argv)


if __name__ == "__main__":
    unittest.main()
