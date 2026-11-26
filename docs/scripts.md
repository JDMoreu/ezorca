# Scripts de EzOrca

`<skill>` es la carpeta de la skill instalada, por ejemplo `~/.agents/skills/ezorca`. Todos los scripts viven en `scripts/`, usan solo la biblioteca estándar de Python 3.11 o superior, escriben JSON por stdout y devuelven 0 si todo va bien, 1 si una comprobación sale negativa y 2 si el uso o los datos son inválidos. La regla: si un script existe para un paso, se usa en vez de hacerlo a mano. Cuándo usar cada uno, en [references/scripts.md](../references/scripts.md).

## resources.py

Entrega el presupuesto de cuota y el catálogo de precios antes de delegar: lee los límites de Orca, los modelos de OpenCode, Codex y Claude, y los precios públicos de `models.dev`, y devuelve los candidatos ordenados por precio de salida.

```bash
python scripts/resources.py --reserve 80 --reserve-window 5h=95 --reserve-window week=90
```

| Flag | Efecto |
|---|---|
| `--reserve N` | Uso (0–100 %) desde el cual un plan se bloquea; por omisión 80. |
| `--reserve-plan PLAN=N` | Tope propio para `claude`, `codex` u `opencodeGo`; repetible. |
| `--reserve-window VENTANA=N` | Tope por ventana (`5h`, `week`, `month`); prevalece sobre el del plan; repetible. |
| `--exhausted <plan\|opencode\|agente:modelo>` | Marca como agotado lo que falló por cuota en esta sesión; repetible. |
| `--max-age-days D` | Edad máxima de la caché de precios antes de descargarla de nuevo; por omisión 7. Una caché reciente con JSON inválido se descarga una vez. |
| `--cache-dir RUTA` | Carpeta de la caché (`models.dev.json`); por omisión `~/.cache/ezorca`. |
| `--full RUTA` | Escribe en ese archivo el inventario completo de candidatos. |

Exit 0: hay niveles en `available`; 1: ningún modelo elegible; 2: argumentos, catálogo o fuentes inválidos (mensaje `error: …` en stderr).

Campos del JSON: `plans` (uso por ventana y `blocked` de cada plan), `available` (niveles con candidatos), `pick` (hasta 3 candidatos por nivel, de menor a mayor precio), `blocked` (motivo de cada bloqueo) y `warnings` (fuentes no disponibles o modelos sin precio). La salida compacta no pasa de 1500 bytes: si se excede, recorta primero avisos, luego candidatos y luego bloqueos; `--full` conserva todo.

## discover.py

Lista los agentes instalados y el inventario de OpenCode. Deja `tier: null` para modelos sin precio; `resources.py` es la autoridad. Paso del Run: **descubrir**, una vez por Run.

```bash
python <skill>/scripts/discover.py --cache <carpeta del Run>/roster.json
```

```json
{"generated_at": "...", "agents": ["claude", "codex", "opencode"], "models": [{"agent": "opencode", "model": "opencode-go/modelo", "tier": null}, {"agent": "codex", "model": "configurado", "tier": "medio"}]}
```

`warnings` aparece si un comando falló sin impedir el informe. Opciones: `--cache RUTA` (si está fresca y contiene JSON válido, no ejecuta comandos), `--max-age-hours HORAS` (12). En Windows, una ruta estilo Git Bash como `/c/Users/x/roster.json` se interpreta como `C:/Users/x/roster.json`, al leer y al escribir la caché. Si la caché contiene JSON inválido, se regenera, y si hay un error de lectura, sale con exit 2 y el mensaje `error: no se pudo leer la caché en <ruta>: <detalle>` en stderr. Si la caché no se puede escribir, sale con exit 2 y el mensaje `error: no se pudo escribir la caché en <ruta>: <detalle>` en stderr. El informe se emite con exit 0. Si no se pudo leer el entorno, sale con exit 2.

## choose_mode.py

Se ejecuta antes de planear. Elige el modo con la mejor calidad posible, validada, como si el modelo más fuerte hiciera todo; después prioriza la eficiencia (tiempo) y al final el costo, siempre dentro de los topes del plan (los filtra `resources.py` vía `--available`). El costo ya no decide el modo: solo se informa en `options.<modo>.cost` y desempata entre alternativas.

```text
python <skill>/scripts/choose_mode.py --chat-tier NIVEL --size {trivial,chica,mediana,grande}
    [--parts N] [--risk {bajo,alto}] [--verified] [--chat-no-code] [--frontier-ok]
    [--available NIVEL[,NIVEL...]] [--prefer {auto,directo,delegado,coordinado}]
```

`--parts` cuenta las partes independientes, admite de 1 a 50 y vale 1 por defecto. El riesgo predeterminado es `bajo`. Usa `--verified` para la entrega verificada, `--chat-no-code` cuando el chat no deba escribir código y `--frontier-ok` cuando el usuario ya autorizó sesiones nuevas de frontera. `--available` indica los niveles con cuota y toma todos por defecto. `--prefer` vale `auto` por defecto; si se pide un modo (`directo`, `delegado` o `coordinado`) y es factible, el script lo usa; si no, elige en automático y lo explica en `reason`. Cuando el modo ideal no es factible y cae a otro (respaldo), `reason` empieza con «Respaldo: <motivo>».

Política, en orden:

1. **Modo.** `directo` solo con `--size trivial` o `--prefer directo`, y sin `--verified`. `coordinado` con `--parts` ≥ 2, `--size grande`, `--risk alto` o `--verified`. En otro caso, `delegado`.
2. **Planificador.** Obligatorio en `coordinado` y en `delegado` de tamaño `mediana`: el nivel más alto disponible (frontera si hay) con esfuerzo alto. En `delegado` de tamaño `chica` planifica el propio chat (sin rol). Si el chat es de frontera, el planificador es el propio chat: el rol lleva `"session": "chat"`, es de frontera aunque no haya cuota de frontera en `--available`, y no cuenta para `ask_user`; en ese caso se planifica en el chat, sin abrir una sesión nueva.
3. **Ejecutor.** Nunca frontera: el nivel siguiente al piso de capacidad con tope `medio` (o el más cercano hacia arriba y, si no, el piso). Si ni el piso tiene cuota, la opción no es factible. Con `grande` y riesgo alto el ejecutor queda en `medio` aunque el piso sea frontera: la frontera describe la solución y valida dos veces. Esfuerzo `medio` en `chica`, `alto` en `mediana` y `grande`. En `coordinado` hay un ejecutor por parte (`"count": parts`).
4. **Validador.** En todo lo que no sea trivial, y también en una tarea trivial con `--risk alto` (1 pase) o `--verified` (2): el nivel más alto disponible, esfuerzo alto, de otra familia si hay o en una sesión nueva y ciega. Son 2 pases con `--verified` o con `--risk alto` en tareas no triviales, y 1 en los demás casos. En `directo` el validador debe ser como mínimo del nivel del chat que implementa; si `--available` no lo permite, `directo` no es factible (no se degrada la validación ni se pregunta); incluye `"loop"` (corregir y revalidar hasta que no queden hallazgos bloqueantes ni mayores, máx. 3 rondas).
5. **Pregunta.** `ask_user` es `true` si algún rol es de frontera y no es el propio chat (`session: chat`), salvo que se pase `--frontier-ok`.

Ejemplo con `--chat-tier frontera --size mediana --available economico,medio,frontera`:

```json
{
  "mode": "delegado",
  "reason": "tarea mediana: planificador frontera, ejecutor medio y validador frontera; calidad primero",
  "options": {
    "directo": {"feasible": true, "why": "Es factible con los niveles disponibles.", "cost": 51.0},
    "delegado": {"feasible": true, "why": "Es factible con los niveles disponibles.", "cost": 113.0},
    "coordinado": {"feasible": true, "why": "Es factible con los niveles disponibles.", "cost": 113.0}
  },
  "roles": [
    {"role": "planificador", "tier": "frontera", "effort": "alto", "session": "chat"},
    {"role": "ejecutor", "tier": "medio", "effort": "alto"},
    {"role": "validador", "tier": "frontera", "effort": "alto", "family": "distinta si hay; si no, sesión nueva ciega del mismo agente", "loop": "corregir y revalidar hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas)"}
  ],
  "ask_user": true
}
```

`roles` contiene los papeles del modo elegido. El código de salida es 0 si hay un modo factible, 1 si ninguno lo es (`mode: null` en el JSON) y 2 si los argumentos son inválidos (`error:` en stderr).

### Pesos y tamaños (solo para informar y desempatar)

Los costos son estimaciones relativas calibradas con el [A/B justo](evaluation.md#ab-justo-sesiones-nuevas-con-y-sin-ezorca).

| Nivel | Peso |
|---|---:|
| `gratis` | 0,2 |
| `economico` | 1 |
| `economico-capaz` | 2 |
| `medio` | 4 |
| `frontera` | 10 |

| Tamaño | Trabajo | Piso de capacidad del ejecutor | Esfuerzo del ejecutor |
|---|---:|---|---|
| `trivial` | 1 | `gratis` | `bajo` |
| `chica` | 2 | `economico` | `medio` |
| `mediana` | 4 | `economico-capaz` | `alto` |
| `grande` | 10 | `medio` | `alto` |

- El riesgo alto sube un escalón el piso de capacidad. El ejecutor llega como máximo a `medio`.
- Implementar cuesta el trabajo multiplicado por el peso del nivel que lo hace. Coordinar cuesta al chat `(4,8 + 0,4 × trabajo) × peso del chat`. Cada sesión adicional suma 1; un planificador cuesta 21 con su sesión.
- Cada pase de validación suma el peso del validador más 1 por la sesión.

## check_spec.py

Comprueba que los encargos traen lo mínimo para un modelo económico. Entrada: archivos Markdown. Paso del Run: **antes de lanzar la tanda**, sobre todos los encargos.

```bash
python <skill>/scripts/check_spec.py specs/g1.md specs/g2.md --kind implementacion
```

```json
[{"file": "specs/g1.md", "ok": true, "missing": [], "warnings": []}]
```

Además de lo que falta, avisa (en `warnings`, sin fallar) si un encargo de implementación no trae la regla de no debilitar pruebas o si uno de revisión no comprueba que no se debilitaron.

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
{"accepted": true, "baseline_passes": 5, "candidate_passes": 6, "total_judgments_per_variant": 8, "regressions": [], "critical_failures": [],
 "baseline_pass_k": {"cases": {"c1": {"pass_at_k": true, "pass_hat_k": false}}, "total_pass_at_k": 1, "total_pass_hat_k": 0},
 "candidate_pass_k": {"cases": {"c1": {"pass_at_k": true, "pass_hat_k": true}}, "total_pass_at_k": 1, "total_pass_hat_k": 1},
 "reliability_regression": false, "warnings": []}
```

Acepta solo con más aciertos totales, ninguno menos por par caso–criterio, todos los críticos aprobados en cada repetición y sin regresión de confiabilidad. Por brazo y por caso calcula **pass@k** (al menos una repetición aprueba) y **pass^k** (todas aprueban), más el total de casos con pass^k; una repetición aprueba un caso si cumple sus criterios críticos (todos, si el caso no tiene críticos). Rechaza si la candidata tiene menos casos con pass^k que la línea base (`reliability_regression`). Con una sola repetición ambos valores coinciden y `warnings` lo avisa. Opciones: los posicionales `rubric`, `baseline` y `candidate`. Exit 0 si acepta; 1 si rechaza, con las regresiones; 2 si los datos son inválidos o incompletos.

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

`resources.py` consume `price_output_per_million` como única clasificación: compara el precio de salida por millón con límites ordenados. `discover.py` deja `tier: null` para modelos cuyo precio aún no se consultó y regenera cachés antiguas con niveles por nombre. Los modelos sin precio no son elegibles.

Los límites están en `price_output_per_million`; los escalones son `gratis`, `economico`, `economico-capaz`, `medio` y `frontera`.

## Pruebas

Están en `scripts/tests/`, con `unittest` y ejecutores falsos: nunca llaman a Orca de verdad.

```bash
python -m unittest discover -s scripts/tests -q
```
