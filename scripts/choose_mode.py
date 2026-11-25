#!/usr/bin/env python3
"""Elige el modo de trabajo factible de menor costo relativo."""

from __future__ import annotations

import argparse
import json
import sys

if __package__:
    from .discover import use_utf8_stdout
else:
    from discover import use_utf8_stdout


# Estimaciones relativas calibradas con el A/B justo de docs/evaluation.md.
W_TIER = {"gratis": 0.2, "economico": 1, "economico-capaz": 2, "medio": 4, "frontera": 10}
WORK = {"trivial": 1, "chica": 2, "mediana": 4, "grande": 10}
FLOOR = {"trivial": "gratis", "chica": "economico", "mediana": "economico-capaz", "grande": "medio"}
OVERHEAD = 1.0
COORD_FIXED = 4.8
COORD_RATE = 0.4
EFFORT = {"trivial": "bajo", "chica": "bajo", "mediana": "medio", "grande": "alto"}
TIERS = tuple(W_TIER)
MODES = ("directo", "delegado", "coordinado")


class Parser(argparse.ArgumentParser):
    """Devuelve al punto de entrada los errores de sintaxis."""

    def error(self, message: str) -> None:
        """Informa que la sintaxis es inválida y remite a la ayuda."""
        raise ValueError("argumentos inválidos. Consulta --help para ver la sintaxis.")


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Lee y valida los niveles y las restricciones de la tarea."""
    parser = Parser(description=__doc__, allow_abbrev=False, usage=(
        "%(prog)s --chat-tier NIVEL --size {trivial,chica,mediana,grande} "
        "[--parts N] [--risk {bajo,alto}] [--verified] [--chat-no-code] "
        "[--available NIVEL[,NIVEL...]] [--prefer {auto,directo,delegado,coordinado}]"
    ))
    parser.add_argument("--chat-tier", required=True, metavar="NIVEL")
    parser.add_argument("--size", required=True, metavar="{trivial,chica,mediana,grande}")
    parser.add_argument("--parts", default="1", metavar="N", help="partes independientes, de 1 a 50")
    parser.add_argument("--risk", default="bajo", metavar="{bajo,alto}")
    parser.add_argument("--verified", action="store_true")
    parser.add_argument("--chat-no-code", action="store_true")
    parser.add_argument("--available", default=",".join(TIERS), metavar="NIVEL[,NIVEL...]")
    parser.add_argument("--prefer", default="auto", metavar="{auto,directo,delegado,coordinado}")
    args = parser.parse_args(argv)
    for flag, value, allowed in (
        ("--chat-tier", args.chat_tier, TIERS),
        ("--size", args.size, WORK),
        ("--risk", args.risk, ("bajo", "alto")),
        ("--prefer", args.prefer, ("auto", *MODES)),
    ):
        if value not in allowed:
            raise ValueError(f"valor inválido para {flag}: {value!r}")
    parts_error = "--parts debe ser un entero entre 1 y 50."
    try:
        args.parts = int(args.parts)
    except ValueError:
        raise ValueError(parts_error) from None
    if not 1 <= args.parts <= 50:
        raise ValueError(parts_error)
    args.available = {tier.strip() for tier in args.available.split(",")}
    if args.available == {""}:
        raise ValueError("--available debe incluir al menos un nivel.")
    if args.available.difference(TIERS):
        raise ValueError("--available contiene un nivel desconocido o vacío.")
    return args


def cheapest_tier(floor: str, available: set[str], ceiling: str = "frontera") -> str | None:
    """Busca el nivel más barato con cuota entre el mínimo y el máximo."""
    eligible = TIERS[TIERS.index(floor):TIERS.index(ceiling) + 1]
    return next((tier for tier in eligible if tier in available), None)


def validation(args: argparse.Namespace) -> tuple[list[dict], float, str]:
    """Devuelve los pases de validación, su costo y cualquier impedimento."""
    if args.size == "trivial" and not args.verified:
        return [], 0, ""
    high_risk = args.risk == "alto"
    tier = cheapest_tier("frontera" if high_risk else "economico-capaz", args.available)
    if tier is None:
        return [], 0, "No hay cuota para el nivel de validación requerido."
    passes = 2 if args.verified else 1
    role = {"role": "validador", "tier": tier, "effort": "alto" if high_risk else "medio",
            "family": "distinta si hay; si no, sesión nueva ciega del mismo agente"}
    return [role.copy() for _ in range(passes)], passes * (W_TIER[tier] + OVERHEAD), ""


def evaluate(args: argparse.Namespace) -> tuple[dict, dict]:
    """Calcula factibilidad, costos y roles para los tres modos."""
    high_risk = args.risk == "alto"
    minimum = TIERS.index(FLOOR[args.size])
    floor = TIERS[min(minimum + high_risk, len(TIERS) - 1)]
    executor_floor = TIERS[min(minimum + high_risk, TIERS.index("medio"))]
    needs_planner = high_risk or args.size == "grande" or args.parts >= 3
    executor = cheapest_tier(executor_floor, args.available, ceiling="medio")
    validation_roles, validation_cost, validation_block = validation(args)
    executor_roles = [{"role": "ejecutor", "tier": executor, "effort": EFFORT[args.size]}]
    planner_roles = [{"role": "planificador", "tier": "frontera", "effort": "alto"}] if needs_planner else []

    chat_weight = W_TIER[args.chat_tier]
    work = WORK[args.size]
    direct_cost = work * chat_weight + validation_cost
    coord_cost = (COORD_FIXED + COORD_RATE * work) * chat_weight
    common_cost = coord_cost + work * W_TIER.get(executor, 0) + validation_cost
    planner_cost = 2 * W_TIER["frontera"] + OVERHEAD if needs_planner else 0

    executor_block = f"No hay cuota para un ejecutor elegible con nivel mínimo {executor_floor}." if not executor else ""
    run_block = ""
    if args.verified:
        run_block = "La entrega verificada requiere un Run coordinado."
    elif needs_planner:
        run_block = "La tarea requiere un planificador en un Run coordinado."

    direct_block = run_block
    if not direct_block and args.chat_no_code:
        direct_block = "El chat tiene restringida la implementación."
    if not direct_block and chat_weight < W_TIER[floor]:
        direct_block = f"El chat requiere nivel {floor} o superior para implementar."
    planner_block = ""
    if needs_planner and "frontera" not in args.available:
        planner_block = "No hay cuota de frontera para el planificador obligatorio."

    options = {
        "directo": option(direct_cost, direct_block or validation_block, "El chat implementa."),
        "delegado": option(common_cost + OVERHEAD, run_block or executor_block or validation_block,
                           "Un ejecutor implementa."),
        "coordinado": option(common_cost + args.parts * OVERHEAD + planner_cost,
                             executor_block or planner_block or validation_block,
                             "Un Run coordina la ejecución."),
    }
    roles = {
        "directo": validation_roles,
        "delegado": executor_roles + validation_roles,
        "coordinado": planner_roles + executor_roles + validation_roles,
    }
    return options, roles


def option(cost: float, blocker: str, why: str) -> dict:
    """Resume el costo de una opción factible o el motivo que la impide."""
    return {"feasible": not blocker, "cost": None if blocker else round(cost, 2), "why": blocker or why}


def choose(args: argparse.Namespace) -> dict:
    """Aplica la preferencia o elige por costo y orden de desempate."""
    options, roles = evaluate(args)
    feasible = [mode for mode in MODES if options[mode]["feasible"]]
    if args.prefer in feasible:
        mode = args.prefer
        reason = f"Se eligió {mode} por la preferencia indicada."
    else:
        mode = min(feasible, key=lambda name: options[name]["cost"], default=None)
        if args.prefer == "auto":
            subject = "El selector"
        else:
            subject = f"Como la preferencia {args.prefer} no es factible, el selector"
        if mode:
            reason = f"{subject} eligió {mode} por costo y número de sesiones."
        else:
            reason = f"{subject} no encontró opciones que cumplan los requisitos con los niveles disponibles."
    if mode == "coordinado" and args.size == "grande" and args.risk == "alto":
        reason = (f"{reason.removesuffix('.')}, con un Run en el que la frontera describe la solución con detalle "
                  "y un modelo medio la escribe.")
    selected_roles = roles.get(mode, [])
    return {
        "mode": mode,
        "reason": reason,
        "options": options,
        "roles": selected_roles,
        "ask_user": any(role["tier"] == "frontera" for role in selected_roles),
    }


def main(argv: list[str] | None = None) -> int:
    """Imprime el resultado en JSON o un diagnóstico de uso en stderr."""
    use_utf8_stdout()
    try:
        args = parse_args(argv)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    result = choose(args)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["mode"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
