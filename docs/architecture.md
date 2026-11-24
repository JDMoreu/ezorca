# Arquitectura de EzOrca

EzOrca coordina una tarea en Orca con dos clases de sesión: una que piensa y
revisa, y varias que escriben. La meta es un resultado de nivel frontera con la
mitad del costo o menos (meta de diseño): el trabajo caro se concentra en decidir y comprobar, y
el trabajo mecánico va a modelos económicos, gratis o locales.

## Elefante y Goldfish

| Sesión | Qué es | Qué tiene en la cabeza |
|---|---|---|
| **Elefante** | El chat que recibe el encargo. Es el PM del Run. | Todo el Run: objetivo, criterios, plan, decisiones, reportes y costo. |
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
de ellos según su capacidad, su costo y su disponibilidad. La política de costo
por defecto se mantiene: los modelos caros se usan para razonar y casi nunca
escriben código, salvo que el usuario diga otra cosa.

Papeles habituales, como ejemplo:

| Papel | Quién | Hace | No hace |
|---|---|---|---|
| Elefante (PM) | El modelo de este chat | Estrategia, plan, registro, encargos, decisiones, integración y aceptación | Escribir código ni pruebas, ni siquiera ediciones triviales |
| Senior | Modelo caro o de esfuerzo alto | Diseño difícil, casos de aceptación de riesgo, revisión de riesgo, describir la solución | Escribir código; trabajo repetitivo o ya bien definido |
| Junior | Modelo económico, gratis o local | Todo el código y las pruebas, con un encargo detallado | Decisiones de diseño abiertas |
| QA | Otra familia de agente, o sesión nueva y ciega | Revisar el resultado contra los criterios, sin ver el razonamiento del implementador | Corregir lo que revisa |

Se arma solo lo que aporte; un Run con otra tarea puede inventar los papeles que
le sirvan:

| Encargo | Equipo |
|---|---|
| Trivial (una errata, una edición mecánica) | Un junior. Sin QA. |
| Pequeño y bien definido | Un junior y un pase QA si el cambio toca lógica. |
| Mediano o con partes independientes | Juniors en paralelo (unas 4 por tanda y modelo), cada uno en su worktree con archivos delimitados, y un QA. |
| Riesgoso (seguridad, datos, concurrencia, arquitectura) | Senior para el diseño y los casos de aceptación, juniors para escribirlo, QA de otra familia que compruebe también si las pruebas cubren esos casos. |

## Por defecto, la frontera no escribe código

Por defecto, la frontera no escribe código; el usuario puede indicar otra cosa.
El Elefante y toda sesión cara (Opus, Codex en esfuerzo alto u otro modelo de
frontera) orquestan, planean, escriben encargos y revisan. Todo el código,
incluidas las pruebas y las ediciones triviales, lo escriben Goldfish económicos,
gratis o locales.

El motivo es doble. Primero, el costo: los tokens de frontera son el recurso
escaso, y escribir boilerplate con ellos es la forma más rápida de gastar el
presupuesto sin mejorar el resultado. Segundo, el rol: quien escribe tiende a
defender lo que escribió; separar la escritura de la aceptación mantiene la
revisión honesta y permite repetir el trabajo barato sin repetir el caro.

Si algo es difícil, por defecto la frontera no lo escribe: describe la interfaz, los casos
con entrada y resultado esperado, los pasos y el archivo y el símbolo que hay que
cambiar, y un junior lo escribe. Resolver un conflicto al integrar también es
escribir código: va a un junior con su propio encargo.

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
  una sesión de frontera nueva (Opus, Codex en esfuerzo alto) o si se superaría
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

1. **Descubrir.** Una vez por Run: agentes instalados, modelos disponibles y qué
   admite `worker-start`. El resultado se clasifica por escalón.
2. **Plan por papel.** Una línea por papel: papel, agente y modelo, nivel de
   costo y motivo. Cierra con las sesiones previstas por nivel.
3. **Encargos validados.** Cada encargo en un archivo, con alcance cerrado,
   ejemplo y comprobaciones. Se validan antes de lanzar.
4. **Tanda.** Los workers arrancan en paralelo, con tope por modelo y recibos
   guardados junto al registro.
5. **Despertar.** El Elefante termina el turno; Orca lo despierta con los
   reportes. No sondea. Al recibirlos resume la evidencia y actualiza el registro.
6. **Integrar con puerta.** Un cambio a la vez: solo archivos permitidos y las
   pruebas del conjunto. Si algo falla, ese cambio se retira y vuelve con su
   evidencia.
7. **Cierre con costo.** Resumen por criterio con evidencia, pendientes y costo
   real (sesiones por nivel, reintentos, escalados, aceptadas y rechazadas).

![Flujo de EzOrca](img/flow.svg)

## Entrega normal y entrega verificada

| | Entrega normal | Entrega verificada |
|---|---|---|
| Cuándo | Es la predeterminada, también con «sin verificación» | El usuario la pide o el ciclo exige verificación independiente |
| Revisión | **Un pase QA único** en una sesión distinta de la del implementador | Un Goldfish verificador nuevo, de otra familia si hay, en solo lectura |
| Versión | No se fija | Se fija con un commit o una **huella** del conjunto verificable completo |
| Cierre | Un pase; otra sesión solo si la corrección cambia el diseño | **Dos pases limpios consecutivos** sobre la misma huella |

En la entrega normal, correr las pruebas no la convierte en verificada, y la
lectura del Elefante no sustituye al QA. Si el QA dio hallazgos bloqueantes o
mayores, el implementador corrige y el Elefante comprueba la corrección con su
evidencia; solo hay otra sesión QA si la corrección cambia el diseño o toca
archivos nuevos. Un cambio trivial no lleva QA.

En la entrega verificada, el veredicto empieza con la versión verificada en la
primera línea; sin esa línea es inválido. La huella cubre el contenido, no la
lista de nombres: HEAD más el diff, los archivos nuevos y los externos que citen
los criterios. Se recalcula antes de cada pase. Si la versión cambia, se incumple
un criterio o aparece un hallazgo bloqueante o mayor, el conteo vuelve a cero.
Por defecto se pausa tras cinco rondas de corrección o dos horas.

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
mecánico: comprobar que un encargo está completo, repartir el cupo de una tanda,
medir una huella, detectar un worker colgado, verificar el alcance de un cambio.

La razón es simple: **las reglas en prosa se omiten**. Un modelo económico que
lee veinte páginas salta la mitad; un `exit 1` con la lista de lo que falta no se
puede saltar. Lo que se puede decidir con un booleano va a un script que devuelve
0, 1 o 2 y dice por qué. Lo que exige juicio —elegir el escalón, redactar un
encargo, aceptar un resultado— queda en prosa, porque ningún script puede
hacerlo bien. Por eso cada paso del flujo tiene, si existe, su script, y los
códigos de salida mandan más que la costumbre.
