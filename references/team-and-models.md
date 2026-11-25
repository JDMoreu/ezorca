# Equipo y modelos

## Con el usuario

- **Contexto primero.** Antes de preguntar, lee el repo, los archivos citados, los logs, la salida de las pruebas y los reportes y el `run.md` de Runs previos sobre el mismo objetivo. No relances lo que un Run previo ya resolvió.
- **Qué preguntar.** Solo lo que cambia el plan y no puedes averiguar: el objetivo real, el criterio de éxito, el alcance, el presupuesto o los límites, las preferencias de agentes y las sesiones de frontera previstas en el plan. La modalidad, los agentes, los modelos, los worktrees y los comandos los decides tú.
- **Encargo claro o ambiguo.** Es claro solo si trae el resultado esperado, un criterio de éxito verificable y el alcance. Si falta alguno, no lo fijes en silencio: reúne el contexto (mide si hace falta), propón una meta concreta con la cifra actual y la objetivo, y confírmala en la misma tanda antes de lanzar implementación. Medir o leer antes de confirmar sí está permitido.
- **Cómo preguntar.** Todas las preguntas en un solo mensaje corto, cada una con una opción recomendada para que baste con «sí» o una letra. Ejemplo: «¿Alcance? (a) solo `src/config.rs` — recomendado; (b) también la documentación». Ejemplo de meta: «¿Meta? (a) que la app empiece a hablar en menos de 0,8 s después de que dejas de hablar (hoy tarda 1,9 s) — recomendado; (b) solo que abra en menos de 2 s».
- **Palabras simples.** Un término técnico o una sigla va solo con su explicación breve, por ejemplo «p95 (el tiempo que no supera el 95 % de las respuestas)» o «TTS (la voz sintetizada)». Las cifras técnicas exactas van en la spec, no en la pregunta.
- **Durante el Run.** Pregunta solo ante decisiones del usuario: ampliar el alcance, un riesgo (borrar datos, publicar, tocar algo fuera de lo acordado) o un costo que la [escalera](#escalera-de-modelos) manda preguntar. Lo demás lo resuelves y lo informas.
- **Cómo informar.** Qué tarea, en qué estado está, qué resultado dio y qué queda pendiente. Menciona IDs de Orca solo si el usuario los necesita. Al cerrar, el costo real en una o dos líneas, por ejemplo: «Usé 6 sesiones: 4 económicas, 1 media y este chat. Hubo 1 reintento y 1 escalado; las 3 tareas quedaron aceptadas».

## Papeles

La tabla reúne los papeles más frecuentes en un Run coordinado. El usuario
puede indicar otro reparto.

| Papel | Quién | Hace | No hace por defecto |
|---|---|---|---|
| Elefante (PM) | El modelo del chat principal | Estrategia, plan, `run.md`, encargos, decisiones, aceptación e integración | Escribir código o pruebas, ni siquiera ediciones triviales |
| Senior | Modelo caro (frontera o esfuerzo alto) | Diseño difícil, casos de aceptación de riesgo alto, revisión de riesgo; describe la solución cuando la escalera llega a él | Escribir código; trabajo repetitivo o bien definido |
| Junior | Modelo económico, gratis o local | Todo el código y las pruebas, con encargo detallado | Decisiones de diseño abiertas |
| QA | Otra familia de agente o sesión nueva y ciega | Revisión del resultado contra los criterios, sin ver el razonamiento del implementador | Corregir lo que revisa |

Cuando la tarea es difícil, en un Run coordinado la frontera no la escribe: describe la interfaz, los casos con entrada y resultado esperado, los pasos y el archivo y el símbolo que hay que cambiar, y un junior la escribe. Resolver un conflicto al integrar también es escribir código: va a un junior. El usuario puede indicar otra cosa.

**Papeles adaptativos.** Los papeles no son una lista fija: cada Run define los que necesita la tarea y cualquier agente o modelo puede ocupar cualquiera según su capacidad, su costo y su disponibilidad. La política de costo por defecto se mantiene en un Run coordinado: los modelos caros razonan y casi nunca escriben código salvo que el usuario diga otra cosa; antes de planear, decide si conviene coordinar ([¿Coordinar o hacerlo directo?](../SKILL.md#coordinar-o-hacerlo-directo)). La revisión va en una sesión distinta de la del autor, de otra familia de agente si hay. La tabla siguiente es orientativa: no obliga a abrir una sesión por papel.

| Papel de ejemplo | Qué hace | Modelo que suele convenir |
|---|---|---|
| Elefante (PM) | Coordina el Run, escribe los encargos, decide, integra y acepta | El modelo de este chat; caro |
| Investigador | Busca, contrasta y resume fuentes antes de planear | Económico o medio, con acceso a web |
| Arquitecto | Fija interfaces, descomposición y casos de aceptación | Medio o caro, solo razona |
| Senior | Diseño difícil y revisión de riesgo | Caro; describe el código y en un Run coordinado no lo escribe |
| Junior | Escribe el código y las pruebas con un encargo detallado | Económico, gratis o local |
| Revisor de seguridad | Busca riesgos, permisos y datos expuestos, sin corregir | Medio o caro, solo lectura |
| Tester | Ejecuta y amplía pruebas contra los criterios | Económico o medio |
| Documentador | Redacta guías y referencias del cambio | Económico |

## Proporción

Esta tabla orienta el reparto cuando el encargo ya se clasificó como coordinado.

| Encargo | Equipo |
|---|---|
| Trivial: una errata o una edición mecánica | Un junior económico. Sin QA. Sin `--model` si el modelo configurado ya encaja. |
| Pequeño y bien definido | Un junior y un pase QA único si el cambio toca lógica |
| Mediano o con varias partes independientes | Juniors en paralelo (hasta unos 4 por tanda y modelo), cada uno en su worktree con archivos delimitados, y un QA. Se serializan solo las partes que tocan los mismos archivos o dependen de otra. |
| Riesgoso (seguridad, datos, concurrencia, arquitectura) | Senior para el diseño y los casos de aceptación, juniors para escribirlo y QA de otra familia que revise también si las pruebas cubren esos casos |

Lanza un Goldfish por perspectiva que necesite contexto limpio, otro agente o su propio workspace. No partas en sesiones lo que una sola sesión resuelve igual.

## Descubrir y clasificar

1. Una vez por Run, consulta `orca agent installed --json` para conocer los agentes y sus IDs.
2. Si OpenCode está instalado, consulta `opencode models` (lista en vivo, formato `proveedor/modelo`). Para los agentes sin comando de listado, usa su modelo configurado.
3. Clasifica cada opción como **económica**, **media** o **cara** según tu conocimiento actual de su capacidad y su costo, y ubícala en un escalón de la [escalera](#escalera-de-modelos). Las señales del nombre (flash, mini, lite, haiku, free frente a pro, opus o esfuerzo alto) orientan, pero no deciden. Si dudas, clasifícala como media y dilo en el plan.
4. Si quieres, guarda la clasificación en una caché local regenerable, por ejemplo `<temp>/ezorca/models.json`, con la fecha y la fuente de cada entrada. Regénerala si tiene más de un día, si un arranque falla por un modelo no disponible o si cambian los agentes instalados. El usuario nunca mantiene esta lista.
5. Consulta `orca orchestration worker-start --help` una vez por Run. Ahí se indica qué agentes aceptan `--model` y `--effort`. Para OpenCode, el modelo exige un worktree existente y no admite esfuerzo; con una sola tarea de edición, ese worktree es el workspace actual, no uno hijo nuevo; con varias tareas independientes, cada una usa su propio worktree.

## Asignar

- **Junior:** el candidato económico más capaz para la tarea; empieza en el escalón más bajo que la resuelva con un buen encargo, o más arriba si el riesgo es alto.
- **QA:** una familia distinta de la del implementador. Su nivel depende del riesgo: un modelo caro si el riesgo es alto y uno económico o medio con una lista cerrada de comprobaciones en los demás casos.
- **Senior:** un modelo caro, preferiblemente de otra familia que la del Elefante.
- **Límite de frontera:** el plan prevé como máximo unas 2 sesiones de frontera además del Elefante, solo para razonar (diseño, casos de aceptación, revisión de riesgo). Van en la tanda inicial de preguntas para que el usuario las confirme. El último escalón de la escalera lo cubre el Elefante o ese senior ya previsto; abrir una sesión de frontera nueva exige preguntar.
- **Un solo agente:** si el usuario dice que solo tiene uno, ese agente es también el del Elefante. Cubre los papeles con sus modelos o esfuerzos, si `--help` lo permite. La independencia del QA viene de una sesión nueva y ciega.

En el plan, cada papel lleva una línea: `papel → agente y modelo elegidos de lo descubierto → nivel → motivo (capacidad frente a costo)`. La primera identifica al propio Elefante (el agente y el modelo del chat que coordina) y lo que decide: criterios de éxito, encargos y aceptación. Nunca dejes a «el coordinador» sin agente ni modelo. Por ejemplo:

```text
Elefante (PM): Claude, modelo de este chat (caro) — fija los criterios, escribe los encargos, integra y acepta; en un Run coordinado no escribe código.
Junior: OpenCode <proveedor/modelo-a> (económico) — el más capaz de los económicos listados; la tarea está bien definida.
QA: Codex, modelo configurado (medio) — otra familia; riesgo bajo, basta lista cerrada.
Senior: no se usa — sin diseño abierto ni riesgo alto.
Previsto: 2 sesiones económicas, 1 media y este chat.
```

Con un solo agente, por ejemplo «solo tengo Codex»:

```text
Elefante (PM): Codex, modelo de este chat — fija los criterios, escribe los encargos, integra y acepta; en un Run coordinado no escribe código.
Junior: Codex con el modelo o el esfuerzo más bajo que liste --help (económico) — tarea bien definida.
QA: Codex en sesión nueva y ciega (económico o medio) — no hay otra familia.
Respaldo: Codex en esfuerzo medio; esfuerzo alto solo si el usuario lo aprueba.
```

Ejemplos de combinaciones (los modelos concretos salen del descubrimiento):

| Disponibles | Junior | QA | Respaldo de la escalera |
|---|---|---|---|
| Claude, Codex y OpenCode | OpenCode con un modelo económico | La familia que no implementó; cara solo si el riesgo es alto | OpenCode «pro», luego Codex medio |
| Claude y OpenCode | OpenCode con un modelo económico | Claude en sesión nueva | OpenCode «pro»; luego el Elefante describe |
| Solo uno | El mismo agente con su modelo o esfuerzo más bajo | Sesión nueva y ciega del mismo agente | El mismo agente en esfuerzo medio; alto, con permiso |

## Modelo y esfuerzo

Usa el modelo configurado del agente cuando ya encaja en el nivel elegido. Fija `--model` y `--effort` solo si el usuario los nombró, si ningún modelo configurado encaja o al subir un escalón. Justifícalo en el plan o en el aviso («junior: OpenCode con `<proveedor/modelo>` porque el configurado es caro»). Las preferencias explícitas del usuario mandan.

## Escalera de modelos

Escalones, de abajo arriba, elegidos de lo descubierto en vivo; salta los que no existan:

1. Económico o gratis (incluidos los locales).
2. Económico capaz, por ejemplo un modelo «pro» de OpenCode.
3. Codex en esfuerzo medio u otro modelo medio.
4. Último recurso: la frontera (el Elefante o el senior previsto) describe la solución (interfaz, casos con entrada y resultado, pasos, archivo y símbolo) y un modelo del escalón 2 o 3 la escribe.

Cuándo subir:

- **Primer fallo** (criterio incumplido, pruebas en rojo o reporte inválido): corrige el encargo con el fallo concreto, más detalle y un ejemplo, y reenvíalo al mismo worker con `send`.
- **Dos fallos en la misma tarea:** sube un escalón; es obligatorio.
- **Subir antes** está permitido ante un fallo crítico (rompe algo que ya pasaba en la línea base o toca archivos no permitidos), falta de evidencia (sin salida de las comprobaciones, o un «no verificable» en un criterio de aceptación) o riesgo alto de la tarea.
- **Registra** cada subida en `run.md`: tarea, de qué escalón a cuál y el motivo.

Avisa y sigue. Al subir o reasignar, avisa en una línea y continúa, por ejemplo: «La tarea 2 falló dos veces con el modelo gratis; la paso a OpenCode pro. Sigue siendo económica; el costo sube poco». Pregunta antes solo si:

- usarías Opus u otro modelo de frontera, o Codex en esfuerzo alto, en una sesión nueva; o
- se superaría el presupuesto acordado.

Si el último escalón también falla, pausa esa tarea e informa al usuario con evidencia.

### Concurrencia y cuelgues

- **Tandas por modelo.** Hasta unos 4 workers a la vez por modelo económico. En un Run real, 8 workers de OpenCode con el mismo modelo chocaron con el límite de concurrencia del proveedor y sufrieron cortes. Si necesitas más, reparte entre modelos de nivel parecido o lanza la siguiente tanda cuando termine la anterior.
- **Espera, no caída.** Un rate limit, un timeout o un corte de conexión que el agente reintenta solo es transitorio: deja correr al worker. Reasigna solo ante un fallo confirmado: escalada del worker, `failedStage`, cuota agotada o un error que ya no se reintenta.
- **Cuelgues.** Orca te despierta con los avisos; no sondees. Si al despertar un worker sigue vivo pero lleva unos 20 min sin avanzar, lee su salida con `worker-read`. Si está atascado (sin salida nueva o repitiendo el mismo error), detenlo según la guía de Orca y relánzalo una vez con el mismo agente y la misma spec. Un segundo fallo en la misma tarea sigue la escalera.

### Caída o falta de cuota

- Las señales son una escalada del worker, un `failedStage` de arranque o un error de límite de uso o cuota en `worker-read`.
- Sigue la recuperación de Orca (`references/recovery-and-cleanup.md` de la guía). Reasigna el papel al siguiente candidato del mismo escalón o, si no hay, del siguiente, y repite el agente y la ubicación que correspondan.
- Avisa en una línea, por ejemplo: «OpenCode se quedó sin cuota; paso la implementación a Codex en esfuerzo medio. Consume tu suscripción de Codex y esta tarea pasa de económica a media». Pregunta antes solo en los dos casos de arriba. Si el usuario limitó los agentes y no queda ninguno, informa el bloqueo.
