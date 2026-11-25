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

`warnings` aparece si un comando falló sin impedir el informe. Opciones: `--cache RUTA` (si está fresca y contiene JSON válido, no ejecuta comandos), `--max-age-hours HORAS` (12). En Windows, una ruta estilo Git Bash como `/c/Users/x/roster.json` se interpreta como `C:/Users/x/roster.json`, al leer y al escribir la caché. Si la caché contiene JSON inválido, se regenera, y si hay un error de lectura, sale con exit 2 y el mensaje `error: no se pudo leer la caché en <ruta>: <detalle>` en stderr. Si la caché no se puede escribir, sale con exit 2 y el mensaje `error: no se pudo escribir la caché en <ruta>: <detalle>` en stderr. El informe se emite con exit 0. Si no se pudo leer el entorno, sale con exit 2.

## choose_mode.py

Se ejecuta antes de planear. Estima el costo de los modos directo, delegado y coordinado y elige el más barato que cumple los requisitos.

```text
python <skill>/scripts/choose_mode.py --chat-tier NIVEL --size {trivial,chica,mediana,grande}
    [--parts N] [--risk {bajo,alto}] [--verified] [--chat-no-code]
    [--available NIVEL[,NIVEL...]] [--prefer {auto,directo,delegado,coordinado}]
```

`--parts` cuenta las partes independientes, admite de 1 a 50 y vale 1 por defecto. El riesgo predeterminado es `bajo`. Usa `--verified` para la entrega verificada y `--chat-no-code` cuando el chat no deba escribir código. `--available` indica los niveles con cuota y toma todos por defecto. `--prefer` vale `auto` por defecto. Si se pide un modo y resulta factible, el script lo usa. Si el modo pedido resulta inviable, el script elige en automático y explica el motivo en `reason`. En empate, gana el modo con menos sesiones, en orden directo, delegado y coordinado.

Ejemplo con `--chat-tier frontera --size mediana`:

```json
{
  "mode": "directo",
  "reason": "El selector eligió directo por costo y número de sesiones.",
  "options": {
    "directo": {"feasible": true, "cost": 43.0, "why": "El chat implementa."},
    "delegado": {"feasible": true, "cost": 76.0, "why": "Un ejecutor implementa."},
    "coordinado": {"feasible": true, "cost": 76.0, "why": "Un Run coordina la ejecución."}
  },
  "roles": [
    {"role": "validador", "tier": "economico-capaz", "effort": "medio", "family": "distinta si hay; si no, sesión nueva ciega del mismo agente"}
  ],
  "ask_user": false
}
```

Los textos de `reason` y `why` explican la decisión y la factibilidad. `roles` contiene los papeles del modo elegido. Si `ask_user` es `true`, pregunta antes de abrir una sesión de frontera. El código de salida es 0 si hay un modo factible, 1 si ningún modo es factible (`mode: null` en el JSON) y 2 si los argumentos son inválidos (`error:` en stderr).

### Pesos y tamaños

Los costos son estimaciones relativas calibradas con el [A/B justo](evaluation.md#ab-justo-sesiones-nuevas-con-y-sin-ezorca).

| Nivel | Peso |
|---|---:|
| `gratis` | 0,2 |
| `economico` | 1 |
| `economico-capaz` | 2 |
| `medio` | 4 |
| `frontera` | 10 |

| Tamaño | Trabajo | Nivel mínimo del ejecutor | Esfuerzo del ejecutor |
|---|---:|---|---|
| `trivial` | 1 | `gratis` | `bajo` |
| `chica` | 2 | `economico` | `bajo` |
| `mediana` | 4 | `economico-capaz` | `medio` |
| `grande` | 10 | `medio` | `alto` |

- Implementar cuesta el trabajo multiplicado por el peso del nivel del chat o del ejecutor. El riesgo alto sube un escalón el nivel requerido. En modo delegado o coordinado, el ejecutor llega como máximo a `medio`. Si la tarea exige más capacidad, la frontera planifica y describe la solución y un ejecutor de nivel medio la escribe.
- Coordinar cuesta al chat `(4,8 + 0,4 × trabajo) × peso del chat`. Cada sesión adicional suma 1. El modo delegado cuenta una sesión de ejecución y el coordinado cuenta una por parte independiente.
- Cada pase de validación suma el peso del validador más 1 por la sesión. Se usa el nivel disponible más barato desde `economico-capaz`, con esfuerzo medio. Con riesgo alto se usa frontera con esfuerzo alto. La revisión va a otra familia si hay una o a una sesión nueva y ciega del mismo agente. La entrega verificada siempre cuenta dos pases, incluso para tareas triviales. Una tarea trivial con entrega normal no lleva validación.
- Una tarea grande, con riesgo alto o con al menos tres partes independientes requiere un planificador de frontera con esfuerzo alto. Su costo es 21, incluida la sesión. Estos requisitos y la entrega verificada exigen el modo coordinado.

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
              "model": null, "effort": null, "base_branch": null, "worktree_name": null, "repo": null}]}
```

`name`, `spec_file`, `agent` y `title` son obligatorios y no vacíos; `name` no se repite. `cap_per_model` es un entero positivo. `worktree` es `current` (por omisión), `new-child` o `new-top-level`; `new-child` y `new-top-level` exigen `worktree_name`, y `new-top-level` exige además `repo`, que solo vale con ese valor (si falta `repo` o `worktree_name`, la tanda es inválida: exit 2 sin lanzar ningún worker); `repo` con `current` o `new-child` es inválido. Para `new-top-level` el comando lleva `--worktree new-top-level --repo <repo> --name <worktree_name> --setup skip`, más `--base-branch` si se da. `model`, `effort`, `base_branch`, `worktree_name` y `repo` son texto o `null`; `effort` solo se envía cuando `model` no es `null` (los dos son opciones de `worker-start` que el script reenvía).

En `new-top-level`, un `repo` o `worktree_name` compuesto solo por espacios en blanco invalida la tanda y causa exit 2 sin lanzar ningún worker.

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

## cost_report.py

Resume los tokens de cada sesión de Claude Code, Codex y OpenCode leyendo sus registros locales, sin leer ni imprimir contenidos, credenciales ni rutas. Entrada: `~/.claude/projects`, `~/.codex/sessions` y `~/.local/share/opencode/opencode.db` (o las rutas que pases). Paso del Run: **medir el costo**, al cerrar una tanda o un Run.

```bash
python <skill>/scripts/cost_report.py --since 2026-11-24T00:00:00Z --until 2026-11-25T00:00:00Z
```

```json
{"sessions": [{"agent": "codex", "session": "cx1", "model": "gpt-x",
  "started_at": "2026-11-24T09:00:00Z", "ended_at": "2026-11-24T09:10:00Z",
  "input_tokens": 90, "output_tokens": 30, "cache_read_tokens": 60, "cache_write_tokens": 0,
  "reasoning_tokens": 8, "total_tokens": 180}],
 "totals": {"claude": {"sessions": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
   "cache_write_tokens": 0, "reasoning_tokens": 0, "total_tokens": 0}, "codex": {"sessions": 1,
   "input_tokens": 90, "output_tokens": 30, "cache_read_tokens": 60, "cache_write_tokens": 0,
   "reasoning_tokens": 8, "total_tokens": 180}, "opencode": {"sessions": 0, "input_tokens": 0,
   "output_tokens": 0, "cache_read_tokens": 0, "cache_write_tokens": 0, "reasoning_tokens": 0,
   "total_tokens": 0}},
 "warnings": []}
```

`total_tokens` suma entrada, salida, caché leída y caché escrita; `reasoning_tokens` se informa aparte. En Claude cada `message.id` cuenta una sola vez (usa la última aparición), en Codex se usa el último `token_count`, que ya es acumulado, con `input_tokens` descontando lo cacheado, y en OpenCode una fila de `session_v2` (o de `session` si aquella no existe) es una sesión, la base se abre en modo solo lectura y un `model` en JSON se informa por su `id`. Las sesiones salen ordenadas por `started_at` y, si falta una fuente, se anota en `warnings` sin impedir el informe.

Opciones: `--claude-dir DIR`, `--codex-dir DIR`, `--opencode-db FILE` (por omisión las rutas de arriba), `--since ISO` y `--until ISO` (sin zona = UTC; una sesión cuenta si su intervalo cruza el rango), `--session ID` (repetible), `--no-claude`, `--no-codex`, `--no-opencode`. Exit 0 con el informe; 2 si una fecha está mal formada o una ruta pasada explícitamente no existe.

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
