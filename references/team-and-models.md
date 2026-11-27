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
| Senior (planificador) | El modelo más fuerte disponible (frontera) | Diseño difícil, casos de aceptación, describe la solución; en tamaño mediana o mayor siempre planifica | Escribir código; trabajo repetitivo o bien definido |
| Ejecutor (junior) | Modelo capaz de nivel medio como máximo, nunca frontera | Todo el código y las pruebas, con encargo detallado | Decisiones de diseño abiertas |
| QA (validador) | El más fuerte disponible, en otra familia de agente o sesión nueva y ciega | Revisión del resultado contra los criterios, sin ver el razonamiento del implementador; corrige el ejecutor y se revalida hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas) | Corregir lo que revisa |

En un Run coordinado, la frontera puede describir la interfaz, los casos con entrada y resultado esperado, los pasos, el archivo y el símbolo que hay que cambiar. Si la tarea exige más capacidad que la de un modelo medio, la frontera planifica y un ejecutor de nivel medio escribe. Los conflictos de integración también se asignan a un ejecutor.

**Papeles adaptativos.** Cada Run define los papeles que necesita según la capacidad, la disponibilidad y el costo de los modelos, en ese orden. La meta es calidad de frontera validada; los modelos de frontera planifican y validan y no escriben código, salvo que el usuario diga otra cosa. El Elefante aplica el [modo inteligente](../SKILL.md#modo-inteligente-la-mejor-calidad-dentro-del-presupuesto) antes de planear. Si `choose_mode.py` incluye una sesión de frontera en `roles` y el usuario no la autorizó (`--frontier-ok`), el Elefante pide permiso para abrir esa sesión nueva. La revisión va en una sesión distinta de la del autor, de otra familia de agente si hay. La tabla siguiente es orientativa.

| Papel de ejemplo | Qué hace | Modelo que suele convenir |
|---|---|---|
| Elefante (PM) | Coordina el Run, escribe los encargos, decide, integra y acepta | Cualquier modelo disponible en el chat |
| Investigador | Busca, contrasta y resume fuentes antes de planear | Económico o medio, con acceso a web |
| Arquitecto | Fija interfaces, descomposición y casos de aceptación | Frontera, solo razona |
| Senior | Diseño difícil y planificación | Frontera; describe el código y en un Run coordinado no lo escribe |
| Ejecutor (junior) | Escribe el código y las pruebas con un encargo detallado | Medio capaz, nunca frontera |
| Revisor de seguridad | Busca riesgos, permisos y datos expuestos, sin corregir | Frontera, solo lectura |
| Tester | Ejecuta y amplía pruebas contra los criterios | Económico o medio |
| Documentador | Redacta guías y referencias del cambio | Económico |

## Proporción

Esta tabla orienta el reparto según el tamaño y el riesgo del encargo; el modo lo fija `choose_mode.py`.

| Encargo | Equipo |
|---|---|
| Trivial: una errata o una edición mecánica | Directo en el chat, sin validador, salvo con riesgo alto (un validador). |
| Pequeño y bien definido | Delegado: planifica el chat, un ejecutor económico capaz (o medio si no hay cuota) escribe y un validador de frontera revisa en otra sesión. |
| Mediano | Delegado: planificador de frontera, un ejecutor medio con esfuerzo alto y un validador de frontera. |
| Varias partes independientes o grande | Coordinado: planificador de frontera, un ejecutor por parte en paralelo (hasta unos 4 por tanda y modelo), cada uno en su worktree con archivos delimitados, y validador de frontera. Se serializan solo las partes que tocan los mismos archivos o dependen de otra. |
| Riesgoso (seguridad, datos, concurrencia, arquitectura) o entrega verificada | Coordinado con planificador de frontera, ejecutores medios y **dos pases** de validación de otra familia, que revisan también si las pruebas cubren los casos de aceptación |

Lanza un Goldfish por perspectiva que necesite contexto limpio, otro agente o su propio workspace. No partas en sesiones lo que una sola sesión resuelve igual.

## Descubrir y clasificar

1. Una vez por Run, consulta `orca agent installed --json` para conocer los agentes y sus IDs.
2. Si OpenCode está instalado, consulta `opencode models` (lista en vivo, formato `proveedor/modelo`). Para los agentes sin comando de listado, usa su modelo configurado.
3. Corre `resources.py` antes del selector. Solo su precio de salida conocido ubica una opción en la [escalera](#escalera-de-modelos); el nombre nunca sustituye el precio. `discover.py` es inventario y deja sin nivel los modelos no tasados.
4. `resources.py` guarda su propia caché de precios en `~/.cache/ezorca` (7 días por omisión, `--max-age-days`); no mantengas otra clasificación. El usuario nunca mantiene esta lista.
5. Consulta `orca orchestration worker-start --help` una vez por Run. Ahí se indica qué agentes aceptan `--model` y `--effort`. Para OpenCode, el modelo exige un worktree existente y no admite esfuerzo; con una sola tarea de edición, ese worktree es el workspace actual, no uno hijo nuevo; con varias tareas independientes, cada una usa su propio worktree.

## Modo inteligente: cómo llenar el selector

- **Nivel del chat (`--chat-tier`).** Usa el nivel sustentado por el precio conocido de `resources.py`; si no aparece, usa provisionalmente el nivel más alto razonable solo para estimar el modo, dilo y no declares elegible ningún worker hasta confirmar el precio en `pick` o `--full`.
- **Tamaño (`--size`).** Usa `trivial` para una errata, un renombre o una edición mecánica. Usa `chica` para uno o dos archivos y un comportamiento. Usa `mediana` para tres a seis archivos o un módulo, con pruebas y documentación. Usa `grande` para varios módulos, más de unos seis archivos o un diseño nuevo.
- **Partes (`--parts`).** Cuenta las partes independientes, de 1 a 50.
- **Riesgo (`--risk`).** Usa `alto` si hay seguridad, datos de usuarios, dinero, concurrencia, migraciones, arquitectura o un cambio difícil de revertir.
- **Disponibilidad (`--available`).** Pasa el CSV completo de `resources.py`; quita niveles solo por cuota agotada en esta sesión o descarte explícito. Para cada papel, elige un candidato de `pick` en el nivel que pide `roles` (planificador y validador, el más alto disponible; ejecutor, hasta `medio`); el costo solo desempata entre candidatos de igual calidad y el costo desconocido nunca es elegible.
- **Autorización de frontera (`--frontier-ok`).** Agrégala cuando el usuario ya autorizó abrir sesiones de frontera; sin ella, `ask_user` es `true` si algún papel de frontera no es el chat.
- **Salida 0.** Sigue `mode` y `roles`.
- **Salida 1.** Explica qué nivel falta y propone esperar a que vuelva la cuota o aceptar otro nivel. Corre de nuevo el selector con lo que confirme el usuario.
- **Salida 2.** Corrige los argumentos y repite.
- **Planificador del chat.** Si el planificador trae `"session": "chat"` (el chat ya es de frontera), planifica el propio chat sin abrir otra sesión; si no, abre una sesión nueva y respeta `ask_user`.
- **Si `ask_user` es `true`.** Pregunta antes de abrir la sesión de frontera. Si el usuario la rechaza, repite sin `frontera` en `--available`. Si sale 1, explica el bloqueo.

## Asignar

- **Ejecutor:** el candidato más capaz dentro del tope `medio` que fija `roles`; la capacidad manda sobre el costo.
- **Validador:** el más fuerte disponible, en una familia distinta de la del implementador, o en una sesión nueva y ciega del mismo agente. Con riesgo alto o entrega verificada, dos pases.
- **Planificador (senior):** el más fuerte disponible, preferiblemente de otra familia que la del Elefante.
- **Sesiones de frontera:** planifican y validan, no escriben. El plan las lista en la tanda inicial de preguntas para que el usuario las confirme, salvo que ya las autorizó (`--frontier-ok`). El último escalón de la escalera lo cubre el Elefante o ese senior ya previsto; abrir una sesión de frontera que el usuario no autorizó exige preguntar.
- **Un solo agente:** si el usuario dice que solo tiene uno, ese agente es también el del Elefante. Cubre los papeles con sus modelos o esfuerzos, si `--help` lo permite. La independencia del QA viene de una sesión nueva y ciega.

En el plan, cada papel lleva una línea: `papel → agente y modelo elegidos de lo descubierto → nivel → motivo (capacidad frente a costo)`. La primera identifica al propio Elefante (el agente y el modelo del chat que coordina) y lo que decide: criterios de éxito, encargos y aceptación. Nunca dejes a «el coordinador» sin agente ni modelo. Por ejemplo:

```text
Elefante (PM): Claude, modelo de este chat — fija los criterios, escribe los encargos, integra y acepta; en un Run coordinado no escribe código.
Planificador: Claude, modelo de frontera (esfuerzo alto) — el propio chat si ya es de frontera; si no, una sesión nueva; diseña y describe la solución.
Ejecutor: Claude, modelo medio con esfuerzo alto — escribe el código y las pruebas; nunca frontera.
Validador: Codex, el modelo más fuerte disponible (otra familia) — revisa contra los criterios; si hay hallazgos, corrige y revalida.
Previsto: 2 sesiones de frontera (planificar y validar), 1 media y este chat.
```

Con un solo agente, por ejemplo «solo tengo Codex»:

```text
Elefante (PM): Codex, modelo de este chat — fija los criterios, escribe los encargos, integra y acepta; en un Run coordinado no escribe código.
Ejecutor: Codex en esfuerzo medio (nunca el máximo) — tarea bien definida.
Validador: Codex en sesión nueva y ciega, con el esfuerzo más alto que permita --help — no hay otra familia.
Respaldo: Codex en esfuerzo medio para escribir; esfuerzo alto solo si el usuario lo aprueba.
```

Ejemplos de combinaciones (los modelos concretos salen del descubrimiento):

| Disponibles | Ejecutor | Validador | Respaldo de la escalera |
|---|---|---|---|
| Claude, Codex y OpenCode | Un modelo medio capaz (Claude o Codex medio) | El más fuerte de la familia que no implementó | La frontera describe la solución y la escribe otro candidato medio |
| Claude y OpenCode | Claude medio o un OpenCode «pro» | Claude de frontera en sesión nueva | La frontera describe y escribe el otro candidato medio |
| Solo uno | El mismo agente en esfuerzo medio | Sesión nueva y ciega del mismo agente, en su esfuerzo más alto | La frontera describe y escribe otra sesión del mismo agente en esfuerzo medio; alto, con permiso |

## Modelo y esfuerzo

Usa el modelo configurado del agente cuando ya encaja en el nivel elegido. Fija `--model` y `--effort` solo si el usuario los nombró, si ningún modelo configurado encaja o al subir un escalón. Justifícalo en el plan o en el aviso («ejecutor: OpenCode con `<proveedor/modelo>` (medio), porque el configurado es de frontera y el ejecutor tiene techo medio»). Las preferencias explícitas del usuario mandan.

## Escalera de modelos

Escalones, de abajo arriba, elegidos de lo descubierto en vivo; el selector fija desde cuál empieza cada ejecutor y se salta los que no existan:

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
