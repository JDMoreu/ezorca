# Evaluación

EzOrca se cambió midiendo, no por impresión. Cada candidata se comparó con la
versión instalada bajo la misma rúbrica, con ejecutores baratos y jueces ciegos.
Este documento resume el método, los resultados y los límites de esa medición.
La rúbrica y las plantillas quedan en [`eval/`](../eval/cases.json) para repetirla.

## Por qué se evaluó

La meta era calidad de frontera con la mitad o menos del costo (meta de diseño;
aquí no se midió en dólares): modelos caros
solo para razonar y trabajo bien definido en modelos económicos. Agregar prosa a
una skill de coordinación puede mejorar un caso y empeorar otro sin que se note.
La evaluación existía para decidir entre textos con evidencia, detectar
regresiones y no aceptar una candidata solo porque suene mejor.

## Método

### Casos y criterios

- **9 casos fijos** de encargo completo: tarea trivial, entrega verificada de dos
  pases, revisión de solo lectura, reparto por papeles, un solo agente
  disponible, caída de cuota a mitad de tarea, mejora de la propia skill,
  presupuesto eficiente y encargo ambiguo.
- **45 criterios binarios** (cumple o no cumple), **26 marcados como críticos**.
  Cada criterio pide algo explícito y observable en el plan; si es ambiguo, se
  cuenta como incumplido.
- Los ids de casos y criterios son estables entre rondas para poder comparar. La
  rúbrica completa está en [`eval/cases.json`](../eval/cases.json).

### Ejecutores en seco

Un agente económico recibe el encargo del usuario y escribe el **plan completo
del coordinador**: modalidad, papeles, comandos exactos, specs de cada worker y
fronteras de turno. No ejecuta Orca ni lanza workers; así el intento cuesta una
sesión y no deja efectos. La plantilla es
[`eval/templates/exec.md`](../eval/templates/exec.md).

### Jueces ciegos

Un juez por caso, en sesión propia, recibe los dos planes del mismo caso en
**orden aleatorio** y los juzga por separado contra los criterios. No ve el
nombre de la variante, ni el resultado de rondas anteriores, ni el juicio del
otro plan. La plantilla es [`eval/templates/judge.md`](../eval/templates/judge.md).
La versión instalada se volvió a juzgar en cada ronda, junto a su candidata.

### Editor independiente y comparador estricto

- El editor de cada ronda trabaja en una sesión nueva, solo con los fallos y su
  evidencia; no participa en la ejecución ni en el juicio.
- `scripts/compare_skill_results.py` exige que la candidata tenga **más
  aciertos**, **ninguna regresión** por caso y criterio, y **ningún fallo
  crítico** en ninguna repetición. Devuelve 0 si acepta y 1 si rechaza.

### Repeticiones

El cribado usa **una repetición por caso**. Los casos y criterios decisivos se
confirmaron con dos repeticiones adicionales, en tres juicios agregados. Una
repetición sirve para descartar; no basta para declarar una diferencia pequeña.

### Papeles

Los papeles que aparecen en este documento (Elefante, senior, junior, QA) son
ejemplos, no una lista fija: cada Run define los que necesita (por ejemplo,
investigador, arquitecto, revisor de seguridad, tester) y cualquier agente o
modelo puede ocupar cualquiera según capacidad, costo y disponibilidad. Por
defecto, los modelos caros razonan y casi nunca escriben código, salvo que el
usuario indique otra cosa.

## Rondas y resultados

| Ronda | Qué cambió | Versión anterior | Candidata |
|---|---|---|---|
| Versión anterior | — (texto instalado, re-juzgado en cada ronda) | 21–23 / 45 | — |
| Ronda 1 | Papeles de ejemplo por riesgo y costo, QA en sesión distinta, descubrimiento de modelos en vivo, escalado y recuperación ante cuota | 21 / 45 | **38 / 45** |
| Ronda 2 | Meta y criterio confirmados en encargos ambiguos, plan por papel con modelo y motivo, un solo editor en el workspace actual, veredicto con versión, concurrencia y cuelgues | 22 / 45 | **41 / 45** |
| Ronda 3 | Paralelismo con worktrees, lenguaje simple, ejemplo obligatorio en las specs, límite de sesiones de frontera, Elefante identificado, principios de cambio mínimo y prueba primero | 21 / 45 | **37 / 45** |
| Final | La frontera no escribe código por defecto, escalera de modelos por evidencia, «avisa y sigue», un solo agente también es el Elefante, QA de un pase, `run.md` y puerta de integración | 23 / 45 | **39 / 45** |

Las rondas 1 a 3 se midieron con las rúbricas anteriores (v2 y v3); la ronda
final usó la rúbrica v4, alineada con las decisiones del usuario. Los totales de
la versión anterior varían entre rondas (21, 22, 21 y 23) porque los jueces y la
rúbrica cambiaron; por eso cada fila se lee contra su propia base, no contra la
de otra ronda. Las tres candidatas intermedias mejoraron mucho, pero el
comparador las rechazó por regresiones puntuales; cada rechazo alimentó la ronda
siguiente.

Resultado por caso de la ronda final (rúbrica alineada con las decisiones del
usuario):

| Caso | Anterior | Final |
|---|---|---|
| entrega-normal-pequena | 5/5 | 5/5 |
| entrega-verificada-dos-pases | 5/5 | 4/5 |
| revision-proporcional | 2/6 | 5/6 |
| reparto-por-papeles | 1/6 | 4/6 |
| solo-un-agente | 3/4 | 4/4 |
| reparto-mixto-con-caida | 2/4 | 3/4 |
| mejora-skill-proporcional | 3/5 | 4/5 |
| presupuesto-eficiente | 1/6 | 6/6 |
| encargo-ambiguo | 1/4 | 4/4 |

La mejora se concentra donde la versión anterior no tenía regla: reparto por
papeles, revisión proporcional, presupuesto, caída de cuota y encargo ambiguo.
En la entrega verificada se perdió un criterio, atribuido al ejecutor económico
(ver límites).

### Confirmación en los casos sensibles

En los tres casos con más movimiento se juzgó tres veces (una original y dos
repeticiones). Tasas agregadas, anterior → final: papeles por riesgo 0/3 → 3/3,
encargo junior 0/3 → 3/3, QA de otra familia 0/3 → 3/3, escalado 0/3 → 3/3,
modo plan 0/3 → 3/3 y sesiones acotadas 0/3 → 3/3. Dos criterios bajaron de 2/3
a 1/3 (jueces ciegos y dos pases limpios) por omisiones del ejecutor económico en
reglas que el texto sí dice. Con un juez y un ejecutor ruidoso, el comparador
estricto no puede aceptar ninguna versión: más repeticiones también agregan más
oportunidades de fallar.

## A/B real: dos tareas de un proyecto Rust privado

Además del simulacro, dos tareas reales de un **proyecto Rust privado**, una
pequeña y una mediana, cada una resuelta por una sesión de modelo económico y una
sesión de QA medio:

| Tarea | Resultado frente a la solución de referencia | Costo |
|---|---|---|
| Pequeña | Equivalente según QA ciego | 1 sesión económica + 1 de QA |
| Mediana | Mejor según QA ciego: la referencia tenía un defecto de manejo de errores que la candidata no tenía | 1 sesión económica + 1 de QA |

Ninguna sesión de frontera escribió código.

## A/B real con y sin EzOrca: cost_report.py

La misma tarea, `scripts/cost_report.py` (resumir tokens por sesión de Claude
Code, Codex y OpenCode leyendo sus registros locales), con un contrato idéntico
para los dos lados y el mismo commit de partida:

- **Equipos:** sin EzOrca, una sesión de Codex en esfuerzo medio que resolvió
  sola; con EzOrca, el Elefante escribió el encargo, un junior OpenCode económico
  implementó, un QA Codex medio revisó en sesión nueva y el mismo junior corrigió.
- **Árbitros:** 10 pruebas ocultas escritas por un tercero a partir del contrato,
  y un juez ciego en sesión nueva con su propia batería de 15 casos límite y las
  implementaciones en carpetas X/Y aleatorias.

| métrica | sin EzOrca | con EzOrca |
|---|---|---|
| Pruebas ocultas (10) | 10/10 | 10/10 |
| Batería del juez ciego (15 casos límite) | 9/15 | 14/15 |
| Bloqueantes según el juez | 1 (traceback con rutas locales ante registros malformados; pérdida silenciosa de sesiones) | 0 |
| Pruebas propias | 1 prueba | 10 pruebas (antes del código) |
| Veredicto del juez | peor; no apta | mejor; apta tras un arreglo localizado |
| Tiempo de pared | ~2 min | ~10 min (incluye QA y correcciones) |
| Sesiones | 1 medio | 1 económico + 1 medio + Elefante (frontera) |
| Tokens Codex medio (in / out / caché leída) | 10 453 / 4 244 / 324 352 (total 339 049) | QA: 18 335 / 2 992 / 239 616 (total 260 943) |
| Tokens OpenCode económico (in / out / caché leída) | — | 111 339 / 25 966 / 3 590 016 (total 3 727 321) |
| Tokens frontera Claude (in / out / caché leída / caché escrita) | 0 | 48 / 12 335 / 10 600 989 / 17 367 en 18 llamadas |

![A/B real: calidad y tokens](img/ab-results.svg)

### Lectura

- **Las pruebas ocultas empataron; el juez ciego no.** Las dos implementaciones
  pasaron 10/10, pero en los 15 casos límite del juez EzOrca obtuvo 14/15 sin
  bloqueantes y sin EzOrca 9/15 con uno: un traceback con rutas locales ante
  registros malformados y pérdida silenciosa de sesiones. La diferencia vino del
  ciclo QA → correcciones, no de escribir más código.
- **Más tokens, más calidad.** EzOrca gastó varias veces más tokens, sobre todo
  en el junior económico, y a cambio entregó robustez y privacidad.
- **Un solo modelo medio basta en tareas chicas y muy especificadas.** Sin
  EzOrca, Codex medio resolvió la tarea en ~2 min y con menos tokens: para ese
  tipo de tarea, coordinar no se paga.
- **El costo del coordinador lo domina el tamaño de su contexto.** El Elefante
  releyó unos 590 000 tokens de contexto por llamada porque el chat ya era muy
  largo; en un chat nuevo habría sido una fracción. El ahorro de EzOrca aparece
  cuando la frontera no escribe código y su contexto se mantiene corto.

### Hallazgo: los registros de OpenCode cambiaron

Los dos lados siguieron el mismo error del contrato: OpenCode ya no guarda sus
sesiones en `session` sino en `session_v2`, y solo medir contra registros reales lo reveló.

### Límites de este A/B

- **Una repetición por lado.** Es una señal, no una diferencia demostrada.
- **Jueces LLM.** La batería de 15 casos y el veredicto los produjo un modelo, no
  una persona.
- **Dólares no calculados.** Los precios no se verificaron en esa sesión; el
  costo se mide en tokens, y las lecturas de caché suelen cobrarse a una fracción
  del precio de entrada según cada proveedor.

## Límites honestos

- **Una repetición en el cribado.** Es suficiente para descartar, no para
  distinguir diferencias pequeñas. El mismo texto dio 5/5, 5/5 y 2/5 en un caso
  y 4/5, 5/5 y 4/5 en otro.
- **Jueces LLM.** Tienen sesgo de posición y de estilo, y aquí hubo un solo juez
  por caso. Se mitigó con orden aleatorio y repeticiones en los casos sensibles,
  no con juicio humano.
- **Ejecutores económicos ruidosos.** Algunos fallos son del ejecutor, no del
  texto: omitió reglas que el plan sí contenía. Eso ensucia la señal y explica
  parte de las regresiones.
- **Comparador estricto.** Un solo fallo crítico o una regresión rechaza toda la
  candidata, aunque el total suba; con ruido, más repeticiones producen más
  rechazos. La versión publicada se adoptó por decisión del usuario sobre la
  evidencia, no porque el script la aceptara: el comparador rechazó la medición
  de 39/45 por tres fallos críticos, que la edición final corrige en el texto
  pero no se volvió a medir completa.
- **Rúbrica ajustada durante el proceso.** Los criterios se alinearon con
  decisiones del usuario (que la frontera no escribe código por defecto, escalera de modelos,
  «avisa y sigue»). Es un cambio legítimo pero también un riesgo de medir lo que
  se acaba de decidir; los ajustes quedaron documentados en el registro del Run
  y en los ids de la rúbrica.
- **Un solo proyecto en el A/B.** Dos tareas no demuestran superioridad general.

## Costo del proceso

Unas **110 sesiones**, la mayoría económicas (OpenCode) y medias (Codex); unas
12 de frontera, casi todas de edición y corrección. Las cuotas gratuitas de
OpenCode se agotaron dos veces y obligaron a cambiar de ejecutor. El costo es
parte del resultado: evaluar con un modelo caro por intento habría costado más
que el cambio que se buscaba.

## Cómo reproducirlo

Los archivos necesarios están en este repositorio:

- [`eval/cases.json`](../eval/cases.json): 9 casos, 45 criterios y `repeats`.
- [`eval/templates/exec.md`](../eval/templates/exec.md): encargo del ejecutor.
- [`eval/templates/judge.md`](../eval/templates/judge.md): encargo del juez ciego.

1. Copia la carpeta de una variante de la skill y prepara una carpeta de trabajo
   con `cases.json` y `templates/`.
2. Crea un ensayo por caso:

   ```sh
   python scripts/eval_kit.py --dir <trabajo> exec --variant-dir <variante> --label <etiqueta> --template <trabajo>/templates/exec.md
   ```

3. Lanza cada spec `specs/exec-<tid>.md` en una sesión de ejecutor; guarda su
   plan en `trials/<tid>.md`.
4. Empareja dos ensayos del mismo caso (base y candidata) para un juez:

   ```sh
   python scripts/eval_kit.py --dir <trabajo> pair --a <tid-base> --b <tid-candidata> --template <trabajo>/templates/judge.md --out-dir <trabajo>/juicios
   ```

5. Ejecuta cada spec `specs/pjudge-*.md` y deja los JSON en `<trabajo>/juicios/`.
6. Junta los juicios de una etiqueta y compara:

   ```sh
   python scripts/eval_kit.py --dir <trabajo> merge --label <etiqueta> --judgments <trabajo>/juicios --out <trabajo>/candidata.json
   python scripts/compare_skill_results.py <trabajo>/cases.json <trabajo>/base.json <trabajo>/candidata.json
   ```

`eval_kit.py` asigna ids opacos, conserva el mapa de ensayos en
`trials/map.json` y no revela la variante al juez. El comparador imprime
aciertos, regresiones y fallos críticos, y su código de salida sirve en CI.
Para el día a día basta una repetición; sube `repeats` solo en los pares que
cambien. El proceso completo, con criterios de parada y reparto de sesiones,
está en [`references/skill-evaluation.md`](../references/skill-evaluation.md).
