"""Pruebas de check_spec.py con specs de ejemplo en una carpeta temporal."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import check_spec  # noqa: E402

SPEC_COMPLETA = """# Tarea

Solo puedes editar estos archivos; el resto queda fuera.

## Puede editar
- `scripts/a.py`

## Ejemplo
Entrada `x` y salida `y`.

## Comprobaciones
- `python -m unittest` en verde.

## Límites del proyecto
Sin dependencias nuevas.

No edites pruebas ni relajes pruebas existentes para que algo pase.

Cierra con worker_done.
"""

SPEC_EJEMPLO = """# Tarea

## Puede editar
- `scripts/a.py`

## Comprobaciones
- `python -m unittest` en verde.

Cierra con worker_done.
"""

SPEC_REVISION = """# Revisión

## Comprobaciones
Dime qué rompe.

Cierra con worker_done.
"""

SPEC_REVISION_OK = """# Revisión

## Qué devolver
Un veredicto.

Marca lo no verificable.

## Método
Qué leíste en el código y qué dedujiste.

Cierra con worker_done.
"""


SIN_REGLA_PRUEBAS = "sin regla: no debilitar pruebas"
SIN_REVISION_PRUEBAS = "sin comprobación: pruebas debilitadas"


def run_main(argv: list[str]) -> tuple[int, str, str]:
    """Ejecuta check_spec.main capturando salida y error."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = check_spec.main(argv)
    return code, out.getvalue(), err.getvalue()


class CheckSpecTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def spec(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_ejemplo_del_encargo(self) -> None:
        path = self.spec("ejemplo.md", SPEC_EJEMPLO)
        code, out, err = run_main([str(path)])

        self.assertEqual(code, 1, err)
        data = json.loads(out)[0]
        self.assertEqual(data["file"], str(path))
        self.assertFalse(data["ok"])
        self.assertEqual(data["missing"], ["Ejemplo", "Límites del proyecto"])
        self.assertEqual(data["warnings"], [SIN_REGLA_PRUEBAS])

    def test_implementacion_completa(self) -> None:
        path = self.spec("completa.md", SPEC_COMPLETA)
        code, out, _ = run_main([str(path)])

        self.assertEqual(code, 0)
        data = json.loads(out)[0]
        self.assertTrue(data["ok"])
        self.assertEqual(data["missing"], [])

    def test_etiquetas_sin_tildes_y_mayusculas(self) -> None:
        text = (
            "# Tarea\n\npuede editar: scripts/a.py\n\n## EJEMPLO\nx\n\n"
            "## comprobaciones\nnada\n\n## LIMITES DEL PROYECTO\nnada\n\nworker_done\n"
        )
        path = self.spec("tildes.md", text)
        code, out, _ = run_main([str(path)])

        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)[0]["ok"])

    def test_revision_incompleta(self) -> None:
        path = self.spec("revision.md", SPEC_REVISION)
        code, out, _ = run_main(["--kind", "revision", str(path)])

        self.assertEqual(code, 1)
        self.assertEqual(
            json.loads(out)[0]["missing"], ["no verificable", "Método y límites"]
        )

    def test_revision_completa_por_alternativas(self) -> None:
        path = self.spec("revision-ok.md", SPEC_REVISION_OK)
        code, out, _ = run_main(["--kind", "revision", str(path)])

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["missing"], [])

    def test_coletilla_no_delegues_es_advertencia(self) -> None:
        path = self.spec("coletilla.md", SPEC_COMPLETA + "\nNo delegues.\n")
        code, out, _ = run_main([str(path)])

        self.assertEqual(code, 0)
        data = json.loads(out)[0]
        self.assertTrue(data["ok"])
        self.assertEqual(data["warnings"], ["coletilla: No delegues"])

    def test_implementacion_sin_regla_de_pruebas_avisa(self) -> None:
        sin_regla = SPEC_COMPLETA.replace(
            "No edites pruebas ni relajes pruebas existentes para que algo pase.\n", ""
        )
        path = self.spec("sin-regla.md", sin_regla)
        code, out, _ = run_main([str(path)])

        self.assertEqual(code, 0)
        data = json.loads(out)[0]
        self.assertTrue(data["ok"])
        self.assertEqual(data["missing"], [])
        self.assertEqual(data["warnings"], [SIN_REGLA_PRUEBAS])

    def test_implementacion_con_regla_no_avisa(self) -> None:
        for frase in ("No relajes pruebas.", "Ninguna prueba se debilitó."):
            with self.subTest(frase=frase):
                sin_regla = SPEC_COMPLETA.replace(
                    "No edites pruebas ni relajes pruebas existentes para que algo pase.",
                    frase,
                )
                path = self.spec("con-regla.md", sin_regla)
                _, out, _ = run_main([str(path)])

                self.assertEqual(json.loads(out)[0]["warnings"], [])

    def test_revision_sin_comprobacion_de_pruebas_avisa(self) -> None:
        path = self.spec("revision-ok.md", SPEC_REVISION_OK)
        code, out, _ = run_main(["--kind", "revision", str(path)])

        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)[0]["warnings"], [SIN_REVISION_PRUEBAS])

        con = SPEC_REVISION_OK.replace(
            "Un veredicto.", "Un veredicto. Ninguna prueba existente se debilitó."
        )
        path = self.spec("revision-con.md", con)
        _, out, _ = run_main(["--kind", "revision", str(path)])

        self.assertEqual(json.loads(out)[0]["warnings"], [])

    def test_revision_aviso_exige_frase_dentro_de_la_seccion(self) -> None:
        casos = {
            "fuera de la sección": SPEC_REVISION_OK + "\nSe debilitó una prueba.\n",
            "palabra suelta": SPEC_REVISION_OK.replace(
                "Un veredicto.", "Un veredicto; no debilites el análisis."
            ),
        }
        for nombre, texto in casos.items():
            with self.subTest(caso=nombre):
                path = self.spec("revision-falsa.md", texto)
                _, out, _ = run_main(["--kind", "revision", str(path)])

                self.assertEqual(
                    json.loads(out)[0]["warnings"], [SIN_REVISION_PRUEBAS]
                )
        for frase in ("pruebas debilitadas", "debilitar pruebas", "relajes pruebas"):
            with self.subTest(frase=frase):
                texto = SPEC_REVISION_OK.replace("Un veredicto.", f"1. Sin {frase}.")
                path = self.spec("revision-frase.md", texto)
                _, out, _ = run_main(["--kind", "revision", str(path)])

                self.assertEqual(json.loads(out)[0]["warnings"], [])

    def test_archivo_inexistente_devuelve_2(self) -> None:
        missing = self.dir / "no-existe.md"
        code, out, err = run_main([str(missing)])

        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("archivo no existe", err)

    def test_varios_archivos_una_linea_json_por_archivo(self) -> None:
        good = self.spec("buena.md", SPEC_COMPLETA)
        bad = self.spec("mala.md", SPEC_EJEMPLO)
        code, out, _ = run_main([str(good), str(bad)])

        self.assertEqual(code, 1)
        lines = json.loads(out)
        self.assertEqual([item["ok"] for item in lines], [True, False])

    def test_etiqueta_solo_como_prefijo_no_cuenta(self) -> None:
        text = (
            "# Tarea\n\n## Puede editar\n- `scripts/a.py`\n\n## Ejemplosidad: x\n\n"
            "## Comprobaciones\n- nada\n\n## Límites del proyecto\nnada\n\nworker_done\n"
        )
        path = self.spec("prefijo.md", text)
        code, out, err = run_main([str(path)])

        self.assertEqual(code, 1, err)
        self.assertEqual(json.loads(out)[0]["missing"], ["Ejemplo"])

    def test_plurales_explicitos_aceptados(self) -> None:
        text = (
            "# Tarea\n\n## Pueden editar\n- `scripts/a.py`\n\n## Ejemplos\nx\n\n"
            "## Comprobación\n- nada\n\n## Límites del proyecto\nnada\n\nworker_done\n"
        )
        path = self.spec("plurales.md", text)
        code, out, err = run_main([str(path)])

        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)[0]["missing"], [])

    def test_ejemplos_en_negrita_aceptado(self) -> None:
        text = (
            "# Tarea\n\n## Puede editar\n- `scripts/a.py`\n\n**Ejemplos:** entrada y salida\n\n"
            "## Comprobaciones\n- nada\n\n## Límites del proyecto\nnada\n\nworker_done\n"
        )
        path = self.spec("ejemplos-negrita.md", text)
        code, out, err = run_main([str(path)])

        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)[0]["missing"], [])

    def test_plurales_inventados_rechazados(self) -> None:
        base = (
            "# Tarea\n\n## Puede editar\n- `scripts/a.py`\n\n## Ejemplo\nx\n\n"
            "## Comprobaciones\n- nada\n\n## Límites del proyecto\nnada\n\nworker_done\n"
        )
        cases = {
            "## Ejemplosidad: x": ("## Ejemplo", "Ejemplo"),
            "## Comprobacioneses": ("## Comprobaciones", "Comprobaciones"),
            "## Límites del proyectos": ("## Límites del proyecto", "Límites del proyecto"),
        }
        for falso, (real, falta) in cases.items():
            with self.subTest(linea=falso):
                path = self.spec("inventado.md", base.replace(real, falso))
                code, out, _ = run_main([str(path)])

                self.assertEqual(code, 1)
                self.assertEqual(json.loads(out)[0]["missing"], [falta])

        revision = (
            "# Revisión\n\n## Ques devolver\nnada\n\nno verificable\n\n"
            "## Método y límites\nnada\n\nworker_done\n"
        )
        path = self.spec("ques.md", revision)
        code, out, _ = run_main(["--kind", "revision", str(path)])

        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)[0]["missing"], ["Comprobaciones"])

    def test_metodos_y_limites_aceptado_en_revision(self) -> None:
        text = (
            "# Revisión\n\n## Qué devolver\nUn veredicto.\n\nno verificable\n\n"
            "## Métodos y límites\nnada\n\nworker_done\n"
        )
        path = self.spec("metodos.md", text)
        code, out, err = run_main(["--kind", "revision", str(path)])

        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)[0]["missing"], [])

    def test_help_sale_con_0(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with (
            contextlib.redirect_stdout(out),
            contextlib.redirect_stderr(err),
            self.assertRaises(SystemExit) as raised,
        ):
            check_spec.main(["--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--kind", out.getvalue())


if __name__ == "__main__":
    unittest.main()
