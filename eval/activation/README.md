# Eval de activación de la skill

Mide si una sesión nueva de `claude -p` carga la skill `ezorca` cuando debe, y no la carga cuando se le pide que no lo haga. Nace de un A/B donde «Usa EzOrca para lo siguiente» no activó la skill (0 de 3).

## Casos (`cases.json`)

3 niveles × 2 tareas chicas del repo (traducir el docstring de `digest` en `scripts/fingerprint.py`; agregar una prueba de `idle_minutes` en `scripts/tests/test_stalled.py`).

| Nivel | Prompt | Criterio |
|---|---|---|
| `favor` | «Usa EzOrca para …» | la skill se carga en todas las corridas |
| `neutro` | solo la tarea | se informa, sin criterio |
| `contra` | «Hazlo tú directo, sin skills: …» | la skill no se carga en ninguna |

## Cómo correrla

1. Instala en `~/.agents/skills/ezorca/` el `SKILL.md` que quieres probar (guarda antes una copia del instalado).
2. Haz una copia del repo fuera de él (p. ej. `git archive HEAD | tar -x -C <temp>`) para que nada toque tu árbol de trabajo.
3. Para cada caso y cada modelo (`claude-haiku-5-5`, `claude-sonnet-5-5`), desde la copia temporal:

```sh
claude -p "<prompt del caso>" --model <modelo> --permission-mode plan \
  --output-format stream-json --verbose --max-turns 6 > <carpeta>/<id del caso>__<haiku|sonnet>.jsonl
```

   El modo plan impide editar archivos. Antes de lanzar, revisa los topes con `python scripts/resources.py --reserve 80 --reserve-window 5h=95 --reserve-window week=90`.
4. Evalúa la carpeta:

```sh
python eval/activation/check_activation.py --results <carpeta>
```

Imprime un JSON por corrida (`loaded`, `via`, `ok`) y un resumen por nivel. Exit 0 si se cumplen los criterios, 1 si no, 2 si la entrada es inválida (carpeta o corridas faltantes, línea que no es JSON).

## Qué cuenta como carga

Un evento `assistant` con un `tool_use` de la herramienta `Skill` cuyo `skill` es `ezorca`, o un `Read` de `.../ezorca/SKILL.md`. La lista de skills del evento `init` no cuenta: solo muestra que la skill estaba disponible. Las salidas crudas no se guardan en el repo.

## Resultados (cargas de la skill por corrida)

Descripción probada (ronda 1 de un máximo de 3; no hizo falta ajustarla porque ya era la versión reforzada de la rama):

> Usa esta skill cuando el usuario diga "Usa EzOrca", "con EzOrca", "EzOrca" o pida coordinar, delegar o repartir una tarea entre agentes o modelos en Orca. Planifica, delega a ejecutores, valida en sesiones independientes y corrige hasta cumplir los criterios, buscando calidad de frontera validada; después tiempo y costo, dentro de los topes de cada plan.

| Nivel | Tarea | Haiku 5.5 | Sonnet 5.5 |
|---|---|---|---|
| a favor | docstring | carga (`Skill`) | carga (`Skill`) |
| a favor | prueba | carga (`Skill`) | carga (`Skill`) |
| neutro | docstring | no carga | no carga |
| neutro | prueba | no carga | no carga |
| en contra | docstring | no carga | no carga |
| en contra | prueba | no carga | no carga |

Resumen: a favor 4/4 cargas, neutro 0/4 (informativo), en contra 0/4. Las 12 corridas terminaron con `success` y la skill figuraba disponible en todas.

Límites: una sola repetición por caso y dos tareas por nivel; con tan pocas corridas un fallo ocasional no se vería. Ampliar tareas o repeticiones antes de afirmar una tasa de activación.
