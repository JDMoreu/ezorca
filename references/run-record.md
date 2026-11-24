# Registro del Run

El Run de Orca solo guarda el título. El estado real vive en un `run.md` que escribe el Elefante: es un artefacto de coordinación, no código del producto.

## Dónde y cuándo

- **Ruta.** Fuera del producto, para no ensuciar el repo: la que acuerde el usuario o, por defecto, una carpeta de artefactos del Run fuera del repo. Dila en el plan. Junto al `run.md` se guardan los recibos de `scripts/launch_wave.py` (`--receipts`) y la salida de `scripts/discover.py`.
- **Cuándo escribir.** Al fijar el plan y en cada cambio de estado: lanzamiento, reporte, fallo, escalado, replanificación, integración y cierre.
- **Cuándo releer.** Al retomar un Run, tras compactar contexto y antes de lanzar una tanda. Si difieren, el orden de confianza es: lo que muestra Orca, luego `run.md`, luego lo que recuerdas.

## Plantilla

```markdown
# Run <ID de Orca> — <título>
Objetivo: <resultado en una oración>. Alcance: <qué entra y qué no>.
Modalidad: normal | verificada. Presupuesto: <sesiones, tiempo o costo acordados>.

## Criterios y cobertura
| Criterio | Tarea | Prueba o comprobación |
|---|---|---|
| C1 <observable> | T1 | <comando> → <esperado> |

## Línea base
<comando> → <qué ya fallaba antes de editar>. Reproducción del fallo (si es un arreglo): <comando, salida actual, salida esperada>; localización: <archivo y símbolo>.

## Tareas
| ID | Tarea | Depende de | Produce / consume | Puede editar | Asignado (agente, modelo, nivel) | Estado | Intentos |
|---|---|---|---|---|---|---|---|
Estados: pendiente, en curso, hecha, bloqueada, fallida, pausada.

## Decisiones
- <hora> <decisión> — <motivo>

## Escalados y reasignaciones
- T2: escalón 1 → 2 — dos fallos (pruebas en rojo). Avisado al usuario.

## Integración
- T1 integrada: archivos dentro de lo permitido; pruebas del conjunto <N pasan, M fallan como en la línea base>. Versión: <commit o huella>.

## Costo
| Agente y modelo | Nivel | Sesiones | Reintentos | Escalados | Aceptadas / rechazadas |
|---|---|---|---|---|---|
```

## Chequeo previo de cobertura

Antes del primer worker:

1. Cada criterio tiene al menos una tarea y una prueba o comprobación que lo acredita.
2. Cada tarea tiene un resultado comprobable; no hay tareas sin criterio.
3. Lo que una tarea produce (función, archivo, formato, comando) coincide con lo que consume la siguiente: mismo nombre, tipos y ruta.
4. Las tareas en paralelo no comparten archivos editables.

Corrige los huecos en el plan antes de gastar workers.

## Línea base y reproducción

- Una vez por Run, antes de la primera edición, se corren las comprobaciones del proyecto y se anota qué ya fallaba. Con varios editores en paralelo, la toma un Goldfish económico antes de la tanda; con uno solo, es el primer paso de su encargo.
- En un arreglo, nadie cambia código hasta tener la reproducción (comando, salida actual y salida esperada) y la localización (archivo y símbolo).
- Un fallo que ya estaba en la línea base no cuenta contra el implementador, pero se informa como pendiente.

## Replanificar

Si un reporte revela un supuesto falso, una interfaz que no encaja o alcance nuevo:

1. Marca como pausadas solo la tarea afectada y las que dependen de ella; las independientes siguen.
2. Ajusta el plan, los criterios afectados y los encargos siguientes antes de relanzarlos; registra la decisión.
3. Si el cambio amplía el alcance, sube el riesgo o el costo por encima de lo acordado, pregunta al usuario.

## Puerta de integración

Integra un cambio a la vez. Para cada uno:

1. Compara los archivos que modificó (por ejemplo, `git diff --name-only` contra la base del worktree) con su lista «Puede editar». Un archivo de más se rechaza o vuelve al implementador.
2. Corre las pruebas y el lint del proyecto sobre el resultado integrado. Si aparece un fallo que no estaba en la línea base, retira ese cambio, devuélvelo con la evidencia y no integres más encima.
3. Un conflicto al integrar es código: lo resuelve un junior con su propio encargo.
4. Anota el resultado y la versión integrada en `run.md`.

## Costo real

Lleva la tabla de costo al día: sesiones por agente, modelo y nivel; reintentos; escalados con su motivo; y entregas aceptadas o rechazadas. Al cerrar, informa al usuario en palabras simples cuántas sesiones hubo por nivel, cuántos reintentos y escalados, y cuántas tareas quedaron aceptadas. Compáralo con lo previsto en el plan.
