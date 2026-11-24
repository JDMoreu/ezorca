# Evaluación y mejora de una skill

Mejorar la skill debe costar mucho menos que usarla. Estima las sesiones antes de medir y mantenlas proporcionales al presupuesto.

## Preparar un Run de evaluación

1. Identifica la skill, el incidente o la mejora esperada y la capacidad que se evaluará. Fija el conjunto de casos antes de medir. Incluye un caso que reproduzca el problema y casos que la versión actual resuelva y deba seguir resolviendo. Asigna IDs estables a cada caso y criterio. Marca los criterios críticos desde el inicio.
2. **Casos reservados.** Separa los casos en dos grupos: los de edición, cuyos fallos ve el editor, y los reservados, que el editor nunca ve (ni el texto ni los resultados) y que solo sirven para la aceptación final. Renueva los reservados entre ciclos de mejora. Una candidata que mejora en edición pero empeora en reservados no se acepta.
3. Reserva un directorio de trabajo para los artefactos autorizados. Guarda la rúbrica en `cases.json` y conserva una copia de la versión original. Fija agentes, modelos, entornos, entradas y método de juicio para ambas variantes.
4. **Presupuesto de sesiones.** Calcula ejecutores = casos × repeticiones × variantes, jueces = casos (más uno por cada caso decisivo, ver abajo) y un editor. Por ejemplo, 4 casos con 1 repetición y 2 variantes suman 8 ejecutores, 4 jueces y 1 editor: 13 sesiones. Si el total no cabe en el presupuesto del usuario, recorta casos y dilo.
   - **Cribado:** siempre con `repeats: 1`.
   - **Confirmación:** solo en casos dudosos (el resultado depende de uno o dos pares caso–criterio, la evidencia del juez es débil o hay contradicción entre casos), con un `cases.json` reducido a esos casos y `repeats: 2`. No repitas los casos ya claros.
5. **Modelos por papel.** Los ejecutores de simulacro usan el mismo agente y modelo que coordinaría en la realidad (para una skill de coordinación, el del Elefante), iguales para ambas variantes. Si por costo usas otro, declara la diferencia en el informe y no extrapoles sin reservas. Los jueces pueden usar un modelo económico o medio con una rúbrica cerrada. El editor es una sola sesión con un modelo caro.
6. **Modo plan para skills de coordinación.** El ejecutor escribe el plan del coordinador sin ejecutarlo: comandos, specs, modalidad, papeles y modelos, y fronteras de turno. No corre `worker-start` ni lanza Goldfish anidados. Para otras skills, el ejecutor hace el trabajo real en un workspace o destino de salida aislado por intento.
7. Lanza los intentos independientes en paralelo con Orca, en tandas de hasta unos 4. Da a cada ejecutor una sola variante, el caso y sus insumos. Mantén los artefactos accesibles al coordinador para que el juez reciba la salida completa.

## Evaluar

1. Mide la versión actual y la candidata con los mismos casos y repeticiones.
2. Usa **un juez ciego por caso**, en sesión nueva. Recibe el caso, la rúbrica y todas las salidas de ese caso, con etiquetas neutras en orden aleatorio, sin nombre de variante, información del editor ni resultados previos. Guarda tú la correspondencia entre etiquetas y variantes. El juez devuelve un booleano y evidencia por salida y criterio, y tú separas sus juicios en `baseline.json` y `candidate.json`. Los ejecutores y los jueces se generan con `scripts/eval_kit.py exec` y `pair`, y sus juicios se juntan con `merge` antes de `compare_skill_results.py`. Los archivos de los intentos llevan nombres opacos (p. ej., `t3fbb4b05.md`), sin «original», «candidata», «baseline», letras de variante ni números de ronda; el mapa intento → variante solo lo ve el coordinador y nunca aparece en rutas, títulos ni nombres que lea un juez.
3. **Comparaciones decisivas: dos juicios con el orden invertido.** Si un caso decide la aceptación (por ejemplo, de él depende una regresión o un criterio crítico), júzgalo dos veces en sesiones nuevas, con las salidas en orden inverso. Si ambos juicios coinciden, usa ese resultado. Si discrepan, el par es incierto, no una victoria: resuélvelo con un tercer juicio de otra familia o con decisión humana antes de pasar al comparador, y dilo en el informe.
4. Da a un editor independiente el texto original y el resumen de fallos de los casos de edición, nunca los reservados. Pídele que prepare una candidata en un archivo separado, mantenga el objetivo y los metadatos de la skill y limite la edición a cambios respaldados por los casos.
5. Si falta un intento por un error de ejecución, autorización o infraestructura, registra la evaluación como incompleta. Reserva `passed: false` para un juicio válido sobre un resultado evaluable.
6. Ejecuta el comparador incluido con Python 3 sobre todos los casos, de edición y reservados. Recibe la rúbrica fija, los juicios de la línea base y los juicios de la candidata. Si haces rondas adicionales, comprueba cada candidata contra el original y conserva la mejor que también mejore frente a la candidata líder, si existe.

```text
python "<directorio-de-la-skill>/scripts/compare_skill_results.py" cases.json baseline.json candidate.json
```

El comando emite JSON con el conteo de aciertos, las regresiones por caso y criterio, los fallos críticos y `accepted`. Devuelve 0 si acepta la candidata, 1 si la evaluación completa la rechaza y 2 si los datos son inválidos o incompletos. Guarda el resultado junto a la versión exacta que se evaluó. La mejora exige más aciertos totales, como mínimo el mismo número de aciertos por cada par caso–criterio y todos los criterios críticos aprobados en cada repetición. Informa también las sesiones usadas y la longitud de cada variante, aunque el comparador no las mida.

7. Entrega el informe y la candidata para decisión humana. Aplica la candidata cuando el usuario lo autorice. Si la versión instalada cambió durante el Run, vuelve a medir con la versión vigente antes de proponer su reemplazo.

## Formato de entrada

`cases.json` incluye las repeticiones y un criterio verificable por entrada. Los campos narrativos disponibles para el Run pueden acompañar estos campos.

```json
{
  "repeats": 1,
  "cases": [
    {
      "id": "fecha-ausente",
      "prompt": "Resume una nota sin fecha.",
      "criteria": [
        {"id": "no-inventa-fecha", "description": "Omite fechas ausentes en el insumo.", "critical": true}
      ]
    }
  ]
}
```

Tanto `baseline.json` como `candidate.json` incluyen un juicio por cada combinación de caso, criterio y repetición. Las repeticiones comienzan en 1.

```json
{
  "judgments": [
    {"case": "fecha-ausente", "criterion": "no-inventa-fecha", "repeat": 1, "passed": true,
     "evidence": "El resumen identifica la acción y omite la fecha."}
  ]
}
```
