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

## A/B justo: sesiones nuevas con y sin EzOrca

> Nota: este ensayo comparó procesos distintos (directo frente a ciclos de planificación y validación); sus diferencias de tiempo y costo no se atribuyen solo a la skill. Ver [Resultados del A/B justo con proceso equivalente](#resultados-del-ab-justo-con-proceso-equivalente-t2).

Ocho sesiones nuevas de Claude Code con Claude Opus, cada una en un worktree
nuevo del mismo commit y con el mismo texto de tarea. La única diferencia entre
brazos fue la frase inicial «Usa EzOrca para lo siguiente.». Ambos brazos
tuvieron los mismos modelos permitidos: Opus para el chat y DeepSeek V4.1 Flash
por OpenCode; el brazo sin EzOrca no usó DeepSeek y escribió el código con el
propio Opus. Fueron 2 tareas × 2 brazos × 2 repeticiones. Los árbitros fueron
pruebas ocultas escritas por un tercero solo a partir del texto de la tarea (7
para T1 y 9 para T2) y un juez ciego por tarea, con las cuatro implementaciones
en carpetas A–D en orden aleatorio. El costo se mide en tokens de los registros
locales de cada intento; el tiempo, desde el lanzamiento hasta el último
mensaje del chat.

### Resultados

T1 (tarea pequeña):

| Intento | Pruebas ocultas | Juez ciego (/15) | Lugar | Minutos | Opus salida | Opus caché leída | DeepSeek (sesiones · salida) |
|---|---|---|---|---|---|---|---|
| sin EzOrca 1 | 7/7 | 10/15 | 2.º | 1,2 | 4 755 | 240 650 | 0 · — |
| sin EzOrca 2 | 7/7 | 13/15 | 1.º | 2,2 | 6 434 | 408 456 | 0 · — |
| con EzOrca 1 | 7/7 | 9/15 | 3.º | 3,1 | 16 166 | 1 618 254 | 2 · 11 804 |
| con EzOrca 2 | 7/7 | 7/15 | 4.º | 3,1 | 14 892 | 1 979 853 | 2 · 7 407 |

T2 (tarea mediana):

| Intento | Pruebas ocultas | Suite del repo | Juez ciego (/25) | Lugar | Minutos | Opus salida | Opus caché leída | DeepSeek (sesiones · salida) |
|---|---|---|---|---|---|---|---|---|
| sin EzOrca 1 | 9/9 | 80 OK | 20/25 | 2.º | 2,8 | 16 862 | 1 304 654 | 0 · — |
| sin EzOrca 2 | 9/9 | 80 OK | 16/25 | 4.º | 4,1 | 21 451 | 1 799 536 | 0 · — |
| con EzOrca 1 | 9/9 | 85 OK | 22/25 | 1.º | 7,8 | 29 115 | 3 143 903 | 4 · 18 057 |
| con EzOrca 2 | 9/9 | 90 OK | 17/25 | 3.º | 11,8 | 32 429 | 4 298 289 | 4 · 28 953 |

Promedio del juez en T2: con EzOrca 19,5/25 y sin EzOrca 18,0/25, un empate
dentro del ruido. Defecto común en T1: ninguna versión maneja bien el plural de
etiquetas de varias palabras; en T2: `repo` o `worktree_name` hechos solo de
espacios se aceptan como válidos.

### Lectura

- **Calidad.** En T1 el brazo sin EzOrca quedó 1.º y 2.º; en T2 los brazos se
  alternan, con EzOrca 1.º y 3.º. Las ocho implementaciones pasaron las pruebas
  ocultas. Con 2 repeticiones y un solo juez LLM por tarea, ninguna diferencia
  de calidad es concluyente.
- **Costo.** Salida de Opus: T1 ≈ 2,8× (15,5 k frente a 5,6 k de promedio) y T2
  ≈ 1,6× (30,8 k frente a 19,2 k). Caché leída de Opus: ≈ 5,5× en T1 y ≈ 2,4× en
  T2. Además, el brazo con EzOrca sumó DeepSeek: 2 sesiones por intento en T1 y
  4 en T2.
- **Tiempo.** Con EzOrca 1,8× en T1 (3,1 frente a 1,7 min) y 2,8× en T2 (9,8
  frente a 3,5 min).
- **Conclusión.** En estas dos tareas, la salida de Opus con EzOrca fue 2,8× en
  la chica y 1,6× en la mediana; con solo dos tareas no se puede afirmar una
  tendencia por tamaño. En ambas, un Opus que escribe el código directo consumió
  menos tokens de Opus y tardó menos. Queda como hipótesis por probar que EzOrca
  compense su costo en tareas grandes, de riesgo, o donde el QA independiente
  encuentre defectos que el autor no ve.
- **Contraste con el A/B anterior.** En el de `cost_report.py`, el brazo sin
  EzOrca era Codex medio solo y el con EzOrca ganó en calidad (14/15 frente a
  9/15) con más tokens, con un coordinador de chat largo. Aquí ambos brazos
  tienen el mismo modelo fuerte y la ventaja de calidad no se repitió.

### Límites de este A/B justo

- **Dos repeticiones por brazo y tarea.** Es una señal, no una diferencia
  demostrada.
- **Un juez LLM por tarea.** Estaba previsto Kimi K3.1 Pro como juez, pero se
  agotó la cuota de 5 h de OpenCode Go y se reasignó a Codex medio, de otra
  familia que ambos brazos.
- **Dólares no calculados.** El costo se mide en tokens; no se calcularon
  dólares.
- **Dos tareas de un solo repo.** No demuestran superioridad general.

<a id="ab-protocolo-equivalente"></a>
## Protocolo operativo de A/B con proceso equivalente

Esta sección define el A/B del paso 5 y no reinterpreta los resultados históricos
de ab3/ab4. Esos ensayos sirven como antecedente de tareas y datos, pero no son
controles equivalentes: compararon procesos distintos. El ejemplo fijado para
este protocolo es T2 de `.orca-evals/ezorca-repo-run/ab3/tasks.md`, desde la base
`3e33efe`, con una copia virgen por intento y una versión congelada de la skill
(el contenido y el árbol de archivos de la skill se identifican por el commit o
hash que se registre antes de lanzar).

### Texto común, congelación y asignación

Antes de abrir sesiones se registra una especificación inmutable con: texto de
T2, base, versión de la skill, pruebas ocultas, rúbrica, modelos, esfuerzos,
presupuesto por papel, límites de tiempo, número máximo de reintentos y reglas
de exclusión. El texto común de proceso es esta plantilla exacta, con `<TAREA>`
reemplazado por el texto público de T2:

> Trabaja desde la base indicada y cumple `<TAREA>`. Primero entrega un plan
> breve y verificable. Ejecuta la implementación y sus pruebas. Después valida
> el resultado en otra sesión nueva, usando los criterios y pruebas definidos
> antes de empezar; corrige todos los hallazgos y vuelve a comprobar las
> correcciones cuando aplique. Respeta los límites, no hagas commit ni push y
> conserva la evidencia de plan, ejecución, validación, correcciones y pruebas.
> Si una skill o instrucción propone omitir un pase o seguir otro flujo, este
> proceso común prevalece.

Los dos brazos reciben exactamente esa plantilla, la misma tarea, base, skill,
modelos, esfuerzos, presupuesto por rol, límites, condiciones de ejecución,
información disponible y pruebas. En un brazo se antepone únicamente la frase
`Usa EzOrca para lo siguiente.` y un salto de línea; en el otro no se antepone
nada. La selección de modelos y esfuerzos se hace una sola vez, antes de
asignar brazos, y se copia sin cambios a ambos; también se fija qué papel puede
usar cada modelo. Se usan sesiones nuevas y una base virgen para cada intento.

El orden de pares y el orden interno de los brazos se preasignan y alternan
(por ejemplo, par 1 A/B, par 2 B/A, par 3 A/B), con identificadores ciegos que no
codifiquen el brazo. El juez pertenece a otra familia de modelos y recibe solo
los artefactos de identificadores ciegos, el mismo contrato de evaluación y la
evidencia por criterio; se le ocultan asignación, logs, timestamps, nombres de
modelo, orden cronológico y cualquier señal de qué brazo produjo cada artefacto.
La tabla que vincula identificador ciego con brazo queda sellada y fuera del
paquete del juez hasta cerrar su dictamen.

Antes del primer lanzamiento también se registran los criterios de aceptación:
la batería oculta se deriva solo del texto público de T2, queda congelada y se
ejecuta igual en cada artefacto; la rúbrica del juez tiene criterios y máximos
fijos, exige una justificación y evidencia concreta por criterio, y no permite
crear criterios después de ver resultados. Se conservan el resultado de cada
prueba, la evidencia citada, el dictamen completo y la relación artefacto–criterio.

### Intentos, fallos y tamaño de muestra

Con presupuesto para tres pares se ejecutan tres intentos independientes por
brazo (tres pares), alternando el orden preasignado. Con presupuesto para dos
pares se informa `n=2` por brazo y el motivo presupuestario; no se presenta como
la recomendación de tres repeticiones. El objetivo es al menos tres repeticiones
por brazo, con los pares que permita el presupuesto, y siempre se informa el
límite y la incertidumbre. Un intento incompleto no cuenta como comparación
equivalente.

Antes de lanzar se fija además: un fallo de infraestructura puede reintentarse
una vez con sesión nueva, base virgen y la misma asignación, conservando el
fallo original; un fallo de cuota, límite o ejecución se marca y no se sustituye
silenciosamente; y no se permite corregir manualmente un artefacto fuera del
proceso común. Si falla un miembro del par, se conserva toda su evidencia, se
marca el par como incompleto/excluido y se reporta el motivo, sin cambiar el
orden ni reciclar su resultado en otro par. Los reintentos, exclusiones y
desviaciones se enumeran antes de calcular promedios o diferencias.

### Medición reproducible

Para cada intento se guarda un registro con: `par_id`, `intento_id` ciego,
asignación sellada, base y hash de la skill, modelo y esfuerzo por papel,
presupuesto, timestamps de inicio (lanzamiento) y fin (último mensaje o cierre
definido), duración de pared, estado, fallos y reintentos; resultados de suite
oculta por caso, criterio y salida; puntuación ciega por criterio con su
evidencia; y el inventario de sesiones que pertenecen al intento. El tiempo de
pared es fin menos inicio con el mismo reloj y definición en ambos brazos; no
se mezclan esperas ajenas ni sesiones de preparación.

La calidad se informa como casos ocultos aprobados/total y como puntos del juez
por criterio, por intento y agregados por brazo, además de la diferencia en
puntos porcentuales de la batería oculta. Se muestran también fallos críticos,
intervalos o límites descriptivos apropiados al `n` observado; con dos o tres
repeticiones no se presenta una diferencia pequeña como concluyente.

El costo atribuible a las sesiones se calcula en US$ por intento y brazo. Primero
se ejecuta `scripts/cost_report.py` sobre la ventana exacta y se conserva su
JSON: el script lee registros locales, suma `input_tokens`, `output_tokens`,
`cache_read_tokens`, `cache_write_tokens` y deja advertencias, pero no calcula
US$. Después se guarda una instantánea fechada de `models.dev` y se multiplica,
por modelo y categoría, cada token por su precio por millón / 1 000 000:
entrada, salida, caché leída y caché escrita cuando el catálogo las publique.
El informe incluye versión/fecha del catálogo, fórmula, tokens por categoría,
precio usado, subtotal y total; si falta un precio o la caché no es separable,
esa parte queda `no verificable`, no se reemplaza por el precio de entrada.
Los recibos pueden corroborar qué sesiones y modelos pertenecen al intento,
pero no convierten por sí solos tokens a dólares.

Por ejemplo, con precios fechados sintéticos de entrada US$1,00/M, salida
US$5,00/M, caché leída US$0,50/M y caché escrita US$1,25/M, un intento con
12 000 tokens de entrada, 3 000 de salida, 20 000 de caché leída y 2 000 de
caché escrita cuesta: `12 000/1 000 000×1,00 = 0,012`; `3 000/1 000 000×5,00
= 0,015`; `20 000/1 000 000×0,50 = 0,010`; `2 000/1 000 000×1,25 = 0,0025`;
total **US$0,0395**. Es un ejemplo de cálculo, no un resultado del A/B.

Por separado, se ejecuta `orca account list` justo antes y después de la tanda,
registrando el porcentaje de cada ventana por plan, y se calcula el delta en
puntos porcentuales por plan/ventana. Ese delta no se llama costo y no se
atribuye a sesiones si hubo actividad ajena, cambio de ventana, datos faltantes
o una caché no separable: se documenta el alcance y se etiqueta la medición
afectada como `no verificable`. Las ventanas de cuota nunca se tratan como
equivalentes a US$.

El archivo de datos debe permitir reconstruir cada suma: un registro por sesión
con agente, modelo, inicio, fin, tokens por categoría, precio y fuente/fecha;
un registro por prueba y criterio; un registro por juez ciego; y las instantáneas
de cuenta antes/después, más fallos, reintentos y exclusiones. El reporte final
incluye `n` completo por brazo, pares excluidos y su motivo, calidad, tiempo,
US$, delta de ventana, incertidumbres y cualquier campo `no verificable`.

## Resultados del A/B justo con proceso equivalente (T2)

### Diseño

Tarea T2 (dos mejoras en `launch_wave.py` y `discover.py`) desde la base `3e33efe`, con 3 pares (n = 3 por brazo). Cada intento fue una sesión nueva de Claude Code con Claude Sonnet 5.5 (esfuerzo medio) en ambos brazos. La única diferencia fue el prefijo «Usa EzOrca para lo siguiente.»; ambos brazos siguieron el mismo texto de proceso: planificar, implementar y probar, validar en una sesión independiente y corregir.

La validación independiente la hizo GPT-5.6 Luna (esfuerzo medio, otra familia), en una sesión nueva por candidato y con los mismos criterios. El juez ciego fue GPT-6.1 Terra (esfuerzo medio) con seis candidatos en carpetas A–F en orden aleatorio, 5 criterios y máximo 25; su primer intento quedó incompleto y se repitió con método incremental. Las pruebas ocultas fueron 9 casos escritos por un tercero solo desde el texto público. El costo se midió con los tokens de los registros locales (`scripts/cost_report.py`) y los precios de `models.dev` del 24-nov-2026 (entrada, salida, caché leída y escrita), en el nivel de precio base; el contexto máximo por llamada de los validadores fue de 53 000 tokens, bajo el umbral de 272 000.

### Resultados por intento

Minutos activos = implementación + validación + corrección. US$ = chat + validación.

| Par | Brazo | Juez (/25) | Pruebas ocultas | Min activos | Salida del chat | US$ | Hallazgo de validación |
|---|---|---|---|---|---|---|---|
| 1 | Sin EzOrca | 22 | 9/9 | 5,1 | 10 554 | 0,3838 | ninguno |
| 1 | Con prefijo | 21 | 9/9 | 5,7 | 15 079 | 0,4531 | mayor, corregido |
| 2 | Con prefijo | 22 | 9/9 | 4,9 | 14 100 | 0,4597 | ninguno |
| 2 | Sin EzOrca | 21 | 9/9 | 4,2 | 9 628 | 0,3682 | ninguno |
| 3 | Sin EzOrca | 19 | 9/9 | 5,1 | 9 377 | 0,3604 | mayor, corregido |
| 3 | Con prefijo | 21 | 9/9 | 5,2 | 12 945 | 0,4139 | mayor, corregido |

### Resultados por brazo (promedio de 3)

| Brazo | Juez (/25) | Pruebas ocultas | Min activos | Salida del chat | US$ (chat + validación = total) | Hallazgo mayor |
|---|---|---|---|---|---|---|
| Sin EzOrca | 20,7 | 9/9 en los 3 | 4,8 | 9 853 | 0,342 + 0,029 = 0,371 | 1 de 3 |
| Con prefijo «Usa EzOrca» | 21,3 | 9/9 en los 3 | 5,3 | 14 041 | 0,417 + 0,025 = 0,442 | 2 de 3 |

El único hallazgo mayor de las validaciones fue el mismo en 6 de los 9 intentos validados (3 de los 6 del A/B principal y los 3 del brazo suplementario): `repo` o `worktree_name` compuestos solo por espacios aceptados. La plantilla de validación lo mencionaba como ejemplo, lo que pudo sesgar a los validadores. Todas las correcciones las hizo la misma sesión del intento, y la coordinación las verificó con pruebas, pruebas ocultas y un caso de espacios (exit 2).

### Brazo suplementario con invocación explícita

Brazo suplementario (exploratorio; desviación declarada del protocolo): 3 intentos con el texto «Usa EzOrca para lo siguiente. Carga primero la skill ezorca con la herramienta Skill.». Los 3 cargaron la skill, pero ninguno corrió `choose_mode.py` ni delegó: trabajaron en modo directo. Pruebas ocultas 9/9 en los tres; minutos activos 5,6 / 4,8 / 4,9 (promedio 5,1); US$ 0,5667 / 0,4156 / 0,5277 (promedio 0,503, chat y validación). Se validaron con Claude Haiku 5.5 y no con GPT-5.6 Luna, porque el plan de Codex estaba a un punto de su tope. Los 3 recibieron el mismo hallazgo mayor (valores en blanco), corregido. No hubo juez ciego nuevo. El precio de Haiku usa el nivel base; no se verificó que ninguna llamada superara el umbral de 100 000 tokens del nivel alto, así que su costo de validación puede estar subestimado.

### Lectura

1. **Calidad.** Con el mismo proceso no hay diferencia de calidad observable: 9/9 en todos los intentos y 20,7 frente a 21,3 en el juez, dentro del ruido.
2. **Costo y tiempo.** El brazo con prefijo costó más (+0,07 US$ por intento, +19 %) y tardó 0,5 min más, pero con n = 3 no es concluyente.
3. **Activación de la skill.** Escribir «Usa EzOrca» no bastó para activar la skill con un chat Sonnet y este texto: 0 de 3. Con instrucción explícita sí la cargó (3 de 3), pero ninguno de los 3 corrió `choose_mode.py` ni delegó: trabajaron directo.
4. **Procesos distintos.** Por tanto, las diferencias de tiempo y costo de los A/B [justo](#ab-justo-sesiones-nuevas-con-y-sin-ezorca) y del [modo inteligente](#prueba-del-modo-inteligente-chat-de-menor-nivel) reflejan procesos distintos (directo frente a ciclos), no solo la skill.
5. **Pendiente.** Probar una tarea grande o de riesgo donde el selector elija delegar o coordinar, y reforzar la descripción de la skill para que se active con «Usa EzOrca».

### Límites

- **n = 3 por brazo.** Un solo modelo de chat (Claude Sonnet 5.5) y una sola tarea.
- **Ruido.** Diferencias de 0,6 puntos del juez y de US$ 0,07 caen dentro del ruido.
- **Un solo juez LLM.** Su hallazgo sobre simular `os.name` en las pruebas es una deducción no ejecutada; las suites pasaron en la máquina de prueba.
- **Asignación.** La coordinación vio qué id correspondía a qué brazo antes del juicio, pero no se lo dio al juez.
- **Cuota no atribuida.** El cambio de las ventanas de cuota por plan no se pudo atribuir (coordinación y reinicio de Codex en la misma ventana); queda como no verificable. Delta total observado en la ventana del A/B (instantáneas de `orca account list` antes y después, que incluyen la coordinación y las validaciones, por lo que no se atribuye a ningún brazo): Claude, ventana de 5 h 9 % a 27 % y semanal 43 % a 45 %; Codex, semanal 86 % a 88 % (su ventana de 5 h se reinició en ese lapso, así que su consumo no es verificable); OpenCode Go sin cambio.
- **Proceso.** El ciclo lo impone el texto común, así que la ventaja de EzOrca sobre un proceso sin guía no se midió.

## Prueba del modo inteligente: chat de menor nivel

> Nota: este ensayo comparó procesos distintos (directo frente a ciclos de planificación y validación); sus diferencias de tiempo y costo no se atribuyen solo a la skill. Ver [Resultados del A/B justo con proceso equivalente](#resultados-del-ab-justo-con-proceso-equivalente-t2).

### Diseño

Se repitió la tarea mediana (T2) del A/B justo desde el mismo commit de partida:
`launch_wave.py` admite `new-top-level` con `repo` y `worktree_name`;
`discover.py --cache` interpreta rutas de Git Bash en Windows y sale con exit 2
si no puede escribir; pruebas y documentación. La skill EzOrca usó el modo
inteligente (`scripts/choose_mode.py`): antes de planear, el chat estimó tamaño,
partes y riesgo, y el selector eligió la opción más barata que cumplía. Hubo
sesiones nuevas con el mismo texto «Usa EzOrca para lo siguiente.», 2 brazos × 2
repeticiones (25-nov-2026): Sonnet en Claude Code pudo usar Sonnet, DeepSeek
V4.1 Flash y Kimi K3.1 Pro por OpenCode; DeepSeek en OpenCode pudo usar DeepSeek
V4.1 Flash y Kimi K3.1 Pro. Se comparó con los 4 intentos de T2 del A/B justo:
Opus directo (sin EzOrca) y Opus con EzOrca 1.2 (coordinado). Los árbitros
fueron las mismas 9 pruebas ocultas y un juez ciego nuevo (Codex en esfuerzo
medio, sesión nueva), que puntuó juntas las 8 versiones en carpetas A–H en orden
aleatorio, con 5 criterios y máximo 25. El costo se midió en tokens de los
registros locales de Claude Code y OpenCode; el tiempo va del lanzamiento al
último mensaje. No se calcularon dólares.

### Modo que eligió cada chat

- **Sonnet 1:** directo; declaró su nivel como «medio» en vez de «económico
  capaz», pero el modo salió igual.
- **Sonnet 2:** directo; selector: 11 frente a 24,8 delegando y 25,8
  coordinando; validó Kimi.
- **DeepSeek 1:** delegado a Kimi (ejecutor) con QA de Kimi.
- **DeepSeek 2:** delegado a Kimi (ejecutor) con QA de DeepSeek en otra sesión.

Los 4 eligieron el modo que predecía el diseño.

### Resultados

| Versión | Modo | Pruebas ocultas | Suite | Juez (/25) | Lugar | Minutos | Salida del chat | Caché leída del chat | Otros modelos (sesiones · salida) |
|---|---|---|---|---|---|---|---|---|---|
| Opus directo 1 | — | 9/9 | 80 | 19 | 3.º–5.º | 2,8 | Opus 16 862 | 1 304 654 | — |
| Opus directo 2 | — | 9/9 | 80 | 17 | 7.º–8.º | 4,1 | Opus 21 451 | 1 799 536 | — |
| Opus + EzOrca 1.2, 1 | coordinado | 9/9 | 85 | 18 | 6.º | 7,8 | Opus 29 115 | 3 143 903 | DeepSeek 4 · 18 057 |
| Opus + EzOrca 1.2, 2 | coordinado | 9/9 | 90 | 20 | 2.º | 11,8 | Opus 32 429 | 4 298 289 | DeepSeek 4 · 28 953 |
| Sonnet 1 | directo | 9/9 | 86 | 19 | 3.º–5.º | 39,2 | Sonnet 26 962 | 3 026 880 | Kimi 4 · 3 321; DeepSeek 1 · 1 188 |
| Sonnet 2 | directo | 9/9 | 86 | 22 | 1.º | 7,9 | Sonnet 21 987 | 2 619 224 | Kimi 1 · 9 306 |
| DeepSeek 1 | delegado | 9/9 | 83 | 17 | 7.º–8.º | 16,8 | DeepSeek 11 836 | 3 398 144 | Kimi 2 · 22 502 |
| DeepSeek 2 | delegado | 9/9 | 79 | 19 | 3.º–5.º | 7,6 | DeepSeek 9 133 (2 sesiones) | 1 136 512 | Kimi 1 · 7 297 |

Promedio del juez: Sonnet directo 20,5; Opus + EzOrca 1.2 19,0; Opus directo
18,0; DeepSeek delegado 18,0.

Tokens de Opus: 0 en los 4 intentos del modo inteligente (frente a 19 157 de
salida promedio en Opus directo y 30 772 en Opus + EzOrca 1.2). Los intentos con
DeepSeek no usaron ningún modelo de Claude.

![Modo inteligente: calidad y tokens](img/smart-mode.svg)

### Ruido

- La evaluación nueva difirió hasta 4 puntos de la anterior en las mismas cuatro
  versiones. Con dos repeticiones por brazo, las diferencias pequeñas de puntaje
  no permiten ordenar los brazos con confianza.
- Puntajes anterior y nuevo: Opus + EzOrca 1.2, 1, de 22 a 18; Opus + EzOrca
  1.2, 2, de 17 a 20; Opus directo 1, de 20 a 19; Opus directo 2, de 16 a 17.
  La evaluación nueva usó un solo juez LLM.

### Incidentes

- Sonnet 1 tardó 39,2 min: su QA con Kimi falló varias veces (sesiones que se
  cortaron casi sin salida) hasta que lo hizo DeepSeek. Sin ese incidente,
  Sonnet 2 tardó 7,9 min.
- Sonnet 1 declaró mal su nivel («medio»); la guía estaba en un archivo de
  referencia aparte. Corrección: poner los ejemplos de nivel en `SKILL.md`.

### Lectura

- **Calidad.** En la tarea mediana, el modo inteligente obtuvo una calidad
  comparable. Las 8 versiones pasan las pruebas ocultas y el juez las ubicó
  entre 17 y 22. Sonnet directo obtuvo el mayor puntaje observado (22).
- **Tokens de salida.** La salida media del chat Sonnet fue de 24 474,5 tokens
  frente a 19 156,5 de Opus directo (+27,8 %). Al sumar la salida auxiliar de
  Kimi y DeepSeek, el brazo Sonnet promedió 31 382 tokens (+63,8 %). La salida
  del brazo Sonnet procede de modelos de menor nivel que Opus. La comparación
  mide tokens de salida y no estima dólares. El modo inteligente usó cero
  tokens de Opus. DeepSeek delegado repartió el trabajo entre DeepSeek y Kimi.
- **Tiempo.** El modo inteligente fue más lento que Opus directo (7,6 a 16,8 min,
  y 39,2 con el incidente, frente a 3,5 min de promedio).
- **Selector.** Eligió en los 4 casos el modo previsto: directo con un chat capaz
  (Sonnet) y delegado con un chat económico (DeepSeek).
- **Conclusión.** Para esta tarea mediana, un chat de menor nivel con el modo
  inteligente obtuvo calidad comparable a Opus, usó cero tokens de Opus y
  tardó más.
  Sigue pendiente medir tareas grandes o de riesgo, donde el modo pediría un
  planificador de frontera.

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
  El A/B justo usó 2 repeticiones por brazo y tarea y no mostró ventaja de
  calidad con EzOrca. La prueba del modo inteligente usó la misma tarea mediana
  y queda pendiente medir tareas grandes o de riesgo.

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
