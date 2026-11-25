#!/usr/bin/env python3
"""Resume modelos con precio y cuota disponible antes de delegar trabajo."""
from __future__ import annotations
import argparse, json, os, re, shutil, subprocess, sys, time, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
TIERS = ("gratis", "economico", "economico-capaz", "medio", "frontera")
PLANS = ("claude", "codex", "opencodeGo")
class Parser(argparse.ArgumentParser):
    """Devuelve errores de argumentos al punto de entrada."""
    def error(self, message: str) -> None: raise ValueError(message)
def run_cmd(args: list[str]) -> tuple[int, str, str]:
    """Ejecuta un comando sin shell; queda sustituible en pruebas."""
    try:
        done = subprocess.run([shutil.which(args[0]) or args[0], *args[1:]], capture_output=True, text=True, timeout=30)
        return done.returncode, done.stdout, done.stderr
    except (OSError, subprocess.TimeoutExpired) as exc: return 127, "", str(exc)
def download_prices() -> dict[str, Any]:
    """Descarga el catálogo público de precios."""
    req = urllib.request.Request("https://models.dev/api.json", headers={"User-Agent": "ezorca-resources"})
    with urllib.request.urlopen(req, timeout=30) as response: return json.loads(response.read().decode("utf-8"))
def load_prices(cache: Path, max_days: float) -> tuple[dict, float, list[str]]:
    """Carga precios y conserva un archivo viejo si falla la actualización."""
    warnings = []
    try: age = (time.time() - cache.stat().st_mtime) / 86400 if cache.is_file() else None
    except OSError: age = None
    if age is None or age > max_days:
        try:
            data = download_prices(); cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data), encoding="utf-8"); age = 0
        except (OSError, ValueError, TimeoutError) as exc:
            warnings.append(f"descarga de precios falló: {exc}")
            if age is None: raise RuntimeError("no hay catálogo de precios") from exc
    try: return json.loads(cache.read_text(encoding="utf-8")), round(age or 0, 1), warnings
    except (OSError, ValueError) as exc: raise RuntimeError(f"catálogo inválido: {exc}") from exc
def read_limits() -> dict[str, Any]:
    """Lee límites de cuenta desde Orca."""
    code, out, err = run_cmd([os.environ.get("ORCA_CLI_COMMAND", "orca"), "account", "list", "--json"])
    if code: raise RuntimeError(err.strip() or f"orca account list: {code}")
    return json.loads(out)["result"]["rateLimits"]
def plan_summary(limits: dict | None, reserves: dict, exhausted: set[str], warnings: list[str]) -> tuple[dict, dict]:
    """Normaliza ventanas, cuotas desconocidas y bloqueos de plan."""
    plans, blocked = {}, {}
    for name in PLANS:
        source = (limits or {}).get(name)
        if not isinstance(source, dict):
            reason = "agotado durante esta sesión" if name in exhausted else "cuota desconocida (Orca no disponible)" if limits is None else "cuota desconocida (plan sin límites)"
            plans[name] = {"status": "unknown", "blocked": True}; blocked[name] = reason
            if limits is None: continue
            warnings.append(f"cuota desconocida: {name}"); continue
        plan = {}
        for key, label in (("session", "5h"), ("weekly", "week"), ("monthly", "month")):
            window = source.get(key)
            if isinstance(window, dict) and window.get("usedPercent") is not None: plan[label] = window["usedPercent"]
        status = source.get("status"); status_ok = status is None or str(status).lower() == "ok"
        if status is not None: plan["status"] = str(status)[:24]
        hits = [(w, v) for w, v in plan.items() if w in ("5h", "week", "month")
                and v >= reserves.get(w, reserves.get(name, reserves["default"]))]
        missing = not hits and not any(w in plan for w in ("5h", "week", "month")) and status is None
        is_blocked = bool(hits) or not status_ok or missing or name in exhausted
        plan["blocked"] = is_blocked; plans[name] = plan
        if name in exhausted: blocked[name] = "agotado durante esta sesión"
        elif not status_ok:
            blocked[name] = f"estado {str(status)[:32]}"; warnings.append(f"plan {name}: estado {str(status)[:48]}")
        elif hits:
            w, v = hits[0]; threshold = reserves.get(w, reserves.get(name, reserves["default"]))
            blocked[name] = f"{w} {v} % ≥ {threshold:g} %"
        elif missing: blocked[name] = "cuota desconocida"
    return plans, blocked
def cost(data: dict, provider: str, model: str) -> tuple[float, float] | None:
    """Busca costos por millón y exige entrada y salida válidas."""
    try:
        value = data[provider]["models"][model]["cost"]; inc, out = float(value["input"]), float(value["output"])
        return (inc, out) if min(inc, out) >= 0 else None
    except (KeyError, TypeError, ValueError): return None
def tier(out: float) -> str:
    """Clasifica por precio de salida en dólares por millón."""
    return "gratis" if out == 0 else "economico" if out <= .6 else "economico-capaz" if out <= 2 else "medio" if out <= 12 else "frontera"
def latest_claude(data: dict) -> list[str]:
    """Elige la última versión numérica encontrada por familia."""
    ids = data.get("anthropic", {}).get("models", {}); found = []
    for family in ("opus", "sonnet", "haiku", "fable"):
        matches = [(tuple(map(int, m.group(1).split("-"))), key) for key in ids
                   if (m := re.fullmatch(rf"claude-{family}-(\d+(?:-\d+)+)", key))]
        if matches: found.append(max(matches)[1])
    return found
def model_sources(data: dict, limits: dict | None, warnings: list[str]):
    """Lee modelos de OpenCode, Codex y Claude; cuota se decide después."""
    code, out, err = run_cmd(["opencode", "models"])
    if code: warnings.append(f"opencode models no disponible: {err.strip() or code}")
    else:
        for line in out.splitlines():
            model = line.strip()
            if "/" in model:
                provider, ident = model.split("/", 1); yield "opencode", provider, f"{provider}/{ident}", ""
    cache = Path.home() / ".codex" / "models_cache.json"
    try:
        for item in json.loads(cache.read_text(encoding="utf-8"))["models"]:
            levels = item.get("supported_reasoning_levels", []); effort = f"{levels[0]['effort']}..{levels[-1]['effort']}" if levels else ""
            yield "codex", "openai", item["slug"], effort
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc: warnings.append(f"modelos Codex no disponibles: {exc}")
    ids = data.get("anthropic", {}).get("models", {}); detected = latest_claude(data)
    families = {m.split("-")[1] for m in detected}; fixed = {"fable": "claude-fable-5-2", "opus": "claude-opus-5-5",
        "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5"}
    claudes = list(detected) + [model for family, model in fixed.items() if family not in families and cost(data, "anthropic", model)]
    for model in dict.fromkeys(claudes): yield "claude", "anthropic", model, ""
def collect(data: dict, limits: dict | None, reserves: dict, exhausted: set[str], warnings: list[str]) -> tuple[dict, dict, dict]:
    """Construye picks y el catálogo íntegro, con motivos de exclusión."""
    plans, blocked = plan_summary(limits, reserves, exhausted, warnings); candidates = []; missing = Counter()
    for agent, provider, model, effort in model_sources(data, limits, warnings):
        price = cost(data, provider, model.split("/", 1)[1] if agent == "opencode" else model)
        if price is None: missing[provider] += 1; continue
        inc, out = price; name = f"{agent}:{model}" if agent != "opencode" else f"opencode:{model}"
        plan = "opencodeGo" if provider.startswith("opencode-go") else agent
        bill = "plan con ventanas" if agent in ("claude", "codex") else "cuota mensual" if plan == "opencodeGo" else "gratis con cuota propia" if provider.endswith("-free") or out == 0 else "cuota propia"
        lock = None
        if name in exhausted: lock = "agotado durante esta sesión"
        elif agent in exhausted or plan in exhausted: lock = "plan agotado durante esta sesión"
        elif plan in PLANS and (limits is None or plan not in (limits or {})):
            lock = "cuota desconocida (Orca no disponible)" if limits is None else "cuota desconocida (plan sin límites)"
        elif plans.get(plan, {}).get("blocked"): lock = blocked.get(plan, "plan agotado")
        elif plan == "opencodeGo" and out > .6: lock = f"caro para cuota mensual (salida {out:g})"
        item = {"m": name, "in": inc, "out": out, "tier": tier(out), "billing": bill, "blocked": lock}
        if effort: item["efforts"] = effort
        candidates.append(item)
        if lock and (plan == "opencodeGo" or name in exhausted): blocked[name] = lock
    for provider, count in missing.items(): warnings.append(f"sin precio: {provider} ({count} modelos)")
    if "opencode" in exhausted: blocked["opencode"] = "familia agotada durante esta sesión"
    go = [key for key in blocked if key.startswith("opencode:opencode-go/")]
    if len(go) > 5:
        label = "caros" if all("caro para cuota mensual" in blocked[k] for k in go) else "bloqueados"
        for key in go: blocked.pop(key, None)
        blocked[f"opencode-go ({label})"] = f"{len(go)} modelos"
    picks = {}
    for level in TIERS:
        items = sorted((m for m in candidates if m["tier"] == level and not m["blocked"]), key=lambda m: (m["out"], m["in"]))[:3]
        if items: picks[level] = [{k: v for k, v in m.items() if k in ("m", "in", "out", "efforts")} for m in items]
    full = {"models": sorted(candidates, key=lambda m: (m["tier"], m["out"], m["in"]))}
    return picks, blocked, full
def compact(result: dict) -> str:
    """Limita el resumen a 1500 caracteres; full conserva todos los candidatos."""
    def dump() -> str: return json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    while len(dump().encode("utf-8")) > 1500:
        if result["warnings"]:
            warnings = result["warnings"]
            if any(len(w) > 80 for w in warnings): result["warnings"] = [w[:77] + "..." for w in warnings]
            elif len(warnings) > 1: result["warnings"] = [f"{len(warnings)} avisos resumidos"]
            else: result["warnings"] = []
        elif result["pick"]:
            level = next(reversed(result["pick"])); result["pick"][level].pop()
            if not result["pick"][level]: result["pick"].pop(level)
            result["available"] = list(result["pick"])
        elif result["blocked"]: result["blocked"].pop(next(reversed(result["blocked"])))
        else: break
    return dump()
def main(argv: list[str] | None = None) -> int:
    """Imprime el resumen compacto y, si se solicita, el catálogo completo."""
    for stream in (sys.stdout, sys.stderr): getattr(stream, "reconfigure", lambda **_: None)(encoding="utf-8")
    parser = Parser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--cache-dir", type=Path, default=Path.home() / ".cache" / "ezorca"); parser.add_argument("--max-age-days", type=float, default=7)
    parser.add_argument("--reserve", type=float, default=80); parser.add_argument("--reserve-plan", action="append", default=[])
    parser.add_argument("--reserve-window", action="append", default=[]); parser.add_argument("--exhausted", action="append", default=[]); parser.add_argument("--full", type=Path)
    try:
        args = parser.parse_args(argv)
        if args.max_age_days < 0 or not 0 <= args.reserve <= 100: raise ValueError("reservas deben estar entre 0 y 100")
        exhausted = set()
        for value in args.exhausted:
            if value in (*PLANS, "opencode"): exhausted.add(value)
            elif ":" in value and all(value.split(":", 1)): exhausted.add(value)
            else: raise ValueError(f"exclusión inválida: {value}")
        reserves = {"default": args.reserve}
        for values, allowed in ((args.reserve_plan, PLANS), (args.reserve_window, ("5h", "week", "month"))):
            for value in values:
                name, sep, raw = value.partition("="); threshold = float(raw) if sep else -1
                if name not in allowed or not 0 <= threshold <= 100: raise ValueError(f"reserva inválida: {value}")
                reserves[name] = threshold
        data, age, warnings = load_prices(args.cache_dir / "models.dev.json", args.max_age_days)
        try: limits = read_limits()
        except (RuntimeError, ValueError, KeyError, TypeError) as exc: limits = None; warnings.append(f"límites Orca no disponibles: {str(exc)[:80]}")
        picks, blocked, full = collect(data, limits, reserves, exhausted, warnings)
        if not any(cost(data, p, m) for p in data for m in data[p].get("models", {})): raise RuntimeError("no hay precios utilizables")
        if args.full: args.full.write_text(json.dumps(full, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        result = {"generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "prices_age_days": age, "reserve": reserves,
                  "plans": plan_summary(limits, reserves, exhausted, [])[0], "available": list(picks), "pick": picks, "blocked": blocked,
                  "warnings": list(dict.fromkeys(warnings))}
        print(compact(result)); return 0 if result["available"] else 1
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as exc: print(f"error: {exc}", file=sys.stderr); return 2
if __name__ == "__main__": raise SystemExit(main())
