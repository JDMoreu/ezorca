"""Pruebas del catálogo de modelos y presupuesto."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import resources  # noqa: E402


def prices(models: dict[str, dict]) -> dict:
    return {"openai": {"models": models}, "anthropic": {"models": {}},
            "opencode-go": {"models": {}}}


class ResourcesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cache = self.root / "models.dev.json"
        self.account = {"result": {"rateLimits": {
            "claude": {"session": {"usedPercent": 92}, "weekly": {"usedPercent": 41}},
            "codex": {"session": {"usedPercent": 42}, "weekly": {"usedPercent": 77}},
            "opencodeGo": {"session": {"usedPercent": 34}, "weekly": {"usedPercent": 93},
                            "monthly": {"usedPercent": 100}},
        }}}

    def setup_sources(self, payload: dict | None = None) -> dict[str, tuple[int, str, str]]:
        codex = self.root / ".codex" / "models_cache.json"
        codex.parent.mkdir()
        codex.write_text(json.dumps({"models": [
            {"slug": "gpt-6-luna", "supported_reasoning_levels": [{"effort": "low"}, {"effort": "max"}]},
            {"slug": "gpt-6.2-sol", "supported_reasoning_levels": [{"effort": "low"}, {"effort": "max"}]},
        ]}), encoding="utf-8")
        self.payload = payload or prices({
            "gpt-6-luna": {"cost": {"input": .1, "output": .5}},
            "gpt-6.2-sol": {"cost": {"input": 2, "output": 10}},
        })
        self.cache.write_text(json.dumps(self.payload), encoding="utf-8")
        os.utime(self.cache, None)
        return {"orca": (0, json.dumps(self.account), ""),
                "opencode": (0, "", "" )}

    def invoke(self, reserve: int = 80, extra: list[str] | None = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        codex_path = self.root / "models_cache.json"
        with mock.patch.object(resources.Path, "home", return_value=self.root), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = resources.main(["--cache-dir", str(self.root), "--reserve", str(reserve), *(extra or [])])
        return code, out.getvalue(), err.getvalue()

    def test_presupuesto_y_niveles_del_ejemplo(self) -> None:
        responses = self.setup_sources()
        with mock.patch.object(resources, "run_cmd", side_effect=lambda args: responses.get(Path(args[0]).stem, (1, "", "no"))):
            code, out, _ = self.invoke()
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertTrue(data["plans"]["claude"]["blocked"])
        self.assertTrue(data["plans"]["opencodeGo"]["blocked"])
        self.assertEqual(data["pick"]["economico"][0]["m"], "codex:gpt-6-luna")
        self.assertIn("codex:gpt-6.2-sol", [x["m"] for x in data["pick"]["medio"]])
        with mock.patch.object(resources, "run_cmd", side_effect=lambda args: responses.get(Path(args[0]).stem, (1, "", "no"))):
            code, out, _ = self.invoke(70)
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(out)["plans"]["codex"]["blocked"])

    def test_reserva_especifica_de_plan(self) -> None:
        responses = self.setup_sources()
        with mock.patch.object(resources, "run_cmd", side_effect=lambda args: responses.get(Path(args[0]).stem, (1, "", "no"))):
            code, out, _ = self.invoke(70, ["--reserve-plan", "codex=95"])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["plans"]["codex"]["blocked"])
        self.assertEqual(json.loads(out)["reserve"], {"default": 70, "codex": 95})

    def test_reserva_por_ventana_prevalece(self) -> None:
        responses = self.setup_sources()
        options = ["--reserve-window", "5h=95", "--reserve-window", "week=90"]
        with mock.patch.object(resources, "run_cmd", side_effect=lambda args: responses.get(Path(args[0]).stem, (1, "", "no"))):
            code, out, _ = self.invoke(extra=options)
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertFalse(data["plans"]["claude"]["blocked"])
        self.assertFalse(data["plans"]["codex"]["blocked"])
        self.assertTrue(data["plans"]["opencodeGo"]["blocked"])

    def test_intenta_actualizar_precios_viejos(self) -> None:
        self.setup_sources()
        old = time.time() - 8 * 86400
        os.utime(self.cache, (old, old))
        called = []
        with mock.patch.object(resources, "download_prices", side_effect=lambda: (called.append(1) or self.payload)), \
             mock.patch.object(resources, "run_cmd", return_value=(0, json.dumps(self.account), "")):
            self.invoke()
        self.assertEqual(called, [1])

    def test_descarga_fallida_usa_archivo_viejo_y_avisa(self) -> None:
        self.setup_sources()
        old = time.time() - 8 * 86400
        os.utime(self.cache, (old, old))
        with mock.patch.object(resources, "download_prices", side_effect=OSError("sin red")), \
             mock.patch.object(resources, "run_cmd", return_value=(0, json.dumps(self.account), "")):
            code, out, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["warnings"])

    def test_sin_precios_termina_en_dos(self) -> None:
        with mock.patch.object(resources, "download_prices", side_effect=OSError("offline")):
            code, out, _ = self.invoke()
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_modelo_go_caro_bloqueado(self) -> None:
        self.setup_sources({"opencode-go": {"models": {"kimi-k3.1-pro": {"cost": {"input": 2, "output": 10}}}}})
        responses = {"orca": (0, json.dumps(self.account), ""), "opencode": (0, "opencode-go/kimi-k3.1-pro\n", "")}
        with mock.patch.object(resources, "run_cmd", side_effect=lambda args: responses.get(Path(args[0]).stem, (1, "", "no"))):
            code, out, _ = self.invoke()
        self.assertEqual(code, 1)
        self.assertIn("opencode-go/kimi-k3.1-pro", json.dumps(json.loads(out)["blocked"]))

    def test_json_compacto_y_full(self) -> None:
        entries = {f"model-{i}": {"cost": {"input": .1, "output": .5}} for i in range(60)}
        self.setup_sources({"openai": {"models": entries}})
        codex = self.root / ".codex" / "models_cache.json"
        codex.parent.mkdir(exist_ok=True)
        codex.write_text(json.dumps({"models": [{"slug": k, "supported_reasoning_levels": []} for k in entries]}), encoding="utf-8")
        responses = {"orca": (0, json.dumps(self.account), ""), "opencode": (0, "", "")}
        full = self.root / "full.json"
        with mock.patch.object(resources, "run_cmd", side_effect=lambda args: responses.get(Path(args[0]).stem, (1, "", "no"))):
            code, out, _ = self.invoke(extra=["--full", str(full)])
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertLessEqual(len(out.encode("utf-8")), 1500)
        self.assertTrue(full.is_file())
        self.assertEqual(len(json.loads(full.read_text(encoding="utf-8"))["models"]), 60)

    def test_ids_opencode_conservan_proveedor(self) -> None:
        payload = {"free-provider": {"models": {"flash": {"cost": {"input": 0, "output": 0}}}},
                   "other-provider": {"models": {"flash": {"cost": {"input": 0, "output": 0}}}}}
        self.setup_sources(payload)
        responses = {"orca": (0, json.dumps(self.account), ""),
                     "opencode": (0, "free-provider/flash\nother-provider/flash", "")}
        full = self.root / "full.json"
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke(extra=["--full", str(full)])
        ids = [m["m"] for m in json.loads(full.read_text(encoding="utf-8"))["models"]]
        self.assertEqual(code, 0)
        self.assertEqual(set(ids), {"opencode:free-provider/flash", "opencode:other-provider/flash"})

    def test_plan_estado_no_ok_bloqueado_y_avisado(self) -> None:
        responses = self.setup_sources()
        data = json.loads(json.dumps(self.account))
        data["result"]["rateLimits"]["codex"] = {"status": "exhausted", "session": None, "weekly": None}
        responses["orca"] = (0, json.dumps(data), "")
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke()
        result = json.loads(out)
        self.assertIn("codex", result["blocked"])
        self.assertTrue(any("codex" in item and "exhausted" in item for item in result["warnings"]))

    def test_orca_ausente_conserva_independientes_y_bloquea_dependientes(self) -> None:
        payload = {"openai": {"models": {"gpt-6-luna": {"cost": {"input": .1, "output": .5}}}},
                   "anthropic": {"models": {"claude-opus-5-5": {"cost": {"input": 1, "output": 1}}}},
                   "opencode-go": {"models": {"flash": {"cost": {"input": 0, "output": 0}}}},
                   "free-provider": {"models": {"flash": {"cost": {"input": 0, "output": 0}}}}}
        self.setup_sources(payload)
        responses = {"orca": (127, "", "orca no encontrado"),
                     "opencode": (0, "free-provider/flash\nopencode-go/flash", "")}
        full = self.root / "full.json"
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke(extra=["--full", str(full)])
        result = json.loads(out)
        models = {m["m"]: m for m in json.loads(full.read_text(encoding="utf-8"))["models"]}
        self.assertEqual(code, 0)
        self.assertEqual(result["pick"]["gratis"][0]["m"], "opencode:free-provider/flash")
        self.assertTrue(models["opencode:opencode-go/flash"]["blocked"])
        self.assertIn("Orca no disponible", models["opencode:opencode-go/flash"]["blocked"])
        self.assertTrue(any("Orca" in item or "orca" in item for item in result["warnings"]))

    def test_avisos_sin_precio_se_agrupan_y_salida_cabe(self) -> None:
        models = {f"missing-{i}": {"cost": None} for i in range(80)}
        models["flash"] = {"cost": {"input": 0, "output": 0}}
        self.setup_sources({"provider": {"models": models}})
        responses = {"orca": (0, json.dumps(self.account), ""), "opencode": (0, "provider/flash\n" +
                     "\n".join(f"provider/missing-{i}" for i in range(80)), "")}
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke()
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertLessEqual(len(out.encode("utf-8")), 1500)
        self.assertTrue(any("80" in item for item in result["warnings"]))

    def test_diagnostico_largo_de_comando_se_acota(self) -> None:
        responses = self.setup_sources()
        responses["opencode"] = (127, "", "error " * 1000)
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertLessEqual(len(out.encode("utf-8")), 1500)

    def test_exhausted_repetible_por_modelo_y_plan(self) -> None:
        payload = {"provider-a": {"models": {"flash": {"cost": {"input": 0, "output": 0}}}},
                   "provider-b": {"models": {"flash": {"cost": {"input": 0, "output": 0}}}},
                   "openai": {"models": {"gpt-6-luna": {"cost": {"input": .1, "output": .5}}}}}
        responses = self.setup_sources(payload)
        responses["opencode"] = (0, "provider-a/flash\nprovider-b/flash", "")
        full = self.root / "full.json"
        extra = ["--exhausted", "opencode:provider-a/flash", "--exhausted", "codex", "--full", str(full)]
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke(extra=extra)
        result = json.loads(out)
        models = {m["m"]: m for m in json.loads(full.read_text(encoding="utf-8"))["models"]}
        self.assertEqual(code, 0)
        self.assertEqual(result["pick"]["gratis"][0]["m"], "opencode:provider-b/flash")
        self.assertTrue(models["codex:gpt-6-luna"]["blocked"])
        self.assertIn("agotado", models["codex:gpt-6-luna"]["blocked"])
        with mock.patch.object(resources, "run_cmd", side_effect=lambda a: responses[Path(a[0]).stem]):
            code, out, _ = self.invoke(extra=["--exhausted", "opencode", "--exhausted", "codex"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["available"], [])

    def test_fallback_claude_por_familia(self) -> None:
        payload = {"anthropic": {"models": {
            "claude-opus-5-5": {"cost": {"input": 1, "output": 1}},
            "claude-sonnet-5-5": {"cost": {"input": 1, "output": 1}},
            "claude-haiku-5-5": {"cost": {"input": 1, "output": 1}},
            "claude-fable-5-2": {"cost": {"input": 1, "output": 1}},
        }}}
        with mock.patch.object(resources.Path, "home", return_value=self.root), \
             mock.patch.object(resources, "run_cmd", return_value=(0, "", "")), \
             mock.patch.object(resources, "latest_claude", return_value=["claude-opus-5-5"]):
            ids = [item[2] for item in resources.model_sources(payload, {"claude": {}}, [])]
        self.assertEqual(set(ids), set(payload["anthropic"]["models"]))


if __name__ == "__main__":
    unittest.main()
