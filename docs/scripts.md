# Scripts de EzOrca

`<skill>` es la carpeta de la skill instalada, por ejemplo `~/.agents/skills/ezorca`. Todos los scripts viven en `scripts/`, usan solo la biblioteca estándar de Python 3.11 o superior, escriben JSON por stdout y devuelven 0 si todo va bien, 1 si una comprobación sale negativa y 2 si el uso o los datos son inválidos. La regla: si un script existe para un paso, se usa en vez de hacerlo a mano. Cuándo usar cada uno, en [references/scripts.md](../references/scripts.md).

## discover.py

Lista los agentes instalados y clasifica los modelos de OpenCode por escalón con `tiers.json`. Entrada: el entorno. Paso del Run: **descubrir**, una vez por Run.

```bash
python <skill>/scripts/discover.py --cache <carpeta del Run>/roster.json
```

```json
{"generated_at": "...", "agents": ["claude", "codex", "opencode"], "models": [{"agent": "opencode", "model": "opencode-go/deepseek-v4.1-flash", "tier": "economico"}, {"agent": "codex", "model": "configurado", "tier": "medio"}]}
```

`warnings` aparece si un comando falló sin impedir el informe. Opciones: `--cache RUTA` (si está fresca, no ejecuta comandos), `--max-age-hours HORAS` (12). Exit 0 con el informe; 2 si no pudo leer el entorno.

## check_spec.py

Comprueba que los encargos traen lo mínimo para un modelo económico. Entrada: archivos Markdown. Paso del Run: **antes de lanzar la tanda**, sobre todos los encargos.

```bash
python <skill>/scripts/check_spec.py specs/g1.md specs/g2.md --kind implementacion
```

```json
[{"file": "specs/g1.md", "ok": true, "missing": [], "warnings": []}]
```

`missing` lista lo que falta (por ejemplo `"Ejemplo"`) y `warnings` avisa de la coletilla «No delegues». Opciones: `SPEC [SPEC ...]`; `--kind {implementacion,revision}` (por omisión `implementacion`; la revisión exige `no verificable` y `Método y límites`). Exit 0 si todos están completos; 1 con lo que falta; 2 si un archivo no existe.

## launch_wave.py

Lanza una tanda en paralelo con tope por modelo. Entrada: un `tanda.json`. Paso del Run: **lanzar la tanda**.

```bash
python <skill>/scripts/launch_wave.py tanda.json --receipts <carpeta del Run>/receipts.jsonl
```

```json
{"launched": [{"name": "g1", "exit": 0, "receipt": {"ok": true}}], "deferred": ["g3"], "failed": [], "receipt_errors": []}
```

Con `--dry-run` cada `launched` trae `command` y `receipt: null`, y se añade `commands`. Opciones: `wave`; `--active ACTIVE` (JSON con workers vivos por clave `agente/modelo`); `--dry-run`; `--receipts RECEIPTS` (`.jsonl` al que añade cada recibo). Exit 0 sin fallos (revisa `deferred`); 1 si hay `failed` o `receipt_errors`; 2 si la tanda es inválida.

### Formato de `tanda.json`

```json
{"run": "<id del Run>", "cap_per_model": 4,
 "workers": [{"name": "g1", "spec_file": "specs/g1.md", "agent": "opencode", "title": "Goldfish 1 – tema", "worktree": "current",
              "model": null, "effort": null, "base_branch": null, "worktree_name": null}]}
```

`name`, `spec_file`, `agent` y `title` son obligatorios y no vacíos; `name` no se repite. `cap_per_model` es un entero positivo. `worktree` es `current` (por omisión) o `new-child`, y `new-child` exige `worktree_name`. `model`, `effort`, `base_branch` y `worktree_name` son texto o `null`; `effort` solo se envía cuando `model` no es `null` (los dos son opciones de `worker-start` que el script reenvía).

## stalled.py

Detecta workers vivos que dejaron de avanzar, sin leer su correo. Entrada: el Run de Orca. Paso del Run: **en segundo plano como latido** de la tanda.

```bash
python <skill>/scripts/stalled.py --run <id del Run> --wait 1200
```

```json
{"run": "<id del Run>", "checked": 2, "workers": [{"dispatch": "<id>", "agent": "opencode", "idle_minutes": 4, "stalled": false, "action": "seguir esperando"}]}
```

Un worker colgado añade `tail` con sus últimas cinco líneas. Opciones: `--run RUN` (obligatoria), `--minutes MINUTES` (20), `--wait WAIT` (segundos antes de revisar). Exit 0 si nadie está colgado; 1 si alguno trae `stalled: true` (lee su salida y decide); 2 con error.

## fingerprint.py

Calcula la huella SHA-256 de la versión exacta que se verifica: HEAD, diff y archivos no rastreados. Entrada: un repositorio git. Paso del Run: **antes de cada pase** de la entrega verificada.

```bash
python <skill>/scripts/fingerprint.py --repo <repo> --extra <archivo ignorado>
```

```json
{"fingerprint": "sha256:<64 hex>", "head": "<commit completo>", "dirty": true, "untracked": ["docs/nuevo.md"], "extra": []}
```

Opciones: `--repo REPO` (obligatoria), `--extra EXTRA` (archivo adicional que cubre, repetible; sirve para los ignorados que citan criterios). Exit 0 con la huella, que va como versión en el veredicto; 2 si no es un repo con HEAD válido o un `--extra` no existe.

## check_scope.py

Puerta de integración: comprueba que un cambio solo tocó los archivos permitidos. Entrada: repo y globs. Paso del Run: **al integrar**, con la lista «Puede editar» del encargo.

```bash
python <skill>/scripts/check_scope.py --repo <repo> --allowed "src/**" --allowed "tests/**"
```

```json
{"ok": false, "changed": ["notas.txt", "src/a.py"], "outside": ["notas.txt"]}
```

Los archivos no rastreados cuentan. Opciones: `--repo REPO` (obligatoria), `--allowed GLOB` (relativo a la raíz, con `/`, repetible y obligatorio), `--base BASE` (referencia del diff, por omisión HEAD). Exit 0 si todo está dentro; 1 si `outside` lista archivos de más (rechaza o devuelve el cambio); 2 si el repo o la base no existen.

## eval_kit.py

Prepara una evaluación ciega de skills y junta sus juicios. Entrada: `cases.json`, plantillas y carpetas. Paso del Run: **evaluación de una skill**, no en el de entrega.

```bash
python <skill>/scripts/eval_kit.py --dir <carpeta> exec --variant-dir <skill> --label baseline --template exec.md
python <skill>/scripts/eval_kit.py --dir <carpeta> merge --label baseline --judgments juicios --out baseline.json
```

```json
{"tids": ["t3fbb4b05", "t9a1c0d2e"]}
```

`pair` devuelve `{"spec": "specs/pjudge-<hex>.md"}` y `merge` `{"out": "baseline.json", "judgments": 8}`, o `{"missing": ["<tid>"]}` si faltan juicios. Opciones: `--dir DIR` (obligatoria) más:

| Subcomando | Opciones |
|---|---|
| `exec` | `--variant-dir VARIANT_DIR`, `--label LABEL`, `--template TEMPLATE`, `--case CASES` (repetible) |
| `pair` | `--a A`, `--b B`, `--template TEMPLATE`, `--out-dir OUT_DIR` |
| `merge` | `--label LABEL`, `--judgments JUDGMENTS`, `--out OUT` |

Exit 0 si el paso salió bien; 1 en `merge` si faltan juicios; 2 con datos o rutas inválidos.

## compare_skill_results.py

Compara los juicios de dos variantes contra una rúbrica fija. Entrada: tres JSON. Paso del Run: **al cerrar la evaluación**, tras `merge`.

```bash
python <skill>/scripts/compare_skill_results.py cases.json baseline.json candidate.json
```

```json
{"accepted": true, "baseline_passes": 5, "candidate_passes": 6, "total_judgments_per_variant": 8, "regressions": [], "critical_failures": []}
```

Acepta solo con más aciertos totales, ninguno menos por par caso–criterio y todos los críticos aprobados en cada repetición. Opciones: los posicionales `rubric`, `baseline` y `candidate`. Exit 0 si acepta; 1 si rechaza, con las regresiones; 2 si los datos son inválidos o incompletos.

## tiers.json

Reglas de `discover.py`: gana la primera que coincide (regex, sin distinguir mayúsculas) y, si ninguna, `default`.

```json
{"rules": [
  {"pattern": "free", "tier": "gratis"},
  {"pattern": "flash|mini|haiku|lite", "tier": "economico"},
  {"pattern": "pro|plus|kimi|glm-5|sonnet", "tier": "economico-capaz"}
], "default": "economico-capaz",
 "agents": {"claude": "frontera", "codex": "medio", "pi": "medio", "copilot": "medio"}}
```

Escalones: `gratis`, `economico`, `economico-capaz`, `medio` y `frontera`. `agents` fija el escalón de los agentes sin listado, que salen con `model: "configurado"`. Las señales del nombre orientan, no deciden: si dudas, clasifica como `medio` y dilo en el plan.

## Pruebas

Están en `scripts/tests/`, con `unittest` y ejecutores falsos: nunca llaman a Orca de verdad.

```bash
python -m unittest discover -s scripts/tests -q
```
