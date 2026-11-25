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

    def test_acepta_bom_y_parafrasis_equivalente_de_topes(self) -> None:
        payload = self.payload("resources")
        argv = payload["argv"]
        payload["argv"] = [argv[0], argv[1], "--cache-dir", "eval-cache", "--reserve-window", "week=90", "--reserve", "80", "--reserve-window", "5h=95", "--exhausted", "claude:claude-haiku-5-5", "--exhausted", "opencode:opencode-go/deepseek-v4.1-flash"]
        path = Path(self.tmp.name) / "bom.json"; path.write_text("\ufeff" + json.dumps(payload), encoding="utf-8")
        self.assertEqual(verify.main(["resources", str(path)]), 0)

    def test_rechaza_topes_reasignados_ventana_ausente_y_tanda_erronea(self) -> None:
        bad = self.payload("resources"); bad["argv"] = [x.replace("5h=95", "5h=90").replace("week=90", "week=95") for x in bad["argv"]]
        self.assertEqual(self.run_case("resources", bad), 1)
        bad = self.payload("resources"); bad["argv"].remove("week=90"); self.assertEqual(self.run_case("resources", bad), 1)
        bad = self.payload("wave"); bad["argv"] = ["python", "scripts/launch_wave.py", "--wave", "wave.json", "--dry-run"]
        self.assertEqual(self.run_case("wave", bad), 1)

    def test_contratos_no_permiten_repeticiones_opciones_y_spec_completo(self) -> None:
        bad = self.payload("resources"); bad["argv"] += ["--reserve", "10"]
        self.assertEqual(self.run_case("resources", bad), 1)
        bad = self.payload("choose"); bad["argv"] += ["--verified"]
        self.assertEqual(self.run_case("choose", bad), 1)
        spec = self.payload("spec")
        body = spec["files"]["spec.md"].replace("topes 80/95/90", "reserva general de 80 %, reserva de 95 % para la ventana de 5 horas y reserva de 90 % para la ventana semanal")
        body += "\n## Puede editar\n- eval/tools/fixtures.py\n## LÃ­mites del proyecto\nSin red, sin Orca real ni datos de cuenta.\n"
        spec["files"]["spec.md"] = body
        self.assertEqual(self.run_case("spec", spec), 0)
        for phrase in ("sin Orca real", "datos de cuenta"):
            missing = self.payload("spec"); missing["files"]["spec.md"] = missing["files"]["spec.md"].replace(phrase, "")
            self.assertEqual(self.run_case("spec", missing), 1)

    def test_prompt_publico_no_expone_fixture(self) -> None:
        out = prompt.main(["wave"])
        self.assertEqual(out, 0)

if __name__ == "__main__":
    unittest.main()
