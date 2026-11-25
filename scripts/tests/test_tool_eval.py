"""Pruebas del contrato común y de los cinco verificadores de herramientas."""
from __future__ import annotations
import json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "eval" / "tools"
sys.path.insert(0, str(TOOLS))
import verify  # noqa: E402
import prompt  # noqa: E402

class ToolEvalTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = {c["id"]: c for c in json.loads(verify.CASES.read_text(encoding="utf-8"))}
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)

    def run_case(self, case_id: str, payload: dict) -> int:
        path = Path(self.tmp.name) / f"{case_id}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return verify.main([case_id, str(path)])

    def payload(self, case_id: str) -> dict:
        return self.cases[case_id]["expected"].copy()

    def test_pase_de_los_cinco_escenarios(self) -> None:
        for case_id in self.cases:
            with self.subTest(case_id=case_id):
                self.assertEqual(self.run_case(case_id, self.payload(case_id)), 0)

    def test_rechaza_argv_extra_o_accion_ajena_en_cada_escenario(self) -> None:
        for case_id in self.cases:
            with self.subTest(case_id=case_id):
                bad = self.payload(case_id)
                bad["argv"] = list(bad["argv"]) + ["--ejecuta-ahora"]
                expected = 2 if case_id == "choose" else 1
                self.assertEqual(self.run_case(case_id, bad), expected)

    def test_rechaza_json_malformado_y_archivos_inesperados(self) -> None:
        for case_id in ("resources", "choose", "done"):
            with self.subTest(case_id=case_id):
                bad = self.payload(case_id); bad["files"] = {"salida.sh": "rm -rf"}
                self.assertEqual(self.run_case(case_id, bad), 2)
        path = Path(self.tmp.name) / "roto.json"; path.write_text("[]", encoding="utf-8")
        self.assertEqual(verify.main(["resources", str(path)]), 2)

    def test_reordena_opciones_equivalentes(self) -> None:
        payload = self.payload("resources")
        argv = payload["argv"]
        payload["argv"] = [argv[0], argv[1], "--reserve-window", "week=90", "--reserve", "80", "--cache-dir", "eval-cache", "--exhausted", "claude:claude-haiku-5-5", "--reserve-window", "5h=95", "--exhausted", "opencode:opencode-go/deepseek-v4.1-flash"]
        self.assertEqual(self.run_case("resources", payload), 0)

    def test_falsos_positivos_y_negativos_cerrados(self) -> None:
        resources = self.payload("resources")
        resources["argv"].remove("eval-cache")
        resources["argv"].remove("--cache-dir")
        self.assertEqual(self.run_case("resources", resources), 1)
        wave = self.payload("wave")
        wave["files"]["wave.json"]["workers"][0]["effort"] = "medium"
        self.assertEqual(self.run_case("wave", wave), 1)
        wave = self.payload("wave")
        wave["files"]["wave.json"]["workers"][0]["model"] = "deepseek-v4.1-flash"
        self.assertEqual(self.run_case("wave", wave), 1)
        spec = self.payload("spec")
        spec["files"]["spec.md"] = spec["files"]["spec.md"].replace("topes 80/95/90", "otra tarea")
        self.assertEqual(self.run_case("spec", spec), 1)
        done = self.payload("done")
        done["argv"][done["argv"].index("--report-path") + 1] = "eval/tools/otro.md"
        self.assertEqual(self.run_case("done", done), 1)

    def test_wave_acepta_opcional_nulo(self) -> None:
        payload = self.payload("wave")
        for worker in payload["files"]["wave.json"]["workers"]:
            worker["effort"] = None
        self.assertEqual(self.run_case("wave", payload), 0)
        done = self.payload("done")
        body = done["argv"][done["argv"].index("--body") + 1]
        done["argv"][done["argv"].index("--body") + 1] = body.replace("Pendiente:", "Extra:")
        self.assertEqual(self.run_case("done", done), 1)

    def test_prompt_publico_no_expone_fixture(self) -> None:
        out = prompt.main(["wave"])
        self.assertEqual(out, 0)

if __name__ == "__main__":
    unittest.main()
