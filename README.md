# EzOrca

Skill para resolver tareas de código directamente en el chat o coordinar equipos de agentes en Orca.

## Qué es y para quién

EzOrca elige entre trabajar directo en el chat (solo lo trivial), delegar a un ejecutor con validador o coordinar un Run de Orca. La meta es la mejor calidad validada, como si el modelo más fuerte hiciera todo; después vienen el tiempo y el paralelismo, y el costo solo desempata, siempre dentro de los topes de cada plan (5 h, semanal y mensual). El modelo más fuerte disponible planifica y valida, el ejecutor llega como máximo a nivel medio, y se corrige y revalida hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas). El nivel de cada modelo sale de su precio de salida, nunca de su nombre.

Es para quien ya usa Orca con uno o más agentes de código (Claude Code, Codex, OpenCode u otro que Orca liste) y quiere delegar trabajo real con resultados validados por sesiones independientes. También sirve para comparar dos versiones de una skill con evidencia, en vez de a ojo.

## Ideas clave

- **Elefante y Goldfish, por ejemplo.** El Elefante es el chat principal y puede ser cualquier modelo. Conserva el contexto, encarga el trabajo y acepta el resultado. Los Goldfish ejecutan o revisan con el modelo y el esfuerzo que pide su papel.
- **Modo inteligente.** Antes de planear, EzOrca estima el tamaño, las partes independientes y el riesgo, y usa `choose_mode.py` para elegir el modo por calidad: delegar es lo normal en lo no trivial, con el modelo más fuerte disponible planificando y validando, un ejecutor capaz (nunca de frontera) escribiendo y un ciclo de corrección hasta que no queden hallazgos bloqueantes ni mayores. Solo lo trivial va directo. Anuncia el modo, el motivo y el costo estimado.
- **Papeles adaptativos.** Cada Run define los papeles según el encargo y los asigna por calidad, luego tiempo y costo, entre los modelos con cuota disponible. Por ejemplo, un cambio riesgoso puede sumar diseño senior y un QA de otra familia.
- **Escalera de modelos.** Económico o gratis → económico capaz → modelo medio → y como último recurso la frontera describe la solución para que la escriba un modelo medio. Dos fallos en la misma tarea obligan a subir un escalón.
- **Avisa y sigue.** Al escalar o reasignar, el coordinador avisa en una línea qué cambia, por qué y cuánto cuesta. Pregunta solo si abriría una sesión de frontera que no autorizaste o si se supera el presupuesto acordado.
- **Dos modalidades en Runs coordinados.** La entrega normal incluye las comprobaciones habituales y, para cambios no triviales, un pase de revisión en otra sesión. La entrega verificada exige dos pases ciegos consecutivos sobre una versión con huella.
- **Reglas en código.** `resources.py` lee los topes de cada plan y los precios; los niveles salen solo del precio de salida (`scripts/tiers.json`). `choose_mode.py` elige el modo y los niveles por calidad. Otros scripts validan encargos, arrancan tandas, calculan la huella de versión, cuidan el alcance y apoyan la evaluación.

## Requisitos

- Orca instalado, con su CLI `orca` en el PATH.
- Al menos un agente compatible instalado en Orca: Claude Code, Codex, OpenCode u otro que Orca liste.
- Python 3.11 o superior para los scripts de `scripts/` (solo biblioteca estándar).

## Instalación rápida

```sh
git clone https://github.com/JDMoreu/ezorca.git ~/.agents/skills/ezorca
```

En Claude Code también se puede usar `~/.claude/skills/ezorca` o un enlace simbólico a la copia de `~/.agents/skills/ezorca`. En Windows las rutas equivalentes viven bajo `%USERPROFILE%`. Comprobación y actualización paso a paso en [docs/install.md](docs/install.md).

## Uso rápido

En un chat de Orca que ya pueda coordinar:

```text
Usa EzOrca para agregar caché de respuestas a la CLI de notas y que la segunda consulta no vuelva a la red.
```

EzOrca anuncia en una línea el modo, el motivo y el costo estimado. Lo trivial lo hace el chat; lo demás se delega: el modelo más fuerte disponible planifica (si hace falta) y valida, un ejecutor de nivel medio como máximo escribe, y se corrige hasta que no queden hallazgos bloqueantes ni mayores. Con varias partes, tamaño grande, riesgo alto o «entrega verificada», coordina un Run. Más ejemplos en [docs/usage.md](docs/usage.md).

## Resultados

- **A/B con proceso equivalente (T2, 3 repeticiones por brazo, mismo modelo y mismo proceso).** Ambos brazos pasaron 9/9 pruebas ocultas; la diferencia del juez ciego (20,7 frente a 21,3 sobre 25) no es concluyente. Costo medio por intento: US$ 0,371 sin EzOrca y US$ 0,442 con el prefijo; 4,8 y 5,3 minutos activos. En ese ensayo, la skill (anterior a 1.4.0) no se cargó con solo escribir «Usa EzOrca», así que no mide el flujo de 1.4.0. [Evaluación](docs/evaluation.md#resultados-del-ab-justo-con-proceso-equivalente-t2)
- **Activación.** Con la descripción de 1.4.0, la skill se cargó en 4 de 4 corridas con «Usa EzOrca» y en 0 de 4 cuando se pidió no usar skills (muestra chica). [eval/activation](eval/activation/README.md)
- **Pendiente.** Medir 1.4.0 en una tarea grande o de riesgo donde el selector delegue o coordine. Los ensayos anteriores, con lo que salió mal en cada uno, están en el [Historial](docs/evaluation.md#historial).

## Estructura del repo

```text
SKILL.md                 la skill y su contrato
references/              equipo y modelos, encargos, registro del Run, scripts, evaluación
scripts/                 11 utilidades en Python, un módulo auxiliar (cost_sources.py) y tiers.json
scripts/tests/           pruebas de los scripts
docs/                    instalación, uso, arquitectura, scripts, evaluación, investigación
eval/                    rúbrica y plantillas de simulacros, activation/ (activación de la skill) y tools/ (llamadas a scripts)
```

- El contrato completo de la skill: [SKILL.md](SKILL.md); el detalle operativo, en [references/team-and-models.md](references/team-and-models.md), [references/task-specs.md](references/task-specs.md) y [references/run-record.md](references/run-record.md).
- Cómo está diseñada y por qué: [docs/architecture.md](docs/architecture.md)
- Cada script y sus salidas: [docs/scripts.md](docs/scripts.md)
- Cómo se midió: [docs/evaluation.md](docs/evaluation.md)
- Qué se leyó antes de diseñarla: [docs/research.md](docs/research.md)
- Historial: [CHANGELOG.md](CHANGELOG.md). Cómo aportar: [CONTRIBUTING.md](CONTRIBUTING.md).

## Licencia

MIT. Ver [LICENSE](LICENSE).

## English summary

EzOrca is an Orca skill that picks how to do a coding task: directly in the chat (trivial work only), delegated to an executor with an independent validator, or as a coordinated Orca run. Its goal is validated frontier-level quality, as if the strongest model had done everything; time and parallelism come next, and cost only breaks ties, always within each plan's 5-hour, weekly and monthly limits. The strongest available model plans and validates, executors are capped at the mid tier, and fixes are revalidated until no blocking or major findings remain (up to 3 rounds). Tiers come from each model's output price (`scripts/tiers.json`), never from its name.

- Picks roles by quality first, then time and cost, and escalates by evidence instead of impatience.
- Supports normal and verified delivery in coordinated runs. The frontier model plans and validates, while executors capped at the mid tier write the code and tests unless the user asks otherwise.
- Discovers installed agents and models on every run instead of hardcoding a list.
- Ships small Python 3.11+ scripts for agent discovery, resource and budget checks (`resources.py`), mode selection (`choose_mode.py`), spec checks, wave launching, version fingerprints, scope gates and skill evaluation.

Requirements: Orca with its `orca` CLI, at least one agent supported by Orca installed, and Python 3.11 or newer. Clone into `~/.agents/skills/ezorca` or `~/.claude/skills/ezorca` and ask `Use EzOrca for <task>`.

Latest measurement: in an equivalent-process A/B (3 repetitions per arm) both arms passed 9/9 hidden tests and the judge difference (20.7 vs 21.3 out of 25) is not conclusive; in that trial the pre-1.4.0 skill did not load from "Usa EzOrca" alone. With the 1.4.0 description it loaded in 4 of 4 runs (small sample, `eval/activation`). Earlier trials, including what went wrong, are summarized in the [evaluation history](docs/evaluation.md#historial). Licensed under MIT.
