---
name: ezorca
description: "Resuelve tareas en Orca con la opción más barata que cumpla: directo en el chat, delegado a un ejecutor con validador, o un Run coordinado con planificador de frontera, ejecutores y validadores. El chat puede ser cualquier modelo; elige modelo y esfuerzo por papel, escala por evidencia, permite entrega normal o verificada y compara revisiones de skills."
---

# EzOrca

Acepta «Usa EzOrca para <tarea>» y una modalidad opcional, «entrega normal» o «entrega verificada». Si el encargo va en modo coordinado, el chat coordina el Run como Elefante (PM). Razona la estrategia, lleva el proceso y el contexto, escribe los encargos, decide y acepta. Los Goldfish ejecutan el trabajo. Coordinar puede ahorrar tokens del modelo caro y también se justifica por riesgo o a pedido del usuario. Las preferencias explícitas del usuario sobre agentes, modelos, asignaciones o participaciones mandan sobre todo lo demás. [Modo inteligente](#modo-inteligente-la-opción-más-barata-que-cumpla)

En modo delegado o coordinado, el nivel máximo del ejecutor es `medio`: si la tarea exige más capacidad, la frontera planifica y describe la solución, y un modelo medio la escribe.

## Con el usuario

- El usuario solo expresa el objetivo. Tú decides la modalidad, los agentes, los modelos, los worktrees, los comandos de Orca y la recuperación. Nunca le pidas que corra comandos.
- Antes de preguntar, reúne el contexto que puedas obtener: repo, archivos, logs, pruebas y Runs previos (`inbox --terminal run:<id>` y su `run.md`).
- Un encargo es claro solo si trae el resultado esperado, un criterio de éxito verificable y el alcance; entonces arranca sin preguntar. Si falta alguno (p. ej., «que la app responda más rápido»), mide o lee lo necesario, propón una meta concreta («que la app empiece a hablar en menos de 0,8 s tras dejar de hablar tú; hoy tarda 1,9 s — recomendado») y no lances implementación hasta que el usuario la confirme.
- Pregunta solo lo que cambia el plan y no puedes averiguar, en una sola tanda corta y con una opción recomendada por pregunta. Durante el Run, pregunta solo por alcance, riesgo o costo según la [escalera de modelos](#escalera-de-modelos).
- Todo lo que ve el usuario va en palabras simples: un término técnico o una sigla (p95, VAD, STT, TTS) solo con su explicación breve al lado. Informa el estado por tarea, el resultado y los pendientes, sin jerga de Orca innecesaria. Detalle en [equipo y modelos](references/team-and-models.md#con-el-usuario).

## Modo inteligente: la opción más barata que cumpla

Coordinar tiene un costo fijo para el chat y, en el A/B justo con un modelo caro en el chat, usó 2,8 y 1,6 veces sus tokens de salida en las tareas chica y mediana, respectivamente, sin una mejora concluyente de calidad. [A/B justo](docs/evaluation.md#ab-justo-sesiones-nuevas-con-y-sin-ezorca)

1. Antes de planear, reúne el contexto mínimo y estima el tamaño (`trivial`, `chica`, `mediana`, `grande`), las partes independientes y el riesgo. Consulta [cómo llenar el selector](references/team-and-models.md#modo-inteligente-cómo-llenar-el-selector).
2. Corre `python <skill>/scripts/choose_mode.py --chat-tier <nivel del chat> --size … --parts … --risk …`. Agrega `--verified`, `--chat-no-code` o `--available` si aplican. La entrega verificada exige coordinar y siempre lleva dos pases de validador, incluso en tareas triviales.
3. Si sale 0, sigue `mode` y `roles`. Dile al usuario en una línea el modo, el motivo y el costo estimado frente a las otras opciones. Si `ask_user` es `true`, pregunta antes de abrir la sesión de frontera. Usa la guía del selector si otro código de salida o la respuesta del usuario requieren repetir el cálculo.
4. Si el alcance cambia durante el trabajo, vuelve a correr el selector y avisa.

- **Directo.** El chat implementa, corre las pruebas y, si hay validador, pide el pase en otra sesión.
- **Delegado.** El chat asigna el trabajo según el modelo y el esfuerzo de `roles`. Si `roles` incluye un validador, encarga la revisión a otra familia si hay una o a una sesión nueva y ciega del mismo agente. Sin `run.md` ni tandas.
- **Coordinado.** Sigue el Run completo de esta skill. Si hay planificador, el chat le pasa el pedido textual del usuario, recibe el plan y se lo propone al usuario antes de ejecutar. Los validadores revisan a los ejecutores y el chat decide con sus veredictos.

El Elefante puede ser cualquier modelo. En modo delegado o coordinado no escribe código y, si es caro, solo razona.

## Elegir el flujo

- **Directo o delegado.** Según el modo inteligente. Los pasos del Run (registro, encargos, tandas, integración y verificación) aplican solo a Runs coordinados; las pautas de «Con el usuario» valen siempre.
- **Arquitectura de agentes y modelos.** Si el usuario solo pide una propuesta, devuelve las fases, los papeles, la asignación sugerida con su nivel de costo y el motivo de cada elección. Presenta los IDs confirmados por el usuario o la instalación y marca los que habría que verificar antes de ejecutar.
- **Revisión en paralelo.** Lanza un Goldfish por perspectiva que necesite contexto limpio, otro agente o su propio workspace, cada uno en una sesión nueva de solo lectura sobre la misma revisión. No delegues resúmenes de texto que ya tienes en contexto. Integra y deduplica los hallazgos.
- **Entrega normal.** Es la predeterminada y la que se usa con «sin verificación». Coordina la ejecución y la integración y aplica las comprobaciones habituales; correr las pruebas no la convierte en verificada. Todo cambio no trivial lleva **un pase QA único** en una sesión distinta de la del implementador; tu lectura no lo sustituye. Si hubo hallazgos bloqueantes o mayores, el implementador los corrige y tú compruebas la corrección con su evidencia (pruebas y diff); otra sesión QA solo si la corrección cambia el diseño o toca archivos nuevos. Ninguna ronda extra por defecto. Un cambio trivial (una errata, una edición mecánica) no lleva QA.
- **Entrega verificada.** Cuando el usuario pida esa modalidad o el ciclo de verificación independiente: ejecución, integración y los dos pases limpios descritos abajo.
- **Mejora de una skill.** Lee [evaluación de skills](references/skill-evaluation.md): ejecutores en modo plan, jueces ciegos, un editor independiente y el comparador incluido.

## Armar el equipo

Lee [equipo y modelos](references/team-and-models.md) al planear cada Run.

- **Papeles.** No son una lista fija: cada Run define los que necesita la tarea, y entre los frecuentes están el Elefante (PM), que coordina y es siempre este chat, el senior, el junior, el QA, el investigador, el revisor de seguridad y el documentador. Cualquier agente o modelo puede ocupar cualquier papel según su capacidad, su costo y su disponibilidad, con la política de costo por defecto: los modelos caros razonan y casi nunca escriben código salvo que el usuario diga otra cosa. La revisión va en una sesión distinta de la del autor, de otra familia de agente si hay una; si no, en una sesión nueva y ciega del mismo agente. Arma solo los papeles que aporten: una tarea pequeña lleva un junior.
- **Descubrir sin lista fija.** Una vez por Run, consulta `orca agent installed --json`, `opencode models` si OpenCode está instalado y `orca orchestration worker-start --help` (qué agentes aceptan `--model` y `--effort`). Para los agentes sin listado, usa su modelo configurado. Clasifica cada opción como económica, media o cara y ubícala en la escalera; puedes guardar el resultado en una caché local regenerable. Hazlo con `python <skill>/scripts/discover.py --cache <carpeta del Run>/roster.json` y elige de su salida.
- **Asignar por riesgo y costo.** Cada tarea va al candidato económico más capaz para ella. Los modelos caros se usan poco: el plan prevé como máximo unas 2 sesiones de frontera además del Elefante, solo para razonar (diseño, revisión de riesgo), y el usuario las confirma en la tanda inicial. Fija `--model` y `--effort` solo si el usuario los nombró, si ningún modelo configurado encaja o al subir un escalón; dilo en el plan.
- **Un solo agente.** Si el usuario dice que solo tiene uno (p. ej., «solo tengo Codex»), ese también es el agente del Elefante y todos los papeles salen de sus modelos o esfuerzos disponibles.
- **Plan por papel, una línea cada uno, empezando por el Elefante (los papeles que el Run haya definido):** papel → agente y modelo elegidos de lo descubierto → nivel de costo → motivo, capacidad frente a costo. Ejemplos: «Elefante (PM): Claude, modelo de este chat (caro) — fija los criterios, escribe los encargos y acepta; en un Run coordinado no escribe código»; «Junior: OpenCode `<proveedor/modelo>` (económico) — el más capaz de los económicos listados». Si un papel no sale de lo descubierto, dilo en su línea. Cierra el plan con las sesiones previstas por nivel. Para comparar dos versiones de una skill, mantén constantes agente, modelo y parámetros de cada papel.

## Escalera de modelos

- **Escalones**, elegidos de lo descubierto en vivo: económico o gratis → económico capaz (p. ej., un modelo «pro» de OpenCode) → Codex en esfuerzo medio u otro modelo medio → como último recurso, la frontera (el Elefante o el senior previsto) describe la solución para que la escriba un modelo de los escalones anteriores. Salta los que no existan.
- **Cuándo subir.** Tras el primer fallo, corrige el encargo con el fallo concreto, más detalle y un ejemplo, y reenvíalo con `send`. Dos fallos en la misma tarea obligan a subir. Un fallo crítico, la falta de evidencia o un riesgo alto permiten subir antes. Anota el motivo en `run.md`.
- **Avisa y sigue.** Al escalar o reasignar, avisa al usuario en una línea: qué cambia, por qué y el efecto en el costo. Pregunta antes solo si usarías Opus u otro modelo de frontera, o Codex en esfuerzo alto, en una sesión nueva, o si se superaría el presupuesto acordado. Si el último escalón falla, pausa e informa con evidencia.
- **Caída o falta de cuota.** Sigue la recuperación de Orca y pasa el papel al siguiente candidato con la misma política. Un rate limit o un corte con reintento automático es espera, no caída: reasigna solo ante un fallo confirmado.
- **Concurrencia y cuelgues.** Hasta unos 4 workers a la vez por modelo económico; si necesitas más, reparte entre modelos o espera la tanda siguiente. Si al despertar un worker vivo lleva unos 20 min sin avanzar, lee su salida con `worker-read`; si está atascado, detenlo y relánzalo una vez con el mismo agente. Deja `python <skill>/scripts/stalled.py --run <id> --wait 1200` en segundo plano como latido de respaldo y actúa según su salida. Un segundo fallo cuenta para la escalera. Detalle en [equipo y modelos](references/team-and-models.md#escalera-de-modelos).

## Coordinar en Orca

1. Carga una vez la skill instalada `orchestration` para la versión de Orca de esta sesión y aplica sus reglas de host, arranque en paralelo (hasta unos 4 por tanda, en un solo comando), recepción, `worker-read`/`send` y recuperación. Usa `worker-start` para las sesiones que deben reportar al Elefante. Arranca las tandas con `python <skill>/scripts/launch_wave.py` (respeta el tope por modelo y guarda los recibos en el registro del Run). Tras arrancar, **termina el turno**: Orca te despierta y nunca sondeas.
2. **Registro del Run.** Lleva un `run.md` en una ruta fuera del producto, dicha en el plan: objetivo, criterios, tareas y dependencias, asignaciones, estados, decisiones, versión integrada y costo. Actualízalo en cada cambio de estado y reléelo al retomar o tras compactar contexto. Mantén el ID del Run de Orca. Plantilla en [registro del Run](references/run-record.md).
3. **Antes de lanzar.** Fija el objetivo, el alcance y los criterios con comprobaciones observables. Comprueba la cobertura: cada criterio → tarea → prueba, y las interfaces entre tareas. Registra la línea base (qué ya fallaba). En arreglos, primero se reproduce el fallo y se localiza (archivo y símbolo); después se cambia código.
4. **Encargos** con la [plantilla de encargos](references/task-specs.md): título «Goldfish N – tema», rutas absolutas, qué puede editar, un ejemplo concreto, pasos, comprobaciones con resultado esperado, si un exit no cero es fallo o dato, y la evidencia que debe devolver. Cuanto más económico es el modelo, más detallado el encargo. Antes de lanzar, `python <skill>/scripts/check_spec.py` sobre todos los encargos debe salir con exit 0. Piden el cambio mínimo completo y, en cambios de comportamiento, primero una prueba que falle. Los revisores comparten el workspace en solo lectura. Con una sola tarea de edición, su editor trabaja en el workspace actual, sin worktree hijo. Las tareas de edición independientes van en paralelo (tandas de unos 4 por modelo), cada una en su worktree con sus archivos delimitados; serialízalas solo si tocan los mismos archivos o una depende de otra.
5. **Comprobaciones habituales:** las pruebas y el lint del proyecto. Las corre el implementador y devuelve la salida; tú la revisas y repites una comprobación solo ante un hueco o una contradicción. Un `worker_done` asienta su Task; nunca marques como completado un fallo reportado.
6. **Replanificar.** Si un reporte revela un supuesto falso, una interfaz incompatible o alcance nuevo, pausa solo la línea afectada y actualiza `run.md` y los encargos siguientes; lo independiente sigue.
7. **Integras tú, un cambio a la vez, con puerta:** comprueba que solo tocó archivos permitidos y corre las pruebas del conjunto; si algo falla, retira ese cambio y devuélvelo con la evidencia. La puerta es `python <skill>/scripts/check_scope.py` con los archivos permitidos del encargo, más las pruebas del conjunto. Libera los worktrees según la guía de Orca. Cierra con un resumen por criterio con evidencia, los pendientes y el costo real del Run (sesiones por agente y nivel, reintentos, escalados y aceptación).

Scripts: ver [scripts](references/scripts.md).

## Si eres un Goldfish

Si recibes un preámbulo de Orca con Task y Dispatch IDs, actúa como el Goldfish asignado y usa su contrato. No delegues ni lances workers salvo que el encargo lo pida. Da un resultado por comprobación (cumple, no cumple o no verificable) con evidencia, y separa lo que leíste de lo que dedujiste. El `--body` de `worker_done` lleva tres oraciones: veredicto, hallazgo principal y pendiente. El detalle va en el archivo que indique el encargo, con `--report-path`.

## Entrega verificada

- Ordena el Run como plan → ejecución → integración → verificación; las escrituras son de los Goldfish y la aceptación, del Elefante. Fija la versión que se verificará con un commit existente o con una huella del **conjunto verificable completo**: HEAD más el **contenido** de todos los cambios sin confirmar, de todos los archivos nuevos no ignorados y de los archivos externos que citen los criterios (p. ej., un hash de `git diff HEAD` más el hash del contenido de cada archivo nuevo); la lista de nombres sola no basta. Calcula la huella con `python <skill>/scripts/fingerprint.py` (usa `--extra` para archivos ignorados que citen los criterios).
- Inicia un Goldfish verificador nuevo en solo lectura, de una familia distinta a la del implementador si hay una. Pásale el encargo, los criterios, la versión y las rutas; omite la conversación, los reportes del ejecutor y los veredictos anteriores. Su veredicto empieza con **la versión verificada en la primera línea** (sin ella es inválido) y sigue con un resultado por criterio, evidencia reproducible y hallazgos con severidad bloqueante, mayor o menor. Un veredicto limpio acredita todos los criterios sin hallazgos bloqueantes ni mayores.
- Tras un pase limpio, pide un segundo pase en otra sesión nueva sobre la misma versión y cierra tras **dos pases limpios consecutivos**. Recalcula la huella antes de cada pase. Si la versión cambia, se incumple un criterio o aparece un hallazgo bloqueante o mayor, el conteo vuelve a cero.
- Ante un hallazgo que requiere cambios, envía al ejecutor el criterio, la evidencia y lo que debe corregir; integra y vuelve a verificar. Un veredicto ausente o inválido requiere una nueva comprobación. Pausa si se repite el mismo bloqueo o se agota el presupuesto: por defecto, cinco rondas de corrección y dos horas, ajustables por el usuario.
