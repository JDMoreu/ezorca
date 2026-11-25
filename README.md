# EzOrca

Skill para resolver tareas de código directamente en el chat o coordinar equipos de agentes en Orca.

## Qué es y para quién

EzOrca decide primero entre trabajar directo en el chat o coordinar un Run de Orca. En un Run, un modelo caro planea, escribe los encargos, integra y acepta. Los modelos económicos, gratis o locales escriben el código y las pruebas. La meta de diseño era un resultado de nivel frontera con la mitad del costo o menos. EzOrca ahora elige el modo antes de planear porque, en el A/B justo, coordinar las tareas chica y mediana costó más sin una mejora concluyente de calidad. [Evaluación](docs/evaluation.md#ab-justo-sesiones-nuevas-con-y-sin-ezorca)

Es para quien ya usa Orca con uno o más agentes de código (Claude Code, Codex, OpenCode u otro que Orca liste) y quiere delegar trabajo real sin pagar modelos caros por escribir líneas. También sirve para comparar dos versiones de una skill con evidencia, en vez de a ojo.

## Ideas clave

- **Elefante y Goldfish, por ejemplo.** El Elefante suele ser el modelo de tu chat: piensa, planifica, reparte, revisa y acepta. Los Goldfish son los modelos económicos que ejecutan. En un Run coordinado la frontera no escribe código, ni las pruebas, ni las ediciones triviales; el usuario puede indicar otra cosa.
- **Directo o coordinado.** Antes de planear, EzOrca anuncia el modo y el motivo en una línea. Por defecto, el modelo del chat hace las tareas chicas y medianas y, si tocan lógica, suma un QA barato en otra sesión.
- **Papeles adaptativos.** Cada Run coordinado define los papeles según el encargo y los asigna por capacidad, costo y disponibilidad. Por ejemplo, un cambio riesgoso puede sumar diseño senior y un QA de otra familia.
- **Escalera de modelos.** Económico o gratis → económico capaz → modelo medio → y como último recurso la frontera describe la solución para que la escriba un modelo barato. Dos fallos en la misma tarea obligan a subir un escalón.
- **Avisa y sigue.** Al escalar o reasignar, el coordinador avisa en una línea qué cambia, por qué y cuánto cuesta. Pregunta solo si abriría una sesión de frontera nueva o si se supera el presupuesto acordado.
- **Dos modalidades en Runs coordinados.** La entrega normal incluye las comprobaciones habituales y, para cambios no triviales, un pase de revisión en otra sesión. La entrega verificada exige dos pases ciegos consecutivos sobre una versión con huella.
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

Si el encargo amerita coordinar, el chat elige los agentes, modelos y papeles, reparte el trabajo e integra los resultados. Pedir «entrega verificada» o dos pases ciegos activa un Run coordinado, incluso en tareas chicas. Más ejemplos en [docs/usage.md](docs/usage.md).

## Resultados

- En 9 simulacros con 45 criterios fijos, la versión candidata medida obtuvo 39/45 frente a 21–23/45 de la versión anterior, con 1 repetición y jueces LLM ciegos. La versión publicada incluye ediciones posteriores (correcciones de texto, scripts y papeles adaptativos) que no se volvieron a medir completas; método y límites en [docs/evaluation.md](docs/evaluation.md).
- En dos tareas reales de un proyecto Rust privado, el equipo económico igualó y superó la solución de referencia según una revisión ciega; ninguna sesión de frontera escribió código.
- En el A/B justo (2 tareas × 2 brazos × 2 repeticiones, con el mismo modelo fuerte en el chat), coordinar las tareas chica y mediana usó 2,8 y 1,6 veces los tokens de salida del modelo caro y tardó 1,8 y 2,8 veces más, respectivamente, sin una mejora concluyente de calidad. [Evaluación](docs/evaluation.md#ab-justo-sesiones-nuevas-con-y-sin-ezorca)

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

EzOrca is an Orca skill that first decides whether the chat should do the work directly or coordinate a team of coding agents. Small and medium tasks default to direct work because coordination used more frontier-model output tokens without a conclusive improvement in quality in the fair A/B test. [Evaluation](docs/evaluation.md#ab-justo-sesiones-nuevas-con-y-sin-ezorca)

- Picks roles by risk and cost, and escalates by evidence instead of impatience.
- Supports normal and verified delivery in coordinated runs. The frontier model plans and reviews, while cheaper models write the code and tests unless the user asks otherwise.
- Discovers installed agents and models on every run instead of hardcoding a list.
- Ships small Python 3.11+ scripts for agent discovery, spec checks, wave launching, version fingerprints, scope gates and skill evaluation.

Requirements: Orca with its `orca` CLI, at least one agent supported by Orca installed, and Python 3.11 or newer. Clone into `~/.agents/skills/ezorca` or `~/.claude/skills/ezorca` and ask `Use EzOrca for <task>`.

Evaluation is documented honestly: the measured candidate scored 39/45 criteria across 9 scripted simulations against 21–23/45 for the previous version, plus two real tasks, with a single repetition and LLM judges; later edits to the published version were not re-measured in full. Licensed under MIT.
