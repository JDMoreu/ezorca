# Arquitectura de EzOrca

EzOrca elige el modo antes de planear. El chat puede implementar, delegar a un
ejecutor con validador o coordinar un Run completo.
[Modo inteligente](../SKILL.md#modo-inteligente-la-mejor-calidad-dentro-del-presupuesto)

## Elefante y Goldfish

| Sesión | Qué es | Qué tiene en la cabeza |
|---|---|---|
| **Elefante** | El chat que recibe el encargo. Puede usar cualquier modelo. | El contexto del encargo, los criterios, las decisiones, los reportes y el costo. |
| **Goldfish** | Un worker de Orca (`worker-start`), con contexto nuevo. | Solo su encargo, las rutas que cita y su tarea. Nada del resto del Run. |

El Goldfish no recuerda nada entre tareas: por eso cada encargo lleva rutas
absolutas, el alcance cerrado y un ejemplo concreto. A cambio, varias tareas
avanzan en paralelo sin arrastrar contexto, y una sesión contaminada no puede
contagiar a las demás. El Elefante es el único que integra y acepta.

## Papeles y cuándo se arman

Los papeles son **adaptativos y abiertos**: Elefante, senior, junior y QA son
ejemplos, no una lista fija. Cada Run define los que la tarea necesite —por
ejemplo, investigador, diseñador, arquitecto, revisor de seguridad, tester,
documentador o integrador—, y cualquier agente o modelo puede ocupar cualquiera
de ellos según su capacidad, su disponibilidad y su costo, en ese orden. La
política por defecto, al delegar o coordinar: los modelos de frontera
planifican y validan y no escriben código, salvo que el usuario diga otra cosa.

Papeles habituales, como ejemplo:

| Papel | Quién | Hace | No hace |
|---|---|---|---|
| Elefante (PM) | El modelo de este chat | Estrategia, plan, registro, encargos, decisiones, integración y aceptación | Escribir código ni pruebas, ni siquiera ediciones triviales |
| Senior | Modelo de frontera o de esfuerzo alto | Diseño difícil, casos de aceptación de riesgo, validación, describir la solución | Escribir código; trabajo repetitivo o ya bien definido |
| Ejecutor | Modelo de nivel medio o inferior | Todo el código y las pruebas, con un encargo detallado | Decisiones de diseño abiertas |
| QA | El modelo más fuerte disponible, de otra familia de agente o en una sesión nueva y ciega | Revisar el resultado contra los criterios, sin ver el razonamiento del implementador | Corregir lo que revisa |

Antes de planear, el Elefante estima tamaño, partes independientes y riesgo.
`choose_mode.py` elige por calidad, luego eficiencia y luego costo: delegar es lo
normal en todo lo no trivial; directo queda para lo trivial o a pedido; el
coordinado, para varias partes, tamaño grande, riesgo alto o entrega verificada.
El costo se estima solo para informar y desempatar. Con todos los niveles
disponibles:

- `--chat-tier frontera --size mediana` → delegado: planifica el propio chat (frontera), escribe un ejecutor medio con esfuerzo alto y valida frontera en otra sesión, con un pase. Costo estimado 113.
- `--chat-tier economico --size chica` → delegado: sin planificador (planifica el chat), ejecutor económico capaz (o medio si no hay cuota) y validador de frontera. Costo estimado 21,6 con chat económico.
- `--chat-tier economico --size grande --parts 4 --risk alto` → coordinado: planificador de frontera, cuatro ejecutores medios y validador de frontera con dos pases. Con `ask_user: true`, el chat pregunta antes de abrir la sesión de frontera, salvo que el usuario ya la autorizó (`--frontier-ok`).

## Límite del nivel del ejecutor

En los modos delegado y coordinado, el ejecutor llega como máximo al nivel
`medio`. Si la tarea exige más capacidad, un planificador de frontera diseña
y describe la solución y un ejecutor de nivel medio escribe el código y las
pruebas.

El motivo es doble. Primero, la calidad: quien escribe tiende a defender lo que
escribió; separar la escritura de la validación mantiene la revisión honesta, y
la frontera se reserva para planificar y validar, donde más aporta. Segundo, la
eficiencia: los ejecutores medios trabajan en paralelo y se puede repetir su
trabajo sin repetir el de la frontera, siempre dentro de los topes de cada plan.

Si algo es difícil, la frontera describe la interfaz, los casos
con entrada y resultado esperado, los pasos y el archivo y el símbolo que hay que
cambiar. Resolver un conflicto al integrar también requiere un encargo para
un ejecutor.

Las mediciones de costo y tiempo de ensayos anteriores, que compararon procesos
distintos, están en el [Historial de la evaluación](evaluation.md#historial); el
selector solo usa sus pesos relativos para informar el costo y desempatar.

## Escalera de modelos

Los escalones se eligen de lo que esté instalado en el entorno; los que no
existan se saltan.

![Escalera de modelos](img/ladder.svg)

- **Cuándo subir.** Ante el primer fallo, corrige el encargo con el fallo
  concreto, más detalle y un ejemplo, y reenvíalo al mismo worker. Dos fallos en
  la misma tarea obligan a subir un escalón. Un fallo crítico, la falta de
  evidencia o un riesgo alto permiten subir antes. Cada subida se anota en el
  registro del Run con su motivo.
- **Avisa y sigue.** Al escalar o reasignar, avisa en una línea qué cambia, por
  qué y cuánto sube el costo, y continúa. Se pregunta antes solo si se abriría
  una sesión de frontera no autorizada (incluido Codex en esfuerzo alto) o si se superaría
  el presupuesto acordado. Si el último escalón falla, se pausa esa tarea y se
  informa con evidencia.
- **Caída o falta de cuota.** Si un worker se cae o se queda sin cuota, se
  reasigna el papel al siguiente candidato con la misma política. Un rate limit
  o un corte que el agente reintenta solo es espera, no caída.
- **Concurrencia y cuelgues.** Hasta unas 4 sesiones a la vez por modelo
  económico. En un Run real, 8 workers de OpenCode con el mismo modelo chocaron
  con el límite de concurrencia del proveedor y sufrieron cortes. Si al despertar
  un worker vivo lleva unos 20 min sin avanzar, se lee su salida, se detiene y se
  relanza una vez con el mismo agente. Un segundo fallo cuenta para la escalera.

## Flujo de un Run

1. **Recursos y descubrimiento.** Antes de elegir el modo (en todos los modos),
   `resources.py` lee los topes de cada plan (5 h, semanal y mensual) y los precios,
   ubica cada modelo en un nivel por su precio de salida (`scripts/tiers.json`) y su
   `available` alimenta a `choose_mode.py`. En el Run, `discover.py` guarda el
   inventario de agentes y modelos para diagnóstico. Se repite si cambia el alcance.
2. **Plan por papel.** Una línea por papel: papel, agente y modelo de `pick`, nivel
   de costo y motivo. Elige un candidato de `pick` en el nivel que pide `roles`;
   cierra con las sesiones previstas por nivel.
3. **Encargos validados.** Cada encargo en un archivo, con alcance cerrado,
   ejemplo y comprobaciones. Se validan antes de lanzar.
4. **Tanda.** Los workers arrancan en paralelo, con tope por modelo y recibos
   guardados junto al registro.
5. **Despertar.** El Elefante termina el turno; Orca lo despierta con los
   reportes. No sondea. Al recibirlos resume la evidencia y actualiza el registro.
6. **Validar y corregir.** Un validador del nivel más alto disponible revisa en
   otra sesión; el ejecutor corrige y se revalida hasta que no queden hallazgos
   bloqueantes ni mayores (máx. 3 rondas); después, pausa e informa.
7. **Integrar con puerta.** Un cambio a la vez: solo archivos permitidos y las
   pruebas del conjunto. Si algo falla, ese cambio se retira y vuelve con su
   evidencia.
8. **Cierre con costo.** Resumen por criterio con evidencia, pendientes y costo
   real (sesiones por nivel, reintentos, escalados, aceptadas y rechazadas).

![Flujo de EzOrca](img/flow.svg)

## Entrega normal y entrega verificada

| | Entrega normal | Entrega verificada |
|---|---|---|
| Cuándo | Es la predeterminada, también con «sin verificación» | El usuario la pide o el ciclo exige verificación independiente |
| Revisión | Un pase QA en una sesión distinta de la del implementador para cambios no triviales, con revalidación tras cada corrección | **Dos pases** en sesiones nuevas y ciegas, de otra familia si hay, incluso para cambios triviales |
| Versión | No se fija | Se fija con un commit o una **huella** del conjunto verificable completo |
| Cierre | Sin hallazgos bloqueantes ni mayores (máx. 3 rondas; después, pausa e informa) | **Dos pases limpios consecutivos** sobre la misma huella |

En la entrega normal, correr las pruebas no la convierte en verificada, y la
lectura del Elefante no sustituye al QA. Si el QA dio hallazgos bloqueantes o
mayores, el implementador corrige y el validador revalida tras cada corrección,
hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas); después,
pausa e informa. Un cambio trivial no lleva QA, salvo con riesgo alto (un validador).

En la entrega verificada, el veredicto empieza con la versión verificada en la
primera línea; sin esa línea es inválido. La huella cubre el contenido, no la
lista de nombres: HEAD más el diff, los archivos nuevos y los externos que citen
los criterios. Se recalcula antes de cada pase. Si la versión cambia, se incumple
un criterio o aparece un hallazgo bloqueante o mayor, el conteo vuelve a cero.
Por defecto se pausa tras cinco rondas de corrección o dos horas, ajustables por el
usuario. Es un tope propio de la entrega verificada; el de la entrega normal es de
3 rondas.

## Registro del Run

El Run de Orca solo guarda el título. El estado real vive en un `run.md` fuera
del producto, con: objetivo y alcance, modalidad, criterios y su cobertura,
línea base, tareas con dependencias y asignación, decisiones, escalados,
integración con su versión y tabla de costo. Se escribe al fijar el plan y en
cada cambio de estado, y se relee al retomar o tras compactar contexto. Si las
fuentes discrepan, el orden de confianza es: lo que muestra Orca, luego el
registro, luego la memoria.

## Qué hace la prosa y qué hace el código

Este documento y la skill explican el criterio: cuándo subir un escalón, qué
papel armar, cómo redactar un encargo, qué aceptar. Los scripts hacen lo
mecánico: leer topes y precios, elegir el modo y los niveles por calidad
(informando el costo), comprobar que un encargo está completo, repartir el cupo de una tanda,
medir una huella, detectar un worker colgado, verificar el alcance de un cambio.

La razón es simple: **las reglas en prosa se omiten**. Un modelo económico que
lee veinte páginas salta la mitad; un `exit 1` con la lista de lo que falta no se
puede saltar. Lo que se puede decidir con un booleano va a un script que devuelve
0, 1 o 2 y dice por qué. Lo que exige juicio —elegir el escalón, redactar un
encargo, aceptar un resultado— queda en prosa, porque ningún script puede
hacerlo bien. Por eso cada paso del flujo tiene, si existe, su script, y los
códigos de salida mandan más que la costumbre.
