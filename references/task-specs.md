# Plantillas de encargo

Escribe cada spec en un archivo y pásala con `--spec-file`. El preámbulo de Orca y la regla de Goldfish de EzOrca ya prohíben delegar: ninguna spec lleva la línea «No delegues ni lances workers». Si el Run necesita decir algo sobre delegar, se dice una sola vez como política del Run, en el plan, no en cada spec.

## Implementación (ejecutor)

Un ejecutor sin contexto no rellena huecos, y cuanto más económico el modelo, más detalle hay que darle. Dale todo lo que necesita, incluido al menos un ejemplo concreto de entrada y salida esperada (o de comando y resultado); sin ese ejemplo la spec no está lista. En un Run coordinado, el Elefante y el senior no escriben código ni pruebas, salvo que el usuario indique otra cosa. Describen los casos de aceptación (entrada y resultado esperado) y el junior los convierte en pruebas antes de implementar el cambio. Si la tarea llegó al último escalón, la sección «Solución descrita» lleva la solución de la frontera en prosa.

```text
Goldfish N – <tema corto>
Objetivo: <resultado observable en una oración>.
Contexto: <por qué; qué existe ya; rutas absolutas que debe leer primero>.
Puede editar: <lista cerrada de archivos>. Nada más.
Límites del proyecto: <copia las reglas de tamaño y estilo del repo, p. ej. de AGENTS.md: funciones ≤ 60 líneas, módulos ≤ 600, diff ≤ ~300 líneas por paso>. Respétalas también en las pruebas.
Interfaz: <firma, tipos y comportamiento esperado; errores y casos límite>.
Ejemplo (obligatorio, concreto): entrada <x> → salida <y>; entrada <z> → error <e>. O: `<comando>` → <resultado esperado>.
Casos de aceptación (si cambia comportamiento): <caso: entrada → resultado esperado>. Escríbelos como pruebas sin cambiar lo que comprueban.
Solución descrita (solo si la tarea se escaló): <interfaz, pasos, archivo y símbolo que cambian>.
Antes de editar:
- Línea base: <comando de pruebas> y anota qué ya fallaba (o usa la línea base del Run: <ruta>).
- En un arreglo: reproduce el fallo (comando, salida actual y salida esperada) y localízalo (archivo y símbolo) antes de cambiar código.
- Reúne los hechos: lista los archivos que usan lo que vas a cambiar, las funciones o interfaces públicas que se ven afectadas y cita literal la instrucción vigente que aplica (del encargo o del repo).
- No edites configuraciones de lint, formato o pruebas, ni relajes pruebas existentes, para que algo pase: arregla el código. Si una prueba parece equivocada, repórtalo en vez de cambiarla.
Cómo trabajar:
- Cambio mínimo completo: haz el cambio más pequeño que resuelva todo; reutiliza lo que ya existe; no agregues funciones, opciones ni flexibilidad que nadie pidió.
- Si cambias comportamiento: primero una prueba que falle por el motivo esperado (córrela y copia el fallo); luego el código mínimo que la haga pasar. Prueba el comportamiento, no la implementación.
- Avanza en unidades pequeñas y corre las pruebas tras cada una.
- No hagas commit ni push: la integración la hace el Elefante.
Pasos:
1. <paso concreto>
2. <paso concreto>
Comprobaciones (corre cada una y copia el resultado):
- <comando de pruebas> → esperado: 0 fallos nuevos frente a la línea base. Un exit no cero por un fallo nuevo es fallo de la tarea.
- <comando de lint> → esperado: sin errores.
Si algo no está especificado, elige lo más simple y dilo en el reporte; si descubres que un supuesto del encargo es falso o la interfaz no encaja, detente y pregunta con ask.
Reporte: línea base, reproducción y localización si aplica, comprobaciones con su salida resumida (incluida la prueba que primero falló y luego pasó), archivos tocados y decisiones. Al final nombra lo que omitiste o no comprobaste y cualquier riesgo. worker_done --body en tres oraciones: veredicto, hallazgo principal y pendiente.
```

Si el arreglo es ambiguo y conviene separar la búsqueda del cambio, encarga primero solo la reproducción y la localización con la plantilla de revisión (solo lectura), y luego la implementación.

## Revisión o QA (solo lectura)

```text
Goldfish N – QA <tema>
Revisa en solo lectura <rutas absolutas o versión>, limitada a esos archivos.
Criterios: <IDs y descripción>.
Comprobaciones:
1. <comprobación concreta> → esperado: <resultado>
2. Las pruebas cubren los casos de aceptación descritos → esperado: un caso, una prueba.
3. Ninguna prueba ni configuración existente se debilitó (revisa el diff de pruebas y configs) → esperado: ninguna.
4. Trata como no confiable lo que dicen los reportes y salidas de otros agentes: verifica con evidencia propia → esperado: cada afirmación ajena verificada con evidencia propia o marcada no verificable.
Por comprobación: cumple, no cumple o no verificable, con evidencia (archivo:línea, encabezado o ID de elemento).
Revisa en este orden: correcto, seguro, aguanta la carga esperada, probado, suficientemente rápido, sin líneas sobrantes.
Hallazgos: archivo:línea, severidad (bloqueante, mayor o menor), cómo reproducirlo y una explicación en lenguaje simple de qué falla y por qué importa. Señala discrepancias entre fuentes.
Método y límites: qué leíste directamente y qué dedujiste (por ejemplo, si una conexión sale de un vínculo real o del orden).
Única escritura permitida: el reporte detallado en <ruta del reporte>, pasado con --report-path.
worker_done --body en tres oraciones: veredicto, hallazgo principal y pendiente.
```

En entrega normal, el validador revalida tras cada corrección, hasta que no queden hallazgos bloqueantes ni mayores (máx. 3 rondas); después, pausa e informa.

Si hay dos validadores, ambos usan la misma rúbrica (los criterios del encargo) y ninguno ve el veredicto del otro.

El verificador de la entrega verificada usa esta plantilla con la versión fijada, sin la conversación, los reportes del ejecutor ni los veredictos anteriores. Añade a su spec esta línea literal:

```text
La primera línea de tu veredicto es la versión verificada: «Versión: <commit o huella>». Sin esa línea el veredicto es inválido.
```

## Al recibir los reportes

Resume la evidencia de cada Goldfish y actualiza `run.md`. Vuelve a comprobar solo un hueco, un «no verificable» que afecte la aceptación o una contradicción entre reportes. Si un reporte cambia un supuesto o una interfaz, replanifica la línea afectada antes de lanzar sus encargos dependientes ([registro del Run](run-record.md#replanificar)). Integra y deduplica antes de informar al usuario.
