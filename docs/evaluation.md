# Evaluación

Este documento reúne el método vigente para medir EzOrca, el último resultado y,
al final, un [Historial](#historial) corto de ensayos anteriores, con lo que
salió mal en cada uno.
La rúbrica y las plantillas quedan en [`eval/`](../eval/cases.json) para repetirla.

## Por qué se evaluó

Agregar prosa a una skill de coordinación puede mejorar un caso y empeorar otro
sin que se note. Se mide para decidir entre textos con evidencia, detectar
regresiones y no aceptar una candidata solo porque suene mejor. Desde 1.4.0 se
mide, ante todo, la calidad validada; el tiempo y el costo se informan y
desempatan, dentro de los topes de cada plan.

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
- La rúbrica v4 es anterior a 1.4.0 y todavía premia políticas superadas (p. ej.,
  el criterio `mayoria-economica`). Antes de usarla para medir 1.4.0, revisa esos
  criterios en una rúbrica nueva, con ids nuevos.

### Ejecutores en seco

Un ejecutor con el mismo agente y modelo que coordinaría en la realidad (si por
costo se usa otro, se declara) recibe el encargo del usuario y escribe el **plan
completo del coordinador**: modalidad, papeles, comandos exactos, specs de cada
worker y fronteras de turno. No ejecuta Orca ni lanza workers; así el intento
cuesta una sesión y no deja efectos. La plantilla es
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
  crítico** en ninguna repetición, ni menos casos con pass^k que la línea base
  (`reliability_regression`). Devuelve 0 si acepta y 1 si rechaza.

### Repeticiones

El cribado usa **una repetición por caso**. Los casos y criterios decisivos se
confirmaron con dos repeticiones adicionales, en tres juicios agregados. Una
repetición sirve para descartar; no basta para declarar una diferencia pequeña.

<a id="ab-protocolo-equivalente"></a>
## Protocolo operativo de A/B con proceso equivalente

Esta sección define el A/B con proceso equivalente. Los ensayos del
[Historial](#historial) no son controles equivalentes: compararon procesos
distintos. El ejemplo fijado es la tarea T2 (dos mejoras en `launch_wave.py` y
`discover.py`) desde la base `3e33efe`, con una copia virgen por intento y una
versión congelada de la skill (el contenido y el árbol de archivos se identifican
por el commit o hash que se registre antes de lanzar).

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

Tarea T2 (dos mejoras en `launch_wave.py` y `discover.py`) desde la base `3e33efe`, con 3 pares (n = 3 por brazo). Cada intento fue una sesión nueva de Claude Code con Claude Sonnet 5.5 (esfuerzo medio) en ambos brazos. La única diferencia fue el prefijo «Usa EzOrca para lo siguiente.»; ambos brazos siguieron el mismo texto de proceso: planificar, implementar y probar, validar en una sesión independiente y corregir. La skill evaluada era anterior a 1.4.0: su descripción aún no tenía el disparador «Usa EzOrca».

La validación independiente la hizo GPT-5.6 Luna (esfuerzo medio, otra familia), en una sesión nueva por candidato y con los mismos criterios. El juez ciego fue GPT-6.1 Terra (esfuerzo medio) con seis candidatos en carpetas A–F en orden aleatorio, 5 criterios y máximo 25; su primer intento quedó incompleto y se repitió con método incremental. Las pruebas ocultas fueron 9 casos escritos por un tercero solo desde el texto público. El costo se midió con los tokens de los registros locales (`scripts/cost_report.py`) y los precios de `models.dev` del 24-nov-2026 (entrada, salida, caché leída y escrita), en el nivel de precio base; el contexto máximo por llamada de los validadores fue de 53 000 tokens, bajo el umbral de 272 000 (registros de la coordinación; datos crudos fuera del repositorio).

### Resultados por intento

Minutos activos = implementación + validación + corrección. US$ = chat + validación.

| Par | Brazo | Skill cargada | Juez (/25) | Pruebas ocultas | Min activos | Salida del chat | US$ | Hallazgo de validación |
|---|---|---|---|---|---|---|---|---|
| 1 | Sin EzOrca | — | 22 | 9/9 | 5,1 | 10 554 | 0,3838 | ninguno |
| 1 | Con prefijo | no | 21 | 9/9 | 5,7 | 15 079 | 0,4531 | mayor, corregido |
| 2 | Con prefijo | no | 22 | 9/9 | 4,9 | 14 100 | 0,4597 | ninguno |
| 2 | Sin EzOrca | — | 21 | 9/9 | 4,2 | 9 628 | 0,3682 | ninguno |
| 3 | Sin EzOrca | — | 19 | 9/9 | 5,1 | 9 377 | 0,3604 | mayor, corregido |
| 3 | Con prefijo | no | 21 | 9/9 | 5,2 | 12 945 | 0,4139 | mayor, corregido |

### Resultados por brazo (promedio de 3)

| Brazo | Juez (/25) | Pruebas ocultas | Min activos | Salida del chat | US$ (chat + validación = total) | Hallazgo mayor |
|---|---|---|---|---|---|---|
| Sin EzOrca | 20,7 | 9/9 en los 3 | 4,8 | 9 853 | 0,342 + 0,029 = 0,371 | 1 de 3 |
| Con prefijo «Usa EzOrca» | 21,3 | 9/9 en los 3 | 5,3 | 14 041 | 0,417 + 0,025 = 0,442 | 2 de 3 |

El único hallazgo mayor de las validaciones fue el mismo en 6 de los 9 intentos validados (3 de los 6 del A/B principal y los 3 del brazo suplementario, ver [Historial](#historial)): `repo` o `worktree_name` compuestos solo por espacios aceptados. La plantilla de validación lo mencionaba como ejemplo, lo que pudo sesgar a los validadores. Todas las correcciones las hizo la misma sesión del intento (registros de la coordinación; datos crudos fuera del repositorio), y la coordinación las verificó con pruebas, pruebas ocultas y un caso de espacios (exit 2).

### Lectura

1. **Calidad.** Con el mismo proceso no hay diferencia de calidad observable: 9/9 en todos los intentos y 20,7 frente a 21,3 en el juez, dentro del ruido.
2. **Costo y tiempo.** El brazo con prefijo costó más (+0,07 US$ por intento, +19 %) y tardó 0,5 min más, pero con n = 3 no es concluyente.
3. **Activación.** Con la descripción anterior a 1.4.0, escribir «Usa EzOrca» no cargó la skill (0 de 3, según los registros de sesión revisados por la coordinación), así que este A/B mide el prefijo y no el flujo de EzOrca. Con la descripción de 1.4.0, la skill se cargó en 4 de 4 corridas de `eval/activation` (otra prueba: dos tareas y dos modelos, muestra chica). La medición con 1.4.0 instalada, donde la skill sí se cargó en 3 de 3 intentos con el prefijo, está en [Resultados de EzOrca 1.4.0](#resultados-de-ezorca-140-ab-t2-calidad-primero).
4. **Procesos distintos.** Las diferencias de tiempo y costo de los ensayos del [Historial](#historial) reflejan procesos distintos (directo frente a ciclos), no solo la skill.
5. **Pendiente.** Repetir este protocolo con 1.4.0 en una tarea grande o de riesgo, donde el selector delegue o coordine. La repetición con 1.4.0 en esta misma tarea ya se hizo; sus resultados y lo que sigue pendiente están en [Resultados de EzOrca 1.4.0](#resultados-de-ezorca-140-ab-t2-calidad-primero).

### Límites

- **n = 3 por brazo.** Un solo modelo de chat (Claude Sonnet 5.5) y una sola tarea.
- **Ruido.** Diferencias de 0,6 puntos del juez y de US$ 0,07 caen dentro del ruido.
- **Un solo juez LLM.** Su hallazgo sobre simular `os.name` en las pruebas es una deducción no ejecutada; las suites pasaron en la máquina de prueba.
- **Asignación.** La coordinación vio qué id correspondía a qué brazo antes del juicio, pero no se lo dio al juez.
- **Cuota no atribuida.** El cambio de las ventanas de cuota por plan no se pudo atribuir (coordinación y reinicio de Codex en la misma ventana); queda como no verificable. Delta total observado en la ventana del A/B (instantáneas de `orca account list` antes y después, que incluyen la coordinación y las validaciones, por lo que no se atribuye a ningún brazo): Claude, ventana de 5 h 9 % a 27 % y semanal 43 % a 45 %; Codex, semanal 86 % a 88 % (su ventana de 5 h se reinició en ese lapso, así que su consumo no es verificable); OpenCode Go sin cambio.
- **Proceso.** El ciclo lo impone el texto común, así que la ventaja de EzOrca sobre un proceso sin guía no se midió.

## Resultados de EzOrca 1.4.0 (A/B T2, calidad primero)

Medición del 27-nov-2026 con la skill EzOrca 1.4.0 instalada. Se lee en este orden: calidad primero; después activación y proceso real; al final tiempo y costo. Es una sola tarea con 3 intentos por brazo, así que sirve para ver tendencias y problemas, no para demostrar diferencias.

### Diseño (1.4.0)

- **Tarea.** T2, de tamaño mediano (dos mejoras en `launch_wave.py` y `discover.py`), desde la misma base `3e33efe` en una copia virgen por intento.
- **Muestra.** 3 pares, 3 intentos por brazo. Cada intento fue una sesión nueva de Claude Code con Claude Sonnet 5.5 (esfuerzo medio) en ambos brazos.
- **Único cambio entre brazos.** El prefijo «Usa EzOrca para lo siguiente.» delante del mismo texto común. En el brazo «sin» la skill aparecía en la lista de skills disponibles del chat, pero no se invocó.
- **Mismo proceso pedido.** Ambos brazos recibieron el mismo texto: plan y criterios por escrito, implementar, validar en una sesión nueva y corregir (máximo 3 rondas). Mismos modelos permitidos (Opus, Sonnet y Haiku).
- **Asignación.** El orden dentro de cada par se alternó (sin→con, con→sin, sin→con) y se fijó antes de lanzar; los ids de los intentos son ciegos (no dicen el brazo). Los dos intentos de un par corrieron a la vez.
- **Cómo se midió.** Pruebas ocultas (9 casos que los intentos no ven), la suite de pruebas del repositorio y un juez ciego: un Opus con esfuerzo alto que recibió los seis candidatos como A–F en orden aleatorio y los puntuó de 1 a 5 en cinco criterios (tandas, caché, pruebas, documentación, diseño y alcance; máximo 25). El juez es de la misma familia que los modelos de los brazos.

### Calidad

**Pruebas ocultas y suite del repositorio.** Los seis intentos pasaron las 9 pruebas ocultas (9/9) y dejaron la suite del repositorio en verde con Python 3.12 (la de f4 falla en Python 3.11; ver el hallazgo más abajo). «pass^3 = sí» significa que pasaron los 3 intentos del brazo (no solo el promedio): se cumple en los dos brazos.

**Juez ciego.** Según el juez, ningún candidato tuvo un defecto bloqueante (que invalida la entrega) ni mayor; todos los defectos que anotó son menores.

| Intento | Par | Brazo | Skill cargada | Ocultas | Suite del repo | Juez (de 25) | Defecto principal según el juez (todos menores) |
|---|---|---|---|---|---|---|---|
| v5 | 1 | sin | no | 9/9 | 80 OK | 24 | Limpia los espacios de todos los campos opcionales y reescribe la salida de `--dry-run`, fuera de lo pedido |
| w4 | 1 | con | sí | 9/9 | 81 OK | 23 | `/c` sola (sin barra final) no se convierte a `C:/` |
| f4 | 2 | con | sí | 9/9 | 80 OK (falla en 3.11) | 20 | El mensaje de caché no escribible es el error crudo del sistema y el sufijo «(caché …)» también aparece en fallos de Orca |
| b9 | 2 | sin | no | 9/9 | 82 OK | 22 | Acepta un `worktree_name` en blanco y lanza `--name "  "` |
| b2 | 3 | sin | no | 9/9 | 79 OK | 24 | Limpia los espacios de todos los campos opcionales, fuera de lo pedido |
| s5 | 3 | con | sí | 9/9 | 86 OK | 22 | Validación poco legible, `--cache ""` añadido fuera de alcance y una referencia sin los flags de `new-top-level` |

La suite del repositorio tenía 73 pruebas antes de cada intento. «Skill cargada» es una comprobación objetiva sobre el registro de la sesión, no lo que dijo el chat.

| Brazo | Juez, promedio (mín–máx) | Tandas | Caché | Pruebas | Documentación | Diseño y alcance |
|---|---|---|---|---|---|---|
| Sin EzOrca | 23,33 (22–24) | 4,67 | 5,00 | 5,00 | 4,67 | 4,00 |
| Con EzOrca | 21,67 (20–23) | 4,67 | 4,00 | 4,67 | 4,67 | 3,67 |

Por pares (con − sin): −1 (23 frente a 24), −2 (20 frente a 22) y −2 (22 frente a 24). Los rangos de los dos brazos se solapan y hay un solo juez, de la misma familia: **no hay una diferencia concluyente**. Si algo, el brazo sin EzOrca quedó 1,7 puntos arriba.

**Un hallazgo que ni las pruebas ocultas ni el juez miden.** Los validadores Opus de dos intentos con EzOrca (w4 y s5) marcaron como bloqueante que las pruebas parchean `os.name` de forma global y se rompen en Python 3.11, la versión mínima declarada y parte de la matriz de CI del repositorio. El intento f4 (con EzOrca, validador Sonnet) conserva ese defecto: su prueba `test_ruta_git_bash_en_windows` falla en Python 3.11 en Windows (1 error en 80 pruebas; `NotImplementedError: cannot instantiate 'PosixPath'`) y por tanto fallaría en el CI. Los intentos sin EzOrca no usan ese parche. Es un caso, no una conclusión: la prueba pasa en Windows con 3.12 y en WSL con 3.14.4, y Linux con 3.11, 3.12 y 3.13 no se verificó.

### Activación

La skill se cargó en **3 de 3** intentos con el prefijo y en **0 de 3** sin él. Antes de 1.4.0 eran 0 de 3 con el prefijo, así que la brecha de activación quedó resuelta. Pero esta cifra es casi trivial: el prefijo nombra la skill, y se cargó entre 4,8 y 25,7 s después del lanzamiento con la herramienta `Skill`. El disparo por la descripción se evaluó aparte en [`eval/activation`](../eval/activation/README.md).

### Proceso real

Los reportes finales de los chats se trataron como no confiables y se contrastaron con los comandos y los registros de cada sesión. Lo que se midió es **«skill + texto común» frente a «texto común»**, no «skill» frente a «nada».

- **Ningún intento con EzOrca corrió `resources.py` ni `choose_mode.py`** (la lectura de cuota y el selector de modo) ni abrió sesiones de Orca. Solo usaron subagentes de Claude Code. No se midió el modo Coordinado ni el selector. El texto común dice que su proceso prevalece sobre el flujo de cualquier skill y limita los modelos a Claude, así que no se puede atribuir solo a la skill que el selector no se ejecutara.
- **El modo del brazo con no estuvo controlado y salieron tres formas distintas.** 2 de 3 improvisaron un modo delegado (w4: ejecutor Sonnet, validadores Opus nuevos y una ronda de corrección; s5: ejecutor Sonnet, tres validadores Opus nuevos y dos correcciones, el máximo de rondas). 1 de 3 (f4) trabajó directo y validó con un Sonnet.
- **El brazo sin siguió el mismo esqueleto**, porque el texto común lo ordena: los tres escribieron criterios antes de implementar y validaron en una sesión nueva (uno con validador Opus, dos con Sonnet).
- **Desvíos declarados por los propios chats y verificados.** f4 escribió los criterios al lanzar a su validador, no antes de implementar; b9 y b2 aplicaron una corrección menor sin revalidarla; f4 no corrigió los hallazgos menores de su validador.
- **«Sesión distinta» fue un subagente de Claude Code**, con contexto aparte, pero no una sesión de Orca ni otra familia de modelos.

### Tiempo y costo

Esto va después de la calidad porque, en esta medición, **el costo no sigue al brazo sino al nivel del validador (Opus) y al número de rondas**.

Definiciones: **pared** es el tiempo desde el lanzamiento hasta el último mensaje de cualquier sesión del intento; **activo** suma los huecos de hasta 5 minutos entre mensajes. El costo en US$ se calculó con los tokens de los registros de cada sesión y los precios por categoría de token (entrada, salida, caché leída y caché escrita) de una instantánea de `models.dev` (archivo del 25-nov-2026). Es el equivalente a tarifa de API, no dinero cobrado (el plan es de suscripción). La variante «caché 1 h» agrega la escritura de caché de 1 hora a su tarifa pública (2 veces el precio de entrada), que no está en el catálogo: es **estimada**.

| Intento | Par | Brazo | Pared (min) | Activo (min) | Sesiones | US$ (catálogo) | US$ con caché 1 h (estimado) |
|---|---|---|---|---|---|---|---|
| v5 | 1 | sin | 6,1 | 6,1 | 4 | 1,56 | 1,64 |
| w4 | 1 | con | 20,3 | 20,3 | 5 | 3,84 | 3,92 |
| f4 | 2 | con | 2,8 | 2,8 | 3 | 0,54 | 0,63 |
| b9 | 2 | sin | 3,3 | 3,3 | 3 | 0,53 | 0,61 |
| b2 | 3 | sin | 13,4 | 4,5 | 3 | 0,71 | 0,80 |
| s5 | 3 | con | 23,5 | 23,5 | 8 | 5,89 | 5,98 |

Cada intento incluye un chat de título automático de unos US$ 0,01. En v5, w4 y s5, Opus aporta el 69,6 %, el 80,3 % y el 81,6 % del costo; f4, b9 y b2 usaron solo Sonnet.

| Brazo | US$ promedio (mín–máx) | US$ mediana | Pared, promedio (mín–máx) | Pared, mediana | Activo, promedio (mín–máx) |
|---|---|---|---|---|---|
| Sin EzOrca | 0,93 (0,53–1,56) | 0,71 | 7,61 (3,34–13,40) min | 6,10 min | 4,65 (3,34–6,10) min |
| Con EzOrca | 3,42 (0,54–5,89) | 3,84 | 15,54 (2,78–23,51) min | 20,32 min | 15,54 (2,78–23,51) min |

Con caché de 1 h (estimado), el promedio de US$ sube a 1,02 sin EzOrca y a 3,51 con EzOrca.

- **El promedio con EzOrca esconde un rango amplio**: dos intentos pesados (US$ 3,84 y 5,89) y uno ligero (US$ 0,54). Ese intento ligero (f4) costó lo mismo que su par sin skill (b9, US$ 0,53). Con n = 3 conviene mirar los seis valores, el rango y la mediana, no la razón entre promedios.
- **El costo sigue al validador y a las rondas.** v5, sin EzOrca pero con un validador Opus, costó 2,9 veces lo que b9, que validó con Sonnet; los validadores Opus ocuparon 16,6 de los 20,3 min de w4 y 18,5 de los 23,5 min de s5.
- **La pared de b2 está inflada.** El chat dejó una reactivación programada y respondió de nuevo tras 8,9 min de espera; su trabajo real fueron unos 4,5 min (activo).

**Ventanas de cuota del plan de Claude.** Se leyeron antes y después de cada par con `orca account list`; los porcentajes son enteros (±1 punto). Cada cambio incluye todo lo que corrió en esa ventana: los dos intentos del par a la vez y la coordinación del chat que dirige la medición (en el par 1, además, un trabajador auxiliar). **No se atribuyen a un brazo.**

| Par | Ventana de 5 h (antes → después) | Ventana semanal (antes → después) |
|---|---|---|
| 1 | 53 % → 80 % (+27) | 69 % → 73 % (+4) |
| 2 | 4 % → 9 % (+5) | 73 % → 74 % (+1) |
| 3 | 9 % → 34 % (+25) | 74 % → 77 % (+3) |

La lectura «después» del par 1 es una anotación del registro de la corrida: el archivo de esa lectura se guardó tarde y no sirve.

### Lectura de 1.4.0

1. **Calidad.** En esta tarea y con este n, EzOrca 1.4.0 **no mostró mejor calidad medida**: las ocultas y la suite empatan, y el juez dio 21,7 con EzOrca y 23,3 sin él, dentro del ruido.
2. **Activación.** Sí se arregló: 3 de 3 con el prefijo (antes, 0 de 3), con la salvedad de que el prefijo nombra la skill.
3. **Costo extra.** Viene de los validadores de frontera y de las rondas de corrección, no de una diferencia de calidad medida. Esos validadores sí encontraron un defecto real (el parche global de `os.name`) que la batería oculta y el juez no ven, pero es un solo caso.
4. **Lo que falta medir.** Que el selector (`resources.py` y `choose_mode.py`) se ejecute en los intentos con la skill, y probar una tarea grande o de riesgo, donde delegar o coordinar sea lo esperable.

### Límites de 1.4.0

- **n = 3 por brazo y una sola tarea (T2).** Un solo modelo de chat (Claude Sonnet 5.5).
- **Un solo juez, de la misma familia que los brazos.** No se usó uno de otra familia porque Codex y OpenCode estaban bloqueados por cuota. Los seis puntajes salen de la misma pasada del mismo juez, así que no son independientes entre sí.
- **El modo del brazo con no estuvo controlado** (tres formas distintas) y la variación dentro del brazo supera la diferencia entre brazos.
- **«Sesión distinta» fue un subagente de Claude Code**, no una sesión de Orca ni otra familia.
- **Pares simultáneos en la misma máquina.** Los dos intentos de un par compiten por CPU, red y límites; los pares 2 y 3 corrieron tras un reinicio de Orca y de la ventana de 5 h.
- **Pared de b2 inflada** por una reactivación programada; el tiempo activo es la mejor base para comparar.
- **Cuota no atribuible.** Las ventanas incluyen la coordinación y los validadores, y los dos intentos de cada par corrieron a la vez.
- **US$ no es dinero cobrado**, y el precio de la caché de 1 h no está en el catálogo (estimado). Tampoco se pudo cruzar el uso de tokens de los registros con el contador de la API.
- **Python 3.11 verificado solo en Windows.** Linux con 3.11, 3.12 y 3.13 no se verificó (la máquina de prueba solo tenía WSL con Python 3.14.4).
- **Activación 3/3 casi trivial**, porque el prefijo nombra la skill.
- **Resellado de la especificación del juez** durante el par 1, antes de ver resultados: según el registro del cambio, solo cambió la descripción del material que recibe el juez, no la rúbrica.

### Pendientes

1. **Hacer que el chat corra el paso 0 (leer los topes de cuota con `resources.py`) y el selector (`choose_mode.py`) de forma fiable.** Es un cambio de la skill (y quizá del texto común del A/B) que hay que evaluar y medir de nuevo; no se hizo en esta ronda.
2. **Una tarea grande o de riesgo**, donde el selector delegue o coordine.
3. **Un juez de otra familia** cuando haya cuota.
4. **Evaluar Graphify** (una skill de grafo de conocimiento del código) como contexto compartido del Run, para que los Goldfish no exploren todo el repositorio. Primero hay que medir, con los registros que ya existen, qué parte del gasto de cada sesión es exploración. Si es significativa en repositorios grandes, se haría un A/B con y sin grafo, con el orden de siempre: calidad, luego tiempo y por último tokens y US$. Se documentaría solo como opción, nunca como requisito; con un solo grafo por Run, refrescado tras cada integración y, en repositorios privados, limitado al código.

## Límites del método

- **Una repetición en el cribado.** Es suficiente para descartar, no para
  distinguir diferencias pequeñas. El mismo texto dio 5/5, 5/5 y 2/5 en un caso
  y 4/5, 5/5 y 4/5 en otro.
- **Jueces LLM.** Tienen sesgo de posición y de estilo, y aquí hubo un solo juez
  por caso. Se mitigó con orden aleatorio y repeticiones en los casos sensibles,
  no con juicio humano.
- **Ejecutores ruidosos.** Algunos fallos son del ejecutor, no del
  texto: omitió reglas que el plan sí contenía. Eso ensucia la señal y explica
  parte de las regresiones.
- **Comparador estricto.** Un solo fallo crítico o una regresión rechaza toda la
  candidata, aunque el total suba; con ruido, más repeticiones producen más
  rechazos.

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
cambien. Reporta pass^k junto al promedio, no solo el conteo de aciertos. El
proceso completo, con criterios de parada y reparto de sesiones, está en
[`references/skill-evaluation.md`](../references/skill-evaluation.md).

## Historial

Ensayos anteriores a 1.4.0, con su cifra principal y lo que salió mal. Varios
midieron procesos distintos o políticas ya cambiadas (ejecutor económico, el
costo como meta, niveles por nombre); no describen cómo trabaja EzOrca hoy.

- **Simulacros 1.0 (9 casos, 45 criterios, rúbricas v2-v4).** Un ejecutor
  económico escribía en seco el plan del coordinador y jueces LLM ciegos lo
  puntuaban. La versión anterior obtuvo 21-23/45; las candidatas de las rondas
  1 a 3, 38, 41 y 37/45, y el comparador las rechazó por regresiones puntuales;
  la final, 39/45 frente a 23/45 (rúbrica v4), con un criterio perdido en la
  entrega verificada. Qué salió mal: el comparador rechazó también la final por
  tres fallos críticos; se adoptó por decisión del usuario y la edición final no
  se volvió a medir completa. Los totales de la
  versión anterior variaron entre rondas (21, 22, 21 y 23) porque cambiaron los
  jueces y la rúbrica; dos criterios bajaron de 2/3 a 1/3 por omisiones del
  ejecutor económico en reglas que el texto sí decía; y la rúbrica se alineó con
  decisiones del usuario durante el proceso (riesgo de medir lo recién decidido).
  Costó unas 110 sesiones y las cuotas gratuitas de OpenCode se agotaron dos
  veces. No vale hoy: ejecutor económico y el costo como parte de la meta.
- **Dos tareas de un proyecto Rust privado.** Una tarea pequeña y una mediana,
  cada una con una sesión de modelo económico y una de QA medio. Según un QA
  ciego, la pequeña quedó equivalente a la solución de referencia y la mediana
  mejor (la referencia tenía un defecto de manejo de errores). Qué salió mal: una
  sesión por tarea, sin repetición; dos tareas de un solo proyecto no demuestran
  superioridad general ni son reproducibles desde este repositorio.
- **A/B `cost_report.py` (24-nov-2026).** Misma tarea y contrato: Codex medio
  solo frente a EzOrca (Elefante de frontera, junior OpenCode económico, QA Codex
  medio y correcciones del mismo junior). Ambos pasaron 10/10 pruebas ocultas; el
  juez ciego (15 casos límite) dio 9/15 con un bloqueante sin EzOrca (traceback
  con rutas locales, pérdida silenciosa de sesiones) y 14/15 sin bloqueantes con
  EzOrca. Sin EzOrca tardó ~2 min y gastó 339 049 tokens; con EzOrca, ~10 min,
  3 727 321 del junior, 260 943 del QA y 10 600 989 de caché leída del Elefante
  en 18 llamadas (~590 000 de contexto por llamada, por su chat muy largo). Qué
  salió mal: en una tarea chica y muy especificada un solo modelo medio bastó y
  coordinar no se pagó; ambos lados siguieron un error del contrato (OpenCode
  ya no guarda sus sesiones en `session` sino en `session_v2`); una repetición
  por lado, un juez LLM y sin dólares. No vale hoy: ejecutor económico y el
  ahorro como meta.

  ![Gráfico histórico (24-nov-2026, antes de 1.4.0): A/B cost_report.py, calidad y tokens](img/ab-results.svg)

- <a id="ab-justo-sesiones-nuevas-con-y-sin-ezorca"></a>**ab3: A/B justo con
  procesos distintos.** Ocho sesiones nuevas de Claude Code con Opus: 2 tareas
  (T1 pequeña, T2 mediana) × 2 brazos × 2 repeticiones; la única diferencia fue
  el prefijo «Usa EzOrca para lo siguiente.». Sin EzOrca, Opus escribió directo;
  con EzOrca (1.2), coordinó y delegó en DeepSeek V4.1 Flash. Las ocho pasaron
  las pruebas ocultas. Juez ciego: en T1, sin EzOrca 10 y 13/15 frente a 9 y
  7/15 con EzOrca; en T2, 19,5/25 con EzOrca frente a 18,0.
  Con EzOrca, la salida de Opus fue 2,8× en T1 y 1,6× en T2, y el tiempo, 1,8× y
  2,8×. Qué salió mal: comparó procesos distintos (directo frente a ciclos de
  planificación y validación), así que sus diferencias de tiempo y costo no se
  atribuyen solo a la skill; con dos repeticiones y un juez LLM por tarea
  ninguna diferencia de calidad es concluyente; el juez previsto (Kimi K3.1 Pro)
  se cambió por Codex medio al agotarse la cuota de 5 h de OpenCode Go; sin
  dólares. Sus cifras calibran los pesos
  relativos de `choose_mode.py`, que solo informan y desempatan.
- <a id="prueba-del-modo-inteligente-chat-de-menor-nivel"></a>**Modo inteligente
  1.3 (T2, 25-nov-2026).** Dos brazos × 2 repeticiones: un chat Sonnet en Claude
  Code y un chat DeepSeek en OpenCode. Los 4 eligieron el modo previsto: Sonnet
  directo y DeepSeek delegando en Kimi K3.1 Pro. Las 8 versiones (4 nuevas y 4
  de T2 del ab3) pasaron 9/9 y un juez ciego nuevo las ubicó entre 17 y 22/25
  (promedios: Sonnet directo 20,5; Opus + EzOrca 1.2 19,0; Opus directo 18,0;
  DeepSeek delegado 18,0). No usó tokens de Opus, pero generó más tokens de
  salida (el chat Sonnet, +27,8 % frente a Opus directo; +63,8 % con Kimi y
  DeepSeek) y fue más lento: de 7,6 a 16,8 min (39,2 en un intento) frente a
  3,5 de Opus directo. Qué salió
  mal: el selector de entonces elegía la opción más barata que cumplía y los
  niveles se asignaban por nombre de modelo, lo contrario de la política
  vigente; un chat declaró mal su nivel («medio» en vez de «económico capaz»);
  su QA con Kimi falló varias veces hasta que lo hizo DeepSeek; la evaluación
  nueva difirió hasta 4 puntos de la anterior en las mismas cuatro versiones
  (p. ej., de 22 a 18), con un solo juez LLM, así que las diferencias pequeñas no
  ordenan los brazos; y comparó procesos distintos.

  ![Gráfico histórico (25-nov-2026, selector 1.3 y niveles por nombre de modelo, antes de 1.4.0): modo inteligente, calidad y tokens](img/smart-mode.svg)

- **Brazo suplementario del A/B T2.** Tres intentos con «Usa EzOrca para lo
  siguiente. Carga primero la skill ezorca con la herramienta Skill.»
  (exploratorio; desviación declarada). Los 3 cargaron la skill (anterior a
  1.4.0), pero ninguno corrió `choose_mode.py` ni delegó: trabajaron en modo
  directo. Pruebas ocultas 9/9, 5,1 min activos y US$ 0,503 de promedio. Qué
  salió mal: se validaron con Claude Haiku 5.5 y no con GPT-5.6 Luna porque el
  plan de Codex estaba a un punto de su tope; no hubo juez ciego nuevo; no se
  verificó que ninguna llamada superara el umbral de 100 000 tokens del nivel
  alto, así que su costo de validación puede estar subestimado.
