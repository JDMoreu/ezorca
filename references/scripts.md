# Scripts de EzOrca

`<skill>` es la carpeta de esta skill (por ejemplo, `~/.agents/skills/ezorca`, o donde el entorno la haya instalado); usa su ruta absoluta.

Todos están en `scripts/` de la skill, usan solo Python 3.11 o superior de la biblioteca estándar, escriben JSON por stdout y devuelven 0 si todo va bien, 1 si una comprobación sale negativa y 2 si el uso o los datos son inválidos.

La regla general: si un script existe para un paso, úsalo en vez de hacerlo a mano; si falla con exit 2, informa el error y sigue la guía de Orca.

| Script | Cuándo usarlo | Comando de ejemplo | Qué hacer según el exit |
|---|---|---|---|
| `<skill>/scripts/discover.py` | Una vez por Run, al planear el equipo y la escalera | `python <skill>/scripts/discover.py --cache <carpeta del Run>/roster.json` | 0: elige agentes y modelos de su salida; 2: no pudo leer el entorno o falló al leer o escribir la caché (el mensaje dice la ruta), informa y usa los comandos de Orca a mano |
| `<skill>/scripts/choose_mode.py` | Antes de planear | `python <skill>/scripts/choose_mode.py --chat-tier frontera --size mediana --parts 1 --risk bajo` | Con 0, sigue `mode`. Con 1, ningún modo es factible con los niveles disponibles. Avisa y propone esperar cuota o usar otro nivel. Con 2, corrige los argumentos inválidos. |
| `<skill>/scripts/check_spec.py` | Antes de lanzar una tanda, sobre todos los encargos | `python <skill>/scripts/check_spec.py specs/g1.md specs/g2.md --kind implementacion` | 0: los encargos están completos; 1: imprime qué falta, corrige el encargo y repite; 2: una ruta no existe, corrígela |
| `<skill>/scripts/launch_wave.py` | Para arrancar la tanda en paralelo con tope por modelo | `python <skill>/scripts/launch_wave.py tanda.json --receipts <carpeta del Run>/receipts.jsonl` | 0: sin fallos, revisa `deferred`; 1: revisa `failed` y `receipt_errors`, comprueba el estado en Orca y sigue su recuperación antes de reintentar; 2: la tanda es inválida (p. ej., `new-top-level` sin `repo` o `worktree_name`), corrige el JSON |
| `<skill>/scripts/stalled.py` | En segundo plano, como latido de respaldo de la tanda | `python <skill>/scripts/stalled.py --run <id> --wait 1200` | 0: nadie está colgado; 1: algún worker tiene `stalled: true`, lee su salida con `worker-read` y decide; 2: error, informa |
| `<skill>/scripts/fingerprint.py` | Antes de cada pase de verificación | `python <skill>/scripts/fingerprint.py --repo <repo> --extra <archivo>` | 0: usa `fingerprint` como versión verificada en el veredicto; 2: no pudo calcularla, corrige la ruta o el repo y repite |
| `<skill>/scripts/check_scope.py` | En la puerta de integración, con los archivos permitidos del encargo | `python <skill>/scripts/check_scope.py --repo <repo> --allowed "src/**" --allowed "tests/**"` | 0: solo tocó lo permitido; 1: `outside` lista archivos de más, rechaza o devuelve el cambio; 2: el repo o la base no existen |
| `<skill>/scripts/eval_kit.py` | Al preparar y juzgar una evaluación ciega de skills | `python <skill>/scripts/eval_kit.py --dir <carpeta de evaluación> exec --variant-dir <skill> --label baseline --template exec.md` (luego `pair` y `merge`) | 0: sigue con el paso siguiente; 1: `merge` encontró juicios faltantes, complétalos; 2: datos o rutas inválidos |
| `<skill>/scripts/compare_skill_results.py` | Al cerrar la evaluación, tras `merge` | `python <skill>/scripts/compare_skill_results.py cases.json baseline.json candidate.json` | 0: acepta la candidata; 1: la rechaza, informa las regresiones; 2: datos inválidos o incompletos |
| `<skill>/scripts/cost_report.py` | Para medir el costo real de un Run con los registros locales de cada agente | `python <skill>/scripts/cost_report.py --since 2026-11-24T00:00:00Z` | 0: lee `sessions` y `totals` (si falta una fuente, aparece en `warnings`); 2: una fecha o una ruta pasada a mano no existe, corrígela |

En Windows, `discover.py` acepta rutas estilo Git Bash (`/c/Users/x/roster.json` → `C:/Users/x/roster.json`), al leer y al escribir la caché.
Si la caché contiene JSON inválido, se regenera, y si hay un error de lectura, sale con exit 2 y el mensaje `error: no se pudo leer la caché en <ruta>: <detalle>` en stderr.

## Tanda para launch_wave

```json
{"run": "run_x", "cap_per_model": 4, "workers": [{"name": "g1", "spec_file": "specs/g1.md", "agent": "opencode", "title": "Goldfish 1 – tema", "worktree": "current", "model": null, "effort": null, "base_branch": null, "worktree_name": null, "repo": null}]}
```

Y uno de primer nivel:

```json
{"name": "g2", "spec_file": "specs/g2.md", "agent": "opencode", "title": "Goldfish 2 – tema", "worktree": "new-top-level", "repo": "id:<id del repo>", "worktree_name": "g2-tema", "base_branch": "main", "model": null, "effort": null}
```

`worktree` admite `current` (por omisión), `new-child` o `new-top-level`; `new-child` y `new-top-level` exigen `worktree_name`. `repo` (texto o `null`) es el selector de repo de Orca (`id:<id>`, de `orca repo list --json`) y solo vale con `new-top-level`, que lo exige: el comando lleva `--worktree new-top-level --repo <repo> --name <worktree_name> --setup skip` (más `--base-branch` si se da); si falta `repo` o `worktree_name`, exit 2 sin lanzar nada.

En `new-top-level`, un `repo` o `worktree_name` compuesto solo por espacios en blanco invalida la tanda y causa exit 2 sin lanzar ningún worker.

`--dry-run` imprime los comandos sin ejecutarlos y `--active` recibe un JSON con los workers vivos por clave de cupo. Los recibos de `--receipts` y la salida de `discover.py` se guardan junto al `run.md`.
