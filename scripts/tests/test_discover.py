"""Pruebas de discover.py con ejecutores falsos (nunca tocan Orca real)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import discover  # noqa: E402

INSTALLED = {
    "ok": True,
    "result": {
        "agents": [
            {"id": "claude", "name": "Claude", "default": True},
            {"id": "codex", "name": "Codex", "default": False},
            {"id": "opencode", "name": "OpenCode", "default": False},
        ]
    },
}

MODELS = "\n".join(
    [
        "opencode-go/hy4-flash-free",
        "opencode-go/deepseek-v4.1-flash",
        "opencode-go/kimi-k3.1-pro",
    ]
) + "\n"


class FakeRun:
    """Sustituto de run_cmd que responde por nombre de ejecutable."""

    def __init__(self, responses: dict[str, tuple[int, str, str]]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> tuple[int, str, str]:
        self.calls.append(list(args))
        name = Path(args[0]).stem.lower()
        return self.responses.get(name, (1, "", "comando no configurado"))


def run_main(argv: list[str]) -> tuple[int, str, str]:
    """Ejecuta discover.main capturando salida y error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = discover.main(argv)
    return code, out.getvalue(), err.getvalue()


class DiscoverTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.cache = self.dir / "cache.json"

    def fake(self, models: tuple[int, str, str] | None = None) -> FakeRun:
        return FakeRun(
            {
                "orca": (0, json.dumps(INSTALLED), ""),
                "opencode": models or (0, MODELS, ""),
            }
        )

    def test_clasifica_escalones_y_agentes(self) -> None:
        with mock.patch.object(discover, "run_cmd", self.fake()):
            code, out, err = run_main([])

        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        data = json.loads(out)
        self.assertEqual(data["agents"], ["claude", "codex", "opencode"])
        self.assertIn("generated_at", data)

        tiers = {item["model"]: (item["agent"], item["tier"]) for item in data["models"]}
        self.assertEqual(tiers["opencode-go/hy4-flash-free"], ("opencode", "gratis"))
        self.assertEqual(tiers["opencode-go/deepseek-v4.1-flash"], ("opencode", "economico"))
        self.assertEqual(tiers["opencode-go/kimi-k3.1-pro"], ("opencode", "economico-capaz"))
        configured = {
            item["agent"]: item["tier"]
            for item in data["models"]
            if item["model"] == "configurado"
        }
        self.assertEqual(configured, {"claude": "frontera", "codex": "medio"})

    def test_cache_fresca_no_ejecuta_comandos(self) -> None:
        first = self.fake()
        with mock.patch.object(discover, "run_cmd", first):
            code, out, _ = run_main(["--cache", str(self.cache)])
        self.assertEqual(code, 0)
        self.assertTrue(self.cache.is_file())

        def explota(args: list[str]) -> tuple[int, str, str]:
            raise AssertionError(f"no debía ejecutarse: {args}")

        with mock.patch.object(discover, "run_cmd", explota):
            code, cached_out, _ = run_main(["--cache", str(self.cache)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(cached_out), json.loads(out))
        self.assertEqual(len(first.calls), 2)

    def test_cache_vieja_se_regenera(self) -> None:
        self.cache.write_text('{"viejo": true}\n', encoding="utf-8")
        old = time.time() - 13 * 3600
        os.utime(self.cache, (old, old))
        fake = self.fake()
        with mock.patch.object(discover, "run_cmd", fake):
            code, out, _ = run_main(["--cache", str(self.cache)])
        self.assertEqual(code, 0)
        self.assertEqual(len(fake.calls), 2)
        self.assertNotIn("viejo", self.cache.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(out)["agents"], ["claude", "codex", "opencode"])

    def test_opencode_models_falla_y_avisa(self) -> None:
        fake = self.fake(models=(1, "", "sin conexión"))
        with mock.patch.object(discover, "run_cmd", fake):
            code, out, err = run_main([])

        self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.assertEqual(data["warnings"], ["opencode models falló: sin conexión"])
        agents = {item["agent"] for item in data["models"]}
        self.assertNotIn("opencode", agents)
        self.assertIn("codex", agents)

    def test_orca_falla_devuelve_2(self) -> None:
        fake = FakeRun({"orca": (1, "", "orca no responde")})
        with mock.patch.object(discover, "run_cmd", fake):
            code, out, err = run_main([])

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("orca no responde", err)

    def test_respuesta_invalida_devuelve_2(self) -> None:
        fake = FakeRun({"orca": (0, "no es json", "")})
        with mock.patch.object(discover, "run_cmd", fake):
            code, out, err = run_main([])

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("respuesta inválida", err)

    def test_timeout_de_opencode_avisa_y_sigue(self) -> None:
        def fake_run(args: list[str], **kwargs: object) -> object:
            if "models" in args:
                raise subprocess.TimeoutExpired(cmd=args, timeout=30)
            return subprocess.CompletedProcess(args, 0, json.dumps(INSTALLED), "")

        with mock.patch.object(discover.subprocess, "run", fake_run):
            code, out, err = run_main([])

        self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.assertEqual(len(data["warnings"]), 1)
        self.assertIn("timeout", data["warnings"][0])
        self.assertIn("opencode models falló", data["warnings"][0])

    def test_timeout_de_orca_devuelve_2(self) -> None:
        def fake_run(args: list[str], **kwargs: object) -> object:
            raise subprocess.TimeoutExpired(cmd=args, timeout=120)

        with mock.patch.object(discover.subprocess, "run", fake_run):
            code, out, err = run_main([])

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("timeout", err)

    def test_run_cmd_real(self) -> None:
        code, out, err = discover.run_cmd([sys.executable, "-c", "print('hola')"])
        self.assertEqual((code, out.strip(), err), (0, "hola", ""))

    def test_help_sale_con_0(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with (
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as raised,
        ):
            discover.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--cache", out.getvalue())


if __name__ == "__main__":
    unittest.main()
