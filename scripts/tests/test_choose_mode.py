"""Pruebas de costos, disponibilidad y preferencias del selector de modo."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import choose_mode  # noqa: E402


VALIDATOR_FAMILY = "distinta si hay; si no, sesión nueva ciega del mismo agente"


def run_main(*argv: str) -> tuple[int, str, str]:
    """Ejecuta el selector y captura sus dos canales de salida."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = choose_mode.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ChooseModeTest(unittest.TestCase):
    def seleccionar(self, chat, size, *args, status=0):
        code, out, err = run_main("--chat-tier", chat, "--size", size, *args)
        self.assertEqual(code, status, err)
        self.assertEqual(err, "")
        return json.loads(out)

    def test_frontera_mediana_directo(self):
        result = self.seleccionar("frontera", "mediana")
        self.assertEqual(result["mode"], "directo")
        self.assertEqual(result["options"]["directo"]["cost"], 4 * 10 + 3)
        self.assertEqual(result["options"]["delegado"]["cost"], 6.4 * 10 + 4 * 2 + 1 + 3)
        self.assertEqual(result["roles"], [
            {"role": "validador", "tier": "economico-capaz", "effort": "medio", "family": VALIDATOR_FAMILY}
        ])
        self.assertFalse(result["ask_user"])

    def test_economico_mediana_delegado_por_desempate(self):
        result = self.seleccionar("economico", "mediana")
        self.assertEqual(result["mode"], "delegado")
        options = result["options"]
        self.assertFalse(options["directo"]["feasible"])
        for mode in ("delegado", "coordinado"):
            self.assertTrue(options[mode]["feasible"])
            self.assertAlmostEqual(options[mode]["cost"], 6.4 + 4 * 2 + 1 + 3)
        self.assertEqual(result["roles"][0], {
            "role": "ejecutor", "tier": "economico-capaz", "effort": "medio",
        })

    def test_economico_capaz_chica_directo(self):
        self.assertEqual(self.seleccionar("economico-capaz", "chica")["mode"], "directo")

    def test_chat_sin_codigo_delega(self):
        self.assertEqual(self.seleccionar("frontera", "chica", "--chat-no-code")["mode"], "delegado")

    def test_grande_con_cuatro_partes_coordina_y_pregunta(self):
        result = self.seleccionar("economico", "grande", "--parts", "4")
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["options"]["coordinado"]["cost"], 8.8 + 10 * 4 + 4 + 3 + 21)
        self.assertTrue(result["ask_user"])
        self.assertEqual([role["role"] for role in result["roles"]], ["planificador", "ejecutor", "validador"])
        self.assertEqual(result["roles"][0], {"role": "planificador", "tier": "frontera", "effort": "alto"})
        self.assertEqual(result["roles"][1], {"role": "ejecutor", "tier": "medio", "effort": "alto"})

    def test_grande_de_riesgo_alto_reserva_frontera_para_planificar_y_validar(self):
        result = self.seleccionar("economico", "grande", "--risk", "alto")
        self.assertEqual(result["mode"], "coordinado")
        self.assertTrue(result["ask_user"])
        self.assertEqual(result["roles"][0], {"role": "planificador", "tier": "frontera", "effort": "alto"})
        self.assertEqual(result["roles"][1], {"role": "ejecutor", "tier": "medio", "effort": "alto"})
        self.assertEqual(result["options"]["coordinado"]["cost"], 8.8 + 10 * 4 + 1 + 11 + 21)
        self.assertIn("frontera describe la solución con detalle", result["reason"])
        self.assertIn("un modelo medio la escribe", result["reason"])

    def test_frontera_no_sustituye_a_un_ejecutor_sin_cuota(self):
        result = self.seleccionar("economico", "mediana", "--available", "frontera", status=1)
        self.assertIsNone(result["mode"])
        self.assertEqual(result["roles"], [])

    def test_verificado_coordina_con_dos_pases(self):
        result = self.seleccionar("frontera", "chica", "--verified")
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["options"]["coordinado"]["cost"], 56 + 2 + 1 + 2 * 3)
        self.assertEqual([role["role"] for role in result["roles"]], ["ejecutor", "validador", "validador"])
        self.assertFalse(result["options"]["delegado"]["feasible"])

    def test_trivial_verificado_tiene_dos_pases(self):
        result = self.seleccionar("economico", "trivial", "--verified")
        self.assertEqual(result["mode"], "coordinado")
        self.assertAlmostEqual(result["options"]["coordinado"]["cost"], 5.2 + 0.2 + 1 + 2 * 3)
        validator = {"role": "validador", "tier": "economico-capaz", "effort": "medio",
                     "family": VALIDATOR_FAMILY}
        self.assertEqual(result["roles"][1:], [validator, validator])

    def test_sin_ejecutor_devuelve_codigo_uno(self):
        result = self.seleccionar("economico", "mediana", "--available", "gratis,economico", status=1)
        self.assertIsNone(result["mode"])
        self.assertEqual(result["roles"], [])
        self.assertFalse(result["ask_user"])
        self.assertTrue(all(not option["feasible"] for option in result["options"].values()))

    def test_argumentos_invalidos_devuelven_codigo_dos(self):
        cases = [
            ("--chat-tier", "marciano", "--size", "chica"),
            ("--chat-tier", "gratis", "--size", "chica", "--parts", "0"),
            ("--chat-tier", "gratis", "--size", "chica", "--parts", "dos"),
            ("--chat-tier", "gratis", "--size", "chica", "--available", ""),
            ("--chat-tier", "gratis", "--size", "chica", "--available", "gratis,marciano"),
        ]
        for args in cases:
            with self.subTest(args=args):
                code, out, err = run_main(*args)
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("error: "), err)

    def test_parts_limita_el_rango_antes_de_calcular(self):
        for parts in ("0", "51", "1" + "0" * 309):
            with (
                self.subTest(parts=parts),
                mock.patch.object(choose_mode, "choose", return_value={"mode": None}) as choose,
            ):
                code, out, err = run_main("--chat-tier", "gratis", "--size", "chica", "--parts", parts)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("entre 1 y 50", err)
                choose.assert_not_called()
        result = self.seleccionar("gratis", "trivial", "--parts", "50")
        self.assertAlmostEqual(result["options"]["coordinado"]["cost"], 1.04 + 0.2 + 50 + 21)

    def test_trivial_directo_sin_validador(self):
        for chat in ("gratis", "economico", "economico-capaz", "medio", "frontera"):
            with self.subTest(chat=chat):
                result = self.seleccionar(chat, "trivial")
                self.assertEqual(result["mode"], "directo")
                self.assertEqual(result["roles"], [])

    def test_preferencia_factible_e_imposible(self):
        result = self.seleccionar("frontera", "mediana", "--prefer", "coordinado")
        self.assertEqual(result["mode"], "coordinado")
        result = self.seleccionar("economico", "mediana", "--prefer", "directo")
        self.assertEqual(result["mode"], "delegado")
        self.assertIn("directo", result["reason"])

    def test_riesgo_alto_sube_el_minimo_y_exige_frontera(self):
        result = self.seleccionar("medio", "mediana", "--risk", "alto")
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["roles"][1]["tier"], "medio")
        self.assertEqual(result["roles"][2], {
            "role": "validador", "tier": "frontera", "effort": "alto", "family": VALIDATOR_FAMILY,
        })
        self.assertTrue(result["ask_user"])
        result = self.seleccionar("frontera", "mediana", "--risk", "alto", "--available", "medio", status=1)
        self.assertIsNone(result["mode"])

    def test_disponibilidad_del_validador(self):
        result = self.seleccionar("economico", "chica", "--available", "medio,economico")
        self.assertEqual(result["roles"][0]["tier"], "medio")
        result = self.seleccionar("frontera", "chica", "--available", "economico", status=1)
        self.assertIsNone(result["mode"])


if __name__ == "__main__":
    unittest.main()
