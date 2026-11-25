#!/usr/bin/env python3
"""Valida propuestas de llamadas EzOrca sin ejecutar acciones externas."""
from __future__ import annotations
import contextlib, io, json, re, subprocess, sys, tempfile, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = Path(__file__).with_name("cases.json")
sys.path.insert(0, str(ROOT / "scripts"))
import check_spec, choose_mode, launch_wave  # noqa: E402

def load(case_id: str) -> dict:
    for case in json.loads(CASES.read_text(encoding="utf-8")):
        if case["id"] == case_id:
            return case
    raise ValueError(f"escenario desconocido: {case_id}")

def folded(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))

def response(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("argv"), list):
        raise ValueError("la respuesta debe ser objeto con argv como arreglo")
    if any(not isinstance(x, str) for x in data["argv"]):
        raise ValueError("argv solo admite textos")
    if set(data) - {"argv", "files"} or ("files" in data and not isinstance(data["files"], dict)):
        raise ValueError("campos no admitidos en la respuesta")
    return data

def exact(argv: list[str], expected: list[str]) -> None:
    """Compara argv permitiendo reordenar opciones, no sus valores."""
    def canonical(items: list[str]) -> tuple[str, ...]:
        head, rest = items[:2], items[2:]
        chunks, i = [], 0
        while i < len(rest):
            flag = rest[i]; i += 1
            if not flag.startswith("-"):
                chunks.append((flag,)); continue
            if flag in ("--dry-run", "--verified", "--chat-no-code"):
                chunks.append((flag,)); continue
            if i >= len(rest) or rest[i].startswith("-"):
                chunks.append((flag,)); continue
            chunks.append((flag, rest[i])); i += 1
        return tuple(head + [x for chunk in sorted(chunks) for x in chunk])
    if canonical(argv) != canonical(expected):
        raise AssertionError("argv no coincide con la propuesta esperada")

def resources_legacy(data: dict, case: dict) -> None:
    exact(data["argv"], case["expected"]["argv"])
    if "--exhausted" not in data["argv"] or data["argv"].count("--exhausted") != 2:
        raise AssertionError("faltan exclusiones de sesión")

def choose_legacy(data: dict, case: dict) -> None:
    if data["argv"][:2] != case["expected"]["argv"][:2]:
        raise AssertionError("comando ajeno a choose_mode.py")
    args = choose_mode.parse_args(data["argv"][2:])
    expected = choose_mode.parse_args(case["expected"]["argv"][2:])
    if (args.chat_tier, args.size, args.parts, args.risk, args.available) != (expected.chat_tier, expected.size, expected.parts, expected.risk, expected.available):
        raise AssertionError("selector incoherente con el contexto del caso")
    result = choose_mode.choose(args)
    if result["mode"] != "coordinado" or not result["options"]["coordinado"]["feasible"]:
        raise AssertionError("selector incoherente con tamaño, riesgo y available")

def files_in(data: dict, required: set[str]) -> dict[str, str]:
    files = data.get("files")
    if not isinstance(files, dict) or set(files) != required or any(not isinstance(v, (str, dict)) for v in files.values()):
        raise ValueError("archivos propuestos incompletos o inválidos")
    return files

def wave_legacy(data: dict, case: dict) -> None:
    exact(data["argv"], case["expected"]["argv"])
    files = files_in(data, {"wave.json"})
    wave_data = files["wave.json"]
    expected = case["expected"]["files"]["wave.json"]
    if not isinstance(wave_data, dict) or wave_data.get("run") != expected["run"] or wave_data.get("cap_per_model") != expected["cap_per_model"]:
        raise AssertionError("tanda distinta al caso: exige dos workers del mismo modelo")
    workers = wave_data.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise AssertionError("tanda distinta al caso: exige dos workers del mismo modelo")
    for actual, wanted in zip(workers, expected["workers"]):
        if not isinstance(actual, dict) or any(actual.get(key) != wanted[key] for key in ("name", "spec_file", "agent", "title", "worktree", "model")):
            raise AssertionError("worker, modelo, colocación o spec inválidos")
        if any(key in actual and actual[key] is not None for key in ("effort", "base_branch", "worktree_name", "repo")):
            raise AssertionError("opción no admitida para este worker OpenCode")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "wave.json").write_text(json.dumps(files["wave.json"]), encoding="utf-8")
        out = subprocess.run([sys.executable, str(ROOT / "scripts/launch_wave.py"), str(root / "wave.json"), "--dry-run"], capture_output=True, text=True, check=False)
        if out.returncode != 0 or not json.loads(out.stdout).get("commands"):
            raise AssertionError("la tanda no pasa el dry-run real")

def spec_legacy(data: dict, case: dict) -> None:
    if data["argv"][:2] != case["expected"]["argv"][:2] or sorted(data["argv"][2:]) not in (sorted(case["expected"]["argv"][2:]), ["spec.md"]):
        raise AssertionError("llamada a check_spec.py invalida")
    files = files_in(data, {"spec.md"})
    text = str(files["spec.md"])
    for phrase in ("reservas sinteticas", "topes 80/95/90", "eval/tools/fixtures.py"):
        if phrase not in folded(text):
            raise AssertionError("el encargo no contiene el contenido específico del caso")
    if "sin red" not in folded(text) and "sin acceso a la red" not in folded(text):
        raise AssertionError("faltan las restricciones de red del caso")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "spec.md"
        path.write_text(str(files["spec.md"]), encoding="utf-8")
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            code = check_spec.main([str(path)])
        if code != 0:
            raise AssertionError("el encargo no pasa check_spec.py")

def done(data: dict, case: dict) -> None:
    argv = data["argv"]
    if argv[:3] != ["orca", "orchestration", "send"]:
        raise AssertionError("comando ajeno a orca orchestration")
    values = {}
    i = 3
    while i < len(argv):
        flag = argv[i]
        if not flag.startswith("--") or i + 1 >= len(argv) or flag in values:
            raise AssertionError("argv de cierre inválido")
        values[flag] = argv[i + 1]; i += 2
    required = {"--from", "--type", "--subject", "--body", "--task-id", "--dispatch-id", "--outcome", "--report-path"}
    if set(values) != required or values["--type"] != "worker_done" or values["--outcome"] != "succeeded":
        raise AssertionError("campos de worker_done incompletos o incoherentes")
    if values["--from"] != "orca_session_id:sintetica" or values["--task-id"] != "task_sintetica" or values["--dispatch-id"] != "ctx_sintetico" or values["--report-path"] != "eval/tools/g3-reporte.md" or not values["--subject"].strip():
        raise AssertionError("IDs, ruta o asunto inválidos")
    body = values["--body"]
    parts = [s.strip() for s in body.split(".") if s.strip()]
    if len(parts) != 3 or not body.endswith(".") or [p.split(":", 1)[0] for p in parts] != ["Veredicto", "Hallazgo", "Pendiente"]:
        raise AssertionError("body o reporte no cumplen el cierre")
def script_argv(argv: list[str], script: str) -> list[str]:
    if len(argv) < 2 or argv[0] != "python": raise AssertionError(f"comando ajeno a {script}")
    candidate = argv[1].replace("\\", "/")
    if candidate not in (f"scripts/{script}", f"<skill>/scripts/{script}"):
        raise AssertionError(f"comando ajeno a {script}")
    return argv[2:]
def resources(data: dict, case: dict) -> None:
    args = script_argv(data["argv"], "resources.py"); pairs, i = [], 0
    while i < len(args):
        if i + 1 >= len(args): raise AssertionError("argumentos de resources incompletos")
        flag, value = args[i], args[i + 1]; i += 2
        if flag not in ("--cache-dir", "--reserve", "--reserve-window", "--exhausted"): raise AssertionError("opción no admitida en resources.py")
        pairs.append((flag, value))
    if any(sum(f == flag for f, _ in pairs) != 1 for flag in ("--cache-dir", "--reserve")): raise AssertionError("flags escalares repetidos o ausentes")
    if pairs.count(("--cache-dir", "eval-cache")) != 1: raise AssertionError("falta --cache-dir eval-cache")
    if pairs.count(("--reserve", "80")) != 1: raise AssertionError("la reserva general debe ser 80")
    if sorted(v for f, v in pairs if f == "--reserve-window") != ["5h=95", "week=90"]: raise AssertionError("topes de ventana incompletos o mal asignados")
    if sorted(v for f, v in pairs if f == "--exhausted") != sorted(("claude:claude-haiku-5-5", "opencode:opencode-go/deepseek-v4.1-flash")): raise AssertionError("exclusiones de sesión incompletas o incorrectas")
def choose(data: dict, case: dict) -> None:
    raw = script_argv(data["argv"], "choose_mode.py"); allowed = {"--chat-tier", "--size", "--parts", "--risk", "--available"}
    if any(flag not in allowed for flag in raw[::2]) or len(raw) != 10:
        if any(flag in raw for flag in ("--verified", "--chat-no-code", "--prefer")): raise AssertionError("opciones no admitidas en choose_mode.py")
        raise ValueError("argumentos invÃ¡lidos. Consulta --help para ver la sintaxis.")
    args = choose_mode.parse_args(script_argv(data["argv"], "choose_mode.py")); expected = choose_mode.parse_args(case["expected"]["argv"][2:])
    if (args.chat_tier, args.size, args.parts, args.risk, args.available) != (expected.chat_tier, expected.size, expected.parts, expected.risk, expected.available): raise AssertionError("selector incoherente con el contexto del caso")
    result = choose_mode.choose(args)
    if result["mode"] != "coordinado" or not result["options"]["coordinado"]["feasible"]: raise AssertionError("selector incoherente con tamaÃ±o, riesgo y available")
def wave(data: dict, case: dict) -> None:
    if script_argv(data["argv"], "launch_wave.py") != ["wave.json", "--dry-run"]: raise AssertionError("launch_wave.py requiere tanda.json --dry-run")
    files = files_in(data, {"wave.json"}); actual = files["wave.json"]; expected = case["expected"]["files"]["wave.json"]
    if not isinstance(actual, dict) or actual.get("run") != expected["run"] or actual.get("cap_per_model") != expected["cap_per_model"]: raise AssertionError("tanda distinta al caso: exige dos workers del mismo modelo")
    workers = actual.get("workers")
    if not isinstance(workers, list) or len(workers) != 2: raise AssertionError("tanda distinta al caso: exige dos workers del mismo modelo")
    for got, want in zip(workers, expected["workers"]):
        if not isinstance(got, dict) or any(got.get(k) != want[k] for k in ("name", "spec_file", "agent", "title", "worktree", "model")): raise AssertionError("worker, modelo, colocación o spec inválidos")
        if any(k in got and got[k] is not None for k in ("effort", "base_branch", "worktree_name", "repo")): raise AssertionError("opción no admitida para este worker OpenCode")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "wave.json"; path.write_text(json.dumps(actual), encoding="utf-8")
        out = subprocess.run([sys.executable, str(ROOT / "scripts/launch_wave.py"), str(path), "--dry-run"], capture_output=True, text=True, check=False)
        if out.returncode != 0 or not json.loads(out.stdout).get("commands"): raise AssertionError("la tanda no pasa el dry-run real")
def spec(data: dict, case: dict) -> None:
    args = script_argv(data["argv"], "check_spec.py")
    if sorted(args) not in (sorted(("--kind", "implementacion", "spec.md")), ["spec.md"]): raise AssertionError("llamada a check_spec.py invalida")
    files = files_in(data, {"spec.md"}); text = str(files["spec.md"]); flat = folded(text)
    if "reserva" not in flat or not re.search(r"(?:dos|2) exclusiones.{0,80}sintetic", flat) or "eval/tools/fixtures.py" not in flat: raise AssertionError("el encargo no contiene el contenido especÃ­fico del caso")
    compact = "topes 80/95/90" in flat
    associations = re.search(r"95.{0,80}5\s*h(?:oras)?|5\s*h(?:oras)?.{0,80}95", flat) and re.search(r"90.{0,80}(week|seman)|(week|seman).{0,80}90", flat)
    if not compact and (not re.search(r"(general|base).{0,40}80|80.{0,40}(general|base)", flat) or not associations): raise AssertionError("faltan topes 80/95/90 con sus ventanas")
    required = (("sin red", "sin acceso a la red", "no accedas a la red"), ("orcÃ¡ real", "orca real"), ("datos de cuenta",), ("puede editar",), ("ejemplo",), ("comprobaciones",), ("worker_done",))
    if any(not any(p in flat for p in group) for group in required): raise AssertionError("faltan restricciones, alcance, ejemplo, comprobaciones o cierre")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "spec.md"; path.write_text(text, encoding="utf-8"); sink = io.StringIO()
        with contextlib.redirect_stdout(sink): code = check_spec.main(["--kind", "implementacion", str(path)])
        if code != 0: raise AssertionError("el encargo no pasa check_spec.py")
CHECKS = {"resources": resources, "choose": choose, "wave": wave, "spec": spec, "done": done}
def main(argv: list[str] | None = None) -> int:
    if not argv or len(argv) != 2:
        print("uso: verify.py ID RESPUESTA.json", file=sys.stderr); return 2
    try:
        case, data = load(argv[0]), response(argv[1])
        if data.get("files") is not None and case["id"] not in ("wave", "spec"):
            raise ValueError("este escenario no admite archivos")
        CHECKS[case["id"]](data, case)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)); return 2
    except AssertionError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)); return 1
    print(json.dumps({"ok": True, "scenario": argv[0]})); return 0
if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))
