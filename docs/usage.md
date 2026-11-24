# Uso

Escribe el encargo en un chat de Orca que pueda coordinar y menciona la skill:

```text
Usa EzOrca para <la tarea>
Usa EzOrca para <la tarea>, entrega verificada
```

Modalidades:

- **Entrega normal** (predeterminada): el coordinador reparte, integra, corre las comprobaciones habituales y suma un pase de revisión independiente en una sesión distinta de la del implementador (el papel QA del ejemplo). Los cambios triviales no llevan revisión aparte.
- **Entrega verificada**: además, dos pases ciegos consecutivos sobre una versión con huella. Cuesta más sesiones y se reserva para cuando necesitas un veredicto independiente.

No necesitas elegir agentes, modelos ni comandos: eso lo decide el coordinador entre lo que tenga instalado. Si tienes preferencias («usa solo Codex», «nada de modelos gratis», «que el diseño lo haga un modelo caro»), dilas en el encargo y mandan sobre todo lo demás.

## Papeles adaptativos

Los papeles no son una lista fija. Elefante/PM, senior, junior y QA son solo ejemplos: cada Run define los que la tarea necesite —por ejemplo, investigador, diseñador, arquitecto, revisor de seguridad, tester, documentador o integrador— y cualquier agente o modelo puede ocupar cualquiera según su capacidad, su costo y su disponibilidad.

Se mantiene la política de costo por defecto: los modelos caros piensan, planifican, escriben encargos y revisan, y casi nunca escriben código; el trabajo de escritura va a modelos económicos, gratis o locales. Si prefieres otra cosa, dilo y manda tu preferencia.

## Cinco encargos de ejemplo

### 1. Tarea pequeña, entrega normal

> Usa EzOrca para agregar un flag `--desde` a la CLI `notas` que filtre las notas anteriores a una fecha.

Encargo claro: resultado, alcance y criterio. EzOrca arma un solo ejecutor económico (el junior del ejemplo), le pasa un encargo con archivos, ejemplo y comprobaciones, revisa el diff, corre las pruebas y te entrega el resultado. Un pase de revisión en otra sesión porque cambia lógica. Costo: una o dos sesiones económicas.

### 2. Varias tareas independientes

> Usa EzOrca para la API web `facturas`: (a) validar el RFC antes de guardar, (b) devolver 404 con JSON en vez de HTML, (c) agregar paginación a `GET /facturas`.

Tres tareas que no comparten archivos: EzOrca lanza hasta cuatro Goldfish por tanda, cada uno en su worktree con sus archivos delimitados, y une los resultados con una puerta por cambio. Si dos tareas tocaran el mismo archivo, las serializa. Aquí el paralelismo es lo que ahorra tiempo.

### 3. Entrega verificada

> Usa EzOrca para migrar la CLI `notas` de un archivo JSON a SQLite, entrega verificada.

EzOrca fija los criterios, escribe el encargo, integra y luego abre dos verificadores ciegos en sesiones nuevas, de una familia distinta a la del implementador si la hay. Cada veredicto empieza con la versión verificada (huella del commit más los cambios). Hacen falta dos pases limpios seguidos; si algo cambia, el conteo vuelve a cero.

### 4. Encargo ambiguo

> Usa EzOrca para que la API web `facturas` responda más rápido.

Falta el criterio. EzOrca mide o lee primero (por ejemplo, que `GET /facturas` tarda 1,4 s con 10 000 filas), propone una meta concreta —«que baje de 0,4 s»— y te la confirma en una sola tanda de preguntas, con una opción recomendada. No lanza implementación hasta que la apruebas.

### 5. Solo tengo Codex

> Usa EzOrca para ordenar los mensajes de error de la CLI `notas`. Solo tengo Codex.

Codex pasa a ser también el agente del Elefante. Los papeles salen de sus modelos y esfuerzos; por ejemplo: junior con el más bajo, revisión en una sesión nueva y ciega, respaldo en esfuerzo medio. Subir a esfuerzo alto requiere tu permiso, y EzOrca lo dice cuando llega el caso.

## Qué verás

**El plan, una línea por papel.** Antes de tocar nada verás algo así (los cuatro papeles de este ejemplo):

```text
Elefante (PM): Claude, modelo de este chat (caro) — fija los criterios, escribe los encargos, integra y acepta; por defecto no escribe código.
Junior: OpenCode `opencode-go/deepseek-v4.1-flash` (económico) — el más capaz de los económicos listados.
QA: Codex, modelo configurado (medio) — otra familia; riesgo bajo, basta una lista cerrada.
Senior: no se usa — sin diseño abierto ni riesgo alto.
Previsto: 2 sesiones económicas, 1 media y este chat.
```

Si un papel no sale de lo instalado, lo dice en su línea. Los IDs concretos cambian con tu entorno; esa es la razón de que la skill descubra agentes y modelos en cada Run.

**Avisos de escalado.** Cuando sube un escalón, una línea: «La tarea 2 falló dos veces con el modelo gratis; la paso a OpenCode pro. Sigue siendo económica; el costo sube poco». Sigue trabajando sin esperar respuesta.

**Estado por tarea.** Al cerrar: qué quedó aceptado con qué evidencia, qué quedó pendiente y cuánto costó (sesiones por agente y nivel, reintentos y escalados). El detalle vive en el registro del Run, fuera del producto.

## Cuándo escala y cuándo pregunta

Escala por evidencia, no por impaciencia:

| Situación | Qué hace |
|---|---|
| Primer fallo de una tarea | Corrige el encargo con el fallo concreto y lo reenvía al mismo worker |
| Segundo fallo en la misma tarea | Sube un escalón; es obligatorio |
| Fallo crítico, sin evidencia o riesgo alto | Puede subir antes de los dos fallos |
| Límite de uso o corte con reintento automático | Espera: no es una caída |
| Cuota agotada o worker caído | Reasigna al siguiente candidato y avisa del efecto en el costo |

Pregunta antes solo si usaría un modelo de frontera o Codex en esfuerzo alto en una sesión nueva, o si se superaría el presupuesto que acordaron. Para todo lo demás decide y avisa.

## Consejos de costo

- **La frontera razona; por defecto, no escribe.** El modelo caro sirve para el plan, los criterios, los encargos y la revisión de riesgo. Todo el código, incluidas las pruebas, va a un modelo económico con un encargo bien detallado; el usuario puede indicar otra cosa. El plan prevé como máximo unas dos sesiones de frontera además de la que coordina.
- **Tandas de unos cuatro por modelo.** Más workers simultáneos del mismo modelo chocan con el límite de concurrencia del proveedor. Si hay mucho trabajo, reparte entre modelos parecidos o espera la tanda siguiente.
- **Las cuotas se agotan.** Cuando pasa, EzOrca cambia de agente o de nivel y lo dice en una línea. Si limitaste los agentes y no queda ninguno, te informa el bloqueo en vez de inventar una salida.
- **Encargos claros son más baratos.** Un encargo con resultado esperado, criterio verificable y alcance evita rondas de preguntas y reintentos. Si el tuyo no los trae, la primera tanda de preguntas es la inversión más rentable.
- **Elige la modalidad por riesgo.** Entrega normal cubre casi todo; la verificada duplica la revisión y conviene cuando el cambio es difícil de deshacer o hay que demostrar que cumple.

Para saber qué hace cada script por dentro, ver [scripts.md](scripts.md); para el diseño completo, [architecture.md](architecture.md).
