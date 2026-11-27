#!/usr/bin/env python3
"""Elige el modo de trabajo de mayor calidad factible (luego eficiencia y costo)."""

from __future__ import annotations

import argparse
import json
import sys

if __package__:
    from .discover import use_utf8_stdout
else:
    from discover import use_utf8_stdout


# El costo solo informa y desempata; estimaciones relativas de un ensayo anterior (ver el Historial de docs/evaluation.md).
W_TIER = {"gratis": 0.2, "economico": 1, "economico-capaz": 2, "medio": 4, "frontera": 10}
WORK = {"trivial": 1, "chica": 2, "mediana": 4, "grande": 10}
FLOOR = {"trivial": "gratis", "chica": "economico", "mediana": "economico-capaz", "grande": "medio"}
OVERHEAD = 1.0
COORD_FIXED = 4.8
COORD_RATE = 0.4
EFFORT = {"trivial": "bajo", "chica": "medio", "mediana": "alto", "grande": "alto"}
FAMILY = "distinta si hay; si no, sesión nueva ciega del mismo agente"
LOOP = "corregir y revalidar hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas)"
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
        "[--parts N] [--risk {bajo,alto}] [--verified] [--chat-no-code] [--frontier-ok] "
        "[--available NIVEL[,NIVEL...]] [--prefer {auto,directo,delegado,coordinado}]"
    ))
    parser.add_argument("--chat-tier", required=True, metavar="NIVEL")
    parser.add_argument("--size", required=True, metavar="{trivial,chica,mediana,grande}")
    parser.add_argument("--parts", default="1", metavar="N", help="partes independientes, de 1 a 50")
    parser.add_argument("--risk", default="bajo", metavar="{bajo,alto}")
    parser.add_argument("--verified", action="store_true")
    parser.add_argument("--chat-no-code", action="store_true")
    parser.add_argument("--frontier-ok", action="store_true")
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


def highest(available: set[str]) -> str:
    """Devuelve el nivel más alto con cuota."""
    return max(available, key=TIERS.index)


def executor_tier(args: argparse.Namespace) -> str | None:
    """Elige el nivel sobre el piso, con tope medio; sin él, el piso mismo."""
    top = TIERS.index("medio")
    floor = min(TIERS.index(FLOOR[args.size]) + (args.risk == "alto"), top)
    for tier in TIERS[min(floor + 1, top):top + 1]:
        if tier in args.available:
            return tier
    return TIERS[floor] if TIERS[floor] in args.available else None


def needs_run(args: argparse.Namespace) -> bool:
    """Indica si la tarea exige un Run coordinado."""
    heavy = args.parts >= 2 or args.size == "grande" or args.risk == "alto"
    return args.verified or (heavy and args.size != "trivial")


def has_validator(args: argparse.Namespace) -> bool:
    """Indica si lleva validación (todo salvo lo trivial sin riesgo ni entrega verificada)."""
    return args.size != "trivial" or args.verified or args.risk == "alto"


def role_list(mode: str, args: argparse.Namespace, executor: str | None) -> list[dict]:
    """Arma planificador, ejecutor y validador del modo según la calidad."""
    top = highest(args.available)
    roles = []
    if mode == "coordinado" or (mode == "delegado" and args.size == "mediana"):
        chat = args.chat_tier == "frontera"
        roles.append({"role": "planificador", "tier": "frontera" if chat else top, "effort": "alto"} |
                     ({"session": "chat"} if chat else {}))
    if mode != "directo":
        executor_role = {"role": "ejecutor", "tier": executor, "effort": EFFORT[args.size]}
        roles.append(executor_role | ({"count": args.parts} if mode == "coordinado" else {}))
    if has_validator(args):
        passes = 2 if args.verified or (args.risk == "alto" and args.size != "trivial") else 1
        roles += [{"role": "validador", "tier": top, "effort": "alto", "family": FAMILY, "loop": LOOP}
                  for _ in range(passes)]
    return roles


def blockers(args: argparse.Namespace, executor: str | None) -> dict[str, str]:
    """Devuelve el impedimento de cada modo; vacío si es factible."""
    floor = TIERS[min(TIERS.index(FLOOR[args.size]) + (args.risk == "alto"), len(TIERS) - 1)]
    run = "La tarea o la entrega verificada requiere un Run coordinado." if needs_run(args) else ""
    direct = run
    if not direct and args.chat_no_code:
        direct = "El chat tiene restringida la implementación."
    if not direct and W_TIER[args.chat_tier] < W_TIER[floor]:
        direct = f"El chat requiere nivel {floor} o superior para implementar."
    if not direct and has_validator(args) and TIERS.index(highest(args.available)) < TIERS.index(args.chat_tier):
        direct = "No hay cuota para un validador de nivel igual o superior al del chat que implementa."
    no_executor = "" if executor else "No hay cuota para un ejecutor que alcance el piso de capacidad."
    return {"directo": direct, "delegado": run or no_executor, "coordinado": no_executor}


def cost(mode: str, args: argparse.Namespace, roles: list[dict]) -> float:
    """Estima el costo relativo de un modo; solo informa y desempata."""
    work, chat = WORK[args.size], W_TIER[args.chat_tier]
    validators = [role for role in roles if role["role"] == "validador"]
    total = sum(W_TIER[role["tier"]] + OVERHEAD for role in validators)
    if mode == "directo":
        return work * chat + total
    executor = next(role for role in roles if role["role"] == "ejecutor")
    total += (COORD_FIXED + COORD_RATE * work) * chat + work * W_TIER[executor["tier"]]
    total += (args.parts if mode == "coordinado" else 1) * OVERHEAD
    return total + (2 * W_TIER[roles[0]["tier"]] + OVERHEAD if roles[0]["role"] == "planificador" else 0)


def describe(roles: list[dict], size: str) -> str:
    """Resume los niveles elegidos (un validador por rol distinto) para explicar la decisión."""
    seen: dict[str, str] = {}
    for role in roles:
        seen.setdefault(role["role"], role["tier"])
    parts = [f"{name} {tier}" for name, tier in seen.items()]
    text = " y ".join(filter(None, [", ".join(parts[:-1]), *parts[-1:]])) or "la hace el chat sin validación"
    return f"tarea {size}: {text}; calidad primero"


def choose(args: argparse.Namespace) -> dict:
    """Elige el modo de mayor calidad factible y explica la decisión."""
    executor = executor_tier(args)
    block = blockers(args, executor)
    roles = {mode: role_list(mode, args, executor) for mode in MODES if not block[mode]}
    options = {mode: {"feasible": not block[mode], "why": block[mode] or "Es factible con los niveles disponibles.",
                      "cost": round(cost(mode, args, roles[mode]), 2) if mode in roles else None} for mode in MODES}
    base = "coordinado" if needs_run(args) else "directo" if args.size == "trivial" else "delegado"
    if args.prefer in roles:
        mode, lead = args.prefer, f"Se eligió {args.prefer} por la preferencia indicada"
    else:
        lead = "" if args.prefer == "auto" else f"La preferencia {args.prefer} no es factible"
        mode = base if base in roles else min(roles, key=lambda m: options[m]["cost"], default=None)
        if mode and mode != base:
            lead = f"Respaldo: {block[base].rstrip('.')}"
    if mode is None:
        reason = "Ningún modo cumple los requisitos con los niveles disponibles."
    else:
        reason = describe(roles[mode], args.size)
    reason = f"{lead}; {reason[0].lower() + reason[1:]}" if lead else reason
    selected = roles.get(mode, [])
    asks = [r for r in selected if r["tier"] == "frontera" and r.get("session") != "chat"]
    return {"mode": mode, "reason": reason, "options": options, "roles": selected,
            "ask_user": bool(asks) and not args.frontier_ok}


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
