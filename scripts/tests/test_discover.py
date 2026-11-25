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

    def test_cache_path_traduce_rutas_git_bash_en_windows(self) -> None:
        with mock.patch.object(discover, "IS_WINDOWS", True):
            self.assertEqual(
                discover.cache_path("/c/Users/x/roster.json"),
                Path("C:/Users/x/roster.json"),
            )
            self.assertEqual(discover.cache_path("/D/datos"), Path("D:/datos"))
            self.assertEqual(discover.cache_path("/c"), Path("C:/"))
            self.assertEqual(discover.cache_path("/cache/x.json"), Path("/cache/x.json"))
            self.assertEqual(discover.cache_path("C:/a/b.json"), Path("C:/a/b.json"))

    def test_cache_invalida_se_regenera(self) -> None:
        casos = {
            "json incompleto": b'{"incompleto": ',
            "utf-8 inválido": b"\xff",
            "NaN": b'{"valor": NaN}',
            "Infinity": b'{"valor": Infinity}',
            "-Infinity": b'{"valor": -Infinity}',
            "entero demasiado largo": b"[" + b"1" * 5000,
        }
        for caso, contenido in casos.items():
            with self.subTest(caso=caso):
                self.cache.write_bytes(contenido)
                fake = self.fake()
                with mock.patch.object(discover, "run_cmd", fake):
                    code, out, err = run_main(["--cache", str(self.cache)])
                self.assertEqual(code, 0, err)
                self.assertEqual(len(fake.calls), 2)
                self.assertEqual(self.cache.read_text(encoding="utf-8"), out)
                self.assertEqual(json.loads(out)["agents"], ["claude", "codex", "opencode"])

    def test_cache_con_error_de_recursion_se_regenera(self) -> None:
        cached = "[["
        self.cache.write_text(cached, encoding="utf-8")
        loads = json.loads

        def decode(text: str, **kwargs: object) -> object:
            if text == cached:
                raise RecursionError("anidamiento excesivo")
            return loads(text, **kwargs)

        fake = self.fake()
        with (
            mock.patch.object(discover.json, "loads", side_effect=decode),
            mock.patch.object(discover, "run_cmd", fake),
        ):
            code, out, err = run_main(["--cache", str(self.cache)])
        self.assertEqual(code, 0, err)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(self.cache.read_text(encoding="utf-8"), out)

    def test_cache_ilegible_devuelve_2(self) -> None:
        self.cache.write_text("{}", encoding="utf-8")
        fake = mock.Mock()
        with (
            mock.patch.object(discover.Path, "read_text", side_effect=OSError("acceso denegado")),
            mock.patch.object(discover, "run_cmd", fake),
        ):
            code, out, err = run_main(["--cache", str(self.cache)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(err, f"error: no se pudo leer la caché en {self.cache}: acceso denegado\n")
        fake.assert_not_called()

    def test_cache_path_no_cambia_fuera_de_windows(self) -> None:
        with mock.patch.object(discover, "IS_WINDOWS", False):
            self.assertEqual(
                discover.cache_path("/c/Users/x/roster.json"),
                Path("/c/Users/x/roster.json"),
            )

    @unittest.skipUnless(os.name == "nt", "la forma Git Bash solo aplica en Windows")
    def test_cache_acepta_ruta_git_bash(self) -> None:
        drive, rest = os.path.splitdrive(str(self.cache))
        bash = "/" + drive[0].lower() + rest.replace("\\", "/")
        with mock.patch.object(discover, "run_cmd", self.fake()):
            code, out, err = run_main(["--cache", bash])
        self.assertEqual(code, 0, err)
        self.assertTrue(self.cache.is_file())
        self.assertEqual(json.loads(self.cache.read_text(encoding="utf-8")), json.loads(out))

        def explota(args: list[str]) -> tuple[int, str, str]:
            raise AssertionError(f"no debía ejecutarse: {args}")

        with mock.patch.object(discover, "run_cmd", explota):
            code, cached_out, err = run_main(["--cache", bash])
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(cached_out), json.loads(out))

    def test_cache_es_un_directorio_devuelve_2(self) -> None:
        carpeta = self.dir / "carpeta"
        carpeta.mkdir()
        with mock.patch.object(discover, "run_cmd", self.fake()):
            code, out, err = run_main(["--cache", str(carpeta)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no se pudo escribir la caché en", err)

    def test_cache_con_padre_archivo_devuelve_2(self) -> None:
        archivo = self.dir / "archivo.txt"
        archivo.write_text("x", encoding="utf-8")
        with mock.patch.object(discover, "run_cmd", self.fake()):
            code, out, err = run_main(["--cache", str(archivo / "roster.json")])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no se pudo escribir la caché en", err)

    def test_cache_sin_archivo_tras_escribir_devuelve_2(self) -> None:
        with (
            mock.patch.object(discover.Path, "write_text", lambda self, *a, **k: 0),
            mock.patch.object(discover, "run_cmd", self.fake()),
        ):
            code, out, err = run_main(["--cache", str(self.cache)])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("no se pudo escribir la caché en", err)

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
