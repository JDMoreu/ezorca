# Uso

Escribe el encargo en un chat de Orca que pueda coordinar y menciona la skill:

```text
Usa EzOrca para <la tarea>
Usa EzOrca para <la tarea>, entrega verificada
```

EzOrca busca la mejor calidad validada: primero elige el modo (delegado por defecto en todo lo no trivial; directo solo para lo trivial o si lo pides; coordinado con varias partes, tamaño grande, riesgo alto o entrega verificada) y anuncia el motivo y el costo estimado. Si pides entrega verificada o dos pases ciegos, coordina un Run aunque el encargo sea chico.

- **Entrega normal** (predeterminada). Incluye las comprobaciones habituales y un pase de revisión independiente en una sesión distinta de la del implementador (el papel QA del ejemplo). Los cambios triviales no llevan revisión aparte.
- **Entrega verificada**: además, dos pases ciegos consecutivos sobre una versión con huella. Cuesta más sesiones y se reserva para cuando necesitas un veredicto independiente.

No necesitas elegir agentes, modelos ni comandos: eso lo decide el coordinador entre lo que tenga instalado. Si tienes preferencias («usa solo Codex», «nada de modelos gratis», «que el diseño lo haga un modelo caro»), dilas en el encargo y mandan sobre todo lo demás.

## Papeles adaptativos

Los papeles no son una lista fija. Elefante/PM, senior, junior y QA son solo ejemplos: cada Run define los que la tarea necesite —por ejemplo, investigador, diseñador, arquitecto, revisor de seguridad, tester, documentador o integrador— y cualquier agente o modelo puede ocupar cualquiera según su capacidad, su costo y su disponibilidad.

Al delegar o coordinar, los modelos de frontera planifican, escriben encargos y validan. Ejecutores capaces de nivel medio (nunca de frontera) escriben el código. El orden de decisión es calidad, luego eficiencia (tiempo y paralelismo) y luego costo, siempre dentro de los topes de cada plan. Si prefieres otra cosa, indica cómo repartir el trabajo.

## Cinco encargos de ejemplo

### 1. Tarea pequeña, entrega normal

> Usa EzOrca para agregar un flag `--desde` a la CLI `notas` que filtre las notas anteriores a una fecha.

Con cuota para todos los niveles, EzOrca la delega y lo avisa en una línea:

> «Modo delegado (calidad primero): planifica este chat, escribe un ejecutor económico capaz (o medio si no hay cuota) con esfuerzo medio y valida un modelo de frontera en otra sesión (te pide permiso antes de abrirla, salvo que ya hayas autorizado la frontera); si hay hallazgos, corrige y revalida. Costo estimado 38 (unidades relativas, no dólares), con chat de nivel medio, dentro de tus topes.»

El ejecutor hace el cambio y corre las pruebas; el validador lo revisa en otra sesión y el ciclo se repite hasta que no queden hallazgos bloqueantes ni mayores (máximo 3 rondas).

### 2. Varias tareas independientes

> Usa EzOrca para la API web `facturas`: (a) validar el RFC antes de guardar, (b) devolver 404 con JSON en vez de HTML, (c) agregar paginación a `GET /facturas`.

Con tres partes independientes, EzOrca elige un Run coordinado (un ejecutor por parte) y pregunta antes de abrir la sesión del planificador de frontera, salvo que ya autorizaste la frontera. El chat le pasa el pedido textual y te propone el plan antes de ejecutar. Luego lanza hasta cuatro Goldfish por tanda y comprueba cada cambio al integrarlo.

### 3. Entrega verificada

> Usa EzOrca para migrar la CLI `notas` de un archivo JSON a SQLite, entrega verificada.

EzOrca fija los criterios, escribe el encargo, integra y luego abre dos verificadores ciegos en sesiones nuevas, de una familia distinta a la del implementador si la hay. Cada veredicto empieza con la versión verificada (huella del commit más los cambios). Hacen falta dos pases limpios seguidos; si algo cambia, el conteo vuelve a cero.

### 4. Encargo ambiguo

> Usa EzOrca para que la API web `facturas` responda más rápido.

Falta el criterio. EzOrca mide o lee primero (por ejemplo, que `GET /facturas` tarda 1,4 s con 10 000 filas), propone una meta concreta —«que baje de 0,4 s»— y te pide que la confirmes junto con las demás preguntas. Incluye una opción recomendada y espera tu aprobación para implementar.

### 5. Solo tengo Codex

> Usa EzOrca para ordenar los mensajes de error de la CLI `notas`. Solo tengo Codex.

Si es una tarea chica, el chat planifica, una sesión de Codex en esfuerzo medio implementa el cambio y otra sesión nueva y ciega de Codex lo valida. Si el validador encuentra hallazgos, el ejecutor corrige y se revalida.

## Qué verás

**El plan por papel.** Antes de tocar nada verás una línea por papel. Por ejemplo, con Claude y una tarea mediana:

```text
Elefante (PM): Claude, modelo de este chat — fija los criterios, escribe los encargos, integra y acepta; al delegar o coordinar no escribe código.
Planificador: Claude, <modelo de frontera disponible> (esfuerzo alto) — el propio chat si ya es de frontera; si no, una sesión nueva; diseña y describe la solución.
Ejecutor: Claude, <modelo de nivel medio disponible> con esfuerzo alto — escribe el código y las pruebas; nunca frontera.
Validador: el modelo más fuerte disponible, en otra sesión y de otra familia si hay (esfuerzo alto) — revisa contra los criterios; si hay hallazgos, corrige y revalida (máx. 3 rondas).
Previsto: planifica este chat (frontera); 1 sesión media y 1 de frontera para validar.

Aviso del modo (mediana): «Modo delegado (calidad primero): planifica este chat, escribe un modelo medio con esfuerzo alto y valida un modelo de frontera en otra sesión; si hay hallazgos, corrige y revalida. Costo estimado 113 (unidades relativas), con chat de frontera, dentro de tus topes.»
```

El nivel de cada modelo sale de su precio de salida (`scripts/tiers.json`), no de su nombre.

Si un papel no sale de lo instalado, lo dice en su línea. Los IDs concretos cambian con tu entorno; esa es la razón de que la skill descubra agentes y modelos en cada Run.

**Avisos de escalado.** Cuando sube un escalón, una línea: «La tarea 2 falló dos veces con el ejecutor actual; la paso a un modelo de mayor nivel. El costo sube poco y sigue dentro de tus topes». Sigue trabajando sin esperar respuesta.

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

Pregunta antes solo si usaría un modelo de frontera o Codex en esfuerzo alto en una sesión nueva que no autorizaste, o si se superaría el presupuesto que acordaron. Para todo lo demás decide y avisa.

## Consejos

- **Calidad, luego tiempo, luego costo.** El selector elige el modo y los niveles por calidad; el costo se informa y desempata, y los topes de cada plan siempre se respetan. [Modo inteligente](../SKILL.md#modo-inteligente-la-mejor-calidad-dentro-del-presupuesto)
- **La frontera planifica y valida.** Los ejecutores escriben el código y las pruebas con encargos detallados; su nivel máximo es medio. Si ya autorizaste la frontera, dilo para que no te pregunte en cada sesión.
- **Tandas de unos cuatro por modelo.** Más workers simultáneos del mismo modelo chocan con el límite de concurrencia del proveedor. Si hay mucho trabajo, reparte entre modelos parecidos o espera la tanda siguiente.
- **Las cuotas se agotan.** Cuando pasa, EzOrca cambia de agente o de nivel y lo dice en una línea. Si limitaste los agentes y no queda ninguno, te informa el bloqueo en vez de inventar una salida.
- **Encargos claros dan mejor resultado.** Un encargo con resultado esperado, criterio verificable y alcance evita rondas de preguntas y reintentos. Si el tuyo no los trae, la primera tanda de preguntas es la inversión más rentable.
- **Elige la modalidad por riesgo.** Entrega normal cubre casi todo; la verificada duplica la revisión y conviene cuando el cambio es difícil de deshacer o hay que demostrar que cumple.

Para saber qué hace cada script por dentro, ver [scripts.md](scripts.md); para el diseño completo, [architecture.md](architecture.md).
