# EzOrca

Skill para coordinar equipos de agentes de código en Orca: la frontera orquesta, los modelos económicos escriben el código.

## Qué es y para quién

EzOrca toma un encargo escrito en palabras y lo convierte en un Run de Orca con varios agentes: uno caro que razona el plan, escribe los encargos, integra y acepta; y varios económicos, gratis o locales que escriben todo el código y las pruebas. La meta es un resultado de nivel frontera con la mitad del costo o menos (meta de diseño; la primera medición real está en docs/evaluation.md: en una tarea chica un solo modelo medio fue más barato, y EzOrca dio más calidad).

Es para quien ya usa Orca con uno o más agentes de código (Claude Code, Codex, OpenCode u otro que Orca liste) y quiere delegar trabajo real sin pagar modelos caros por escribir líneas. También sirve para comparar dos versiones de una skill con evidencia, en vez de a ojo.

## Ideas clave

- **Elefante y Goldfish, por ejemplo.** El Elefante suele ser el modelo de tu chat: piensa, planifica, reparte, revisa y acepta. Los Goldfish son los modelos económicos que ejecutan. Por defecto la frontera no escribe código, ni las pruebas, ni las ediciones triviales; el usuario puede indicar otra cosa.
- **Papeles adaptativos.** Elefante/PM, senior, junior y QA son ejemplos, no una lista fija: cada Run define los papeles que la tarea necesite (investigador, diseñador, arquitecto, revisor de seguridad, tester, documentador, integrador…) y cualquier agente o modelo puede ocupar cualquiera según capacidad, costo y disponibilidad. Una tarea pequeña puede llevar un solo junior; algo riesgoso suma diseño senior y un QA de otra familia. Los modelos caros razonan y casi nunca escriben código, salvo que el usuario diga otra cosa.
- **Escalera de modelos.** Económico o gratis → económico capaz → modelo medio → y como último recurso la frontera describe la solución para que la escriba un modelo barato. Dos fallos en la misma tarea obligan a subir un escalón.
- **Avisa y sigue.** Al escalar o reasignar, el coordinador avisa en una línea qué cambia, por qué y cuánto cuesta. Pregunta solo si abriría una sesión de frontera nueva o si se supera el presupuesto acordado.
- **Dos modalidades.** Entrega normal: comprobaciones habituales y un pase de revisión independiente en una sesión distinta. Entrega verificada: dos pases ciegos consecutivos sobre una versión con huella.
- **Reglas en código.** Los scripts (descubrimiento de agentes, validación de encargos, arranque de tandas, huella de versión, puerta de alcance, evaluación) hacen mecánicamente lo que la prosa no garantiza.

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

Puedes añadir «entrega normal» (predeterminada) o «entrega verificada». El coordinador elige agentes, modelos y papeles, arranca a los ejecutores en paralelo, integra y te informa por tarea. Más ejemplos en [docs/usage.md](docs/usage.md).

## Resultados

- En 9 simulacros con 45 criterios fijos, la versión candidata medida obtuvo 39/45 frente a 21–23/45 de la versión anterior, con 1 repetición y jueces LLM ciegos. La versión publicada incluye ediciones posteriores (correcciones de texto, scripts y papeles adaptativos) que no se volvieron a medir completas; método y límites en [docs/evaluation.md](docs/evaluation.md).
- En dos tareas reales de un proyecto Rust privado, el equipo económico igualó y superó la solución de referencia según una revisión ciega; ninguna sesión de frontera escribió código.
- Son señales, no garantías: hay una sola repetición por caso y el juicio lo hace un modelo. Método y límites en [docs/evaluation.md](docs/evaluation.md).

![A/B real: calidad y tokens](docs/img/ab-results.svg)

En un A/B real, implementar `scripts/cost_report.py` con el mismo contrato para ambos lados: con EzOrca el juez ciego dio 14/15 casos límite y 0 bloqueantes; sin EzOrca, 9/15 y 1 bloqueante. Sin EzOrca fue más barato y rápido en esa tarea chica; EzOrca gastó más tokens y entregó más calidad. Detalle y límites en [docs/evaluation.md](docs/evaluation.md).

## Estructura del repo

```text
SKILL.md                 la skill y su contrato
references/              equipo y modelos, encargos, registro del Run, scripts, evaluación
scripts/                 8 utilidades en Python y tiers.json
scripts/tests/           pruebas de los scripts
docs/                    instalación, uso, arquitectura, scripts, evaluación, investigación
eval/                    casos y plantillas de la evaluación
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

EzOrca is a skill for coordinating teams of coding agents in Orca: an expensive front-tier model plans, writes the task briefs, integrates and accepts, while cheap, free or local models write all the code and tests.

- Picks roles by risk and cost, and escalates by evidence instead of impatience.
- Supports normal and verified delivery; by default the front tier does not write code, and the user can say otherwise.
- Discovers installed agents and models on every run instead of hardcoding a list.
- Ships small Python 3.11+ scripts for agent discovery, spec checks, wave launching, version fingerprints, scope gates and skill evaluation.

Requirements: Orca with its `orca` CLI, at least one agent supported by Orca installed, and Python 3.11 or newer. Clone into `~/.agents/skills/ezorca` or `~/.claude/skills/ezorca` and ask `Use EzOrca for <task>`.

Evaluation is documented honestly: the measured candidate scored 39/45 criteria across 9 scripted simulations against 21–23/45 for the previous version, plus two real tasks, with a single repetition and LLM judges; later edits to the published version were not re-measured in full. Licensed under MIT.
