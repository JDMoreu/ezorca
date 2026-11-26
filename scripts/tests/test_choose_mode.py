"""Pruebas de la política calidad primero del selector de modo."""

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


FAMILY = "distinta si hay; si no, sesión nueva ciega del mismo agente"
LOOP = "corregir y revalidar hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas)"
ALL = "economico,medio,frontera"


def validator(tier: str = "frontera") -> dict:
    """Arma el rol de validador esperado."""
    return {"role": "validador", "tier": tier, "effort": "alto", "family": FAMILY, "loop": LOOP}


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

    def test_mediana_con_chat_frontera_delega_con_calidad(self):
        result = self.seleccionar("frontera", "mediana", "--available", ALL)
        self.assertEqual(result["mode"], "delegado")
        self.assertEqual(result["roles"], [
            {"role": "planificador", "tier": "frontera", "effort": "alto", "session": "chat"},
            {"role": "ejecutor", "tier": "medio", "effort": "alto"},
            validator(),
        ])
        self.assertIn("calidad primero", result["reason"])
        self.assertTrue(all(option["feasible"] for option in result["options"].values()))
        self.assertIsNotNone(result["options"]["delegado"]["cost"])

    def test_chica_sin_planificador_y_ejecutor_sube_a_medio(self):
        result = self.seleccionar("medio", "chica", "--available", ALL)
        self.assertEqual(result["mode"], "delegado")
        self.assertEqual(result["roles"], [
            {"role": "ejecutor", "tier": "medio", "effort": "medio"},
            validator(),
        ])

    def test_chica_usa_el_siguiente_nivel_si_existe(self):
        result = self.seleccionar("medio", "chica", "--available", "economico,economico-capaz,medio")
        self.assertEqual(result["roles"][0]["tier"], "economico-capaz")
        self.assertEqual(result["roles"][1]["tier"], "medio")

    def test_trivial_directo_sin_validador(self):
        for chat in ("gratis", "economico", "economico-capaz", "medio", "frontera"):
            with self.subTest(chat=chat):
                result = self.seleccionar(chat, "trivial")
                self.assertEqual(result["mode"], "directo")
                self.assertEqual(result["roles"], [])
                self.assertFalse(result["ask_user"])

    def test_grande_con_tres_partes_y_riesgo_alto_coordina(self):
        args = ("--parts", "3", "--risk", "alto", "--available", ALL)
        result = self.seleccionar("economico", "grande", *args)
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["roles"], [
            {"role": "planificador", "tier": "frontera", "effort": "alto"},
            {"role": "ejecutor", "tier": "medio", "effort": "alto", "count": 3},
            validator(), validator(),
        ])
        self.assertTrue(result["ask_user"])
        result = self.seleccionar("economico", "grande", *args, "--frontier-ok")
        self.assertFalse(result["ask_user"])

    def test_dos_partes_coordinan(self):
        result = self.seleccionar("frontera", "chica", "--parts", "2", "--available", ALL)
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["roles"][1]["count"], 2)
        self.assertEqual(len([r for r in result["roles"] if r["role"] == "validador"]), 1)

    def test_ejecutor_sin_piso_no_es_factible(self):
        result = self.seleccionar("economico", "mediana", "--available", "economico", status=1)
        self.assertIsNone(result["mode"])
        self.assertEqual(result["roles"], [])
        self.assertFalse(result["ask_user"])
        self.assertTrue(all(not option["feasible"] for option in result["options"].values()))

    def test_ejecutor_cae_al_piso_si_no_hay_nivel_superior(self):
        result = self.seleccionar("economico", "mediana", "--available", "economico-capaz")
        self.assertEqual(result["mode"], "delegado")
        self.assertEqual(result["roles"][1], {"role": "ejecutor", "tier": "economico-capaz", "effort": "alto"})
        self.assertEqual(result["roles"][2]["tier"], "economico-capaz")

    def test_el_ejecutor_nunca_es_frontera(self):
        result = self.seleccionar("economico", "mediana", "--available", "frontera", status=1)
        self.assertIsNone(result["mode"])

    def test_verificado_coordina_con_dos_pases(self):
        result = self.seleccionar("frontera", "chica", "--verified", "--available", ALL)
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual([role["role"] for role in result["roles"]],
                         ["planificador", "ejecutor", "validador", "validador"])
        self.assertFalse(result["options"]["directo"]["feasible"])
        self.assertFalse(result["options"]["delegado"]["feasible"])

    def test_trivial_verificado_tiene_dos_pases(self):
        result = self.seleccionar("economico", "trivial", "--verified", "--available", ALL)
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["roles"][2:], [validator(), validator()])

    def test_riesgo_alto_coordina_con_dos_pases(self):
        result = self.seleccionar("medio", "mediana", "--risk", "alto", "--available", ALL)
        self.assertEqual(result["mode"], "coordinado")
        self.assertEqual(result["roles"][1], {"role": "ejecutor", "tier": "medio", "effort": "alto", "count": 1})
        self.assertEqual(result["roles"][2:], [validator(), validator()])

    def test_planificador_y_validador_usan_el_nivel_mas_alto_disponible(self):
        result = self.seleccionar("economico", "mediana", "--available", "economico-capaz,medio")
        self.assertEqual(result["roles"][0], {"role": "planificador", "tier": "medio", "effort": "alto"})
        self.assertEqual(result["roles"][2]["tier"], "medio")
        self.assertFalse(result["ask_user"])

    def test_chat_sin_codigo_delega(self):
        result = self.seleccionar("frontera", "trivial", "--chat-no-code", "--available", ALL)
        self.assertEqual(result["mode"], "delegado")
        self.assertEqual([role["role"] for role in result["roles"]], ["ejecutor"])

    def test_preferencias(self):
        result = self.seleccionar("frontera", "mediana", "--prefer", "coordinado", "--available", ALL)
        self.assertEqual(result["mode"], "coordinado")
        result = self.seleccionar("frontera", "chica", "--prefer", "directo", "--available", ALL)
        self.assertEqual(result["mode"], "directo")
        self.assertEqual(result["roles"], [validator()])
        result = self.seleccionar("economico", "mediana", "--prefer", "directo", "--available", ALL)
        self.assertEqual(result["mode"], "delegado")
        self.assertIn("directo", result["reason"])
        result = self.seleccionar("frontera", "chica", "--prefer", "directo", "--verified", "--available", ALL)
        self.assertEqual(result["mode"], "coordinado")

    def test_respaldo_a_directo_exige_validador_del_nivel_del_chat(self):
        for chat in ("frontera", "medio"):
            with self.subTest(chat=chat):
                result = self.seleccionar(chat, "mediana", "--available", "economico", status=1)
                self.assertIsNone(result["mode"])
                self.assertFalse(result["options"]["directo"]["feasible"])
        result = self.seleccionar("medio", "mediana", "--available", "economico,frontera")
        self.assertEqual(result["mode"], "directo")
        self.assertEqual(result["roles"], [validator()])
        self.assertTrue(result["reason"].startswith("Respaldo: No hay cuota para un ejecutor"), result["reason"])
        result = self.seleccionar("frontera", "mediana", "--available", "economico,medio", status=0)
        self.assertEqual(result["mode"], "delegado")

    def test_planificador_del_chat_frontera_no_baja_de_nivel_ni_pregunta(self):
        result = self.seleccionar("frontera", "mediana", "--available", "economico-capaz,medio")
        self.assertEqual(result["roles"][0],
                         {"role": "planificador", "tier": "frontera", "effort": "alto", "session": "chat"})
        self.assertEqual(result["roles"][2]["tier"], "medio")
        self.assertFalse(result["ask_user"])
        result = self.seleccionar("medio", "mediana", "--available", ALL)
        self.assertNotIn("session", result["roles"][0])

    def test_trivial_con_riesgo_alto_lleva_un_validador(self):
        result = self.seleccionar("medio", "trivial", "--risk", "alto", "--available", ALL)
        self.assertEqual(result["mode"], "directo")
        self.assertEqual(result["roles"], [validator()])

    def test_ask_user_no_cuenta_al_chat_como_planificador(self):
        result = self.seleccionar("frontera", "mediana", "--available", ALL)
        self.assertTrue(result["ask_user"])  # el validador es una sesión nueva de frontera
        result = self.seleccionar("frontera", "mediana", "--available", ALL, "--frontier-ok")
        self.assertFalse(result["ask_user"])
        result = self.seleccionar("economico", "chica", "--available", "economico,medio")
        self.assertFalse(result["ask_user"])

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
        result = self.seleccionar("gratis", "chica", "--parts", "50")
        self.assertEqual(result["roles"][1]["count"], 50)


if __name__ == "__main__":
    unittest.main()
